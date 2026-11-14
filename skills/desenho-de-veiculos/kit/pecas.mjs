// Peças de veículo em SVG, em METROS (convertidas pela vista). Cada peça é um <g data-peca="…"> para o inspetor.
// Ordem de pintura: quem chama desenha de trás para a frente (sombra no chão → chassi → tanques → rodas → para-lamas
// → cabine → vidros → acessórios). Detalhe pequeno (porca, furo, ranhura) termina numa aresta real ou fecha o círculo.
import { caminhoReto, caminhoSuave, fmt } from './veiculo.mjs';
import { misturar } from './materiais.mjs';

const esc = (v) => String(v).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
const attrs = (o) => Object.entries(o).filter(([, v]) => v !== undefined && v !== null && v !== false).map(([k, v]) => `${k}="${esc(typeof v === 'number' ? fmt(v) : v)}"`).join(' ');
export const el = (tag, o = {}, filhos = '') => (filhos === null ? `<${tag} ${attrs(o)}/>` : `<${tag} ${attrs(o)}>${filhos}</${tag}>`);
const vazio = (tag, o) => `<${tag} ${attrs(o)}/>`;
export const grupo = (o, filhos) => el('g', o, filhos);
const url = (p, nome) => `url(#${p}-${nome})`;
const SOMBRA = '#141a2e';

/** Polígono regular (porca sextavada etc.) centrado em (cx, cy). */
function poligono(cx, cy, r, lados, giro = 0) {
  const pts = [];
  for (let i = 0; i < lados; i++) { const a = giro + (i / lados) * Math.PI * 2; pts.push(`${fmt(cx + r * Math.cos(a))},${fmt(cy + r * Math.sin(a))}`); }
  return pts.join(' ');
}

// ─── Vista lateral ───────────────────────────────────────────────────────────

/** Sombra de contato no chão sob o veículo (de x0 a x1, em metros). */
export function sombraNoChao(v, p, x0, x1, { altura = 0.12, intensidade = 0.85 } = {}) {
  const cx = (v.X(x0) + v.X(x1)) / 2;
  return grupo({ 'data-peca': 'sombra' }, vazio('ellipse', { cx, cy: v.chao, rx: (v.X(x1) - v.X(x0)) / 2 + v.m(0.15), ry: v.m(altura), fill: url(p, 'sombra'), opacity: intensidade }));
}

/**
 * Roda vista de lado: pneu achatado no chão, banda com ranhuras, flanco, aro abaulado com furos, porcas e cubo.
 * `estilo`: 'disco' (aço com furos de mão), 'aluminio' (polido, sem furos), 'leve' (carro: raios).
 * No eixo duplo vemos a roda de FORA: o cubo fica saliente (capa maior).
 */
