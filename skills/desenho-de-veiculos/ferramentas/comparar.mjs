#!/usr/bin/env node
// Compara o desenho com a referência NA MESMA ESCALA: alinha por dois pontos (padrão: centro da 1ª e da última roda),
// mede a coincidência das silhuetas (IoU) e gera imagens para olhar região por região.
// Uso:
//   node comparar.mjs --desenho lateral.svg --referencia foto.png --ancoras-ref "x1,y1;x2,y2" --saida <pasta>
//        [--ancoras-desenho "x1,y1;x2,y2"] [--regioes "frente:0,1.6;cabine:0,2.4"] [--sem-rotacao]
//        [--fundo-ref auto|#ffffff] [--tolerancia 40] [--espelhar-ref]
// As âncoras da referência saem da régua (medir.mjs regua). --espelhar-ref vira a foto quando ela olha para a direita.
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { abrirNavegador, argumentos, executadoDireto, imagemComoDados, lerSvg, pngDeDados } from './navegador.mjs';

const pares = (s) => String(s).split(';').map((p) => p.split(',').map(Number));

async function compararNaPagina({ svg, ref, ancorasRef, ancorasDesenho, regioes, semRotacao, fundoRef, tolerancia, espelhar }) {
  const carregar = (src) => new Promise((ok, falha) => { const i = new Image(); i.onload = () => ok(i); i.onerror = () => falha(new Error('imagem não carregou')); i.src = src; });
  const host = document.createElement('div');
  host.innerHTML = svg;
  const el = host.querySelector('svg');
  document.body.append(host);
  const vb = el.viewBox.baseVal;
  const W = vb.width, H = vb.height;
  const ppm = +el.dataset.pxPorMetro || 0, x0 = +el.dataset.x0 || 0;
  // Âncoras do desenho: centros da primeira e da última roda (lateral)
  let A = ancorasDesenho;
  if (!A) {
    const rodas = [...el.querySelectorAll('[data-peca="roda"]')].map((r) => [+r.dataset.cx, +r.dataset.cy]).sort((a, b) => a[0] - b[0]);
    if (rodas.length < 2) throw new Error('Desenho sem duas rodas anotadas: informe --ancoras-desenho.');
    A = [rodas[0], rodas[rodas.length - 1]];
  }
  const fator = Math.min(2, 2400 / W);
  const CW = Math.round(W * fator), CH = Math.round(H * fator);
  const serial = (raiz) => 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(new XMLSerializer().serializeToString(raiz))));
  const imgDesenho = await carregar(serial(el));
  const silhueta = el.cloneNode(true);
  silhueta.querySelectorAll('[data-peca="sombra"]').forEach((s) => s.remove());
  silhueta.querySelectorAll('[data-peca="roda"] > ellipse').forEach((s) => s.remove());
  const imgSilhueta = await carregar(serial(silhueta));
  const imgRef = await carregar(ref);

  // Transformação referência → desenho (px do desenho × fator)
  const R = ancorasRef.map(([x, y]) => [espelhar ? imgRef.naturalWidth - x : x, y]);
  const D = A.map(([x, y]) => [x * fator, y * fator]);
  const dr = [R[1][0] - R[0][0], R[1][1] - R[0][1]], dd = [D[1][0] - D[0][0], D[1][1] - D[0][1]];
  const s = Math.hypot(...dd) / Math.hypot(...dr);
  const ang = semRotacao ? 0 : Math.atan2(dd[1], dd[0]) - Math.atan2(dr[1], dr[0]);
  const cos = Math.cos(ang) * s, sen = Math.sin(ang) * s;
  const tx = D[0][0] - (cos * R[0][0] - sen * R[0][1]), ty = D[0][1] - (sen * R[0][0] + cos * R[0][1]);

  const tela = (w = CW, h = CH) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
  const refAlinhada = tela();
  { const g = refAlinhada.getContext('2d'); g.setTransform(cos, sen, -sen, cos, tx, ty); if (espelhar) { g.translate(imgRef.naturalWidth, 0); g.scale(-1, 1); } g.drawImage(imgRef, 0, 0); }
  const desenho = tela(); desenho.getContext('2d').drawImage(imgDesenho, 0, 0, CW, CH);
  const sil = tela(); sil.getContext('2d').drawImage(imgSilhueta, 0, 0, CW, CH);

  // Máscara da referência: diferente do fundo (cor dos cantos da foto original) e dentro da foto
  const original = tela(imgRef.naturalWidth, imgRef.naturalHeight); const go = original.getContext('2d'); go.drawImage(imgRef, 0, 0);
  let fundo = fundoRef && fundoRef !== 'auto' ? [1, 3, 5].map((i) => parseInt(fundoRef.slice(i, i + 2), 16)) : null;
  if (!fundo) {
    const b = go.getImageData(0, 0, original.width, original.height).data, amostras = [];
    for (let x = 0; x < original.width; x += Math.max(1, original.width >> 6)) for (const y of [0, original.height - 1]) { const i = (y * original.width + x) * 4; amostras.push([b[i], b[i + 1], b[i + 2]]); }
    fundo = [0, 1, 2].map((k) => amostras.map((a) => a[k]).sort((p, q) => p - q)[amostras.length >> 1]);
  }
  const cobre = tela(); { const g = cobre.getContext('2d'); g.setTransform(cos, sen, -sen, cos, tx, ty); g.fillStyle = '#fff'; g.fillRect(espelhar ? 0 : 0, 0, imgRef.naturalWidth, imgRef.naturalHeight); }
  const pr = refAlinhada.getContext('2d').getImageData(0, 0, CW, CH).data;
  const pc = cobre.getContext('2d').getImageData(0, 0, CW, CH).data;
  const ps = sil.getContext('2d').getImageData(0, 0, CW, CH).data;
  const dif = tela(); const gd = dif.getContext('2d'); const out = gd.createImageData(CW, CH);
  let ambos = 0, soDesenho = 0, soRef = 0;
  const porColuna = new Float64Array(CW * 3);
  for (let i = 0, k = 0; i < pr.length; i += 4, k++) {
    const naRef = pc[i] > 0 && pr[i + 3] > 20 && Math.hypot(pr[i] - fundo[0], pr[i + 1] - fundo[1], pr[i + 2] - fundo[2]) > tolerancia;
    const noDes = ps[i + 3] > 20;
    const col = k % CW;
    let cor;
    if (naRef && noDes) { ambos++; porColuna[col * 3]++; cor = [150, 156, 164]; }
    else if (noDes) { soDesenho++; porColuna[col * 3 + 1]++; cor = [214, 51, 108]; }
    else if (naRef) { soRef++; porColuna[col * 3 + 2]++; cor = [28, 126, 214]; }
    else cor = [255, 255, 255];
    out.data.set([...cor, 255], i);
  }
  gd.putImageData(out, 0, 0);
  const iou = ambos / Math.max(1, ambos + soDesenho + soRef);

  // Sobreposição: referência apagada + desenho a 55%
  const sob = tela(); { const g = sob.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, CW, CH); g.globalAlpha = 0.85; g.filter = 'grayscale(0.7)'; g.drawImage(refAlinhada, 0, 0); g.filter = 'none'; g.globalAlpha = 0.55; g.drawImage(desenho, 0, 0); }

  // Recortes por região (metros ao longo do veículo): referência em cima, desenho embaixo
  const recortes = [];
  for (const [rotulo, a, b] of regioes) {
    if (!ppm) break;
    const xa = Math.max(0, Math.round((x0 + a * ppm) * fator)), xb = Math.min(CW, Math.round((x0 + b * ppm) * fator));
    const w = xb - xa; if (w < 4) continue;
    let a1 = 0, a2 = 0, a3 = 0; for (let c = xa; c < xb; c++) { a1 += porColuna[c * 3]; a2 += porColuna[c * 3 + 1]; a3 += porColuna[c * 3 + 2]; }
    const z = Math.min(3, 1400 / w);
    const c = tela(Math.round(w * z), Math.round(CH * z * 2) + 6); const g = c.getContext('2d');
    g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height); g.imageSmoothingQuality = 'high';
    g.drawImage(refAlinhada, xa, 0, w, CH, 0, 0, w * z, CH * z);
    g.fillStyle = '#d0d4d9'; g.fillRect(0, CH * z, c.width, 6);
    g.drawImage(desenho, xa, 0, w, CH, 0, CH * z + 6, w * z, CH * z);
    recortes.push({ rotulo, iou: a1 / Math.max(1, a1 + a2 + a3), png: c.toDataURL('image/png') });
  }
  return {
    iou, ambos, soDesenho, soRef,
    escala: s, rotacao: (ang * 180) / Math.PI, refPxPorMetro: ppm ? (ppm * fator) / s : null, fundo,
    sobreposicao: sob.toDataURL('image/png'), diferenca: dif.toDataURL('image/png'), recortes,
  };
}

