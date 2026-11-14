// Exemplo do kit: cavalo 4x2 genérico (sem marca) nas vistas lateral e de cima, da MESMA especificação.
// Uso: node desenhar.mjs [pasta-de-saida]   → lateral.svg e cima.svg
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { defsDeMateriais } from '../../kit/materiais.mjs';
import {
  blocoDeCima, degrau, grupo, ilustracao, longarina, luz, paralamaTraseiro, quintaRoda, retrovisor, rodaLateral, rodasDeCima,
  sombraNoChao, tanque, tubo, vidro, vinco,
} from '../../kit/pecas.mjs';
import { caminhoSuave, fmt, montarLayout, vistaDeCima, vistaLateral } from '../../kit/veiculo.mjs';

const aqui = dirname(fileURLToPath(import.meta.url));
const saida = process.argv[2] ?? aqui;
const spec = JSON.parse(readFileSync(join(aqui, 'veiculo.json'), 'utf8'));
const L = montarLayout(spec);
const [dianteiro, tracao] = L.eixos;
const p = 'cv';
const cores = { pintura: '#b3121d', aro: 'prata' };
const CHASSI = { topo: 1.0, altura: 0.29, x0: 0.6, x1: 6.0 };

// ─── Lateral ────────────────────────────────────────────────────────────────
function lateral() {
  const v = vistaLateral(spec, { pxPorMetro: 120 });
  const arco = 0.684, cxA = v.X(dianteiro.x), cyA = v.Y(dianteiro.raioSobCarga);
  // Casca da cabine: curva suave pelos pontos medidos, com o arco da roda dianteira aberto embaixo
  const contorno = [
    [2.36, 1.3], [2.36, 3.78], [2.3, 3.93], [1.6, 3.95], [0.95, 3.94], [0.55, 3.8], [0.3, 3.45], [0.2, 2.95],
    [0.07, 1.96], [0.02, 1.2], [0.0, 0.8], [0.04, 0.45], [0.3, 0.42], [0.62, 0.5],
  ];
  const casca = caminhoSuave(v, contorno, { fechar: false, quinas: [0, 1, 7, 8, 10, 11, 12, 13] })
    + `L${fmt(v.X(0.77))},${fmt(v.Y(0.7))}A${fmt(v.m(arco))},${fmt(v.m(arco))} 0 0 1 ${fmt(v.X(2.09))},${fmt(v.Y(0.7))}L${fmt(v.X(2.3))},${fmt(v.Y(0.7))}L${fmt(v.X(2.36))},${fmt(v.Y(1.3))}Z`;
  const poco = `M${fmt(cxA - v.m(arco))},${fmt(cyA)}A${fmt(v.m(arco))},${fmt(v.m(arco))} 0 0 1 ${fmt(cxA + v.m(arco))},${fmt(cyA)}Z`;
  const conteudo = [
    sombraNoChao(v, p, 0, spec.comprimento),
    longarina(v, p, { ...CHASSI, travessas: [2.5, 3.6, 4.7, 5.8] }),
    tanque(v, p, { x0: 2.55, x1: 3.85, base: 0.55, altura: 0.62, cintas: 2 }),
    tanque(v, p, { x0: 3.98, x1: 4.48, base: 0.62, altura: 0.36, material: 'aco', cintas: 1, bocal: false, peca: 'cilindro-de-ar' }),
    quintaRoda(v, p, { x: 4.85, topoDaLongarina: CHASSI.topo }),
    degrau(v, p, { x0: 2.42, x1: 3.3, z: 1.31, espessura: 0.04 }),
    luz(v, p, { x: 3.2, z: 0.76, cor: 'ambar' }),
    luz(v, p, { x: 4.6, z: 0.76, cor: 'ambar' }),
    luz(v, p, { x: 5.98, z: 0.95, largura: 0.1, altura: 0.07, cor: 'vermelha', peca: 'luz' }),
    grupo({ 'data-peca': 'poco' }, `<path d="${poco}" fill="url(#${p}-poco)"/>`),
    rodaLateral(v, p, dianteiro, { estilo: 'aluminio' }),
    rodaLateral(v, p, tracao, { estilo: 'disco' }),
    paralamaTraseiro(v, p, tracao),
    grupo({ 'data-peca': 'cabine' }, [
      `<path d="${casca}" fill="url(#${p}-pintura)"/>`,
      // Para-choque e saia em plástico, porta (frestas) e maçaneta
      `<path d="M${fmt(v.X(0.0))},${fmt(v.Y(0.8))}L${fmt(v.X(0.04))},${fmt(v.Y(0.45))}L${fmt(v.X(0.3))},${fmt(v.Y(0.42))}L${fmt(v.X(0.62))},${fmt(v.Y(0.5))}L${fmt(v.X(0.77))},${fmt(v.Y(0.7))}L${fmt(v.X(0.7))},${fmt(v.Y(0.86))}L${fmt(v.X(0.02))},${fmt(v.Y(0.9))}Z" fill="url(#${p}-plastico)"/>`,
      `<path d="M${fmt(v.X(0.42))},${fmt(v.Y(1.36))}L${fmt(v.X(1.66))},${fmt(v.Y(1.36))}L${fmt(v.X(1.66))},${fmt(v.Y(3.0))}L${fmt(v.X(0.3))},${fmt(v.Y(3.0))}" fill="none" stroke="#3a0a0e" stroke-opacity="0.55" stroke-width="${fmt(v.m(0.008))}"/>`,
      `<rect x="${fmt(v.X(1.42))}" y="${fmt(v.Y(1.92))}" width="${fmt(v.m(0.16))}" height="${fmt(v.m(0.035))}" rx="${fmt(v.m(0.012))}" fill="url(#${p}-cromo)"/>`,
      // Saia com os degraus atrás do arco
      `<path d="M${fmt(v.X(2.09))},${fmt(v.Y(0.7))}L${fmt(v.X(2.3))},${fmt(v.Y(0.7))}L${fmt(v.X(2.36))},${fmt(v.Y(1.3))}L${fmt(v.X(2.0))},${fmt(v.Y(1.3))}Z" fill="url(#${p}-plastico)"/>`,
    ].join('')),
    degrau(v, p, { x0: 2.1, x1: 2.32, z: 0.74, espessura: 0.045 }),
    degrau(v, p, { x0: 2.06, x1: 2.32, z: 1.04, espessura: 0.045 }),
    vinco(v, [[0.3, 1.32], [2.34, 1.32]]),
    vinco(v, [[0.12, 2.0], [2.34, 2.0]], { luz: 0.22, sombra: 0.18 }),
    vidro(v, p, [[0.2, 2.95], [0.07, 1.96], [0.13, 1.98], [0.27, 2.92]], { id: 'parabrisa', peca: 'vidro', reflexo: 0.35 }),
    vidro(v, p, [[0.48, 2.08], [0.36, 2.78], [0.44, 2.92], [1.58, 2.92], [1.58, 2.08]], { id: 'janela', peca: 'vidro', suave: true, quinas: [0, 3, 4] }),
    tubo(v, p, [[2.37, 1.45], [2.37, 2.85]], { raio: 0.016, cor: '#c7cdd3', peca: 'corrimao' }),
    // Linhas de ar: saem dos engates na traseira da cabine e terminam no suporte do deque (toda ponta tem conector)
    grupo({ 'data-peca': 'suporte' }, `<rect x="${fmt(v.X(2.66))}" y="${fmt(v.Y(1.5))}" width="${fmt(v.m(0.16))}" height="${fmt(v.m(0.17))}" rx="${fmt(v.m(0.015))}" fill="url(#${p}-aco)"/>`),
    tubo(v, p, [[2.37, 2.5], [2.52, 2.25], [2.62, 1.8], [2.69, 1.6]], { raio: 0.012, cor: '#1f4f9a', peca: 'linha-de-ar' }),
    tubo(v, p, [[2.37, 2.42], [2.57, 2.15], [2.7, 1.78], [2.78, 1.6]], { raio: 0.012, cor: '#c0262d', peca: 'linha-de-ar' }),
    grupo({ 'data-peca': 'engate' }, [[2.37, 2.46], [2.69, 1.6], [2.78, 1.6]].map(([x, z]) => `<rect x="${fmt(v.X(x) - v.m(0.025))}" y="${fmt(v.Y(z) - v.m(0.025))}" width="${fmt(v.m(0.05))}" height="${fmt(v.m(0.05))}" rx="${fmt(v.m(0.01))}" fill="url(#${p}-cromo)"/>`).join('')),
    luz(v, p, { x: 0.55, z: 1.16, largura: 0.07, altura: 0.035, cor: 'ambar' }),
    retrovisor(v, p, { braco: [[0.32, 2.78], [0.16, 2.86], [0.08, 2.84]], carcaca: [0.0, 2.2, 0.11, 0.62] }),
  ].join('');
  return ilustracao(v, { titulo: `${spec.nome}: vista lateral`, defs: defsDeMateriais(p, cores), conteudo });
}