export function rodaLateral(v, p, eixo, { estilo = 'disco', furos = 10, porcas, pcd } = {}) {
  const R = v.m(eixo.raio), cx = v.X(eixo.x), cy = v.Y(eixo.raioSobCarga), chao = v.chao;
  const meia = Math.sqrt(Math.max(0, R * R - (chao - cy) ** 2));
  const id = `${p}-roda${eixo.indice}`;
  const pneu = `M${fmt(cx - meia)},${fmt(chao)}A${fmt(R)},${fmt(R)} 0 1 1 ${fmt(cx + meia)},${fmt(chao)}Z`;
  const Ra = v.m(eixo.pneu.aro / 2);          // assento do talão = borda visível do aro
  const nPorcas = porcas ?? (eixo.pneu.aro >= 0.55 ? 10 : 8);
  const rPcd = v.m((pcd ?? (eixo.pneu.aro >= 0.55 ? 0.335 : 0.225)) / 2);
  const partes = [];
  partes.push(vazio('ellipse', { cx, cy: chao, rx: R * 1.08, ry: Math.max(1, v.m(0.06)), fill: url(p, 'sombra') }));
  partes.push(el('clipPath', { id: `${id}-clip` }, vazio('path', { d: pneu })));
  partes.push(vazio('path', { d: pneu, fill: url(p, 'pneu'), 'data-parte': 'pneu' }));
  // Ranhuras da banda: traços curtos na borda, recortados pelo próprio pneu (somem no trecho achatado)
  const ranhuras = [];
  const n = Math.max(24, Math.round((2 * Math.PI * R) / Math.max(2, v.m(0.07))));
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    const r0 = R * 0.955, r1 = R * 1.01;
    ranhuras.push(`M${fmt(cx + r0 * Math.cos(a))},${fmt(cy + r0 * Math.sin(a))}L${fmt(cx + r1 * Math.cos(a))},${fmt(cy + r1 * Math.sin(a))}`);
  }
  partes.push(grupo({ 'clip-path': `url(#${id}-clip)` }, [
    vazio('path', { d: ranhuras.join(''), fill: 'none', stroke: '#0b0c0e', 'stroke-width': Math.max(0.6, R * 0.022), opacity: 0.7 }),
    vazio('circle', { cx, cy, r: R * 0.94, fill: 'none', stroke: '#33363c', 'stroke-width': Math.max(0.4, R * 0.012) }),
    vazio('circle', { cx, cy, r: R * 0.74, fill: 'none', stroke: '#2f3237', 'stroke-width': Math.max(0.3, R * 0.008), opacity: 0.8 }),
    vazio('path', { d: pneu, fill: url(p, 'pneu-luz') }),
  ].join('')));
  // Aro: aba (escura), disco abaulado, anel do fundo
  partes.push(vazio('circle', { cx, cy, r: Ra * 1.045, fill: '#2a2d32' }));
  partes.push(vazio('circle', { cx, cy, r: Ra, fill: url(p, 'aro') }));
  partes.push(vazio('circle', { cx, cy, r: Ra * 0.93, fill: 'none', stroke: misturar('#8a929b', SOMBRA, 0.2), 'stroke-width': Math.max(0.4, Ra * 0.03) }));
  if (estilo === 'disco') {
    // Furos de mão: elipses no sentido do raio, com a borda de baixo iluminada (o furo é fundo)
    for (let i = 0; i < furos; i++) {
      const a = (i / furos) * Math.PI * 2 + Math.PI / furos;
      const fx = cx + Ra * 0.7 * Math.cos(a), fy = cy + Ra * 0.7 * Math.sin(a);
      const giro = (a * 180) / Math.PI;
      partes.push(vazio('ellipse', { cx: fx, cy: fy, rx: Ra * 0.16, ry: Ra * 0.095, transform: `rotate(${fmt(giro)} ${fmt(fx)} ${fmt(fy)})`, fill: '#121418' }));
      partes.push(vazio('ellipse', { cx: fx, cy: fy + Ra * 0.012, rx: Ra * 0.14, ry: Ra * 0.07, transform: `rotate(${fmt(giro)} ${fmt(fx)} ${fmt(fy)})`, fill: 'none', stroke: '#ffffff', 'stroke-opacity': 0.18, 'stroke-width': Math.max(0.3, Ra * 0.012) }));
    }
  } else if (estilo === 'leve') {
    for (let i = 0; i < 5; i++) {
      const a = (i / 5) * Math.PI * 2 - Math.PI / 2;
      const x1 = cx + Ra * 0.3 * Math.cos(a), y1 = cy + Ra * 0.3 * Math.sin(a), x2 = cx + Ra * 0.88 * Math.cos(a), y2 = cy + Ra * 0.88 * Math.sin(a);
      partes.push(vazio('line', { x1, y1, x2, y2, stroke: '#9aa2ab', 'stroke-width': Ra * 0.2, 'stroke-linecap': 'round' }));
    }
  } else {
    partes.push(vazio('circle', { cx, cy, r: Ra * 0.62, fill: 'none', stroke: '#ffffff', 'stroke-opacity': 0.25, 'stroke-width': Math.max(0.3, Ra * 0.02) }));
  }
  // Prato do cubo, porcas no círculo de furação e a capa
  const rCubo = rPcd * (eixo.duplo ? 1.32 : 1.25);
  partes.push(vazio('circle', { cx, cy, r: rCubo, fill: misturar('#7d858e', SOMBRA, 0.15) }));
  partes.push(vazio('circle', { cx, cy, r: rCubo, fill: 'none', stroke: '#ffffff', 'stroke-opacity': 0.22, 'stroke-width': Math.max(0.3, rCubo * 0.04) }));
  if (estilo !== 'leve') {
    for (let i = 0; i < nPorcas; i++) {
      const a = (i / nPorcas) * Math.PI * 2;
      const nx = cx + rPcd * Math.cos(a), ny = cy + rPcd * Math.sin(a);
      partes.push(vazio('polygon', { points: poligono(nx, ny, Math.max(0.6, v.m(0.019)), 6, a), fill: url(p, 'cromo'), stroke: '#2a2d32', 'stroke-width': Math.max(0.2, v.m(0.003)) }));
    }
  }
  partes.push(vazio('circle', { cx, cy, r: rPcd * (eixo.duplo ? 0.78 : 0.62), fill: url(p, 'cubo') }));
  partes.push(vazio('path', { d: pneu, fill: 'none', stroke: '#0b0c0e', 'stroke-width': Math.max(0.4, v.m(0.006)), opacity: 0.6 }));
  return grupo({ 'data-peca': 'roda', 'data-eixo': eixo.indice, 'data-x': eixo.x, 'data-cx': cx, 'data-cy': cy, 'data-r': R, 'data-base': chao }, partes.join(''));
}

