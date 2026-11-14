// Materiais em SVG para vistas ortográficas, luz vinda de CIMA (céu) e um pouco da frente.
// Cada material é um degradê em objectBoundingBox: serve para qualquer peça, de qualquer tamanho.
// Regras (ver referencias/realismo.md): sombra fria e colorida, nunca preto puro; superfície vertical brilhante
// reflete o HORIZONTE (claro em cima = céu, escuro embaixo = chão, com a linha do horizonte nítida); cilindro deitado
// tem faixa de brilho a ~25% e luz refletida na borda de baixo; borracha e plástico quase sem brilho.

const hex = (c) => {
  const h = String(c).replace('#', '');
  const v = h.length === 3 ? h.split('').map((x) => x + x).join('') : h;
  return [0, 2, 4].map((i) => parseInt(v.slice(i, i + 2), 16));
};
const paraHex = (rgb) => '#' + rgb.map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('');
/** Mistura `a` com `b` (0 = a, 1 = b), em sRGB. */
export const misturar = (a, b, t) => { const A = hex(a), B = hex(b); return paraHex(A.map((v, i) => v + (B[i] - v) * t)); };
const CEU = '#dfe9f5';      // reflexo do céu (frio e claro)
const SOMBRA = '#141a2e';   // sombra fria azulada (não preto)
const CHAO = '#3a3328';     // reflexo do chão (quente e escuro)
const QUENTE = '#f3e3c8';   // luz refletida do chão na borda de baixo

const paradas = (lista) => lista.map(([o, c, a]) => `<stop offset="${o}" stop-color="${c}"${a !== undefined ? ` stop-opacity="${a}"` : ''}/>`).join('');
const linear = (id, lista, { x1 = 0, y1 = 0, x2 = 0, y2 = 1 } = {}) =>
  `<linearGradient id="${id}" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" color-interpolation="linearRGB">${paradas(lista)}</linearGradient>`;
const radial = (id, lista, { cx = 0.5, cy = 0.5, r = 0.5, fx, fy } = {}) =>
  `<radialGradient id="${id}" cx="${cx}" cy="${cy}" r="${r}"${fx !== undefined ? ` fx="${fx}" fy="${fy}"` : ''} color-interpolation="linearRGB">${paradas(lista)}</radialGradient>`;

/** Pintura brilhante numa face VERTICAL (porta, lateral da cabine, baú): reflexo do horizonte em `horizonte` (0–1). */
export function pinturaLateral(id, cor, { horizonte = 0.46 } = {}) {
  return linear(id, [
    [0, misturar(cor, '#ffffff', 0.42)],
    [0.04, misturar(cor, CEU, 0.26)],
    [horizonte - 0.16, misturar(cor, CEU, 0.13)],
    [horizonte - 0.01, misturar(cor, CEU, 0.06)],
    [horizonte + 0.025, misturar(cor, CHAO, 0.12)],
    [horizonte + 0.26, misturar(cor, SOMBRA, 0.12)],
    [0.92, misturar(cor, SOMBRA, 0.2)],
    [1, misturar(cor, QUENTE, 0.1)],
  ]);
}

/** Pintura fosca (implemento, chassi pintado): só a queda de luz de cima para baixo, sem horizonte. */
export function pinturaFosca(id, cor) {
  return linear(id, [[0, misturar(cor, '#ffffff', 0.22)], [0.12, misturar(cor, '#ffffff', 0.08)], [0.55, cor], [0.92, misturar(cor, SOMBRA, 0.22)], [1, misturar(cor, QUENTE, 0.06)]]);
}

/** Pintura vista DE CIMA (teto): mais clara no meio, cai nas bordas que viram para os lados. `direcao` = eixo da largura. */
export function pinturaDeCima(id, cor) {
  return linear(id, [[0, misturar(cor, SOMBRA, 0.28)], [0.12, misturar(cor, '#ffffff', 0.05)], [0.5, misturar(cor, '#ffffff', 0.22)], [0.88, misturar(cor, '#ffffff', 0.05)], [1, misturar(cor, SOMBRA, 0.28)]]);
}

/** Cilindro deitado (tanque, cilindro de ar, escapamento) visto de lado: faixas no sentido da altura. */
export function cilindroDeitado(id, cor, { brilho = 0.7 } = {}) {
  return linear(id, [
    [0, misturar(cor, SOMBRA, 0.25)],
    [0.1, misturar(cor, '#ffffff', 0.25 * brilho)],
    [0.24, misturar(cor, '#ffffff', 0.75 * brilho)],
    [0.34, misturar(cor, '#ffffff', 0.3 * brilho)],
    [0.62, cor],
    [0.84, misturar(cor, SOMBRA, 0.42)],
    [0.95, misturar(cor, SOMBRA, 0.3)],
    [1, misturar(cor, QUENTE, 0.18)],
  ]);
}

export const CORES = {
  borracha: '#1d1f23',
  aco: '#2b2e33',
  aluminio: '#b8c0c8',
  cromo: '#c9d0d7',
  plastico: '#232529',
  vidro: '#1f2c38',
  aroPrata: '#c6ccd2',
  aroBranco: '#e9ebee',
};

