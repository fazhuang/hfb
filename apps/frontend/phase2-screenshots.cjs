const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  await page.goto('http://127.0.0.1:5173/prototype', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  await page.screenshot({ path: '/tmp/phase2-sweep-wide.png', fullPage: true });
  console.log('Wide 1600x1000 screenshot saved');

  // 200% zoom
  await page.evaluate(function() { document.body.style.zoom = '200%'; });
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/phase2-sweep-zoom200.png', fullPage: true });
  console.log('200% zoom screenshot saved');

  await page.evaluate(function() { document.body.style.zoom = ''; });
  await browser.close();
  console.log('Done');
})();
