#!/usr/bin/env node
// Medir a referência em vez de estimar.
//   node medir.mjs regua <imagem> --saida regua.png [--passo 50] [--zoom "x,y,w,h;x,y,w,h"] [--fator 4]
//       Grade numerada em px sobre a imagem (linha forte a cada 5 passos) e recortes ampliados com grade fina:
//       servem para ler centros de roda, nariz, chão e cantos com precisão de 1 px.
//   node medir.mjs perfil <imagem> --chao <yPx> --nariz <xPx> --px-por-metro <n> [--passo 0.05] [--saida perfil]
//       [--fundo auto|#hex] [--tolerancia 40] [--espelhar] [--janela x0,x1,z0,z1]
//       Silhueta pela cor do fundo; para cada x (em m a partir do nariz) dá o TOPO e a BASE da silhueta em m
//       (perfil.json + perfil.csv + perfil.png para conferir). O px/m sai do entre-eixos medido na régua.
//       Também dá, para cada altura, o x mais à FRENTE e o mais ATRÁS (a cara da cabine). --janela (metros) ignora cotas,
//       setas e textos da planta fora dela; numa planta de linhas, --tolerancia alta (~200) pega só o traço preto.
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { abrirNavegador, argumentos, executadoDireto, imagemComoDados, pngDeDados } from './navegador.mjs';

async function reguaNaPagina({ src, passo, zooms, fator }) {
  const img = await new Promise((ok, falha) => { const i = new Image(); i.onload = () => ok(i); i.onerror = falha; i.src = src; });
  const W = img.naturalWidth, H = img.naturalHeight;
  const c = document.createElement('canvas'); c.width = W; c.height = H; const g = c.getContext('2d');
  g.drawImage(img, 0, 0);
  g.font = `${Math.max(10, Math.round(passo * 0.24))}px sans-serif`;
  for (let x = 0; x <= W; x += passo) {
    const forte = (x / passo) % 5 === 0;
    g.strokeStyle = forte ? 'rgba(220,20,60,0.75)' : 'rgba(220,20,60,0.3)'; g.lineWidth = forte ? 1.2 : 0.6;
    g.beginPath(); g.moveTo(x + 0.5, 0); g.lineTo(x + 0.5, H); g.stroke();
    if (forte) { g.fillStyle = 'rgba(255,255,255,0.85)'; g.fillRect(x + 2, 2, g.measureText(String(x)).width + 4, passo * 0.3); g.fillStyle = '#c2185b'; g.fillText(String(x), x + 4, 2 + passo * 0.24); }
  }
  for (let y = 0; y <= H; y += passo) {
    const forte = (y / passo) % 5 === 0;
    g.strokeStyle = forte ? 'rgba(25,90,220,0.75)' : 'rgba(25,90,220,0.3)'; g.lineWidth = forte ? 1.2 : 0.6;
    g.beginPath(); g.moveTo(0, y + 0.5); g.lineTo(W, y + 0.5); g.stroke();
    if (forte) { g.fillStyle = 'rgba(255,255,255,0.85)'; g.fillRect(2, y + 2, g.measureText(String(y)).width + 4, passo * 0.3); g.fillStyle = '#1565c0'; g.fillText(String(y), 4, y + 2 + passo * 0.24); }
  }
  const recortes = zooms.map(([x, y, w, h]) => {
    const z = document.createElement('canvas'); z.width = Math.round(w * fator); z.height = Math.round(h * fator); const gz = z.getContext('2d');
    gz.imageSmoothingEnabled = false; gz.drawImage(img, x, y, w, h, 0, 0, z.width, z.height);
    gz.font = '12px sans-serif';
    const fino = Math.max(1, Math.round(10 / fator) * 1) * (fator >= 4 ? 1 : 2);
    for (let px = Math.ceil(x / fino) * fino; px <= x + w; px += fino) {
      const forte = px % (fino * 5) === 0; gz.strokeStyle = forte ? 'rgba(220,20,60,0.8)' : 'rgba(220,20,60,0.3)';
      const sx = (px - x) * fator + 0.5; gz.beginPath(); gz.moveTo(sx, 0); gz.lineTo(sx, z.height); gz.stroke();
      if (forte) { gz.fillStyle = '#fff'; gz.fillRect(sx + 1, 1, 30, 14); gz.fillStyle = '#c2185b'; gz.fillText(String(px), sx + 2, 12); }
    }
    for (let py = Math.ceil(y / fino) * fino; py <= y + h; py += fino) {
      const forte = py % (fino * 5) === 0; gz.strokeStyle = forte ? 'rgba(25,90,220,0.8)' : 'rgba(25,90,220,0.3)';
      const sy = (py - y) * fator + 0.5; gz.beginPath(); gz.moveTo(0, sy); gz.lineTo(z.width, sy); gz.stroke();
      if (forte) { gz.fillStyle = '#fff'; gz.fillRect(1, sy + 1, 30, 14); gz.fillStyle = '#1565c0'; gz.fillText(String(py), 2, sy + 12); }
    }
    return z.toDataURL('image/png');
  });
  return { W, H, regua: c.toDataURL('image/png'), recortes };
}

