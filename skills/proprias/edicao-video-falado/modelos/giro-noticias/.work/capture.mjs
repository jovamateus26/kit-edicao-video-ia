// Prints reais das matérias (viewport de iPhone 430x932 @3x), sem aceitar cookies: banners/anúncios só são escondidos.
// node capture.mjs jobs.json OUT_DIR [id]  -> OUT_DIR/<id>_<shot>.png + OUT_DIR/shots-<id|all>.json
// Cada job: { id, url, hide?: [seletores], find?: [trechos p/ listar], shots: [
//   { name, top: true, end: 'texto onde o recorte termina', hl: [...] }            -> do topo da página até "end"
//   { name, from: 'início', to: 'fim', hl: [...] } ]}                              -> faixa entre dois trechos
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
const [JOBS_FILE, OUT, ONLY] = process.argv.slice(2);
const JOBS = JSON.parse(fs.readFileSync(JOBS_FILE, 'utf8')).filter(j => !ONLY || j.id === ONLY);
fs.mkdirSync(OUT, { recursive: true });
const K = 3;
const CLEAN = `
  [id*="cookie" i],[class*="cookie" i],[id*="consent" i],[class*="consent" i],[class*="lgpd" i],[id*="lgpd" i],
  [id*="onetrust" i],[class*="onetrust" i],[id*="didomi" i],[class*="didomi" i],[class*="fc-consent" i],[id*="usercentrics" i],
  [id*="google_ads" i],[class*="adsbygoogle" i],[class*="publicidade" i],[class*="banner-ad" i],[id*="div-gpt" i],[class*="ad-slot" i],
  [class*="paywall" i],[class*="newsletter" i],[class*="push-notification" i],[id*="pushnews" i], iframe { display:none !important; }
  html, body { overflow: visible !important; }
  html body[class] { display: block !important; }   /* body com classe "eu-cookie-compliance-…" (Agência Brasil) não pode sumir */`;
const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new',
  args: ['--no-sandbox', '--lang=pt-BR', '--disable-notifications'] });
