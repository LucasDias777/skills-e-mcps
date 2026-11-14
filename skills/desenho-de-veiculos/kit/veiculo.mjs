// Especificação do veículo, em metros → eixos, rodas e as projeções das vistas ortográficas.
// Sem dependências: roda no Node e no navegador. Convenções (iguais às da galeria do Guelgi):
//   x = metros a partir do NARIZ (0) para trás; z = altura a partir do chão; y = lateral, 0 no meio do veículo,
//   POSITIVO para o lado ESQUERDO (o do motorista no Brasil).
//   Vista lateral: frente à ESQUERDA, mostra o lado esquerdo. Vista de cima: frente à esquerda, lado esquerdo EMBAIXO.

const POL = 25.4;

// Pneus fora do padrão métrico: diâmetro e largura de catálogo (Michelin/Bridgestone), em metros.
// Medida que não está aqui NÃO é estimada: a especificação deve trazer `diametro` medido ou de ficha.
const PNEUS_EM_POLEGADAS = {
  '11R22.5': { diametro: 1.054, largura: 0.279 },
  '12R22.5': { diametro: 1.085, largura: 0.300 },
  '11R24.5': { diametro: 1.104, largura: 0.279 },
  '1000R20': { diametro: 1.055, largura: 0.278 },
  '1100R22': { diametro: 1.080, largura: 0.293 },
  '900R20': { diametro: 1.019, largura: 0.259 },
};

/** "315/80R22.5" → { diametro, largura, aro } em metros (conta pelo código, não por tabela). */
export function medidaDoPneu(codigo) {
  const s = String(codigo).trim().toUpperCase().replace(',', '.').replace(/\s+/g, '');
  const metrico = s.match(/^(\d{3})\/(\d{2})(?:R|-|B|ZR)?(\d{2}(?:\.\d)?)$/);
  if (metrico) {
    const largura = +metrico[1] / 1000, perfil = +metrico[2] / 100, aro = (+metrico[3] * POL) / 1000;
    return { diametro: aro + 2 * largura * perfil, largura, aro, codigo: s };
  }
  const tabela = PNEUS_EM_POLEGADAS[s.replace(/^(\d+)\.00/, '$100')];
  if (tabela) return { ...tabela, aro: (+s.split('R')[1] * POL) / 1000, codigo: s };
  throw new Error(`Pneu "${codigo}" sem conta nem tabela: informe "diametro" (m) medido ou de ficha técnica.`);
}

const numero = (v, nome) => {
  if (typeof v !== 'number' || !Number.isFinite(v)) throw new Error(`Especificação: "${nome}" precisa ser um número em metros.`);
  return v;
};

/**
 * Confere a especificação e calcula eixos e rodas.
 * spec = { nome, comprimento, largura, altura, eixos: [{ x, pneu | diametro, duplo?, bitola?, achatamento? }], ... }
 * Cada roda sai com o centro na altura do raio sob carga (o pneu achata `achatamento` × raio, padrão 3%).
 */
export function montarLayout(spec) {
  numero(spec.comprimento, 'comprimento');
  numero(spec.largura, 'largura');
  numero(spec.altura, 'altura');
  if (!Array.isArray(spec.eixos) || !spec.eixos.length) throw new Error('Especificação: "eixos" precisa de ao menos um eixo.');
  const eixos = spec.eixos.map((eixo, indice) => {
    numero(eixo.x, `eixos[${indice}].x`);
    const pneu = eixo.diametro ? { diametro: eixo.diametro, largura: eixo.largura ?? 0.3, aro: eixo.aro ?? eixo.diametro * 0.53 } : medidaDoPneu(eixo.pneu);
    const raio = pneu.diametro / 2;
    const achatamento = eixo.achatamento ?? 0.03;
    const duplo = Boolean(eixo.duplo);
    // Bitola = centro a centro dos pneus (no duplo, centro do par). Padrões de caminhão pesado, só se a ficha não trouxer.
    const bitola = eixo.bitola ?? (duplo ? 1.82 : 2.05);
    return { ...eixo, indice, pneu, raio, raioSobCarga: raio * (1 - achatamento), duplo, bitola, vaoDoDuplo: eixo.vaoDoDuplo ?? pneu.largura + 0.035 };
  });
  for (let i = 1; i < eixos.length; i++) if (eixos[i].x <= eixos[i - 1].x) throw new Error('Especificação: eixos fora de ordem (x deve crescer do nariz para trás).');
  const ultimo = eixos[eixos.length - 1];
  return {
    spec,
    eixos,
    entreEixos: ultimo.x - eixos[0].x,
    balancoDianteiro: eixos[0].x,
    balancoTraseiro: spec.comprimento - ultimo.x,
  };
}

