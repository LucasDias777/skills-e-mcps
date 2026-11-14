// Abre o Chromium (sem rede): leva alguns segundos. node --test testes/
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { after, test } from 'node:test';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { comparar } from '../ferramentas/comparar.mjs';
import { inspecionar } from '../ferramentas/inspecionar.mjs';
import { limparSvg } from '../ferramentas/navegador.mjs';
import { renderizar } from '../ferramentas/renderizar.mjs';

const raiz = fileURLToPath(new URL('..', import.meta.url));
const pasta = mkdtempSync(join(tmpdir(), 'dv-teste-'));
after(() => rmSync(pasta, { recursive: true, force: true }));
execFileSync(process.execPath, [join(raiz, 'exemplos', 'cavalo-4x2', 'desenhar.mjs'), pasta]);
const spec = JSON.parse(readFileSync(join(raiz, 'exemplos', 'cavalo-4x2', 'veiculo.json'), 'utf8'));
const lateral = join(pasta, 'lateral.svg'), cima = join(pasta, 'cima.svg');

test('limparSvg tira script, eventos e links externos', () => {
  const sujo = '<svg><script>alert(1)</script><rect onclick="x()" href="https://mal.example/a"/><use href="#ok"/></svg>';
  const limpo = limparSvg(sujo);
  assert.doesNotMatch(limpo, /script|onclick|mal\.example/);
  assert.match(limpo, /href="#ok"/);
});

test('o exemplo passa na inspeção, contra a especificação e entre as vistas', async () => {
  const r = await inspecionar(lateral, { spec, outra: cima });
  assert.deepEqual(r.achados.filter((a) => a.nivel === 'erro'), []);
  assert.ok(r.checagens > 50);
});

test('o inspetor acusa roda flutuando, eixo fora do lugar e ordem de pintura trocada', async () => {
  let svg = readFileSync(lateral, 'utf8');
  // Sobe a roda dianteira 10 px e troca de lugar o para-lama (passa a ser pintado ANTES da roda de tração)
  svg = svg.replace(/(<g data-peca="roda" data-eixo="0"[^>]*>)/, '$1<g transform="translate(0,-10)">').replace(/(<g data-peca="roda" data-eixo="1")/, '</g>$1');
  const paraLama = svg.match(/<g data-peca="para-lama"[\s\S]*?<\/g>/)[0];
  svg = svg.replace(paraLama, '').replace('<g data-peca="roda" data-eixo="1"', paraLama + '<g data-peca="roda" data-eixo="1"');
  const estragado = join(pasta, 'estragado.svg');
  writeFileSync(estragado, svg);
  const r = await inspecionar(estragado, { spec });
  const regras = new Set(r.achados.filter((a) => a.nivel === 'erro').map((a) => a.regra));
  assert.ok(regras.has('ordem-de-pintura'), 'ordem de pintura');
  assert.ok(regras.has('roda-concentrica') || regras.has('roda-no-chao'), 'roda deslocada');
});

test('renderizar gera a ilustração, os recortes e a miniatura', async () => {
  const r = await renderizar(lateral, { saida: join(pasta, 'png'), largura: 800, regioes: 'frente:0,1.5', zoom: 2, miniatura: 200 });
  assert.equal(r.arquivos.length, 3);
});

test('perfil da silhueta medido no PNG devolve as alturas do desenho em metros', async () => {
  const png = await renderizar(lateral, { saida: join(pasta, 'perfil-png'), largura: 1370, fundo: 'claro', miniatura: 0 });
  const svg = readFileSync(lateral, 'utf8');
  const vb = +svg.match(/viewBox="0 0 ([\d.]+)/)[1], fator = 1370 / vb;
  const ppm = +svg.match(/data-px-por-metro="([\d.]+)"/)[1] * fator, chao = +svg.match(/data-chao="([\d.]+)"/)[1] * fator, nariz = +svg.match(/data-x0="([\d.]+)"/)[1] * fator;
  const { perfil } = await import('../ferramentas/medir.mjs');
  const r = await perfil(png.arquivos[0], { chao, nariz, pxPorMetro: ppm, passo: 0.1, saida: join(pasta, 'perfil') });
  const em = (x) => r.linhas.find((l) => Math.abs(l.x - x) < 1e-6);
  assert.ok(Math.abs(em(1.2).topo - 3.95) < 0.03, `teto da cabine em 1,2 m: ${em(1.2).topo}`);
  assert.ok(Math.abs(em(4.0).topo - 1.0) < 0.05, `chassi em 4,0 m: ${em(4.0).topo}`);
});

test('comparar o desenho com o próprio PNG (sem a sombra) dá silhueta quase igual', async () => {
  const semSombra = join(pasta, 'sem-sombra.svg');
  writeFileSync(semSombra, readFileSync(lateral, 'utf8').replace(/<g data-peca="sombra">[\s\S]*?<\/g>/g, '').replace(/(<g data-peca="roda"[^>]*>)<ellipse[^>]*\/>/g, '$1'));
  const png = await renderizar(semSombra, { saida: join(pasta, 'ref'), largura: 822, fundo: 'transparente', miniatura: 0 });
  const svg = readFileSync(semSombra, 'utf8');
  const rodas = [...svg.matchAll(/data-peca="roda"[^>]*data-cx="([\d.]+)" data-cy="([\d.]+)"/g)].map((m) => `${m[1]},${m[2]}`);
  const vb = +svg.match(/viewBox="0 0 ([\d.]+)/)[1];
  const fator = 822 / vb;
  const ancoras = rodas.map((p) => p.split(',').map((n) => +n * fator).join(',')).join(';');
  const r = await comparar({ desenho: semSombra, referencia: png.arquivos[0], ancorasRef: ancoras, saida: join(pasta, 'cmp'), semRotacao: true, fundoRef: '#ffffff' });
  assert.ok(r.iou > 0.97, `IoU ${r.iou}`);
});