/** Para-lama de quarto (plástico) sobre uma roda, com o apara-barro atrás. Ângulos em graus a partir da frente. */
export function paralamaTraseiro(v, p, eixo, { folga = 0.08, espessura = 0.035, de = 200, ate = 340, aparaBarro = true, alturaDoAparaBarro = 0.3, cor } = {}) {
  const cx = v.X(eixo.x), cy = v.Y(eixo.raioSobCarga);
  const r0 = v.m(eixo.raio + folga), r1 = r0 + v.m(espessura);
  const ponto = (r, g) => [cx + r * Math.cos((g * Math.PI) / 180), cy + r * Math.sin((g * Math.PI) / 180)];
  const [a0x, a0y] = ponto(r1, de), [a1x, a1y] = ponto(r1, ate), [b1x, b1y] = ponto(r0, ate), [b0x, b0y] = ponto(r0, de);
  const grande = ate - de > 180 ? 1 : 0;
  const d = `M${fmt(a0x)},${fmt(a0y)}A${fmt(r1)},${fmt(r1)} 0 ${grande} 1 ${fmt(a1x)},${fmt(a1y)}L${fmt(b1x)},${fmt(b1y)}A${fmt(r0)},${fmt(r0)} 0 ${grande} 0 ${fmt(b0x)},${fmt(b0y)}Z`;
  const partes = [vazio('path', { d, fill: cor ?? url(p, 'plastico') }), vazio('path', { d: `M${fmt(a0x)},${fmt(a0y)}A${fmt(r1)},${fmt(r1)} 0 ${grande} 1 ${fmt(a1x)},${fmt(a1y)}`, fill: 'none', stroke: '#ffffff', 'stroke-opacity': 0.2, 'stroke-width': Math.max(0.4, v.m(0.006)) })];
  if (aparaBarro) {
    const x = Math.max(a1x, b1x) - v.m(0.02), topo = Math.min(a1y, b1y) + v.m(0.04), base = v.Y(alturaDoAparaBarro);
    partes.push(vazio('rect', { x: x - v.m(0.012), y: topo, width: v.m(0.024), height: base - topo, rx: v.m(0.006), fill: '#15171a' }));
  }
  return grupo({ 'data-peca': 'para-lama', 'data-eixo': eixo.indice }, partes.join(''));
}

/** Longarina do chassi vista de lado (perfil C): alma escura, aba de cima iluminada, parafusos nas travessas. */
export function longarina(v, p, { x0, x1, topo, altura = 0.29, travessas = [] }) {
  const x = v.X(x0), w = v.X(x1) - x, y = v.Y(topo), h = v.m(altura);
  const partes = [
    vazio('rect', { x, y, width: w, height: h, fill: url(p, 'aco') }),
    vazio('rect', { x, y, width: w, height: Math.max(0.8, v.m(0.012)), fill: '#6b7178' }),
    vazio('rect', { x, y: y + h - Math.max(0.8, v.m(0.012)), width: w, height: Math.max(0.8, v.m(0.012)), fill: '#15171a' }),
  ];
  for (const xt of travessas) for (const fz of [0.3, 0.7]) partes.push(vazio('circle', { cx: v.X(xt), cy: y + h * fz, r: Math.max(0.5, v.m(0.011)), fill: '#9aa1a8', stroke: '#1a1c20', 'stroke-width': Math.max(0.2, v.m(0.003)) }));
  return grupo({ 'data-peca': 'longarina' }, partes.join(''));
}

