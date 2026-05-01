# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GridUniverse (package name: gridverse) is a power grid simulation and visualization application. It provides a real-time dashboard for monitoring generators, loads, transmission branches, transformers, shunts, and area-level operations in electrical power systems. The app bridges a Vue.js 2 frontend with a Python backend using AMS (Advanced Modeling System) for power flow simulation.

## Commands

```bash
npm install            # Install dependencies
npm run serve          # Dev server (Vue CLI / webpack, default port 8080)
                       # On Node.js v18+: use NODE_OPTIONS=--openssl-legacy-provider
npm run build          # Production build (outputs to dist/)
npm run build-report   # Production build with bundle analysis
```

Backend:
```bash
cd py && pip install -r requirements.txt
python py/server.py --case py/case_ACTIVSg2000.m --port 8000
```

UI testing (Puppeteer):
```bash
node scripts/test-ui.js     # Automated headless test of dashboard + map
```

No test framework is configured. No linter is configured.

## Tech Stack

- **Vue 2.6** + **Vuetify 2.6** (Material Design, always dark theme)
- **Vuex 3** for state management, **Vue Router 3** (history mode)
- **WebSocket** (native) for real-time simulation state push from backend
- **ky** HTTP client for REST API calls
- **Leaflet** for GIS map visualization (pure Leaflet, no ECharts extension)
- **ECharts 5** for charts (bar, pie, area strip — not for maps)
- **FastAPI + uvicorn** Python backend with WebSocket support
- **AMS** (Advanced Modeling System) for power flow simulation (extends ANDES)
- **SQLite** for simulation history persistence
- Build: **Vue CLI 4.5** (webpack 4) is the primary build tool. A `vite.config.js` also exists for Vite-based workflows with `vite-plugin-vue2`.
- Path alias: `@/` and `src/` both resolve to `./src/`

## Architecture

### Data Flow

The Python backend (`py/server.py`) runs AMS power flow simulations and streams structured JSON state to the frontend via WebSocket. REST API handles commands (start/pause/abort, device open/close/setpower) and static data (case data). The Vuex store (`src/store.js`) is the single source of truth — simulation state (`simState`), static case data (`caseData`), and UI state all live there.

### Backend Structure

- `py/server.py` — FastAPI server with REST endpoints + WebSocket `/ws/sim`
- `py/simulator.py` — AMS simulation loop, command handler, state builder
- `py/database.py` — SQLite schema (simulations, ticks, device_states, actions tables)
- `py/case_exporter.py` — Exports static case dictionary from AMS System
- `py/case_ACTIVSg2000.m` — MATPOWER test case (2000 buses, 8 areas)
- `src/assets/2000.json` — Substation coordinates (real Texas lat/lng)

### AMS Dependency

AMS is a separate repository. Now it is already installed, if you don't find it, install it locally before running the backend:
```bash
pip install ams andes>=1.9.3
```

`server.py` also searches common local paths (`~/GitHub/ams`, `~/github/ams`) as fallback. Do not access the local AMS repo directory from this project — treat it as an external dependency.

### REST API Endpoints

```
GET  /api/health                     → { status: "ok" }
GET  /api/case                       → Full case dictionary
POST /api/sim/start                  → { end_soc?, routine? }
POST /api/sim/pause | continue | abort
GET  /api/sim/status
POST /api/devices/{type}/{key}/open|close|power
GET  /api/history/ticks?sim_id=X
GET  /api/history/actions?sim_id=X
```

### WebSocket Messages (Server → Client)

```json
{ "type": "tick", "data": { "soc": 123, "status": "running", "area": {...}, "bus": {...}, "gen": {...}, "load": {...}, "shunt": {...}, "branch": {...}, "transformer": {...}, "risk": {...} } }
{ "type": "event", "data": "The simulation is started @0" }
{ "type": "note", "data": "#Admin just issued Gen OPEN at 4058,20" }
```

### Key State Shape (store.js)

- `simState`: Latest tick data from WebSocket (area aggregates, bus/gen/load/shunt/branch states, risk data)
- `caseData`: Static device dictionary from `GET /api/case` (Substation, Bus, Gen, Load, Shunt, Branch, Transformer)
- `subData` / `lineData`: Map visualization data computed from caseData by `setCaseData` mutation
- `otherArea`: Substation/Branch arrays for areas outside the selected area
- Simulation control: `ready4start`, `simOver`, `startToggler`
- Selected entities: `selectedShunts`, `selectedGens`, `selectedLoads`

### Frontend Services

- `src/services/api.js` — REST client using ky (`simApi`, `deviceApi`, `caseApi`, `historyApi`)
- `src/components/ConnectionManager.vue` — WebSocket client + case data fetcher

### Component Organization

- **`src/views/`**: Route-level views — Home, Login, About, and feature views
- **`src/components/`**: Reusable UI components organized by function:
  - Data tables: `GenTable`, `LoadTable`, `BranchTable`, `ShuntTable`, `TransformerTable` — use `deviceApi` for commands
  - Maps: `puremap` (main interactive map), `OneLine` (dark-themed overview map) — both use pure Leaflet with `L.circleMarker`/`L.polyline`/`L.layerGroup`
  - Charts: `barPlot`, `pie`, `AreaStrip`, `HourlyStrip`, `BusStrip` — use ECharts
  - Dashboard widgets: `Dashboard`, `MWidget`, `MiniStat`
  - Status/monitoring: `Clock`, `AGCBot`, `marquee`
  - Popups/dialogs: `chatpop`, `linepop`, `subpop`, `reportpop`, `startpop`
- **`src/App.vue`**: Root component (renders Login)
- **`src/views/Login.vue`**: Login + dashboard loader (sets `showDash=true` to render Dashboard)
- **`src/components/Dashboard.vue`**: Main dashboard with sidebar nav, renders pages via `<keep-alive><component :is="page"></component></keep-alive>`

### Map Rendering (puremap.vue / OneLine.vue)

Both map components use **pure Leaflet** (not ECharts). Key patterns:
- `L.map()` with `preferCanvas: true` for performance with thousands of features
- Separate `L.layerGroup` for each feature type (substations, lines, open lines, risk lines, other area)
- Substations: `L.circleMarker` colored by type (Gen=#ff5722, Shunt=#8d6e63, default=#283593)
- Lines: `L.polyline` colored by voltage (500=#e53935, 230=#3949ab, 115=#1565c0, 13.8=#7c4dff)
- Simulation updates in `puremap`: open/close tracking, power flow direction, high-risk highlighting
- Tooltips use template literals — never mix single/double quotes with HTML entities in tooltip strings
- Data timing: `$store.watch` on `subData.length` + setTimeout fallbacks at 500ms/2000ms

### Routing

No Vue Router for main navigation. Dashboard uses `store.state.page` + dynamic `<component :is="page">` to switch views (Home, generator, load, shunt, branch, etc.). Pages are cached with `<keep-alive>` — use `activated()`/`deactivated()` lifecycle hooks instead of `mounted()`/`beforeDestroy()` for cached components.

### Production Build

`publicPath` is set to `/GridUniverse/` for GitHub Pages deployment.

### AMS Key Conventions

- Device keys use `"bus_num,model_index"` format (e.g., `"4058,41"` for StaticGen)
- AMS model indices (e.g., `PV_41`, `PQ_37`) are needed for `.set()` calls, not array indices
- `StaticGen` aggregates PV + Slack generators; `PQ` for loads; `Shunt` for shunts
- The MATPOWER case has 8 areas (1-8); substation coordinates come from `2000.json`