export async function comparar({ desenho, referencia, ancorasRef, ancorasDesenho, saida, regioes = '', semRotacao = false, fundoRef = 'auto', tolerancia = 40, espelhar = false }) {
  mkdirSync(saida, { recursive: true });
  const { pagina, fechar } = await abrirNavegador();
  try {
    await pagina.setContent('<!doctype html><body style="margin:0"></body>');
    const r = await pagina.evaluate(compararNaPagina, {
      svg: lerSvg(desenho), ref: imagemComoDados(referencia), ancorasRef: pares(ancorasRef), ancorasDesenho: ancorasDesenho ? pares(ancorasDesenho) : null,
      regioes: String(regioes).split(';').filter(Boolean).map((t) => { const [rot, f] = t.split(':'); const [a, b] = f.split(',').map(Number); return [rot, a, b]; }),
      semRotacao, fundoRef, tolerancia: +tolerancia, espelhar,
    });
    const arquivos = [join(saida, 'sobreposicao.png'), join(saida, 'diferenca.png')];
    writeFileSync(arquivos[0], pngDeDados(r.sobreposicao));
    writeFileSync(arquivos[1], pngDeDados(r.diferenca));
    for (const c of r.recortes) { const f = join(saida, `regiao--${c.rotulo}.png`); writeFileSync(f, pngDeDados(c.png)); arquivos.push(f); }
    const resumo = { iou: r.iou, escala: r.escala, rotacao: r.rotacao, refPxPorMetro: r.refPxPorMetro, fundo: r.fundo, regioes: r.recortes.map(({ rotulo, iou }) => ({ rotulo, iou })) };
    writeFileSync(join(saida, 'comparacao.json'), JSON.stringify(resumo, null, 2));
    return { ...resumo, arquivos };
  } finally {
    await fechar();
  }
}