/** Tanque (combustível, D ou cilíndrico) de lado: corpo com faixas de cilindro, tampas nas pontas, cintas e bocal. */
export function tanque(v, p, { x0, x1, base, altura, material = 'aluminio', cintas = 2, bocal = true, peca = 'tanque' }) {
  const x = v.X(x0), w = v.X(x1) - x, y = v.Y(base + altura), h = v.m(altura);
  const r = Math.min(h * 0.22, w * 0.1);
  const partes = [vazio('rect', { x, y, width: w, height: h, rx: r, fill: url(p, material === 'aco' ? 'aco-cilindro' : 'aluminio') })];
  // Tampas: as pontas escurecem (a superfície vira para longe da vista)
  partes.push(vazio('rect', { x, y, width: Math.min(w * 0.06, v.m(0.05)), height: h, rx: r, fill: SOMBRA, opacity: 0.18 }));
  partes.push(vazio('rect', { x: x + w - Math.min(w * 0.06, v.m(0.05)), y, width: Math.min(w * 0.06, v.m(0.05)), height: h, rx: r, fill: SOMBRA, opacity: 0.22 }));
  for (let i = 0; i < cintas; i++) {
    const cxCinta = x + (w * (i + 1)) / (cintas + 1);
    const lc = v.m(0.045);
    partes.push(vazio('rect', { x: cxCinta - lc / 2, y: y - v.m(0.01), width: lc, height: h + v.m(0.02), rx: lc * 0.2, fill: url(p, 'aco') }));
    partes.push(vazio('circle', { cx: cxCinta, cy: y + h + v.m(0.005), r: Math.max(0.5, v.m(0.012)), fill: '#a7aeb5' }));
  }
  if (bocal) {
    const bx = x + w * 0.12;
    partes.push(vazio('rect', { x: bx, y: y - v.m(0.035), width: v.m(0.09), height: v.m(0.04), rx: v.m(0.012), fill: url(p, 'cromo') }));
  }
  partes.push(vazio('rect', { x, y, width: w, height: h, rx: r, fill: 'none', stroke: '#2d3238', 'stroke-opacity': 0.5, 'stroke-width': Math.max(0.3, v.m(0.004)) }));
  return grupo({ 'data-peca': peca }, partes.join(''));
}

/** Degrau (plástico ou alumínio) com ranhuras antiderrapantes que terminam nas bordas. */
export function degrau(v, p, { x0, x1, z, espessura = 0.05, material = 'aluminio-plano' }) {
  const x = v.X(x0), w = v.X(x1) - x, y = v.Y(z), h = v.m(espessura);
  const ranhuras = [];
  for (let i = 1; i < 4; i++) ranhuras.push(`M${fmt(x + v.m(0.01))},${fmt(y + (h * i) / 4)}H${fmt(x + w - v.m(0.01))}`);
  return grupo({ 'data-peca': 'degrau' }, [
    vazio('rect', { x, y, width: w, height: h, rx: Math.min(h * 0.3, v.m(0.01)), fill: url(p, material) }),
    vazio('path', { d: ranhuras.join(''), fill: 'none', stroke: '#2a2d32', 'stroke-opacity': 0.45, 'stroke-width': Math.max(0.3, v.m(0.004)) }),
  ].join(''));
}

/**
 * Vidro: base fria + duas faixas de reflexo diagonais (larga e fina) recortadas pelo próprio vidro + borracha de
 * vedação. `pontos` em metros; `suave` usa curva que passa pelos pontos (com `quinas` vivas).
 */
export function vidro(v, p, pontos, { id, peca = 'vidro', vedacao = 0.012, suave = false, quinas = [], reflexo = 0.5 } = {}) {
  const d = suave ? caminhoSuave(v, pontos, { quinas }) : caminhoReto(v, pontos);
  const xs = pontos.map(([x]) => v.X(x)), ys = pontos.map(([, z]) => v.Y(z));
  const bx = Math.min(...xs), by = Math.min(...ys), w = Math.max(...xs) - bx, h = Math.max(...ys) - by;
  const faixa = (a, b) => `M${fmt(bx + w * a)},${fmt(by - 1)}L${fmt(bx + w * b)},${fmt(by - 1)}L${fmt(bx + w * b - h * 0.55)},${fmt(by + h + 1)}L${fmt(bx + w * a - h * 0.55)},${fmt(by + h + 1)}Z`;
  const cid = `${p}-${id ?? peca}-clip`;
  return grupo({ 'data-peca': peca }, [
    el('clipPath', { id: cid }, vazio('path', { d })),
    vazio('path', { d, fill: url(p, 'vidro') }),
    grupo({ 'clip-path': `url(#${cid})` }, [
      vazio('path', { d: faixa(0.3, 0.52), fill: url(p, 'reflexo'), opacity: reflexo }),
      vazio('path', { d: faixa(0.58, 0.63), fill: url(p, 'reflexo'), opacity: reflexo * 0.8 }),
    ].join('')),
    vazio('path', { d, fill: 'none', stroke: '#0e1013', 'stroke-width': Math.max(0.5, v.m(vedacao)), 'stroke-linejoin': 'round' }),
  ].join(''));
}

