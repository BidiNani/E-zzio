# MANIFESTE D'ARCHITECTURE & BASELINE DE SÉCURITÉ CAPCAP V03

**Date de Scellement :** 23 Août 2026  
**Moteur Cible :** Godot Engine 4.7.1 Stable Forward+ / Headless  
**Statut Global :** 51/51 Tests Unitaires PASS | Exit Code Runtime 0 | CERTIFIÉ CONFORME  

---

## 1. Principes Fondamentaux & Invariants d'Architecture

### 1.1 Invariant Absolu : *Zero Mutation on Rejection*
Tout échec lors de l'évaluation `can_execute(game_state) -> [false, reason]` garantit formellement qu'**aucune mutation d'état n'a lieu** :
- $0\text{ AP}$ consommé.
- $0\text{ PV}$ perdu.
- $0\text{ case}$ franchie ou réservée.
- Le snapshot `GameState.serialize()` avant et après rejet est strictement identique au bit près.

### 1.2 Unicité d'Exécution & Anti-Double Dépense
- Chaque instance d'action hérite de `BaseAction` et possède un verrou booléen `is_executed`.
- Une action ne peut être exécutée qu'une seule et unique fois. Toute tentative de réexécution est rejetée immédiatement sans débit de ressources.

---

## 2. Matrice des Contrats Spatiaux & Comportementaux

```text
                               CAPCAP ARCHITECTURE V03
                                          │
    ┌──────────────────┬──────────────────┼──────────────────┬──────────────────┐
    ▼                  ▼                  ▼                  ▼                  ▼
GÉOMÉTRIE 2.5D     TOPOLOGIE & A*      ACTIONS & TOURS    COMBAT & LOS       IA TACTIQUE
(iso_math.gd)      (grid_map.gd)       (actions/)         (combat/)          (ai/)
```

### 2.1 Espace Isométrique & 2.5D (`src/core/iso_math.gd`)
- Losange $64 \times 32\text{ px}$, pas d'élévation $H_{\text{step}} = 16\text{ px}$.
- Projection directe $3\text{D} \to 2\text{D}$ : `grid_to_world(pos, z)`.
- Inversion de plan $2\text{D} \to 2\text{D}$ : `world_to_grid_plane(pos, z)`.
- Raycast volumique 2.5D : sonde du sommet $z_{\text{max}}$ vers le sol $z=0$.
- Tri de profondeur déterministe (Painter's Algorithm) : $\text{depth} = (x + y) \times 100 + z$.

### 2.2 Topologie & Connectivité de Navigation (`src/core/grid_map.gd`)
- Contrat `can_traverse(from_pos, to_pos)` :
  - $\Delta z = 0$ (Plat) : Libre si les deux cellules sont marchables.
  - $\Delta z = 1$ avec `STAIR` ou `RAMP` : Autorisé si aligné avec le vecteur de déplacement.
  - $\Delta z \ge 1$ sans escalier (`CLIFF`) : **Strictement infranchissable** (montée et chute bloquées).
  - *Corner-Cutting Prevention* : Interdiction de franchir en diagonale l'angle d'une falaise ou d'un obstacle.

### 2.3 Système d'Actions & Game State (`src/actions/` & `src/state/`)
- Command Pattern : `ActionQueue` séquentielle FIFO.
- Machine à états : `IDLE`, `MOVING`, `ACTING`, `DISABLED` ($0\text{ AP}$), `BLOCKED`.
- `GameState` sérialisable à $100\%$ avec roundtrip exact (`serialize()` / `deserialize()`).

### 2.4 Système de Combat & Ligne de Vue (`src/combat/`)
- Portée en distance euclidienne de grille 3D : $D = \sqrt{\Delta x^2 + \Delta y^2 + \Delta z^2}$.
- Ligne de vue (LOS) 2.5D discrétisée : masquage garanti si le rayon traverse un obstacle opaque ou une falaise intermédiaire $z_{\text{cell}} \ge z(t) + 0.5$.
- Dégâts déterministes avec bonus de position dominante (*High Ground*) $+2$.

### 2.5 IA Tactique Déterministe (`src/ai/`)
- Perception bornée (rayon $10$ cases + LOS dégagée).
- Évaluation de menace sans composante aléatoire (proximité, PV cibles, altitude).
- Émission d'actions standards (`MoveAction`, `AttackAction`) injectées dans l'`ActionQueue` commune.
- **Zéro passe-droit** : l'IA est soumise aux mêmes règles et contraintes que le joueur humain.

---

## 3. Registre des Tests Qualifiés (51/51 PASS)

| Sous-Système | Tests | Statut |
|---|:---:|:---:|
| **V01 / V02.1 / V02.2 / V02.3** (Caméra, Relief, Formations) | 12 | **100% PASS** |
| **V03.1** (Actions, AP, File, GameState) | 8 | **100% PASS** |
| **V03.2** (Combat, Portée 3D, LOS, Dégâts) | 12 | **100% PASS** |
| **V03.3** (IA Perception, Menace, Décision) | 15 | **100% PASS** |
| **V03.4** (Harnais Adversarial & Robustesse) | 16 | **100% PASS** |
| **Total Global** | **51** | **CERTIFIÉ** |

---
*Ce document sert d'ancre architecturale formelle pour le démarrage des travaux de la phase CAPCAP V04.*
