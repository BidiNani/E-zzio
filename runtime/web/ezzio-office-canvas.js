/**
 * E-ZZIO V9.4 — 2.5D TACTICAL LIVING OFFICE CANVAS RENDERER
 * High-performance 60FPS procedural renderer with dynamic lighting,
 * path-driven character sprites, ambient monitors, and camera control.
 */

(function(window) {
  'use strict';

  class OfficeCanvas {
    constructor(canvasId, options = {}) {
      this.canvas = document.getElementById(canvasId);
      if (!this.canvas) throw new Error(`Canvas #${canvasId} not found`);
      this.ctx = this.canvas.getContext('2d');
      this.options = options;

      this.tileSize = 32; // Pixels par tuile
      this.map = null;
      this.agents = new Map(); // agentId -> AgentMotion
      this.selectedAgentId = null;
      this.hoveredAgentId = null;
      this.hoveredRoomKey = null;

      // Caméra
      this.camera = {
        x: 18 * this.tileSize,
        y: 12 * this.tileSize,
        zoom: 1.0,
        targetX: 18 * this.tileSize,
        targetY: 12 * this.tileSize,
        targetZoom: 1.0,
        isDragging: false,
        lastMouseX: 0,
        lastMouseY: 0,
        followAgentId: null
      };

      // Télémétrie & Performance
      this.fps = 60;
      this.lastFrameTime = performance.now();
      this.frameCount = 0;
      this.fpsTimer = performance.now();
      this.renderDurationMs = 0;
      this.reducedMotion = false;
      this.observerMode = false;
      this.observerTimer = 0;

      this.initEvents();
      this.resize();
      window.addEventListener('resize', () => this.resize());
    }

    resize() {
      const rect = this.canvas.parentElement.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      this.canvas.width = rect.width * dpr;
      this.canvas.height = rect.height * dpr;
      this.canvas.style.width = `${rect.width}px`;
      this.canvas.style.height = `${rect.height}px`;
      this.ctx.scale(dpr, dpr);
      this.viewportWidth = rect.width;
      this.viewportHeight = rect.height;
    }

    initEvents() {
      // Pan souris
      this.canvas.addEventListener('mousedown', (e) => {
        this.camera.isDragging = true;
        this.camera.lastMouseX = e.clientX;
        this.camera.lastMouseY = e.clientY;
        this.camera.followAgentId = null; // Désactiver l'auto-follow au clic manuel
      });

      window.addEventListener('mousemove', (e) => {
        if (this.camera.isDragging) {
          const dx = (e.clientX - this.camera.lastMouseX) / this.camera.zoom;
          const dy = (e.clientY - this.camera.lastMouseY) / this.camera.zoom;
          this.camera.targetX -= dx;
          this.camera.targetY -= dy;
          this.camera.lastMouseX = e.clientX;
          this.camera.lastMouseY = e.clientY;
        } else {
          this.handleMouseMove(e);
        }
      });

      window.addEventListener('mouseup', () => {
        this.camera.isDragging = false;
      });

      // Zoom molette
      this.canvas.addEventListener('wheel', (e) => {
        e.preventDefault();
        const factor = e.deltaY < 0 ? 1.12 : 0.89;
        this.camera.targetZoom = Math.max(0.55, Math.min(2.4, this.camera.targetZoom * factor));
      }, { passive: false });

      // Clic de sélection
      this.canvas.addEventListener('click', (e) => {
        const worldPos = this.screenToWorld(e.clientX, e.clientY);
        let clickedAgent = null;

        for (const [id, agent] of this.agents.entries()) {
          const ax = agent.x * this.tileSize;
          const ay = agent.y * this.tileSize;
          if (Math.hypot(worldPos.x - ax, worldPos.y - ay) < this.tileSize * 1.1) {
            clickedAgent = id;
            break;
          }
        }

        if (clickedAgent) {
          this.selectAgent(clickedAgent);
        } else {
          // Vérifier si une pièce a été cliquée
          if (this.map && this.map.rooms) {
            for (const [key, room] of Object.entries(this.map.rooms)) {
              const rx = room.x * this.tileSize;
              const ry = room.y * this.tileSize;
              const rw = room.w * this.tileSize;
              const rh = room.h * this.tileSize;
              if (worldPos.x >= rx && worldPos.x <= rx + rw && worldPos.y >= ry && worldPos.y <= ry + rh) {
                this.focusRoom(key);
                break;
              }
            }
          }
        }
      });
    }

    screenToWorld(screenX, screenY) {
      const rect = this.canvas.getBoundingClientRect();
      const cx = screenX - rect.left;
      const cy = screenY - rect.top;
      const wx = (cx - this.viewportWidth / 2) / this.camera.zoom + this.camera.x;
      const wy = (cy - this.viewportHeight / 2) / this.camera.zoom + this.camera.y;
      return { x: wx, y: wy };
    }

    handleMouseMove(e) {
      const worldPos = this.screenToWorld(e.clientX, e.clientY);
      let found = null;

      for (const [id, agent] of this.agents.entries()) {
        const ax = agent.x * this.tileSize;
        const ay = agent.y * this.tileSize;
        if (Math.hypot(worldPos.x - ax, worldPos.y - ay) < this.tileSize * 1.1) {
          found = id;
          break;
        }
      }
      this.hoveredAgentId = found;
      this.canvas.style.cursor = found ? 'pointer' : 'default';
    }

    selectAgent(agentId) {
      this.selectedAgentId = agentId;
      this.camera.followAgentId = agentId;
      if (window.openAgentDrawer) {
        window.openAgentDrawer(agentId);
      }
    }

    focusRoom(roomKey) {
      if (!this.map || !this.map.rooms || !this.map.rooms[roomKey]) return;
      const room = this.map.rooms[roomKey];
      this.camera.targetX = (room.x + room.w / 2) * this.tileSize;
      this.camera.targetY = (room.y + room.h / 2) * this.tileSize;
      this.camera.targetZoom = 1.35;
      this.camera.followAgentId = null;
    }

    setMap(mapData) {
      this.map = mapData;
    }

    syncBackendAgents(backendAgents) {
      if (!backendAgents) return;

      for (const bAgent of backendAgents) {
        let motion = this.agents.get(bAgent.agent_id);
        if (!motion) {
          motion = new window.EzzioMotion.AgentMotion(
            bAgent.agent_id,
            bAgent.x || 18,
            bAgent.y || 12,
            bAgent.room
          );
          this.agents.set(bAgent.agent_id, motion);
        }

        // Mettre à jour les métadonnées
        motion.status = bAgent.status;
        motion.currentAction = bAgent.current_action;
        motion.model = bAgent.model;
        motion.provider = bAgent.provider;
        motion.progress = bAgent.progress;
        motion.bubble = bAgent.bubble;
        motion.activeTool = (bAgent.tools && bAgent.tools[0]) || '';
        motion.collaboratorId = bAgent.collaborator_id;

        // Synchroniser le mouvement si destination assignée
        if (bAgent.target_x !== undefined && bAgent.target_y !== undefined && (bAgent.target_x !== null)) {
          motion.setDestination(bAgent.target_x, bAgent.target_y, bAgent.animation_state);
        } else if (bAgent.x !== undefined && bAgent.y !== undefined && !motion.isMoving) {
          // Si l'agent est loin de la position cible du serveur, déclencher le déplacement
          if (Math.hypot(motion.x - bAgent.x, motion.y - bAgent.y) > 0.6) {
            motion.setDestination(bAgent.x, bAgent.y, bAgent.animation_state);
          }
        }
      }
    }

    update(deltaTime) {
      // 1. Suivi de l'agent ou de la cible par la caméra
      if (this.camera.followAgentId && this.agents.has(this.camera.followAgentId)) {
        const ag = this.agents.get(this.camera.followAgentId);
        this.camera.targetX = ag.x * this.tileSize;
        this.camera.targetY = ag.y * this.tileSize;
      } else if (this.observerMode) {
        // En mode observateur : switcher automatiquement toutes les 6 secondes sur un agent actif
        this.observerTimer += deltaTime;
        if (this.observerTimer > 6.0) {
          this.observerTimer = 0;
          const activeList = Array.from(this.agents.values()).filter(a => a.status === 'WORKING' || a.status === 'WAITING_APPROVAL');
          if (activeList.length > 0) {
            const nextAgent = activeList[Math.floor(Math.random() * activeList.length)];
            this.camera.followAgentId = nextAgent.agentId;
          }
        }
      }

      // 2. Interpolation caméra
      const lerpFactor = this.reducedMotion ? 1.0 : Math.min(1.0, deltaTime * 5.0);
      this.camera.x += (this.camera.targetX - this.camera.x) * lerpFactor;
      this.camera.y += (this.camera.targetY - this.camera.y) * lerpFactor;
      this.camera.zoom += (this.camera.targetZoom - this.camera.zoom) * lerpFactor;

      // 3. Mise à jour de tous les agents
      const agentList = Array.from(this.agents.values());
      for (const agent of agentList) {
        agent.update(deltaTime, agentList);
      }
    }

    render() {
      const startTime = performance.now();
      const ctx = this.ctx;
      const w = this.viewportWidth;
      const h = this.viewportHeight;

      // Fond cyber sombre
      ctx.fillStyle = '#08090C';
      ctx.fillRect(0, 0, w, h);

      ctx.save();
      // Appliquer la transformation caméra
      ctx.translate(w / 2, h / 2);
      ctx.scale(this.camera.zoom, this.camera.zoom);
      ctx.translate(-this.camera.x, -this.camera.y);

      // A. Grille d'arrière-plan et couloirs
      this.renderWorldGrid(ctx);

      // B. Rendu des 8 pièces (sols, murs 2.5D, bureaux, baies serveurs)
      if (this.map && this.map.rooms) {
        for (const [key, room] of Object.entries(this.map.rooms)) {
          this.renderRoom(ctx, key, room);
        }
      }

      // C. Faisceaux de collaboration entre agents
      this.renderCollaborationBeams(ctx);

      // D. Rendu de tous les agents (triés par Y pour profondeur 2.5D correcte)
      const sortedAgents = Array.from(this.agents.values()).sort((a, b) => a.y - b.y);
      for (const agent of sortedAgents) {
        this.renderAgent(ctx, agent);
      }

      ctx.restore();

      // Mesure des performances
      this.renderDurationMs = performance.now() - startTime;
      this.frameCount++;
      const now = performance.now();
      if (now - this.fpsTimer >= 1000) {
        this.fps = Math.round((this.frameCount * 1000) / (now - this.fpsTimer));
        this.frameCount = 0;
        this.fpsTimer = now;
        const fpsEl = document.getElementById('canvas-fps');
        if (fpsEl) fpsEl.textContent = `${this.fps} FPS · ${this.renderDurationMs.toFixed(1)}ms`;
      }
    }

    renderWorldGrid(ctx) {
      const ts = this.tileSize;
      const maxW = 36 * ts;
      const maxH = 24 * ts;

      // Lignes de quadrillage tactique légères
      ctx.strokeStyle = '#12161F';
      ctx.lineWidth = 1;
      for (let x = 0; x <= maxW; x += ts) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, maxH);
        ctx.stroke();
      }
      for (let y = 0; y <= maxH; y += ts) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(maxW, y);
        ctx.stroke();
      }

      // Sol des couloirs centraux
      ctx.fillStyle = '#0D1117';
      ctx.fillRect(17 * ts, 1 * ts, 2 * ts, 22 * ts); // Nord-Sud
      ctx.fillRect(10 * ts, 4 * ts, 16 * ts, 1 * ts); // Est-Ouest haut
      ctx.fillRect(10 * ts, 12 * ts, 16 * ts, 1 * ts); // Est-Ouest milieu
      ctx.fillRect(10 * ts, 19 * ts, 16 * ts, 1 * ts); // Est-Ouest bas
    }

    renderRoom(ctx, key, room) {
      const ts = this.tileSize;
      const rx = room.x * ts;
      const ry = room.y * ts;
      const rw = room.w * ts;
      const rh = room.h * ts;

      const isHovered = this.hoveredRoomKey === key;

      // Sol de la pièce
      ctx.fillStyle = '#10131A';
      ctx.fillRect(rx, ry, rw, rh);

      // Bordure & Halo lumineux de la zone
      ctx.strokeStyle = isHovered ? '#60A5FA' : room.color || '#334155';
      ctx.lineWidth = isHovered ? 2.5 : 1.5;
      ctx.strokeRect(rx, ry, rw, rh);

      // Bannière de titre de la pièce avec icône
      ctx.fillStyle = room.color || '#3B82F6';
      ctx.font = 'bold 10px "Fira Code", monospace';
      ctx.fillText(`${room.icon} ${room.name}`, rx + 8, ry + 16);

      // Bureau physique 2.5D
      if (room.desk) {
        this.renderDesk(ctx, room.desk.x * ts, room.desk.y * ts, room.color);
      }
      if (room.subdesk) {
        this.renderDesk(ctx, room.subdesk.x * ts, room.subdesk.y * ts, '#10B981');
      }

      // Baies serveurs dans Command Center et Security Vault
      if (key === 'command_center' || key === 'security_vault') {
        this.renderServerRack(ctx, (room.x + 1.5) * ts, (room.y + 2.5) * ts, room.color);
      }
    }

    renderDesk(ctx, x, y, accentColor) {
      // Plateau du bureau
      ctx.fillStyle = '#1E232D';
      ctx.fillRect(x - 18, y - 10, 36, 20);
      ctx.strokeStyle = '#2D3748';
      ctx.lineWidth = 1;
      ctx.strokeRect(x - 18, y - 10, 36, 20);

      // Moniteur principal
      ctx.fillStyle = '#0A0C10';
      ctx.fillRect(x - 10, y - 8, 20, 10);
      ctx.fillStyle = accentColor || '#3B82F6';
      ctx.fillRect(x - 8, y - 6, 16, 6);

      // Halo de l'écran sur le bureau
      const grad = ctx.createRadialGradient(x, y - 3, 2, x, y - 3, 14);
      grad.addColorStop(0, `${accentColor || '#3B82F6'}55`);
      grad.addColorStop(1, 'transparent');
      ctx.fillStyle = grad;
      ctx.fillRect(x - 18, y - 10, 36, 20);
    }

    renderServerRack(ctx, x, y, ledColor) {
      ctx.fillStyle = '#141820';
      ctx.fillRect(x, y, 16, 28);
      ctx.strokeStyle = '#252D3D';
      ctx.strokeRect(x, y, 16, 28);

      // LEDs clignotantes
      const time = performance.now() * 0.003;
      for (let i = 0; i < 4; i++) {
        const blink = Math.sin(time + i * 1.5) > 0;
        ctx.fillStyle = blink ? (ledColor || '#10B981') : '#1E293B';
        ctx.fillRect(x + 3, y + 4 + i * 6, 4, 3);
        ctx.fillStyle = blink ? '#38BDF8' : '#1E293B';
        ctx.fillRect(x + 9, y + 4 + i * 6, 4, 3);
      }
    }

    renderCollaborationBeams(ctx) {
      ctx.save();
      for (const agent of this.agents.values()) {
        if (agent.collaboratorId && this.agents.has(agent.collaboratorId)) {
          const other = this.agents.get(agent.collaboratorId);
          // Dessiner le faisceau de données lumineux
          const time = performance.now() * 0.005;
          ctx.strokeStyle = '#38BDF8';
          ctx.lineWidth = 1.5;
          ctx.setLineDash([4, 4]);
          ctx.lineDashOffset = -time * 20;
          ctx.beginPath();
          ctx.moveTo(agent.x * this.tileSize, agent.y * this.tileSize);
          ctx.lineTo(other.x * this.tileSize, other.y * this.tileSize);
          ctx.stroke();
        }
      }
      ctx.restore();
    }

    renderAgent(ctx, agent) {
      const ts = this.tileSize;
      const px = agent.x * ts;
      const py = agent.y * ts;

      const isSelected = this.selectedAgentId === agent.agentId;
      const isHovered = this.hoveredAgentId === agent.agentId;

      ctx.save();
      ctx.translate(px, py);

      // 1. Aura de statut au sol (Ombre / Anneau)
      let auraColor = '#3B82F6';
      if (agent.status === 'WAITING_APPROVAL') auraColor = '#F59E0B';
      else if (agent.status === 'ERROR') auraColor = '#EF4444';
      else if (agent.status === 'DONE') auraColor = '#10B981';

      ctx.beginPath();
      ctx.ellipse(0, 8, 12, 6, 0, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(0, 0, 0, 0.45)';
      ctx.fill();

      // Anneau lumineux si sélectionné ou en alerte
      if (isSelected || isHovered || agent.status === 'WAITING_APPROVAL') {
        ctx.beginPath();
        ctx.ellipse(0, 8, 14, 7, 0, 0, Math.PI * 2);
        ctx.strokeStyle = auraColor;
        ctx.lineWidth = isSelected ? 2.5 : 1.5;
        ctx.stroke();
      }

      // 2. Corps du sprite agent 2.5D (Pixel-Tactical Vectoriel)
      const walkBob = agent.isMoving ? Math.sin(agent.walkProgress) * 2.5 : 0;

      ctx.translate(0, walkBob);

      // Base / Tunique tactique
      ctx.fillStyle = agent.isMaster ? '#D97706' : (agent.status === 'ERROR' ? '#450A0A' : '#1E293B');
      ctx.fillRect(-7, -4, 14, 12);

      // Tête / Visage
      ctx.fillStyle = '#E2E8F0';
      ctx.fillRect(-5, -12, 10, 8);

      // Visière / Regard selon l'orientation
      ctx.fillStyle = auraColor;
      if (agent.heading === 'DOWN') {
        ctx.fillRect(-4, -9, 8, 3);
      } else if (agent.heading === 'UP') {
        ctx.fillStyle = '#64748B';
        ctx.fillRect(-3, -11, 6, 2); // Arrière de tête
      } else if (agent.heading === 'LEFT') {
        ctx.fillRect(-5, -9, 4, 3);
      } else if (agent.heading === 'RIGHT') {
        ctx.fillRect(1, -9, 4, 3);
      }

      // Accessoire spécifique par agent
      if (agent.isMaster) {
        // Couronne / Diadème royal doré
        ctx.fillStyle = '#FBBF24';
        ctx.fillRect(-6, -15, 12, 3);
        ctx.fillRect(-4, -17, 2, 2);
        ctx.fillRect(2, -17, 2, 2);
      } else if (agent.agentId === 'hermes_executor') {
        // Antennes / Ailes d'Hermès
        ctx.fillStyle = '#38BDF8';
        ctx.fillRect(-8, -13, 2, 4);
        ctx.fillRect(6, -13, 2, 4);
      } else if (agent.agentId === 'antigravity_agent') {
        // Cadenas de quota
        ctx.fillStyle = '#F59E0B';
        ctx.fillText('🔒', -4, -14);
      }

      // Animation WORK : étincelles / frappe clavier
      if (agent.animationState === 'WORK' && !agent.isMoving) {
        const spark = Math.sin(performance.now() * 0.01) > 0.3;
        if (spark) {
          ctx.fillStyle = '#38BDF8';
          ctx.fillRect(-3, 6, 2, 2);
          ctx.fillRect(2, 6, 2, 2);
        }
      }

      // 3. Bulle contextuelle d'activité au-dessus de l'agent
      if (agent.currentAction && (isHovered || isSelected || agent.status === 'WAITING_APPROVAL')) {
        const text = agent.status === 'WAITING_APPROVAL' ? '⚠️ REQUIRE_HUMAN' : agent.currentAction.substring(0, 32);
        ctx.font = 'bold 9px "Fira Code", monospace';
        const tw = ctx.measureText(text).width;

        ctx.fillStyle = 'rgba(8, 9, 12, 0.9)';
        ctx.strokeStyle = auraColor;
        ctx.lineWidth = 1;
        ctx.fillRect(-tw / 2 - 5, -28, tw + 10, 14);
        ctx.strokeRect(-tw / 2 - 5, -28, tw + 10, 14);

        ctx.fillStyle = '#F8FAFC';
        ctx.fillText(text, -tw / 2, -18);
      }

      ctx.restore();
    }
  }

  window.OfficeCanvas = OfficeCanvas;

})(window);