const meta = {};
for (const job of JOBS) {
  const page = await browser.newPage();
  await page.setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1');
  await page.setExtraHTTPHeaders({ 'Accept-Language': job.lang || 'pt-BR,pt;q=0.9,en;q=0.8' });  // job.lang: site que traduz sozinho (Malwarebytes)
  await page.setViewport({ width: 430, height: 932, deviceScaleFactor: K, isMobile: true, hasTouch: true });
  try { await page.goto(job.url, { waitUntil: 'networkidle2', timeout: 60000 }); } catch (e) { console.log(job.id, 'goto', e.message); }
  await new Promise(r => setTimeout(r, 2500));
  for (let k = 0; k < 25; k++) { await page.evaluate(() => scrollBy(0, 900)); await new Promise(r => setTimeout(r, 200)); }  // matéria com carga preguiçosa (The Verge)
  await page.evaluate(() => scrollTo(0, 0));
  await page.addStyleTag({ content: (job.keepPaywall ? CLEAN.replace('[class*="paywall" i],', '') : CLEAN) + (job.hide || []).map(s => `${s}{display:none !important}`).join('\n') });
  // a limpeza casa por pedaço de classe/id e às vezes pega o próprio texto: <html class="cookies …"> do Modernizr (Fox Business),
  // <article class="… tag-…"> (Teletime). html, body, main e article nunca somem.
  await page.evaluate(() => {
    for (const el of [document.documentElement, document.body, ...document.querySelectorAll('main, article')])
      if (getComputedStyle(el).display === 'none') el.style.setProperty('display', 'block', 'important');
  });
  // overlays fixos/sticky (barra de app, banners) somem; o cabeçalho do topo fica para o print "top"
  await page.evaluate(() => {
    for (const el of document.querySelectorAll('body *')) {
      const cs = getComputedStyle(el);
      if (cs.position !== 'fixed' && cs.position !== 'sticky') continue;
      const b = el.getBoundingClientRect();
      if (b.top > 160 || b.height > 260) el.style.setProperty('display', 'none', 'important');
    }
  });
  // acentos decompostos (NFD: Agência Brasil, Canaltech) e espaço não separável (Fox Business, Teletime) não casam com os trechos do jobs.json: NFC + espaço comum
  await page.evaluate(() => {
    const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n;
    while ((n = tw.nextNode())) { const t = n.textContent.normalize('NFC').replace(/\u00a0/g, ' '); if (t !== n.textContent) n.textContent = t; }
  });
  await page.evaluate(() => document.fonts.ready);
  await new Promise(r => setTimeout(r, 800));
  const title = await page.evaluate(() => document.title);
  console.log(job.id, 'title:', title);
  if (job.find) {
    const hits = await page.evaluate((needles) => needles.map(n => {
      const ps = [...document.querySelectorAll('p, li, h1, h2, h3, td, span, div')].filter(p => p.children.length < 6 && p.innerText && p.innerText.includes(n));
      return [n, [...new Set(ps.map(p => p.innerText.slice(0, 500)))].slice(0, 3)];
    }), job.find);
    console.log(JSON.stringify(hits, null, 1));
  }
  meta[job.id] = { url: job.url, title, shots: {} };
  for (const s of job.shots || []) {
    if (!s.top) {  // recortes do meio do texto: sem nenhum fixo/sticky por cima
      await page.evaluate(() => {
        for (const el of document.querySelectorAll('body *')) {
          const cs = getComputedStyle(el);
          if ((cs.position === 'fixed' || cs.position === 'sticky') && el.tagName !== 'HTML') el.style.setProperty('display', 'none', 'important');
        }
      });
      await new Promise(r => setTimeout(r, 300));
    }
    const r = await page.evaluate((s) => {
      scrollTo(0, 0);
      const walk = (needle) => {
        const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let n; const out = [];
        while ((n = tw.nextNode())) {
          const el = n.parentElement; if (!el || !el.getClientRects().length) continue;
          if (el.checkVisibility && !el.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
          const i = n.textContent.indexOf(needle); if (i >= 0) out.push([n, i]);
        }
        return out;
      };
      let box;
      if (s.top) {
        const e = walk(s.end)[s.endNth || 0]; if (!e) return { err: 'miss end ' + s.end };
        const rg = document.createRange(); rg.setStart(e[0], e[1]); rg.setEnd(e[0], e[1] + s.end.length);
        box = { x: 0, y: (s.y0 || 0), w: innerWidth, h: rg.getBoundingClientRect().bottom + scrollY + 18 - (s.y0 || 0) };
      } else {
        const a = walk(s.from)[s.fromNth || 0]; if (!a) return { err: 'miss from ' + s.from };
        const bs = walk(s.to); const b = bs.find(([n, i]) => n === a[0] ? i >= a[1] : (a[0].compareDocumentPosition(n) & Node.DOCUMENT_POSITION_FOLLOWING));  // 1º 'to' depois do 'from'
        if (!b) return { err: 'miss to ' + s.to };
        const rg = document.createRange(); rg.setStart(a[0], a[1]); rg.setEnd(b[0], b[1] + s.to.length);
        const rb = rg.getBoundingClientRect();
        let block = rg.commonAncestorContainer; if (block.nodeType === 3) block = block.parentElement;
        const bb = block.getBoundingClientRect();
        const left = Math.max(0, Math.min(rb.left, bb.left) - 18), right = Math.min(innerWidth, Math.max(rb.right, bb.right) + 18);
        box = { x: left + scrollX, y: rb.top + scrollY - 10, w: right - left, h: rb.height + 20 };  // margem curta: sem meia linha vizinha
      }
      const hls = [];
      for (const h of s.hl || []) {
        // entre as ocorrências dentro do recorte, fica a de letra maior (evita títulos repetidos em barras escondidas)
        let best = null;
        for (const [n, i] of walk(h)) {
          const r2 = document.createRange(); r2.setStart(n, i); r2.setEnd(n, i + h.length);
          const rs = [...r2.getClientRects()].filter(q => q.width > 2).map(q => ({ text: h, x: q.left + scrollX - box.x, y: q.top + scrollY - box.y, w: q.width, h: q.height }))
            .filter(q => q.y >= -2 && q.y + q.h <= box.h + 2);
          if (!rs.length) continue;
          const size = parseFloat(getComputedStyle(n.parentElement).fontSize);
          if (!best || size > best.size) best = { size, rs };
        }
        if (best) hls.push(...best.rs); else hls.push({ text: h, miss: true });
      }
      return { box, hls };
    }, s);
    if (r.err) { console.log(job.id, s.name, r.err); continue; }
    if (!s.top) {  // anúncio fixo que só aparece depois do scrollTo (Olhar Digital): some de novo antes do print
      await page.evaluate(() => {
        for (const el of document.querySelectorAll('body *')) {
          const cs = getComputedStyle(el);
          if (cs.position === 'fixed' || cs.position === 'sticky') el.style.setProperty('display', 'none', 'important');
        }
      });
      await new Promise(r => setTimeout(r, 300));
    }
    const file = `${job.id}_${s.name}.png`;
    await page.screenshot({ path: `${OUT}/${file}`, clip: { x: r.box.x, y: r.box.y, width: r.box.w, height: r.box.h }, captureBeyondViewport: true });
    meta[job.id].shots[s.name] = { file, w: Math.round(r.box.w * K), h: Math.round(r.box.h * K),
      hls: r.hls.filter(q => !q.miss).map(q => ({ text: q.text, x: Math.round(q.x * K), y: Math.round(q.y * K), w: Math.round(q.w * K), h: Math.round(q.h * K) })) };
    const miss = r.hls.filter(q => q.miss).map(q => q.text);
    console.log(job.id, s.name, file, Math.round(r.box.w * K), 'x', Math.round(r.box.h * K), 'hl', r.hls.length - miss.length, miss.length ? 'MISS ' + miss.join(' | ') : '');
  }
  await page.close();
}
fs.writeFileSync(`${OUT}/shots-${ONLY || 'all'}.json`, JSON.stringify(meta, null, 1));
await browser.close();
