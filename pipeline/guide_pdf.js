// Print each pack's Parent-Guide.html to Parent-Guide.pdf with headless Chromium.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const packs = path.resolve(__dirname, '..', 'build', 'packs');
  const browser = await chromium.launch();
  for (const slug of fs.readdirSync(packs)) {
    const src = path.join(packs, slug, 'Parent-Guide.html');
    if (!fs.existsSync(src)) continue;
    const page = await browser.newPage();
    await page.goto('file://' + src);
    await page.pdf({ path: path.join(packs, slug, 'Parent-Guide.pdf'), format: 'A4', printBackground: true });
    await page.close();
    fs.unlinkSync(src);
    console.log('pdf', slug);
  }
  await browser.close();
})();