if (executadoDireto(import.meta.url)) {
  const o = argumentos();
  if (!o.desenho || !o.referencia || !o['ancoras-ref'] || !o.saida) {
    console.log('Uso: node comparar.mjs --desenho d.svg --referencia ref.png --ancoras-ref "x1,y1;x2,y2" --saida <pasta> [--ancoras-desenho …] [--regioes "rot:x0,x1;…"] [--sem-rotacao] [--fundo-ref auto|#hex] [--tolerancia 40] [--espelhar-ref]');
    process.exit(1);
  }
  const r = await comparar({ desenho: o.desenho, referencia: o.referencia, ancorasRef: o['ancoras-ref'], ancorasDesenho: o['ancoras-desenho'], saida: o.saida, regioes: o.regioes, semRotacao: Boolean(o['sem-rotacao']), fundoRef: o['fundo-ref'] ?? 'auto', tolerancia: o.tolerancia ?? 40, espelhar: Boolean(o['espelhar-ref']) });
  console.log(`IoU da silhueta: ${(r.iou * 100).toFixed(1)}% · escala ${r.escala.toFixed(4)} · rotação ${r.rotacao.toFixed(2)}°${r.refPxPorMetro ? ` · referência a ${r.refPxPorMetro.toFixed(1)} px/m` : ''}`);
  for (const g of r.regioes) console.log(`  ${g.rotulo}: IoU ${(g.iou * 100).toFixed(1)}%`);
  for (const a of r.arquivos) console.log(a);
}
