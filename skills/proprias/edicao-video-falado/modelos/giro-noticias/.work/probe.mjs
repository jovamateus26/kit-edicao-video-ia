import puppeteer from 'puppeteer-core';
import { existsSync } from 'node:fs';
// navegador: CHROME=caminho, senão o primeiro Chrome/Chromium/Edge instalado (Linux, Mac ou Windows)
const CHROME = process.env.CHROME || ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium',
  '/usr/bin/chromium-browser', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  `${process.env.PROGRAMFILES}\\Google\\Chrome\\Application\\chrome.exe`,
  `${process.env['PROGRAMFILES(X86)']}\\Google\\Chrome\\Application\\chrome.exe`,
  `${process.env.LOCALAPPDATA}\\Google\\Chrome\\Application\\chrome.exe`,
  `${process.env['PROGRAMFILES(X86)']}\\Microsoft\\Edge\\Application\\msedge.exe`].find((p) => existsSync(p)) || 'google-chrome';
const [url, ...needles] = process.argv.slice(2);
const b = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox'] });
const p = await b.newPage();
await p.setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1');
await p.setViewport({ width: 430, height: 932, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
try { await p.goto(url, { waitUntil: 'networkidle2', timeout: 60000 }); } catch (e) {}
for (let k = 0; k < 25; k++) { await p.evaluate(() => scrollBy(0, 900)); await new Promise(r => setTimeout(r, 200)); }
const out = await p.evaluate((ns) => ns.map(n => {
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let t; const hits = [];
  while ((t = tw.nextNode())) { if (t.textContent.includes(n.slice(0, 12))) { const el = t.parentElement;
    hits.push({ tag: el.tagName, cls: el.className.slice(0, 40), vis: el.checkVisibility ? el.checkVisibility({opacityProperty: true, visibilityProperty: true}) : null,
      rects: el.getClientRects().length, txt: JSON.stringify(t.textContent.slice(0, 90)) }); } }
  return [n, hits.slice(0, 4)];
}), needles);
console.log(JSON.stringify(out, null, 1)); await b.close();
