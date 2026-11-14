// node --test testes/   (da pasta da skill)
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { defsDeMateriais, misturar } from '../kit/materiais.mjs';
import { ilustracao, rodaLateral, rodasDeCima } from '../kit/pecas.mjs';
import { caminhoSuave, medidaDoPneu, montarLayout, vistaDeCima, vistaLateral } from '../kit/veiculo.mjs';

const spec = { comprimento: 6, largura: 2.5, altura: 4, eixos: [{ x: 1.4, pneu: '315/80R22.5' }, { x: 5.2, pneu: '315/70R22.5', duplo: true }] };

test('pneu pelo código: aro + 2 × largura × perfil', () => {
  assert.equal(+medidaDoPneu('315/80R22.5').diametro.toFixed(4), 1.0755);
  assert.equal(+medidaDoPneu('295/80 R 22,5').diametro.toFixed(4), 1.0435);
  assert.equal(+medidaDoPneu('205/55R16').diametro.toFixed(4), 0.6319);
  assert.equal(medidaDoPneu('11R22.5').diametro, 1.054);
  assert.equal(medidaDoPneu('11.00R22').diametro, 1.08);
  assert.throws(() => medidaDoPneu('pneu grande'), /diametro/);
});

test('layout: raio sob carga, entre-eixos, balanços e ordem dos eixos', () => {
  const L = montarLayout(spec);
  assert.equal(+L.entreEixos.toFixed(3), 3.8);
  assert.equal(+L.balancoTraseiro.toFixed(3), 0.8);
  assert.ok(L.eixos[0].raioSobCarga < L.eixos[0].raio);
  assert.equal(L.eixos[1].duplo, true);
  assert.throws(() => montarLayout({ ...spec, eixos: [...spec.eixos].reverse() }), /ordem/);
  assert.throws(() => montarLayout({ ...spec, altura: '4' }), /altura/);
});

test('vistas: mesma escala e mesmo x nas duas', () => {
  const l = vistaLateral(spec, { pxPorMetro: 100 }), c = vistaDeCima(spec, { pxPorMetro: 100 });
  assert.equal(l.X(1.4), c.X(1.4));
  assert.equal(l.Y(0), l.chao);
  assert.equal(c.Y(0), c.meio);
  assert.ok(c.Y(1) > c.meio, 'lado esquerdo do veículo fica embaixo na vista de cima');
});

test('curva suave passa pelos pontos dados', () => {
  const v = vistaLateral(spec, { pxPorMetro: 100 });
  const pts = [[0, 1], [1, 2], [2, 1.5], [3, 1]];
  const d = caminhoSuave(v, pts, { fechar: false });
  for (const [x, z] of pts.slice(1)) assert.ok(d.includes(`${v.X(x)},${v.Y(z)}`), `passa por (${x}, ${z})`);
});

test('materiais e peças: ids com prefixo, peça anotada para o inspetor', () => {
  const defs = defsDeMateriais('t', { pintura: '#123456' });
  for (const id of ['t-pintura', 't-pneu', 't-aro', 't-vidro', 't-cromo', 't-sombra', 't-poco']) assert.ok(defs.includes(`id="${id}"`), id);
  assert.equal(misturar('#000000', '#ffffff', 0.5), '#808080');
  const L = montarLayout(spec), v = vistaLateral(spec);
  const roda = rodaLateral(v, 't', L.eixos[0]);
  assert.match(roda, /data-peca="roda"/);
  assert.match(roda, /data-parte="pneu"/);
  const cima = rodasDeCima(vistaDeCima(spec), 't', L.eixos[1]);
  assert.equal((cima.match(/url\(#t-banda\)/g) || []).length, 4, 'eixo duplo = 4 pneus de cima');
  assert.match(ilustracao(v, { titulo: 'x', defs, conteudo: roda }), /data-vista="lateral"/);
});
