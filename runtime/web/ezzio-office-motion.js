/**
 * E-ZZIO V9.4 LIVING AI OFFICE — A* PATHFINDING & MOTION ENGINE
 * Pure mathematical / visualization layer. No security or execution authority.
 * Authoritative source of truth remains the E-ZZIO backend.
 */

(function(window) {
  'use strict';

  const GRID_W = 36;
  const GRID_H = 24;

  // 1. Matrice de collision (0 = bloqué/mur, 1 = marchable/couloir/pièce)
  const grid = [];
  for (let y = 0; y < GRID_H; y++) {
    grid[y] = [];
    for (let x = 0; x < GRID_W; x++) {
      grid[y][x] = 0; // Défaut = mur
    }
  }

  // Marquer une zone rectangulaire comme marchable
  function markWalkableRect(x1, y1, w, h) {
    for (let y = y1; y < y1 + h; y++) {
      for (let x = x1; x < x1 + w; x++) {
        if (x >= 0 && x < GRID_W && y >= 0 && y < GRID_H) {
          grid[y][x] = 1;
        }
      }
    }
  }

  // Marquer un obstacle fixe (bureau, serveur)
  function markObstacle(x, y) {
    if (x >= 0 && x < GRID_W && y >= 0 && y < GRID_H) {
      grid[y][x] = 0;
    }
  }

  // Initialisation des sols des 8 pièces (sols praticables à l'intérieur)
  markWalkableRect(2, 2, 8, 5);   // Command Center
  markWalkableRect(14, 2, 8, 5);  // Dev Lab
  markWalkableRect(26, 2, 8, 5);  // Research Room
  markWalkableRect(2, 10, 8, 4);  // Test Lab
  markWalkableRect(13, 10, 10, 4); // Central Hub
  markWalkableRect(26, 10, 8, 4); // Security Vault
  markWalkableRect(2, 17, 8, 5);  // Docs Room
  markWalkableRect(14, 17, 8, 5); // DevOps Dock
  markWalkableRect(26, 17, 8, 5); // Memory Core

  // Couloirs principaux reliant toutes les pièces
  markWalkableRect(17, 1, 2, 22); // Couloir central Nord-Sud
  markWalkableRect(10, 4, 16, 1); // Couloir Est-Ouest haut (portes Command, Hub, Research)
  markWalkableRect(10, 12, 16, 1); // Couloir Est-Ouest milieu (portes Test, Hub, Vault)
  markWalkableRect(10, 19, 16, 1); // Couloir Est-Ouest bas (portes Docs, DevOps, Memory)

  // Portes d'accès des pièces
  const DOORS = [
    { x: 10, y: 4 }, { x: 11, y: 4 },  // Command door
    { x: 17, y: 7 }, { x: 18, y: 7 }, { x: 17, y: 8 }, { x: 18, y: 8 }, // Dev Lab door
    { x: 24, y: 4 }, { x: 25, y: 4 },  // Research door
    { x: 10, y: 12 }, { x: 11, y: 12 }, // Test door
    { x: 24, y: 12 }, { x: 25, y: 12 }, // Security door
    { x: 10, y: 19 }, { x: 11, y: 19 }, // Docs door
    { x: 17, y: 15 }, { x: 18, y: 15 }, { x: 17, y: 16 }, { x: 18, y: 16 }, // DevOps door
    { x: 24, y: 19 }, { x: 25, y: 19 }  // Memory door
  ];
  DOORS.forEach(d => { if (d.x < GRID_W && d.y < GRID_H) grid[d.y][d.x] = 1; });

  // 2. Obstacles intérieurs : Bureaux physiques
  const OBSTACLES = [
    { x: 5, y: 4 },   // Bureau Command
    { x: 16, y: 4 },  // Bureau Coder
    { x: 20, y: 4 },  // Bureau Hermes
    { x: 30, y: 4 },  // Bureau Researcher
    { x: 5, y: 12 },  // Bureau QA
    { x: 30, y: 12 }, // Bureau Security
    { x: 5, y: 19 },  // Bureau Docs
    { x: 18, y: 19 }, // Bureau DevOps
    { x: 30, y: 19 }, // Bureau Memory
    { x: 14, y: 2 }   // Baie Antigravity Standby
  ];
  OBSTACLES.forEach(o => markObstacle(o.x, o.y));

  function isWalkable(x, y) {
    if (x < 0 || x >= GRID_W || y < 0 || y >= GRID_H) return false;
    return grid[Math.floor(y)][Math.floor(x)] === 1;
  }

  // 3. Algorithme A* Déterministe
  function aStar(startX, startY, targetX, targetY) {
    startX = Math.max(0, Math.min(GRID_W - 1, Math.round(startX)));
    startY = Math.max(0, Math.min(GRID_H - 1, Math.round(startY)));
    targetX = Math.max(0, Math.min(GRID_W - 1, Math.round(targetX)));
    targetY = Math.max(0, Math.min(GRID_H - 1, Math.round(targetY)));

    // Si la cible est un obstacle (ex: bureau), trouver le voisin marchable le plus proche
    if (!isWalkable(targetX, targetY)) {
      const candidates = [
        { x: targetX, y: targetY + 1 },
        { x: targetX, y: targetY - 1 },
        { x: targetX + 1, y: targetY },
        { x: targetX - 1, y: targetY }
      ];
      let best = null;
      let minD = Infinity;
      for (const c of candidates) {
        if (isWalkable(c.x, c.y)) {
          const d = Math.hypot(c.x - startX, c.y - startY);
          if (d < minD) { minD = d; best = c; }
        }
      }
      if (best) {
        targetX = best.x;
        targetY = best.y;
      }
    }

    if (startX === targetX && startY === targetY) {
      return [{ x: startX, y: startY }];
    }

    const openSet = [{ x: startX, y: startY, g: 0, f: Math.abs(startX - targetX) + Math.abs(startY - targetY), parent: null }];
    const closed = new Set();

    while (openSet.length > 0) {
      // Trouver le nœud ayant le plus petit f
      let lowestIdx = 0;
      for (let i = 1; i < openSet.length; i++) {
        if (openSet[i].f < openSet[lowestIdx].f) lowestIdx = i;
      }
      const current = openSet.splice(lowestIdx, 1)[0];
      const key = `${current.x},${current.y}`;

      if (current.x === targetX && current.y === targetY) {
        // Reconstruire le chemin
        const path = [];
        let curr = current;
        while (curr) {
          path.push({ x: curr.x, y: curr.y });
          curr = curr.parent;
        }
        path.reverse();
        return path;
      }

      closed.add(key);

      // Voisins orthogonaux
      const neighbors = [
        { x: current.x, y: current.y - 1 },
        { x: current.x, y: current.y + 1 },
        { x: current.x - 1, y: current.y },
        { x: current.x + 1, y: current.y }
      ];

      for (const n of neighbors) {
        if (!isWalkable(n.x, n.y)) continue;
        const nKey = `${n.x},${n.y}`;
        if (closed.has(nKey)) continue;

        const gScore = current.g + 1;
        let existing = openSet.find(o => o.x === n.x && o.y === n.y);

        if (!existing) {
          const h = Math.abs(n.x - targetX) + Math.abs(n.y - targetY);
          openSet.push({ x: n.x, y: n.y, g: gScore, f: gScore + h, parent: current });
        } else if (gScore < existing.g) {
          existing.g = gScore;
          existing.f = gScore + (existing.f - existing.g);
          existing.parent = current;
        }
      }
    }

    // Aucun chemin trouvé : retourner position de départ
    return [{ x: startX, y: startY }];
  }

  // 4. Classe AgentMotion : Gère l'interpolation et l'évitement
  class AgentMotion {
    constructor(agentId, initialX, initialY, homeRoom) {
      this.agentId = agentId;
      this.x = initialX;
      this.y = initialY;
      this.targetX = initialX;
      this.targetY = initialY;
      this.homeRoom = homeRoom;
      this.path = [];
      this.pathIndex = 0;
      this.heading = 'DOWN';
      this.animationState = 'IDLE';
      this.speed = 2.4; // Tuiles par seconde
      this.walkProgress = 0;
      this.isMoving = false;
      this.bubble = null;
      this.status = 'IDLE';
      this.currentAction = '';
      this.model = '';
      this.provider = '';
      this.progress = 0;
      this.activeTool = '';
      this.isMaster = agentId === 'master_ezzio';
    }

    setDestination(destX, destY, animState = 'WALK') {
      const targetTileX = Math.round(destX);
      const targetTileY = Math.round(destY);

      if (Math.round(this.x) === targetTileX && Math.round(this.y) === targetTileY) {
        this.isMoving = false;
        this.animationState = animState === 'WALK' ? 'WORK' : animState;
        return;
      }

      this.path = aStar(this.x, this.y, targetTileX, targetTileY);
      this.pathIndex = 0;
      this.isMoving = this.path.length > 1;
      this.targetX = targetTileX;
      this.targetY = targetTileY;
      this.animationState = this.isMoving ? 'WALK' : animState;
    }

    update(deltaTime, allAgents) {
      if (!this.isMoving || this.path.length === 0) {
        return;
      }

      const nextWaypoint = this.path[this.pathIndex];
      if (!nextWaypoint) {
        this.isMoving = false;
        return;
      }

      const dx = nextWaypoint.x - this.x;
      const dy = nextWaypoint.y - this.y;
      const dist = Math.hypot(dx, dy);

      // Calculer l'orientation
      if (Math.abs(dx) > Math.abs(dy)) {
        this.heading = dx > 0 ? 'RIGHT' : 'LEFT';
      } else if (Math.abs(dy) > 0.05) {
        this.heading = dy > 0 ? 'DOWN' : 'UP';
      }

      // Évitement de collision avec les autres agents
      let currentSpeed = this.speed;
      if (allAgents) {
        for (const other of allAgents) {
          if (other.agentId === this.agentId) continue;
          const odx = other.x - this.x;
          const ody = other.y - this.y;
          const oDist = Math.hypot(odx, ody);
          if (oDist < 0.85) {
            // Priorité de passage au Master ou agent plus proche du but
            if (!this.isMaster && other.isMaster) {
              currentSpeed *= 0.2; // Cède le passage
            } else if (this.agentId > other.agentId) {
              currentSpeed *= 0.5; // Décalage pour fluidité
            }
          }
        }
      }

      const step = currentSpeed * deltaTime;
      if (dist <= step) {
        this.x = nextWaypoint.x;
        this.y = nextWaypoint.y;
        this.pathIndex++;

        if (this.pathIndex >= this.path.length) {
          this.isMoving = false;
          this.animationState = this.status === 'WAITING_APPROVAL' ? 'WAIT_APPROVAL' : (this.status === 'WORKING' ? 'WORK' : 'IDLE');
        }
      } else {
        this.x += (dx / dist) * step;
        this.y += (dy / dist) * step;
        this.walkProgress += deltaTime * 8;
      }
    }
  }

  // Exposer les modules globaux
  window.EzzioMotion = {
    GRID_W,
    GRID_H,
    isWalkable,
    aStar,
    AgentMotion,
    DOORS,
    OBSTACLES
  };

})(window);