/**
 * Todos os <defs> de uma ilustração. `p` = prefixo único (duas ilustrações na mesma página não colidem).
 * `cores` = { pintura, pinturaSecundaria?, aro?: 'prata'|'branco'|'#hex' }.
 */
export function defsDeMateriais(p, cores = {}) {
  const pintura = cores.pintura ?? '#c41e2a';
  const secundaria = cores.pinturaSecundaria ?? '#d9dde2';
  const aro = cores.aro === 'branco' ? CORES.aroBranco : cores.aro && cores.aro.startsWith('#') ? cores.aro : CORES.aroPrata;
  return [
    pinturaLateral(`${p}-pintura`, pintura),
    pinturaLateral(`${p}-pintura2`, secundaria),
    pinturaFosca(`${p}-fosca`, pintura),
    pinturaDeCima(`${p}-teto`, pintura),
    pinturaDeCima(`${p}-teto2`, secundaria),
    // Cromo: faixas de alto contraste (reflete céu e chão em bandas finas)
    linear(`${p}-cromo`, [[0, '#f6f8fa'], [0.16, '#a6aeb7'], [0.3, '#eef1f4'], [0.48, '#56606b'], [0.6, '#cfd5db'], [0.82, '#76808a'], [1, '#e4e8ec']]),
    // Alumínio escovado e aço do chassi
    cilindroDeitado(`${p}-aluminio`, CORES.aluminio, { brilho: 0.9 }),
    linear(`${p}-aluminio-plano`, [[0, '#e7ebef'], [0.5, '#bcc4cc'], [1, '#97a0a9']]),
    linear(`${p}-aco`, [[0, '#55595f'], [0.14, '#3a3e44'], [0.5, CORES.aco], [0.9, '#1c1e22'], [1, '#2d2f33']]),
    cilindroDeitado(`${p}-aco-cilindro`, '#3b3f45', { brilho: 0.45 }),
    // Plástico preto fosco (para-choque, degrau, caixa) e borracha
    linear(`${p}-plastico`, [[0, '#3d4046'], [0.1, '#2b2d32'], [0.7, CORES.plastico], [1, '#16171a']]),
    radial(`${p}-pneu`, [[0.5, '#16171a'], [0.62, '#26282c'], [0.8, '#2c2e33'], [0.9, '#202226'], [0.965, '#17181b'], [1, '#0f1012']]),
    linear(`${p}-pneu-luz`, [[0, '#ffffff', 0.13], [0.35, '#ffffff', 0.02], [1, '#ffffff', 0]]),
    linear(`${p}-banda`, [[0, '#2a2c31'], [0.5, '#1b1c20'], [1, '#2a2c31']], { x1: 0, y1: 0, x2: 1, y2: 0 }),
    // Aro: disco abaulado (claro em cima, sombra embaixo) e o miolo fundo
    radial(`${p}-aro`, [[0, misturar(aro, '#ffffff', 0.35)], [0.55, aro], [0.85, misturar(aro, SOMBRA, 0.25)], [1, misturar(aro, SOMBRA, 0.45)]], { fx: 0.5, fy: 0.32 }),
    linear(`${p}-aro-luz`, [[0, '#ffffff', 0.35], [0.45, '#ffffff', 0], [1, SOMBRA, 0.25]]),
    radial(`${p}-cubo`, [[0, '#f2f4f6'], [0.5, '#aab2ba'], [0.85, '#5b636c'], [1, '#3a4048']], { fx: 0.42, fy: 0.35 }),
    // Vidro: escuro, frio, mais claro no alto; o reflexo diagonal é uma forma à parte (reflexoDeVidro)
    linear(`${p}-vidro`, [[0, '#4b6275'], [0.3, '#2a3a48'], [0.75, CORES.vidro], [1, '#151d26']]),
    linear(`${p}-reflexo`, [[0, '#ffffff', 0.42], [1, '#ffffff', 0.06]], { x1: 0, y1: 0, x2: 1, y2: 1 }),
    // Luzes: lente do farol (clara, com brilho), âmbar e vermelha
    radial(`${p}-farol`, [[0, '#ffffff'], [0.35, '#eef4fb'], [0.75, '#b9c7d6'], [1, '#7d8b99']], { fx: 0.35, fy: 0.3 }),
    linear(`${p}-ambar`, [[0, '#ffd27a'], [0.5, '#f29a17'], [1, '#b8650a']]),
    linear(`${p}-vermelha`, [[0, '#ff6b6b'], [0.5, '#c8141e'], [1, '#7c0a10']]),
    // Poço da roda e cavidades: escuro, mas com volume (mais fundo no alto, onde a luz não chega)
    linear(`${p}-poco`, [[0, '#07080a'], [0.6, '#121418'], [1, '#1b1e23']]),
    // Sombra de contato no chão (barata: degradê, não filtro)
    radial(`${p}-sombra`, [[0, SOMBRA, 0.5], [0.6, SOMBRA, 0.22], [1, SOMBRA, 0]]),
  ].join('');
}
