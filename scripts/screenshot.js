const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 900 });

  const url = process.argv[2] || 'http://localhost:8080';
  const outputFile = process.argv[3] || '/tmp/gridverse-screenshot.png';

  console.log(`Navigating to ${url}...`);
  await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

  // Wait a bit for dynamic content
  await new Promise(r => setTimeout(r, 2000));

  // Take screenshot
  await page.screenshot({ path: outputFile, fullPage: false });
  console.log(`Screenshot saved to ${outputFile}`);

  // Also capture console errors
  page.on('console', msg => {
    if (msg.type() === 'error') console.log(`CONSOLE ERROR: ${msg.text()}`);
  });

  await browser.close();
})();
