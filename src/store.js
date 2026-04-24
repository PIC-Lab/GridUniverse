import Vue from "vue";
import Vuex from "vuex";
import notificationSystem from "./assets/notificationsettings";

Vue.use(Vuex);

export default new Vuex.Store({
  state: {
    username: "",
    page: "Home",
    notificationSystem,
    badge: 0,
    badgelist: [],
    badgeShow: false,
    notMuted: true,
    isAdmin: false,
    area: null,
    loginInfo: {},
    serverUrl: "http://localhost:8000",
    wsConnected: false,

    // Simulation state (from WebSocket tick)
    simState: null,

    // Static case data (from GET /api/case)
    caseData: null,

    // Map data (computed from caseData)
    subData: [],
    lineData: [],
    subDetail: {},

    // Accumulated time-series (from ticks)
    areaLoad: [],
    busVoltage: [],

    // Report data
    report: {
      name: null,
      user: [],
      data: [],
      score: [],
      violate: [],
      comment: null,
    },

    // UI state
    showTour: true,
    ready4start: false,
    simOver: 0,
    startToggler: false,
    query: 0,

    // Legacy compat: selected entities
    selectedShunts: [],
    selectedGens: [],
    selectedLoads: [],

    // Legacy compat: cost accumulation
    totalCost: 0,
    totalMWh: 0,
    unitTimeCost: null,
    schedule: null,
    alarm: [],

    // Other area data (substations/branches outside the selected area)
    otherArea: {
      Substation: [],
      Branch: [],
    },
  },
  getters: {
    page(state) {
      return state.page;
    },
    getSimState(state) {
      return state.simState;
    },
    getCaseData(state) {
      return state.caseData;
    },
    getCurrentTime(state) {
      return state.simState ? state.simState.soc : null;
    },
    getStatus(state) {
      return state.simState ? state.simState.status : "offline";
    },
    getSimOver(state) {
      return state.simOver;
    },
    getAreaData(state) {
      return state.simState ? state.simState.area : null;
    },
    getGenData(state) {
      if (!state.simState || !state.caseData) return [];
      const gens = state.caseData.content.Gen;
      const simGens = state.simState.gen;
      return Object.keys(gens).map((key) => {
        const staticData = gens[key];
        const liveData = simGens[key] || {};
        return {
          key: key,
          name: key,
          value: _getGenCoordinates(state.caseData, key),
          MWMax: staticData["Single.MW Max Limit"],
          MWMin: staticData["Single.MW Min Limit"],
          MWSetpoint: liveData.mw_setpoint || staticData["Single.MW Setpoint"] || 0,
          VpuSetpoint: liveData.vpu_setpoint || staticData["Single.Voltage Setpoint"] || 1,
          MW: liveData.mw || 0,
          Mvar: liveData.mvar || 0,
          Status: liveData.status != null ? liveData.status : 1,
          vStatus: liveData.status != null ? liveData.status === 1 : true,
          OperationCost: staticData["OperationCost"],
          MarginalCost: staticData["MarginalCostCoefficients"]
            ? staticData["MarginalCostCoefficients"][0]
            : 0,
          MarginalCostCoefficients: staticData["MarginalCostCoefficients"] || [0, 0],
          AGC: liveData.agc_status === 1,
          id: staticData["String.ID"],
        };
      });
    },
    getBranchData(state) {
      if (!state.simState) return [];
      return Object.entries(state.simState.branch || {}).map(([key, val]) => ({
        key,
        ...val,
      }));
    },
    getTransformerData(state) {
      if (!state.simState) return [];
      return Object.entries(state.simState.transformer || {}).map(([key, val]) => ({
        key,
        ...val,
      }));
    },
    getRiskBuses(state) {
      return state.simState ? state.simState.risk.buses : [];
    },
    getRiskBranches(state) {
      return state.simState ? state.simState.risk.branches : [];
    },
    getRIndex(state) {
      return state.simState ? state.simState.risk.risk_index : 100;
    },
    getTotalCost(state) {
      return state.simState ? state.simState.area.total_cost || 0 : 0;
    },
    getTotalMWh(state) {
      return state.simState ? state.simState.area.total_mwh || 0 : 0;
    },
    getSubData(state) {
      if (!state.caseData) return [];
      const subs = state.caseData.content.Substation || {};
      return Object.entries(subs).map(([id, data]) => ({
        id,
        name: data["String.Name"],
        value: [data["Double.Latitude"], data["Double.Longitude"]],
        attributes: { Gen: false, Shunt: false },
        bus: [],
      }));
    },
    getLineData(state) {
      if (!state.caseData) return [];
      const branches = state.caseData.content.Branch || {};
      const subs = state.caseData.content.Substation || {};
      const buses = state.caseData.content.Bus || {};
      return Object.entries(branches).map(([key, data]) => {
        const fromId = data["Int.From Bus Number"];
        const toId = data["Int.To Bus Number"];
        const fromSub = buses[String(fromId)]
          ? String(buses[String(fromId)]["Int.Sub Number"])
          : "";
        const toSub = buses[String(toId)]
          ? String(buses[String(toId)]["Int.Sub Number"])
          : "";
        const fromCoord = subs[fromSub]
          ? [subs[fromSub]["Double.Latitude"], subs[fromSub]["Double.Longitude"]]
          : [0, 0];
        const toCoord = subs[toSub]
          ? [subs[toSub]["Double.Latitude"], subs[toSub]["Double.Longitude"]]
          : [0, 0];
        return {
          id: key,
          name: (subs[fromSub]?.["String.Name"] || "").split("_")[0] +
            "-" +
            (subs[toSub]?.["String.Name"] || "").split("_")[0],
          coords: [fromCoord, toCoord],
          count: 1,
          attributes: {
            MVALimit: data["Single.MVA Limit"],
            volt: buses[String(fromId)]
              ? buses[String(fromId)]["Single.Nominal kV"]
              : 0,
          },
        };
      });
    },
    getLoadData(state) {
      if (!state.simState || !state.caseData) return [];
      const loads = state.caseData.content.Load;
      const simLoads = state.simState.load;
      return Object.keys(loads).map((key) => {
        const staticData = loads[key];
        const liveData = simLoads[key] || {};
        return {
          key,
          key_cmd: key,
          name: (state.caseData.content.Bus[key.split(",")[0]] || {})["String.Name"] || key,
          value: _getSubCoordinates(state.caseData, key.split(",")[0]),
          MW: liveData.mw || 0,
          Mvar: liveData.mvar || 0,
          Status: liveData.status != null ? liveData.status : 1,
          vStatus: liveData.status != null ? liveData.status === 1 : true,
          FreqHz: state.simState.area ? state.simState.area.frequency : 60,
          id_cmd: staticData["String.ID"],
        };
      });
    },
    getShuntData(state) {
      if (!state.simState || !state.caseData) return [];
      const shunts = state.caseData.content.Shunt;
      const simShunts = state.simState.shunt;
      return Object.keys(shunts).map((key) => {
        const staticData = shunts[key];
        const liveData = simShunts[key] || {};
        return {
          key,
          key_cmd: key,
          name: (state.caseData.content.Bus[key.split(",")[0]] || {})["String.Name"] || key,
          value: _getSubCoordinates(state.caseData, key.split(",")[0]),
          Mvar: liveData.mvar || 0,
          Status: liveData.status != null ? liveData.status : 1,
          vStatus: liveData.status != null ? liveData.status === 1 : true,
          FreqHz: state.simState.area ? state.simState.area.frequency : 60,
          id_cmd: staticData["String.ID"],
        };
      });
    },
    getClockTime(state) {
      if (!state.simState) return null;
      var date = new Date(state.simState.soc * 1000);
      var h = date.getHours();
      var m = date.getMinutes();
      var s = date.getSeconds();
      if (h == 0) h = 12;
      m = (60 * h + m) % 24;
      h = (h < 10) ? "0" + h : h;
      m = (m < 10) ? "0" + m : m;
      s = (s < 10) ? "0" + s : s;
      return m + ":" + s + ":00";
    },
    getGenStat(state) {
      if (!state.caseData || !state.simState) return [0, 0];
      const gens = state.caseData.content.Gen || {};
      const simGens = state.simState.gen || {};
      let totalCapacity = 0;
      let offlineCapacity = 0;
      for (const [key, data] of Object.entries(gens)) {
        const mwMax = data["Single.MW Max Limit"];
        if (mwMax === 0) continue;
        totalCapacity += mwMax;
        const live = simGens[key];
        if (live && live.status === 0) {
          offlineCapacity += mwMax;
        }
      }
      const onlineCapacity = Math.abs(
        Math.round(totalCapacity - offlineCapacity - (state.simState.area.load_mw || 0))
      );
      return [onlineCapacity, offlineCapacity];
    },
    getStartToggler(state) {
      return state.startToggler;
    },
  },
  mutations: {
    setUsername(state, payload) {
      state.username = payload;
    },
    setArea(state, payload) {
      state.area = payload;
    },
    setLoginInfo(state, payload) {
      state.loginInfo = payload;
    },
    setServerUrl(state, payload) {
      state.serverUrl = payload;
    },
    setWsConnected(state, payload) {
      state.wsConnected = payload;
    },
    onAdmin(state) {
      state.isAdmin = true;
    },
    setpage(state, payload) {
      state.page = payload;
    },

    updateSimState(state, payload) {
      state.simState = payload;

      // Accumulate time-series
      if (payload && payload.status === "running") {
        const soc = payload.soc;
        const area = payload.area;
        if (area) {
          state.areaLoad.push([soc, area.load_mw]);

          const busData = payload.bus;
          if (busData) {
            const busKeys = Object.keys(busData);
            const voltageRow = [soc];
            busKeys.forEach((k) => voltageRow.push(busData[k].vpu));
            state.busVoltage.push(voltageRow);
          }
        }
      }

      // Track simulation events
      if (payload && payload.status === "running" && payload.soc === 0) {
        state.startToggler = !state.startToggler;
        state.ready4start = false;
        state.simOver = 0;
        state.areaLoad = [];
        state.busVoltage = [];
        state.report = { name: null, user: [], data: [], score: [], violate: [], comment: null };
        state.totalCost = 0;
        state.totalMWh = 0;
        state.unitTimeCost = null;
      }
      if (payload && payload.status === "finished") {
        state.simOver++;
        state.ready4start = true;
      }
      if (payload && payload.status === "aborted") {
        state.ready4start = true;
      }
    },

    setCaseData(state, payload) {
      state.caseData = payload;

      if (!payload || !payload.content) return;

      const content = payload.content;
      const substations = content.Substation || {};
      const buses = content.Bus || {};
      const gens = content.Gen || {};
      const loads = content.Load || {};
      const shunts = content.Shunt || {};
      const branches = content.Branch || {};

      // Build subData for ECharts Leaflet scatter series
      const subArr = [];
      const subDet = {};

      // Collect buses per substation
      const subBuses = {};
      for (const busKey in buses) {
        const bus = buses[busKey];
        const subNum = String(bus["Int.Sub Number"]);
        if (!subBuses[subNum]) subBuses[subNum] = [];
        subBuses[subNum].push(busKey);
      }

      for (const subKey in substations) {
        const sub = substations[subKey];
        const lat = sub["Double.Latitude"] || 0;
        const lng = sub["Double.Longitude"] || 0;
        if (lat === 0 && lng === 0) continue;

        const busKeys = subBuses[subKey] || [];
        let hasGen = false, hasLoad = false, hasShunt = false;
        for (const bk of busKeys) {
          for (const gk in gens) { if (gens[gk]["Int.Bus Number"] == bk) { hasGen = true; break; } }
          for (const lk in loads) { if (loads[lk]["Int.Bus Number"] == bk) { hasLoad = true; break; } }
          for (const sk in shunts) { if (shunts[sk]["Int.Bus Number"] == bk) { hasShunt = true; break; } }
        }

        subArr.push({
          name: sub["String.Name"] || `Sub ${subKey}`,
          id: subKey,
          value: [lng, lat, 1],
          attributes: { Gen: hasGen, Load: hasLoad, Shunt: hasShunt },
        });

        subDet[subKey] = { Bus: busKeys.map(bk => buses[bk]) };
      }
      state.subData = subArr;
      state.subDetail = subDet;

      // Build lineData for ECharts Leaflet lines series
      const lineArr = [];
      for (const branchKey in branches) {
        const br = branches[branchKey];
        const fromBus = String(br["Int.From Bus Number"]);
        const toBus = String(br["Int.To Bus Number"]);
        const fromSub = String((buses[fromBus] || {})["Int.Sub Number"] || fromBus);
        const toSub = String((buses[toBus] || {})["Int.Sub Number"] || toBus);
        const fromCoord = substations[fromSub];
        const toCoord = substations[toSub];
        if (!fromCoord || !toCoord) continue;
        const lat1 = fromCoord["Double.Latitude"];
        const lng1 = fromCoord["Double.Longitude"];
        const lat2 = toCoord["Double.Latitude"];
        const lng2 = toCoord["Double.Longitude"];
        if ((lat1 === 0 && lng1 === 0) || (lat2 === 0 && lng2 === 0)) continue;

        const fromKV = (buses[fromBus] || {})["Single.Nominal kV"] || 0;
        lineArr.push({
          id: branchKey,
          coords: [[lng1, lat1], [lng2, lat2]],
          attributes: {
            MVA: 0,
            MVFrom: 0,
            MVALimit: br["Single.MVA Limit"] || 999,
            volt: fromKV,
          },
        });
      }
      state.lineData = lineArr;
    },

    setstartready(state) {
      state.ready4start = true;
    },
    flipStartToggler(state) {
      state.startToggler = !state.startToggler;
    },

    // Badge / notification
    updatebadge(state) {
      state.badge++;
      state.badgeShow = true;
    },
    resetbadge(state) {
      state.badge = 0;
      state.badgeShow = false;
    },
    updatebadgelist(state, payload) {
      state.badgelist.unshift(payload);
    },
    resetbadgelist(state) {
      state.badgelist = [];
    },
    toggleMute(state) {
      state.notMuted = !state.notMuted;
    },

    // Report
    addReportUser(state, payload) {
      state.report.user.push(payload);
    },
    addReportData(state, payload) {
      state.report.data.push(payload);
    },
    addReportScore(state, payload) {
      state.report.score.push(payload);
    },
    addReportViolate(state, payload) {
      state.report.violate.push(payload);
    },
    setReportComment(state, payload) {
      state.report.comment = payload;
    },
    setReportName(state, payload) {
      state.report.name = payload;
    },

    // Selected entities
    updateSelectedGens(state, payload) {
      state.selectedGens = payload;
    },
    updateSelectedLoads(state, payload) {
      state.selectedLoads = payload;
    },
    updateSelectedShunts(state, payload) {
      state.selectedShunts = payload;
    },
    updateVBuses(state, payload) {
      state.selectedShunts = payload;
    },

    // Alarm
    triggerAlarm(state, payload) {
      if (!state.alarm.includes(payload)) {
        state.alarm.push(payload);
      }
    },
    dismissAlarm(state, payload) {
      const idx = state.alarm.indexOf(payload);
      if (idx > -1) state.alarm.splice(idx, 1);
    },

    // Violated lines/branches (map interaction)
    addLine(state, payload) {
      state.selectedShunts.push(payload);
    },
    removeLine(state, payload) {
      const idx = state.selectedShunts.indexOf(payload);
      if (idx > -1) state.selectedShunts.splice(idx, 1);
    },
    updateSelectedBranches(state, payload) {
      state.selectedShunts = payload;
    },

    // Cost accumulation
    addCost(state, payload) {
      state.totalCost += payload;
    },
    addMWh(state, payload) {
      state.totalMWh += payload;
    },
    updateUnitTimeCost(state, payload) {
      state.unitTimeCost = payload;
    },
    resetTotalCost(state) {
      state.totalCost = 0;
      state.totalMWh = 0;
      state.unitTimeCost = null;
    },

    // Schedule
    setSchedule(state, payload) {
      state.schedule = payload;
    },

    // UI
    disableTour(state) {
      state.showTour = false;
    },
    query(state) {
      state.query++;
    },
  },
  actions: {},
});

function _getGenCoordinates(caseData, key) {
  const parts = key.split(",");
  const busNum = parts[0];
  return _getSubCoordinates(caseData, busNum);
}

function _getSubCoordinates(caseData, busNum) {
  const buses = caseData.content.Bus;
  const subs = caseData.content.Substation;
  if (!buses || !subs) return [0, 0];
  const bus = buses[busNum];
  if (!bus) return [0, 0];
  const subId = String(bus["Int.Sub Number"]);
  const sub = subs[subId];
  if (!sub) return [0, 0];
  return [sub["Double.Latitude"], sub["Double.Longitude"]];
}
