import ky from "ky";

let baseUrl = "http://localhost:8000";

export function setBaseUrl(url) {
  baseUrl = url;
}

function getApi() {
  return ky.create({ prefixUrl: `${baseUrl}/api`, timeout: 10000 });
}

export const simApi = {
  start: (endSoc = null, routine = "PFlow") =>
    getApi().post("sim/start", { json: { end_soc: endSoc, routine } }).json(),

  pause: () => getApi().post("sim/pause").json(),

  continue: () => getApi().post("sim/continue").json(),

  abort: () => getApi().post("sim/abort").json(),

  runTo: (seconds) =>
    getApi().post("sim/run-to", { json: { seconds } }).json(),

  getStatus: () => getApi().get("sim/status").json(),
};

export const deviceApi = {
  openGen: (key) => getApi().post(`devices/gen/${key}/open`).json(),
  closeGen: (key) => getApi().post(`devices/gen/${key}/close`).json(),
  setGenPower: (key, mw) =>
    getApi().post(`devices/gen/${key}/power`, { json: { mw } }).json(),
  enableAgc: (key) => getApi().post(`devices/gen/${key}/agc/enable`).json(),
  disableAgc: (key) => getApi().post(`devices/gen/${key}/agc/disable`).json(),

  openLoad: (key) => getApi().post(`devices/load/${key}/open`).json(),
  closeLoad: (key) => getApi().post(`devices/load/${key}/close`).json(),
  setLoadPower: (key, mw) =>
    getApi().post(`devices/load/${key}/power`, { json: { mw } }).json(),
  setLoadReactive: (key, mvar) =>
    getApi().post(`devices/load/${key}/reactive`, { json: { mvar } }).json(),

  openShunt: (key) => getApi().post(`devices/shunt/${key}/open`).json(),
  closeShunt: (key) => getApi().post(`devices/shunt/${key}/close`).json(),

  openBranch: (key) => getApi().post(`devices/branch/${key}/open`).json(),
  closeBranch: (key) => getApi().post(`devices/branch/${key}/close`).json(),
};

export const caseApi = {
  getCase: () => getApi().get("case").json(),
  getDevices: (type) => getApi().get(`case/devices/${type}`).json(),
};

export const historyApi = {
  getTicks: (simId, fromSoc, toSoc, limit = 1000) =>
    getApi()
      .get("history/ticks", {
        searchParams: {
          sim_id: simId,
          ...(fromSoc != null && { from_soc: fromSoc }),
          ...(toSoc != null && { to_soc: toSoc }),
          limit,
        },
      })
      .json(),

  getTickDevices: (tickId, deviceType) =>
    getApi()
      .get(`history/ticks/${tickId}/devices`, {
        searchParams: deviceType ? { device_type: deviceType } : {},
      })
      .json(),

  getActions: (simId, limit = 500) =>
    getApi()
      .get("history/actions", { searchParams: { sim_id: simId, limit } })
      .json(),

  getSimulations: () => getApi().get("history/simulations").json(),
};
