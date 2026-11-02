// Print do topo de cada matéria como aparece no celular (logo + manchete + data), com as caixas das frases a destacar.
// node tops.mjs OUT_DIR -> OUT_DIR/<id>_card.png + cards.json
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import { existsSync } from 'node:fs';
// navegador: CHROME=caminho, senão o primeiro Chrome/Chromium/Edge instalado (Linux, Mac ou Windows)
const CHROME = process.env.CHROME || ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium',
  '/usr/bin/chromium-browser', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  `${process.env.PROGRAMFILES}\\Google\\Chrome\\Application\\chrome.exe`,
  `${process.env['PROGRAMFILES(X86)']}\\Google\\Chrome\\Application\\chrome.exe`,
  `${process.env.LOCALAPPDATA}\\Google\\Chrome\\Application\\chrome.exe`,
  `${process.env['PROGRAMFILES(X86)']}\\Microsoft\\Edge\\Application\\msedge.exe`].find((p) => existsSync(p)) || 'google-chrome';
const OUT = process.argv[2];
const JOBS = [
  { id: 'uol', url: 'https://noticias.uol.com.br/cotidiano/ultimas-noticias/2026/10/21/php-falha-sites.ghtm', hide: 'App UOL', ads: ['.solar-snackbar', 'aside.campaign-container'], end: 'Atualizada em', hl: ['governos a derrubarem sites'] },
  { id: 'olhar', url: 'https://olhardigital.com.br/2026/10/22/seguranca/falhas-criticas-no-php-tiram-sistemas-publicos-do-ar-no-brasil/', end: '22/10/2026 12:24', hl: ['sistemas públicos do ar no Brasil'] },
  { id: 'terra', url: 'https://www.terra.com.br/byte/uma-falha-critica-no-php-coloca-metade-da-internet-em-risco-em-todo-o-mundo,d86b8843b9592761d456ff40b519d813g2wdfcv1.html', ads: ['#header-full-ad-container'], end: '(atualizado às', hl: ['metade da internet em risco', 'O PHP já lançou as versões corrigidas e recomenda a atualização imediata'] },
  { id: 'bbc', url: 'https://www.bbc.com/portuguese/articles/cqzjxp10r901o', ads: ['section.css-13j0x7y'], end: 'tirou sites do ar', hl: ['detectada por IA'] },
];
const CLEAN = `[id*="cookie" i],[class*="cookie" i],[id*="consent" i],[class*="consent" i],[class*="lgpd" i],[id*="onetrust" i],[class*="onetrust" i],
  [id*="didomi" i],[class*="didomi" i],[class*="fc-consent" i] { display:none !important; } html, body { overflow: visible !important; }`;
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox', '--lang=pt-BR'] });
const meta = {};
for (const job of JOBS.filter(j => !process.argv[3] || j.id === process.argv[3])) {
  const page = await browser.newPage();
  await page.setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1');
  await page.setExtraHTTPHeaders({ 'Accept-Language': 'pt-BR,pt;q=0.9' });
  await page.setViewport({ width: 430, height: 932, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
  try { await page.goto(job.url, { waitUntil: 'networkidle2', timeout: 45000 }); } catch (e) { console.log(job.id, e.message); }
  await new Promise(r => setTimeout(r, 2500));
  await page.addStyleTag({ content: CLEAN });
  await page.evaluate(() => document.fonts.ready);
  const r = await page.evaluate((job) => {
    for (const el of document.querySelectorAll('body *')) {
      const cs = getComputedStyle(el);
      if (cs.position !== 'fixed' && cs.position !== 'sticky') continue;
      const b = el.getBoundingClientRect();
      if (b.top > 160 || b.height > 260) el.style.setProperty('display', 'none', 'important');
    }
    if (job.hide) {  // banner "baixe o app" do topo
      const n = [...document.querySelectorAll('body *')].find(e => e.children.length < 8 && e.innerText && e.innerText.startsWith(job.hide) && e.getBoundingClientRect().height < 120);
      let p = n; while (p && p.parentElement && p.parentElement.getBoundingClientRect().height < 120) p = p.parentElement;
      if (p) p.style.setProperty('display', 'none', 'important');
    }
    scrollTo(0, 0);
    // espaços de anúncio entre o cabeçalho e a manchete: somem como num bloqueador de anúncios (a página reflui sozinha)
    const killed = [];
    for (const sel of job.ads || []) for (const el of document.querySelectorAll(sel)) { killed.push(sel); el.style.setProperty('display', 'none', 'important'); }
    const find = (needle) => {
      const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n;
      while ((n = tw.nextNode())) { const i = n.textContent.indexOf(needle); if (i >= 0 && n.parentElement.getClientRects().length) return [n, i]; }
    };
    const e = find(job.end); if (!e) return { err: 'miss end' };
    const rg = document.createRange(); rg.setStart(e[0], e[1]); rg.setEnd(e[0], e[1] + job.end.length);
    const bottom = rg.getBoundingClientRect().bottom + scrollY + 18;
    const hls = [];
    for (const h of job.hl) {
      const f = find(h); if (!f) continue;
      const r2 = document.createRange(); r2.setStart(f[0], f[1]); r2.setEnd(f[0], f[1] + h.length);
      for (const q of r2.getClientRects()) hls.push({ text: h, x: q.left, y: q.top + scrollY, w: q.width, h: q.height });
    }
    return { bottom, hls, killed };
  }, job);
  if (r.err) { console.log(job.id, r.err); continue; }
  await new Promise(r => setTimeout(r, 500));
  const file = `${job.id}_card.png`;
  await page.screenshot({ path: `${OUT}/${file}`, clip: { x: 0, y: 0, width: 430, height: r.bottom }, captureBeyondViewport: true });
  const k = 3;
  meta[job.id] = { file, w: 1290, h: Math.round(r.bottom * k), hls: r.hls.map(q => ({ text: q.text, x: Math.round(q.x * k), y: Math.round(q.y * k), w: Math.round(q.w * k), h: Math.round(q.h * k) })) };
  console.log(job.id, r.killed, file, 1290, 'x', Math.round(r.bottom * k), 'hl', r.hls.length);
  await page.close();
}
fs.writeFileSync(`${OUT}/cards.json`, JSON.stringify(meta, null, 1));
await browser.close();