/**
 * Vista lateral (frente à esquerda): metros → px. `chao` é a linha do chão em px; X(x) e Y(z).
 * Devolve também `atributos` para o <svg> raiz, lidos pelas ferramentas de inspeção.
 */
export function vistaLateral(spec, { pxPorMetro = 100, margem = 0.4 } = {}) {
  const largura = (spec.comprimento + 2 * margem) * pxPorMetro;
  const altura = (spec.altura + 2 * margem) * pxPorMetro;
  const chao = altura - margem * pxPorMetro;
  const X = (x) => (margem + x) * pxPorMetro;
  const Y = (z) => chao - z * pxPorMetro;
  return {
    vista: 'lateral', pxPorMetro, largura, altura, chao, X, Y, m: (v) => v * pxPorMetro,
    atributos: { 'data-vista': 'lateral', 'data-chao': chao, 'data-px-por-metro': pxPorMetro, 'data-x0': X(0), 'data-comprimento': spec.comprimento },
  };
}

/** Vista de cima (frente à esquerda, lado esquerdo do veículo embaixo): X(x) igual à lateral; Y(y) com y > 0 = esquerda. */
export function vistaDeCima(spec, { pxPorMetro = 100, margem = 0.4 } = {}) {
  const largura = (spec.comprimento + 2 * margem) * pxPorMetro;
  const altura = (spec.largura + 2 * margem) * pxPorMetro;
  const meio = altura / 2;
  const X = (x) => (margem + x) * pxPorMetro;
  const Y = (y) => meio + y * pxPorMetro;
  return {
    vista: 'cima', pxPorMetro, largura, altura, meio, X, Y, m: (v) => v * pxPorMetro,
    atributos: { 'data-vista': 'cima', 'data-meio': meio, 'data-px-por-metro': pxPorMetro, 'data-x0': X(0), 'data-comprimento': spec.comprimento },
  };
}

/** Pontos em metros [[x, z], …] → caminho SVG na vista (linhas retas). */
export function caminhoReto(vista, pontos, fechar = true) {
  return pontos.map(([x, z], i) => `${i ? 'L' : 'M'}${fmt(vista.X(x))},${fmt(vista.Y(z))}`).join('') + (fechar ? 'Z' : '');
}

/**
 * Pontos em metros → curva suave que PASSA pelos pontos (Catmull-Rom centrípeta convertida em Bézier cúbica).
 * `quinas` = índices onde a curva quebra (canto vivo), ex.: a base de um para-brisa.
 */
export function caminhoSuave(vista, pontos, { fechar = true, quinas = [], tensao = 0.5 } = {}) {
  const P = pontos.map(([x, z]) => [vista.X(x), vista.Y(z)]);
  const n = P.length;
  if (n < 3) return caminhoReto(vista, pontos, fechar);
  const quina = new Set(quinas);
  const pega = (i) => (fechar ? P[(i + n) % n] : P[Math.max(0, Math.min(n - 1, i))]);
  let d = `M${fmt(P[0][0])},${fmt(P[0][1])}`;
  const fim = fechar ? n : n - 1;
  for (let i = 0; i < fim; i++) {
    const p0 = pega(i - 1), p1 = pega(i), p2 = pega(i + 1), p3 = pega(i + 2);
    const k = tensao / 3;
    const c1 = quina.has(i % n) ? p1 : [p1[0] + (p2[0] - p0[0]) * k, p1[1] + (p2[1] - p0[1]) * k];
    const c2 = quina.has((i + 1) % n) ? p2 : [p2[0] - (p3[0] - p1[0]) * k, p2[1] - (p3[1] - p1[1]) * k];
    d += `C${fmt(c1[0])},${fmt(c1[1])} ${fmt(c2[0])},${fmt(c2[1])} ${fmt(p2[0])},${fmt(p2[1])}`;
  }
  return d + (fechar ? 'Z' : '');
}

export const fmt = (v) => (Math.round(v * 100) / 100).toString();