async function perfilNaPagina({ src, chao, nariz, ppm, passo, fundoHex, tolerancia, espelhar, janela }) {
  const img = await new Promise((ok, falha) => { const i = new Image(); i.onload = () => ok(i); i.onerror = falha; i.src = src; });
  const W = img.naturalWidth, H = img.naturalHeight;
  const c = document.createElement('canvas'); c.width = W; c.height = H; const g = c.getContext('2d');
  if (espelhar) { g.translate(W, 0); g.scale(-1, 1); }
  g.drawImage(img, 0, 0);
  const d = g.getImageData(0, 0, W, H).data;
  let fundo = fundoHex && fundoHex !== 'auto' ? [1, 3, 5].map((i) => parseInt(fundoHex.slice(i, i + 2), 16)) : null;
  if (!fundo) {
    const a = []; for (let x = 0; x < W; x += Math.max(1, W >> 6)) for (const y of [0, H - 1]) { const i = (y * W + x) * 4; a.push([d[i], d[i + 1], d[i + 2]]); }
    fundo = [0, 1, 2].map((k) => a.map((v) => v[k]).sort((p, q) => p - q)[a.length >> 1]);
  }
  // Janela de medição em metros (x0,x1,z0,z1): fora dela, cotas, setas e textos da planta não contam
  const [jx0, jx1, jz0, jz1] = janela || [-1e9, 1e9, -1e9, 1e9];
  const px = (m) => nariz + m * ppm, py = (z) => chao - z * ppm;
  const X0 = Math.max(0, Math.ceil(px(jx0))), X1 = Math.min(W - 1, Math.floor(px(jx1))), Y0 = Math.max(0, Math.ceil(py(jz1))), Y1 = Math.min(H - 1, Math.floor(py(jz0)));
  const cheio = (x, y) => { if (x < X0 || x > X1 || y < Y0 || y > Y1) return false; const i = (y * W + x) * 4; return d[i + 3] > 20 && Math.hypot(d[i] - fundo[0], d[i + 1] - fundo[1], d[i + 2] - fundo[2]) > tolerancia; };
  const r3 = (v) => +v.toFixed(3);
  const linhas = [];
  for (let m = Math.max(0, jx0 === -1e9 ? 0 : jx0); ; m += passo) {
    const x = Math.round(px(m));
    if (x >= W || x > X1) break;
    let topo = null, base = null;
    for (let y = Y0; y <= Math.min(Y1, chao + 2); y++) if (cheio(x, y)) { topo = y; break; }
    for (let y = Math.min(Y1, Math.round(chao)); y >= Y0; y--) if (cheio(x, y)) { base = y; break; }
    linhas.push({ x: r3(m), topo: topo === null ? null : r3((chao - topo) / ppm), base: base === null ? null : r3((chao - base) / ppm) });
  }
  // Perfil da frente e de trás: para cada altura, o x mais à frente e o mais atrás (a cara da cabine sai daqui)
  const alturas = [];
  for (let z = Math.max(0, jz0 === -1e9 ? 0 : jz0); ; z += passo) {
    const y = Math.round(py(z));
    if (y < 0 || y < Y0) break;
    let frente = null, tras = null;
    for (let x = X0; x <= X1; x++) if (cheio(x, y)) { frente = x; break; }
    for (let x = X1; x >= X0; x--) if (cheio(x, y)) { tras = x; break; }
    alturas.push({ z: r3(z), frente: frente === null ? null : r3((frente - nariz) / ppm), tras: tras === null ? null : r3((tras - nariz) / ppm) });
  }
  // Prova: máscara clara + perfil em vermelho
  const prova = document.createElement('canvas'); prova.width = W; prova.height = H; const gp = prova.getContext('2d');
  gp.globalAlpha = 0.45; gp.drawImage(c, 0, 0); gp.globalAlpha = 1;
  gp.strokeStyle = '#e8590c'; gp.lineWidth = 2; gp.beginPath();
  let primeiro = true; for (const l of linhas) if (l.topo !== null) { const x = nariz + l.x * ppm, y = chao - l.topo * ppm; primeiro ? gp.moveTo(x, y) : gp.lineTo(x, y); primeiro = false; } gp.stroke();
  gp.strokeStyle = '#1971c2'; gp.beginPath(); gp.moveTo(0, chao); gp.lineTo(W, chao); gp.stroke();
  gp.strokeStyle = '#2f9e44'; gp.beginPath(); gp.moveTo(nariz, 0); gp.lineTo(nariz, H); gp.stroke();
  gp.strokeStyle = '#9c36b5'; gp.beginPath(); primeiro = true;
  for (const a of alturas) if (a.frente !== null) { const x = nariz + a.frente * ppm, y = chao - a.z * ppm; primeiro ? gp.moveTo(x, y) : gp.lineTo(x, y); primeiro = false; } gp.stroke();
  if (janela) { gp.strokeStyle = 'rgba(0,0,0,0.35)'; gp.setLineDash([6, 4]); gp.strokeRect(X0, Y0, X1 - X0, Y1 - Y0); }
  return { linhas, alturas, fundo, prova: prova.toDataURL('image/png') };
}

