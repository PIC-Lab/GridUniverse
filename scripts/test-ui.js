const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 900 });

  const consoleErrors = [];
  const consoleWarns = [];
  const allLogs = [];
  page.on('console', msg => {
    allLogs.push(`[${msg.type()}] ${msg.text()}`);
    if (msg.type() === 'error') consoleErrors.push(msg.text());
    if (msg.type() === 'warning') consoleWarns.push(msg.text());
  });
  page.on('pageerror', err => consoleErrors.push('PAGE: ' + err.message));

  console.log('1. Loading page...');
  await page.goto('http://localhost:8080', { waitUntil: 'networkidle2', timeout: 30000 });
  await new Promise(r => setTimeout(r, 2000));

  // Force bypass slideshow and login
  console.log('2. Force-login...');
  await page.evaluate(() => {
    function findLoginComp(vm) {
      if (vm.show !== undefined && vm.showDash !== undefined && vm.model) return vm;
      if (vm.$children) {
        for (const c of vm.$children) {
          const found = findLoginComp(c);
          if (found) return found;
        }
      }
      return null;
    }
    const app = document.querySelector('#app').__vue__;
    const loginComp = findLoginComp(app);
    if (!loginComp) return 'Login component not found';

    loginComp.show = true;
    loginComp.overlay = false;
    loginComp.serverUrl = 'http://localhost:8000';
    loginComp.area = 2;
    loginComp.$store.commit('setServerUrl', 'http://localhost:8000');
    loginComp.$store.commit('setArea', 2);
    loginComp.$store.commit('setUsername', 'Admin');
    loginComp.showDash = true;
    return 'OK';
  });

  console.log('3. Waiting 12s for dashboard + map...');
  await new Promise(r => setTimeout(r, 12000));

  // Print all console logs
  console.log(`\n=== All console logs (${allLogs.length}) ===`);
  allLogs.forEach((l, i) => console.log(`  ${i+1}. ${l.substring(0, 300)}`));

  // Check store state
  const storeState = await page.evaluate(() => {
    const s = document.querySelector('#app').__vue__.$store.state;
    return {
      hasCaseData: !!s.caseData,
      caseDataContentKeys: s.caseData ? Object.keys(s.caseData.content || {}) : [],
      subDataLen: s.subData?.length || 0,
      lineDataLen: s.lineData?.length || 0,
      hasSimState: !!s.simState,
      wsConnected: s.wsConnected,
    };
  });
  console.log('\n=== Vuex state ===');
  console.log(JSON.stringify(storeState, null, 2));

  // Check map
  const mapInfo = await page.evaluate(() => {
    const main = document.getElementById('main');
    return {
      exists: !!main,
      childCount: main ? main.children.length : 0,
      width: main ? main.offsetWidth : 0,
      height: main ? main.offsetHeight : 0,
      hasLeaflet: !!document.querySelector('.leaflet-container'),
    };
  });
  console.log('\n=== Map (#main) ===');
  console.log(JSON.stringify(mapInfo, null, 2));

  // Check if ECharts has data
  const echartsInfo = await page.evaluate(() => {
    try {
      // Access the echarts instance from the puremap component
      const main = document.getElementById('main');
      if (!main || !main.__echarts__) {
        // Try to find echarts instance via _echarts_instance attribute
        const echartsEl = document.querySelector('[_echarts_instance_]');
        if (!echartsEl) return { found: false, reason: 'no echarts element' };
        const instId = echartsEl.getAttribute('_echarts_instance_');
        return { found: true, instanceId: instId };
      }
    } catch(e) {
      return { found: false, error: e.message };
    }

    // Check subData and lineData from store
    const s = document.querySelector('#app').__vue__.$store.state;
    const subSample = s.subData.length > 0 ? s.subData[0] : null;
    const lineSample = s.lineData.length > 0 ? s.lineData[0] : null;
    return {
      subDataLen: s.subData.length,
      lineDataLen: s.lineData.length,
      subSample: subSample,
      lineSample: lineSample,
    };
  });
  console.log('\n=== ECharts / Map Data ===');
  console.log(JSON.stringify(echartsInfo, null, 2));

  await page.screenshot({ path: '/tmp/gridverse-dashboard.png' });
  console.log('\nScreenshot saved to /tmp/gridverse-dashboard.png');

  await browser.close();
})();
