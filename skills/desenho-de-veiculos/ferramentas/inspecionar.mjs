#!/usr/bin/env node
// Inspetor de qualidade: mede o SVG no navegador e confere regras que o olho deixa passar em 1×.
// Uso:
//   node inspecionar.mjs lateral.svg [--spec veiculo.json] [--outra cima.svg] [--json relatorio.json]
// Sai com código 1 se houver ERRO. Avisos não reprovam, mas devem ser lidos (ver referencias/inspecao.md).
import { readFileSync, writeFileSync } from 'node:fs';
import { montarLayout } from '../kit/veiculo.mjs';
import { abrirNavegador, argumentos, executadoDireto, lerSvg } from './navegador.mjs';

// Quem fica ATRÁS de quem quando as caixas se sobrepõem (vista lateral, lado esquerdo do veículo).
const ORDEM_PADRAO = [
  ['sombra', '*'],
  ['longarina', 'tanque'], ['longarina', 'roda'], ['longarina', 'degrau'],
  ['roda', 'para-lama'], ['tanque', 'degrau'],
  ['cabine', 'vidro'], ['cabine', 'retrovisor'], ['cabine', 'vinco'],
];

/** Roda dentro da página: devolve medidas e achados de UMA ilustração. */
function analisarNaPagina({ eixos, inventario, ordem }) {
  const svg = document.querySelector('svg');
  const vb = svg.viewBox.baseVal;
  const W = vb && vb.width ? vb.width : svg.getBBox().width;
  const H = vb && vb.height ? vb.height : svg.getBBox().height;
  const ds = svg.dataset;
  const vista = ds.vista || null, ppm = +ds.pxPorMetro || 0, chao = +ds.chao, x0 = +ds.x0, meio = +ds.meio;
  const achados = [];
  const add = (nivel, regra, msg) => achados.push({ nivel, regra, msg });
  let checagens = 0;
  const ok = () => checagens++;

  // Tudo medido no espaço da RAIZ: o getBBox mede no espaço do próprio elemento e ignora o transform dos pais
  const raizInv = svg.getScreenCTM().inverse();
  const matriz = (el) => raizInv.multiply(el.getScreenCTM());
  const ponto = (m, x, y) => { const p = svg.createSVGPoint(); p.x = x; p.y = y; return p.matrixTransform(m); };
  const naRaiz = (m, b) => {
    const cantos = [ponto(m, b.x, b.y), ponto(m, b.x + b.width, b.y), ponto(m, b.x, b.y + b.height), ponto(m, b.x + b.width, b.y + b.height)];
    const xs = cantos.map((c) => c.x), ys = cantos.map((c) => c.y);
    return { x: Math.min(...xs), y: Math.min(...ys), width: Math.max(...xs) - Math.min(...xs), height: Math.max(...ys) - Math.min(...ys) };
  };
  const caixaNaRaiz = (el) => naRaiz(matriz(el), el.getBBox());
  // Caixa VISÍVEL: respeita clip-path (o getBBox ignora o recorte) e pula <clipPath>, <defs> e o que não aparece
  const caixaDeClip = (el) => {
    const ref = (el.getAttribute('clip-path') || '').match(/url\(#([^)]+)\)/);
    const cp = ref && document.getElementById(ref[1]);
    if (!cp) return null;
    let u = null;
    for (const f of cp.children) u = uniao(u, naRaiz(matriz(el), f.getBBox()));
    return u;
  };
  const uniao = (a, b) => {
    if (!b || !(b.width > 0 || b.height > 0)) return a;
    if (!a) return { x: b.x, y: b.y, width: b.width, height: b.height };
    const x = Math.min(a.x, b.x), y = Math.min(a.y, b.y);
    return { x, y, width: Math.max(a.x + a.width, b.x + b.width) - x, height: Math.max(a.y + a.height, b.y + b.height) - y };
  };
  const inter = (a, b) => {
    if (!a || !b) return null;
    const x = Math.max(a.x, b.x), y = Math.max(a.y, b.y), x2 = Math.min(a.x + a.width, b.x + b.width), y2 = Math.min(a.y + a.height, b.y + b.height);
    return x2 > x && y2 > y ? { x, y, width: x2 - x, height: y2 - y } : null;
  };
  const caixaVisivel = (el) => {
    if (['clipPath', 'defs', 'mask', 'linearGradient', 'radialGradient', 'filter', 'title', 'desc'].includes(el.tagName)) return null;
    if (getComputedStyle(el).display === 'none') return null;
    const clip = caixaDeClip(el);
    let caixa;
    if (el.tagName === 'g' || el.tagName === 'svg') { caixa = null; for (const f of el.children) caixa = uniao(caixa, caixaVisivel(f)); }
    else {
      const b = caixaNaRaiz(el);
      const sw = parseFloat(getComputedStyle(el).strokeWidth) || 0;
      const temTraco = getComputedStyle(el).stroke !== 'none';
      caixa = temTraco ? { x: b.x - sw / 2, y: b.y - sw / 2, width: b.width + sw, height: b.height + sw } : { x: b.x, y: b.y, width: b.width, height: b.height };
    }
    return clip ? inter(caixa, clip) : caixa;
  };

  const pecas = [...svg.querySelectorAll('[data-peca]')].map((el) => ({ el, nome: el.dataset.peca, caixa: caixaVisivel(el) }));
  if (!vista || !ppm) add('erro', 'estrutura', '<svg> sem data-vista/data-px-por-metro: as checagens geométricas não rodam (use o kit ou anote o <svg>).');
  if (!pecas.length) add('aviso', 'estrutura', 'Nenhum elemento com data-peca: o inspetor só consegue olhar o desenho inteiro.');

  // Dentro do quadro
  for (const p of pecas) {
    if (!p.caixa) continue;
    ok();
    if (p.caixa.x < -1 || p.caixa.y < -1 || p.caixa.x + p.caixa.width > W + 1 || p.caixa.y + p.caixa.height > H + 1) add('erro', 'fora-do-quadro', `"${p.nome}" sai do quadro (${p.caixa.x.toFixed(1)}, ${p.caixa.y.toFixed(1)}, ${p.caixa.width.toFixed(1)} × ${p.caixa.height.toFixed(1)} em ${W} × ${H}).`);
  }

  const medidas = { vista, ppm, x0, rodas: [] };
  const metros = (px) => (px - x0) / ppm;

  if (vista === 'lateral') {
    const rodas = pecas.filter((p) => p.nome === 'roda');
    for (const r of rodas) {
      // O pneu é o maior caminho do grupo (a elipse da sombra não conta)
      let pneu = null, area = 0;
      let pneuEl = r.el.querySelector('[data-parte="pneu"]');
      if (!pneuEl) for (const c of r.el.querySelectorAll('path')) { if (c.closest('clipPath') || c.parentElement.closest('[clip-path]')) continue; const b = c.getBBox(); if (b.width * b.height > area) { area = b.width * b.height; pneuEl = c; } }
      if (pneuEl) pneu = caixaNaRaiz(pneuEl);
      if (!pneu) { add('erro', 'roda', 'Roda sem o caminho do pneu.'); continue; }
      // Centro anotado (data-cx/cy) levado à raiz pelo mesmo transform do pneu
      const centro = r.el.dataset.cy !== undefined ? ponto(matriz(pneuEl), +r.el.dataset.cx, +r.el.dataset.cy) : { x: pneu.x + pneu.width / 2, y: NaN };
      const cx = centro.x, cy = centro.y;
      ok();
      const base = pneu.y + pneu.height;
      if (Math.abs(base - chao) > 0.6) add('erro', 'roda-no-chao', `Roda do eixo ${r.el.dataset.eixo ?? '?'} ${base < chao ? 'flutua' : 'afunda'} ${Math.abs(base - chao).toFixed(1)} px ${base < chao ? 'acima do' : 'abaixo do'} chão.`);
      ok();
      for (const c of r.el.querySelectorAll('circle')) {
        if (c.closest('clipPath') || Number.isNaN(cy)) continue;
        const pc = ponto(matriz(c), +c.getAttribute('cx'), +c.getAttribute('cy'));
        if (Math.abs(pc.x - cx) > 0.5 || Math.abs(pc.y - cy) > 0.5) { add('erro', 'roda-concentrica', `Roda do eixo ${r.el.dataset.eixo ?? '?'}: um círculo do aro/cubo não é concêntrico ao pneu.`); break; }
      }
      medidas.rodas.push({ eixo: r.el.dataset.eixo !== undefined ? +r.el.dataset.eixo : null, x: metros(cx), raio: pneu.width / 2 / ppm });
    }
    // Nada abaixo do chão, salvo sombra e o pneu (achatado exatamente no chão)
    for (const p of pecas) {
      if (!p.caixa || p.nome === 'sombra' || p.nome === 'roda' || p.el.closest('[data-peca="roda"]')) continue;
      ok();
      if (p.caixa.y + p.caixa.height > chao + 1) add('erro', 'abaixo-do-chao', `"${p.nome}" desce ${(p.caixa.y + p.caixa.height - chao).toFixed(1)} px abaixo do chão.`);
    }
    // Para-lama sobre a sua roda
    for (const p of pecas.filter((q) => q.nome === 'para-lama' && q.el.dataset.eixo !== undefined)) {
      const roda = rodas.find((r) => r.el.dataset.eixo === p.el.dataset.eixo);
      if (!roda || !p.caixa) continue;
      ok();
      const cx = +roda.el.dataset.cx, R = +roda.el.dataset.r;
      const centro = p.caixa.x + p.caixa.width / 2;
      if (Math.abs(centro - cx) > R * 0.8) add('aviso', 'para-lama', `Para-lama do eixo ${p.el.dataset.eixo} deslocado ${((centro - cx) / ppm).toFixed(2)} m do centro da roda.`);
    }
  }

  if (vista === 'cima') {
    for (const p of pecas.filter((q) => q.nome === 'rodas-de-cima')) {
      const pneus = [...p.el.querySelectorAll('rect')].filter((r) => /banda/.test(r.getAttribute('fill') || ''));
      const cx = +p.el.dataset.cx;
      medidas.rodas.push({ eixo: p.el.dataset.eixo !== undefined ? +p.el.dataset.eixo : null, x: metros(cx), pneus: pneus.length });
      ok();
      const ys = pneus.map((r) => r.y.baseVal.value + r.height.baseVal.value / 2 - meio).sort((a, b) => a - b);
      const espelhado = ys.every((y, i) => Math.abs(y + ys[ys.length - 1 - i]) < 0.6);
      if (!espelhado) add('erro', 'simetria', `Eixo ${p.el.dataset.eixo}: os pneus não são simétricos em relação ao meio do veículo.`);
    }
  }

  // Ordem de pintura entre peças que se sobrepõem
  const regras = [...ordem];
  for (const [atras, frente] of regras) {
    const A = pecas.filter((p) => p.nome === atras && p.caixa);
    const B = frente === '*' ? pecas.filter((p) => p.nome !== atras && p.caixa) : pecas.filter((p) => p.nome === frente && p.caixa);
    for (const a of A) for (const b of B) {
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      const i = inter(a.caixa, b.caixa);
      if (!i || i.width * i.height < 4) continue;
      ok();
      if (!(a.el.compareDocumentPosition(b.el) & Node.DOCUMENT_POSITION_FOLLOWING)) { add('erro', 'ordem-de-pintura', `"${b.nome}" deveria ser pintado DEPOIS de "${a.nome}" (está atrás dele no SVG).`); break; }
    }
  }

  // Inventário pedido pela especificação ("luz:4" = pelo menos 4)
  for (const item of inventario || []) {
    const [nome, minimo = '1'] = String(item).split(':');
    const n = pecas.filter((p) => p.nome === nome).length;
    ok();
    if (n < +minimo) add('erro', 'inventario', `Falta "${nome}" (${n} de ${minimo}).`);
  }

  // Realismo: superfícies grandes com cor chapada e "círculos" feitos de polígono
  const formas = [...svg.querySelectorAll('path,rect,polygon,ellipse,circle')].filter((e) => !e.closest('clipPath,defs,[data-peca="sombra"]'));
  const chapadas = new Map();
  for (const f of formas) {
    if (!f.hasAttribute('fill') && f.hasAttribute('stroke')) continue; // traço sem preenchimento
    const fill = f.getAttribute('fill') || getComputedStyle(f).fill;
    if (!fill || fill === 'none' || fill === 'transparent' || /url\(/.test(fill)) continue;
    if (+(f.getAttribute('fill-opacity') ?? 1) < 0.5 || +(f.getAttribute('opacity') ?? 1) < 0.5) continue; // véu translúcido
    const b = f.getBBox();
    if (b.width * b.height > W * H * 0.015) { const peca = f.closest('[data-peca]'); chapadas.set(peca ? peca.dataset.peca : f.tagName, fill); }
  }
  ok();
  for (const [peca, fill] of chapadas) add('aviso', 'cor-chapada', `Superfície grande sem degradê em "${peca}" (${fill}): lê como chapado; use um material do kit.`);
  for (const pol of svg.querySelectorAll('polygon,polyline')) {
    const pts = pol.points; if (pts.numberOfItems < 14) continue;
    let sx = 0, sy = 0; for (let i = 0; i < pts.numberOfItems; i++) { sx += pts.getItem(i).x; sy += pts.getItem(i).y; }
    const cx = sx / pts.numberOfItems, cy = sy / pts.numberOfItems;
    const raios = []; for (let i = 0; i < pts.numberOfItems; i++) raios.push(Math.hypot(pts.getItem(i).x - cx, pts.getItem(i).y - cy));
    const media = raios.reduce((a, b) => a + b, 0) / raios.length;
    const desvio = Math.sqrt(raios.reduce((a, r) => a + (r - media) ** 2, 0) / raios.length);
    ok();
    if (desvio / media < 0.03) add('aviso', 'circulo-poligonal', `Polígono de ${pts.numberOfItems} lados imitando círculo: use <circle> ou arco (a faceta aparece no zoom).`);
  }

  // Composição: quanto do quadro o desenho ocupa
  let total = null; for (const p of pecas) if (p.nome !== 'sombra') total = uniao(total, p.caixa);
  if (total) medidas.ocupacao = (total.width * total.height) / (W * H);
  return { achados, checagens, medidas, W, H };
}

export async function inspecionar(arquivo, { spec, outra } = {}) {
  const layout = spec ? montarLayout(spec) : null;
  const dados = {
    eixos: layout ? layout.eixos.map((e) => ({ x: e.x, raio: e.raio, duplo: e.duplo })) : [],
    inventario: [],
    ordem: [...ORDEM_PADRAO, ...((spec && spec.ordem) || [])],
  };
  const { pagina, fechar } = await abrirNavegador({ largura: 1200, altura: 800 });
  const analisar = async (arq) => {
    await pagina.setContent(`<!doctype html><body style="margin:0">${lerSvg(arq)}</body>`);
    const vista = await pagina.evaluate(() => document.querySelector('svg')?.dataset.vista || null);
    const inv = spec && spec.inventario ? spec.inventario[vista] || [] : [];
    return pagina.evaluate(analisarNaPagina, { ...dados, inventario: inv });
  };
  try {
    const principal = await analisar(arquivo);
    const achados = [...principal.achados];
    let checagens = principal.checagens;
    // Contra a especificação: número de eixos, posição e raio de cada roda
    if (layout && principal.medidas.vista) {
      const rodas = principal.medidas.rodas;
      checagens++;
      if (rodas.length !== layout.eixos.length) achados.push({ nivel: 'erro', regra: 'contagem', msg: `${rodas.length} roda(s) desenhada(s) para ${layout.eixos.length} eixo(s) na especificação.` });
      for (const e of layout.eixos) {
        const r = rodas.find((q) => q.eixo === e.indice) || rodas.reduce((m, q) => (!m || Math.abs(q.x - e.x) < Math.abs(m.x - e.x) ? q : m), null);
        if (!r) continue;
        checagens++;
        if (Math.abs(r.x - e.x) > 0.01) achados.push({ nivel: 'erro', regra: 'posicao-do-eixo', msg: `Eixo ${e.indice} desenhado em ${r.x.toFixed(3)} m; a especificação diz ${e.x} m.` });
        if (r.raio !== undefined) { checagens++; if (Math.abs(r.raio - e.raio) / e.raio > 0.015) achados.push({ nivel: 'erro', regra: 'raio-do-pneu', msg: `Pneu do eixo ${e.indice} com raio ${r.raio.toFixed(3)} m; o pneu ${e.pneu?.codigo ?? ''} tem ${e.raio.toFixed(3)} m.` }); }
        if (r.pneus !== undefined) { checagens++; if (r.pneus !== (e.duplo ? 4 : 2)) achados.push({ nivel: 'erro', regra: 'pneus-do-eixo', msg: `Eixo ${e.indice}: ${r.pneus} pneus de cima; ${e.duplo ? 'duplo = 4' : 'simples = 2'}.` }); }
      }
    }
    // Entre vistas: os eixos têm de cair no mesmo x
    if (outra) {
      const segunda = await analisar(outra);
      achados.push(...segunda.achados.map((a) => ({ ...a, msg: `[${outra}] ${a.msg}` })));
      checagens += segunda.checagens;
      const a = principal.medidas.rodas.map((r) => r.x).sort((p, q) => p - q), b = segunda.medidas.rodas.map((r) => r.x).sort((p, q) => p - q);
      checagens++;
      if (a.length !== b.length) achados.push({ nivel: 'erro', regra: 'entre-vistas', msg: `${a.length} eixo(s) numa vista e ${b.length} na outra.` });
      else a.forEach((x, i) => { if (Math.abs(x - b[i]) > 0.01) achados.push({ nivel: 'erro', regra: 'entre-vistas', msg: `Eixo ${i}: ${x.toFixed(3)} m numa vista e ${b[i].toFixed(3)} m na outra.` }); });
    }
    return { arquivo, achados, checagens, medidas: principal.medidas };
  } finally {
    await fechar();
  }
}

if (executadoDireto(import.meta.url)) {
  const o = argumentos();
  if (!o._[0]) { console.log('Uso: node inspecionar.mjs desenho.svg [--spec veiculo.json] [--outra outra-vista.svg] [--json saida.json]'); process.exit(1); }
  const spec = o.spec ? JSON.parse(readFileSync(o.spec, 'utf8')) : undefined;
  const r = await inspecionar(o._[0], { spec, outra: o.outra });
  if (o.json) writeFileSync(o.json, JSON.stringify(r, null, 2));
  const erros = r.achados.filter((a) => a.nivel === 'erro'), avisos = r.achados.filter((a) => a.nivel === 'aviso');
  for (const a of erros) console.log(`✖ [${a.regra}] ${a.msg}`);
  for (const a of avisos) console.log(`⚠ [${a.regra}] ${a.msg}`);
  const oc = r.medidas.ocupacao ? ` · desenho ocupa ${(r.medidas.ocupacao * 100).toFixed(0)}% do quadro` : '';
  console.log(`${erros.length ? '✖' : '✔'} ${r.checagens} checagens · ${erros.length} erro(s) · ${avisos.length} aviso(s)${oc}`);
  process.exit(erros.length ? 1 : 0);
}