export async function regua(imagem, { saida, passo = 50, zoom = '', fator = 4 }) {
  const { pagina, fechar } = await abrirNavegador();
  try {
    await pagina.setContent('<!doctype html><body></body>');
    const zooms = String(zoom).split(';').filter(Boolean).map((z) => z.split(',').map(Number));
    const r = await pagina.evaluate(reguaNaPagina, { src: imagemComoDados(imagem), passo: +passo, zooms, fator: +fator });
    mkdirSync(dirname(saida), { recursive: true });
    writeFileSync(saida, pngDeDados(r.regua));
    const arquivos = [saida];
    r.recortes.forEach((png, i) => { const f = saida.replace(/\.png$/i, `--zoom${i + 1}.png`); writeFileSync(f, pngDeDados(png)); arquivos.push(f); });
    return { largura: r.W, altura: r.H, arquivos };
  } finally { await fechar(); }
}

export async function perfil(imagem, { chao, nariz, pxPorMetro, passo = 0.05, saida = 'perfil', fundo = 'auto', tolerancia = 40, espelhar = false, janela = null }) {
  const { pagina, fechar } = await abrirNavegador();
  try {
    await pagina.setContent('<!doctype html><body></body>');
    const r = await pagina.evaluate(perfilNaPagina, { src: imagemComoDados(imagem), chao: +chao, nariz: +nariz, ppm: +pxPorMetro, passo: +passo, fundoHex: fundo, tolerancia: +tolerancia, espelhar, janela: janela ? String(janela).split(',').map(Number) : null });
    mkdirSync(saida, { recursive: true });
    writeFileSync(join(saida, 'perfil.json'), JSON.stringify({ unidade: 'm', chao: +chao, nariz: +nariz, pxPorMetro: +pxPorMetro, fundo: r.fundo, janela, linhas: r.linhas, alturas: r.alturas }, null, 1));
    writeFileSync(join(saida, 'perfil.csv'), 'x;topo;base\n' + r.linhas.map((l) => `${l.x};${l.topo ?? ''};${l.base ?? ''}`).join('\n'));
    writeFileSync(join(saida, 'perfil.png'), pngDeDados(r.prova));
    return { linhas: r.linhas, alturas: r.alturas, arquivos: ['perfil.json', 'perfil.csv', 'perfil.png'].map((f) => join(saida, f)) };
  } finally { await fechar(); }
}

if (executadoDireto(import.meta.url)) {
  const o = argumentos();
  const [modo, imagem] = o._;
  if (modo === 'regua' && imagem && o.saida) {
    const r = await regua(imagem, { saida: o.saida, passo: o.passo ?? 50, zoom: o.zoom ?? '', fator: o.fator ?? 4 });
    console.log(`imagem ${r.largura} × ${r.altura} px`); for (const a of r.arquivos) console.log(a);
  } else if (modo === 'perfil' && imagem && o.chao && o.nariz && o['px-por-metro']) {
    const r = await perfil(imagem, { chao: o.chao, nariz: o.nariz, pxPorMetro: o['px-por-metro'], passo: o.passo ?? 0.05, saida: o.saida ?? 'perfil', fundo: o.fundo ?? 'auto', tolerancia: o.tolerancia ?? 40, espelhar: Boolean(o.espelhar), janela: o.janela ?? null });
    console.log(`${r.linhas.length} colunas medidas`); for (const a of r.arquivos) console.log(a);
  } else {
    console.log('Uso:\n  node medir.mjs regua <imagem> --saida regua.png [--passo 50] [--zoom "x,y,w,h;…"] [--fator 4]\n  node medir.mjs perfil <imagem> --chao <yPx> --nariz <xPx> --px-por-metro <n> [--passo 0.05] [--saida pasta] [--fundo auto|#hex] [--tolerancia 40] [--espelhar] [--janela x0,x1,z0,z1]');
    process.exit(1);
  }
}