/** Vinco da lataria: linha de luz em cima e de sombra logo abaixo (lê como dobra da chapa). Pontos em metros. */
export function vinco(v, pontos, { luz = 0.32, sombra = 0.28, largura = 0.006 } = {}) {
  const d = pontos.map(([x, z], i) => `${i ? 'L' : 'M'}${fmt(v.X(x))},${fmt(v.Y(z))}`).join('');
  const lw = Math.max(0.4, v.m(largura));
  return grupo({ 'data-peca': 'vinco' }, [
    vazio('path', { d, fill: 'none', stroke: '#ffffff', 'stroke-opacity': luz, 'stroke-width': lw, 'stroke-linecap': 'round' }),
    vazio('path', { d, fill: 'none', stroke: SOMBRA, 'stroke-opacity': sombra, 'stroke-width': lw, 'stroke-linecap': 'round', transform: `translate(0,${fmt(lw * 1.2)})` }),
  ].join(''));
}

/** Tubo/mangueira (linha de ar, escape, corrimão): corpo + brilho na metade de cima + pontas. Pontos em metros. */
export function tubo(v, p, pontos, { raio = 0.012, cor = '#2a2c30', brilho = 0.3, peca = 'tubo' } = {}) {
  const d = pontos.map(([x, z], i) => `${i ? 'L' : 'M'}${fmt(v.X(x))},${fmt(v.Y(z))}`).join('');
  const w = Math.max(0.6, v.m(raio * 2));
  return grupo({ 'data-peca': peca }, [
    vazio('path', { d, fill: 'none', stroke: misturar(cor, SOMBRA, 0.25), 'stroke-width': w, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }),
    vazio('path', { d, fill: 'none', stroke: cor, 'stroke-width': w * 0.72, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }),
    vazio('path', { d, fill: 'none', stroke: '#ffffff', 'stroke-opacity': brilho, 'stroke-width': w * 0.22, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', transform: `translate(0,${fmt(-w * 0.2)})` }),
  ].join(''));
}

/** Luz de sinalização lateral (âmbar) ou lanterna (vermelha): lente com moldura escura. */
export function luz(v, p, { x, z, largura = 0.08, altura = 0.04, cor = 'ambar', peca = 'luz' }) {
  const lx = v.X(x) - v.m(largura) / 2, ly = v.Y(z) - v.m(altura) / 2;
  return grupo({ 'data-peca': peca }, [
    vazio('rect', { x: lx - v.m(0.008), y: ly - v.m(0.008), width: v.m(largura + 0.016), height: v.m(altura + 0.016), rx: v.m(0.012), fill: '#16181b' }),
    vazio('rect', { x: lx, y: ly, width: v.m(largura), height: v.m(altura), rx: v.m(0.008), fill: url(p, cor) }),
    vazio('rect', { x: lx + v.m(largura * 0.12), y: ly + v.m(altura * 0.15), width: v.m(largura * 0.45), height: v.m(altura * 0.22), rx: v.m(0.004), fill: '#ffffff', opacity: 0.45 }),
  ].join(''));
}

/** Retrovisor visto de lado: braço (tubo) e a carcaça (perfil fino, com a pintura). Medidas em metros. */
export function retrovisor(v, p, { braco, carcaca: [x, z, largura, altura], cor = 'pintura' }) {
  const cx = v.X(x), cy = v.Y(z + altura), w = v.m(largura), h = v.m(altura);
  return grupo({ 'data-peca': 'retrovisor' }, [
    tubo(v, p, braco, { raio: 0.014, cor: '#2b2d31', peca: 'braco-do-retrovisor' }),
    vazio('rect', { x: cx, y: cy, width: w, height: h, rx: Math.min(w, h) * 0.35, fill: url(p, cor) }),
    vazio('rect', { x: cx, y: cy, width: w, height: h, rx: Math.min(w, h) * 0.35, fill: 'none', stroke: '#101215', 'stroke-opacity': 0.55, 'stroke-width': Math.max(0.3, v.m(0.004)) }),
  ].join(''));
}

/** Quinta roda (vista lateral): mesa inclinada sobre o suporte, apoiada no topo da longarina. */
export function quintaRoda(v, p, { x, topoDaLongarina, altura = 0.22, comprimento = 0.86 }) {
  const x0 = v.X(x - comprimento / 2), x1 = v.X(x + comprimento / 2), yTopo = v.Y(topoDaLongarina + altura), yBase = v.Y(topoDaLongarina);
  const mesa = v.m(0.07);
  const suporte = `M${fmt(x0 + v.m(0.1))},${fmt(yBase)}L${fmt(x0 + v.m(0.16))},${fmt(yTopo + mesa)}L${fmt(x1 - v.m(0.16))},${fmt(yTopo + mesa)}L${fmt(x1 - v.m(0.1))},${fmt(yBase)}Z`;
  return grupo({ 'data-peca': 'quinta-roda' }, [
    vazio('path', { d: suporte, fill: url(p, 'aco') }),
    vazio('path', { d: `M${fmt(x0)},${fmt(yTopo + mesa)}L${fmt(x0 + v.m(0.05))},${fmt(yTopo)}L${fmt(x1 - v.m(0.05))},${fmt(yTopo)}L${fmt(x1)},${fmt(yTopo + mesa)}Z`, fill: '#3b3f45' }),
    vazio('rect', { x: x0 + v.m(0.05), y: yTopo, width: x1 - x0 - v.m(0.1), height: Math.max(0.6, v.m(0.01)), fill: '#8e959c' }),
  ].join(''));
}

// ─── Vista de cima ───────────────────────────────────────────────────────────

/** Pneu(s) de um eixo vistos de cima: retângulo arredondado com sulcos transversais; duplo = dois pneus por lado. */
export function rodasDeCima(v, p, eixo) {
  const comp = v.m(eixo.raio * 2 * 0.96), larg = v.m(eixo.pneu.largura);
  const partes = [];
  for (const lado of [1, -1]) {
    const centros = eixo.duplo ? [eixo.bitola / 2 - eixo.vaoDoDuplo / 2, eixo.bitola / 2 + eixo.vaoDoDuplo / 2] : [eixo.bitola / 2];
    for (const c of centros) {
      const x = v.X(eixo.x) - comp / 2, y = v.Y(lado * c) - larg / 2;
      const sulcos = [];
      const n = Math.max(6, Math.round(comp / Math.max(2, v.m(0.06))));
      for (let i = 1; i < n; i++) sulcos.push(`M${fmt(x + (comp * i) / n)},${fmt(y + larg * 0.12)}V${fmt(y + larg * 0.88)}`);
      partes.push(vazio('rect', { x, y, width: comp, height: larg, rx: Math.min(larg * 0.3, comp * 0.12), fill: url(p, 'banda') }));
      partes.push(vazio('path', { d: sulcos.join(''), fill: 'none', stroke: '#0c0d0f', 'stroke-opacity': 0.75, 'stroke-width': Math.max(0.4, v.m(0.012)) }));
      partes.push(vazio('rect', { x, y, width: comp, height: larg, rx: Math.min(larg * 0.3, comp * 0.12), fill: 'none', stroke: '#0b0c0e', 'stroke-width': Math.max(0.3, v.m(0.005)) }));
    }
  }
  return grupo({ 'data-peca': 'rodas-de-cima', 'data-eixo': eixo.indice, 'data-x': eixo.x, 'data-cx': v.X(eixo.x) }, partes.join(''));
}

/** Retângulo em metros na vista de cima (x0..x1 ao longo, y0..y1 na largura) com um material. */
export function blocoDeCima(v, p, { x0, x1, y0, y1, material = 'aco', raio = 0.02, peca = 'bloco' }) {
  const x = v.X(x0), y = v.Y(Math.min(y0, y1));
  return grupo({ 'data-peca': peca }, vazio('rect', { x, y, width: v.X(x1) - x, height: Math.abs(v.m(y1 - y0)), rx: v.m(raio), fill: url(p, material) }));
}

/** O <svg> raiz, com os atributos que as ferramentas leem e o título acessível. */
export function ilustracao(v, { titulo, defs, conteudo }) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${fmt(v.largura)} ${fmt(v.altura)}" width="${fmt(v.largura)}" height="${fmt(v.altura)}" role="img" aria-label="${esc(titulo)}" ${attrs(v.atributos)}><defs>${defs}</defs>${conteudo}</svg>`;
}