// ─── De cima ────────────────────────────────────────────────────────────────
function deCima() {
  const v = vistaDeCima(spec, { pxPorMetro: 120 });
  const meiaLargura = spec.largura / 2;
  const trilho = 0.43;
  const cabine = `M${fmt(v.X(0.06))},${fmt(v.Y(-meiaLargura + 0.08))}Q${fmt(v.X(0.0))},${fmt(v.Y(0))} ${fmt(v.X(0.06))},${fmt(v.Y(meiaLargura - 0.08))}`
    + `Q${fmt(v.X(0.1))},${fmt(v.Y(meiaLargura))} ${fmt(v.X(0.3))},${fmt(v.Y(meiaLargura))}L${fmt(v.X(2.3))},${fmt(v.Y(meiaLargura))}`
    + `Q${fmt(v.X(2.36))},${fmt(v.Y(meiaLargura))} ${fmt(v.X(2.36))},${fmt(v.Y(meiaLargura - 0.06))}L${fmt(v.X(2.36))},${fmt(v.Y(-meiaLargura + 0.06))}`
    + `Q${fmt(v.X(2.36))},${fmt(v.Y(-meiaLargura))} ${fmt(v.X(2.3))},${fmt(v.Y(-meiaLargura))}L${fmt(v.X(0.3))},${fmt(v.Y(-meiaLargura))}`
    + `Q${fmt(v.X(0.1))},${fmt(v.Y(-meiaLargura))} ${fmt(v.X(0.06))},${fmt(v.Y(-meiaLargura + 0.08))}Z`;
  const conteudo = [
    ...L.eixos.map((e) => rodasDeCima(v, p, e)),
    blocoDeCima(v, p, { x0: CHASSI.x0, x1: CHASSI.x1, y0: trilho - 0.09, y1: trilho, material: 'aco', peca: 'longarina' }),
    blocoDeCima(v, p, { x0: CHASSI.x0, x1: CHASSI.x1, y0: -trilho, y1: -trilho + 0.09, material: 'aco', peca: 'longarina' }),
    blocoDeCima(v, p, { x0: 2.55, x1: 3.85, y0: trilho, y1: 1.08, material: 'aluminio-plano', raio: 0.12, peca: 'tanque' }),
    blocoDeCima(v, p, { x0: 3.98, x1: 4.48, y0: -trilho, y1: -0.95, material: 'aco', raio: 0.1, peca: 'cilindro-de-ar' }),
    blocoDeCima(v, p, { x0: 2.42, x1: 3.3, y0: -trilho, y1: trilho, material: 'aluminio-plano', raio: 0.01, peca: 'degrau' }),
    grupo({ 'data-peca': 'quinta-roda' }, [
      `<rect x="${fmt(v.X(4.42))}" y="${fmt(v.Y(-0.46))}" width="${fmt(v.m(0.86))}" height="${fmt(v.m(0.92))}" rx="${fmt(v.m(0.08))}" fill="url(#${p}-aco)"/>`,
      `<path d="M${fmt(v.X(5.28))},${fmt(v.Y(-0.08))}L${fmt(v.X(4.86))},${fmt(v.Y(-0.025))}L${fmt(v.X(4.86))},${fmt(v.Y(0.025))}L${fmt(v.X(5.28))},${fmt(v.Y(0.08))}Z" fill="#15171a"/>`,
      `<circle cx="${fmt(v.X(4.86))}" cy="${fmt(v.Y(0))}" r="${fmt(v.m(0.05))}" fill="#15171a"/>`,
    ].join('')),
    blocoDeCima(v, p, { x0: 4.62, x1: 5.86, y0: 0.62, y1: 1.24, material: 'plastico', raio: 0.06, peca: 'para-lama' }),
    blocoDeCima(v, p, { x0: 4.62, x1: 5.86, y0: -1.24, y1: -0.62, material: 'plastico', raio: 0.06, peca: 'para-lama' }),
    grupo({ 'data-peca': 'cabine' }, [
      `<path d="${cabine}" fill="url(#${p}-teto)"/>`,
      `<path d="${cabine}" fill="none" stroke="#3a0a0e" stroke-opacity="0.5" stroke-width="${fmt(v.m(0.01))}"/>`,
      // Defletor do teto e escotilha: o teto não é liso
      `<rect x="${fmt(v.X(0.55))}" y="${fmt(v.Y(-0.32))}" width="${fmt(v.m(0.62))}" height="${fmt(v.m(0.64))}" rx="${fmt(v.m(0.06))}" fill="#000" fill-opacity="0.12"/>`,
      `<rect x="${fmt(v.X(0.6))}" y="${fmt(v.Y(-0.27))}" width="${fmt(v.m(0.52))}" height="${fmt(v.m(0.54))}" rx="${fmt(v.m(0.05))}" fill="url(#${p}-vidro)"/>`,
    ].join('')),
    tubo(v, p, [[0.32, meiaLargura - 0.05], [0.12, meiaLargura + 0.1]], { raio: 0.018, peca: 'braco-do-retrovisor' }),
    tubo(v, p, [[0.32, -meiaLargura + 0.05], [0.12, -meiaLargura - 0.1]], { raio: 0.018, peca: 'braco-do-retrovisor' }),
    grupo({ 'data-peca': 'retrovisor' }, `<rect x="${fmt(v.X(0.02))}" y="${fmt(v.Y(meiaLargura + 0.03))}" width="${fmt(v.m(0.12))}" height="${fmt(v.m(0.22))}" rx="${fmt(v.m(0.03))}" fill="url(#${p}-plastico)"/>`),
    grupo({ 'data-peca': 'retrovisor' }, `<rect x="${fmt(v.X(0.02))}" y="${fmt(v.Y(-meiaLargura - 0.25))}" width="${fmt(v.m(0.12))}" height="${fmt(v.m(0.22))}" rx="${fmt(v.m(0.03))}" fill="url(#${p}-plastico)"/>`),
  ].join('');
  return ilustracao(v, { titulo: `${spec.nome}: vista de cima`, defs: defsDeMateriais(p, cores), conteudo });
}

mkdirSync(saida, { recursive: true });
writeFileSync(join(saida, 'lateral.svg'), lateral());
writeFileSync(join(saida, 'cima.svg'), deCima());
console.log(join(saida, 'lateral.svg'));
console.log(join(saida, 'cima.svg'));
