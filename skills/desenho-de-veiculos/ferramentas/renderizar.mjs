#!/usr/bin/env node
// Renderiza um SVG em PNG para OLHAR: a ilustração inteira na largura pedida e recortes ampliados por região.
// Uso:
//   node renderizar.mjs desenho.svg --saida <pasta> [--largura 1600] [--fundo claro|escuro|transparente]
//        [--regioes "frente:0,1.6;cabine:0,2.4;traseira:4.5,6.2"]   (faixas em METROS ao longo do veículo)
//        [--zoom 3] [--miniatura 240]
// Recortes por região exigem os atributos data-px-por-metro e data-x0 no <svg> (o kit põe). A miniatura mostra como
// o desenho se lê no tamanho pequeno em que o sistema usa (cartão, lista).
import { mkdirSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import { abrirNavegador, argumentos, executadoDireto, lerSvg } from './navegador.mjs';

const FUNDOS = { claro: '#f4f5f7', escuro: '#1e1e1e', transparente: 'transparent' };

export async function renderizar(arquivo, { saida, largura = 1600, fundo = 'claro', regioes, zoom = 3, miniatura = 240 } = {}) {
  const svg = lerSvg(arquivo);
  const nome = basename(arquivo).replace(/\.svg$/i, '');
  mkdirSync(saida, { recursive: true });
  const { pagina, fechar } = await abrirNavegador({ largura: 400, altura: 300, escala: 1 });
  try {
    const cor = FUNDOS[fundo] ?? fundo;
    await pagina.setContent(`<!doctype html><html><body style="margin:0;background:${cor}"><div id="alvo" style="display:inline-block;line-height:0">${svg}</div></body></html>`);
    const info = await pagina.evaluate((alvoLargura) => {
      const el = document.querySelector('#alvo svg');
      const vb = el.viewBox.baseVal;
      const w = vb && vb.width ? vb.width : el.getBBox().width;
      const h = vb && vb.height ? vb.height : el.getBBox().height;
      el.setAttribute('width', alvoLargura);
      el.setAttribute('height', (alvoLargura * h) / w);
      return { w, h, ppm: +el.dataset.pxPorMetro || null, x0: el.dataset.x0 !== undefined ? +el.dataset.x0 : null, comprimento: +el.dataset.comprimento || null };
    }, +largura);
    const fator = +largura / info.w;
    const alturaPx = Math.ceil(info.h * fator);
    await pagina.setViewportSize({ width: +largura, height: alturaPx });
    const arquivos = [];
    const inteiro = join(saida, `${nome}.png`);
    await pagina.screenshot({ path: inteiro, clip: { x: 0, y: 0, width: +largura, height: alturaPx }, omitBackground: cor === 'transparent' });
    arquivos.push(inteiro);
    if (regioes) {
      if (!info.ppm || info.x0 === null) throw new Error('Recorte por região precisa de data-px-por-metro e data-x0 no <svg>.');
      for (const trecho of String(regioes).split(';').filter(Boolean)) {
        const [rotulo, faixa] = trecho.split(':');
        const [a, b] = faixa.split(',').map(Number);
        const x = (info.x0 + a * info.ppm) * fator, w = (b - a) * info.ppm * fator;
        const destino = join(saida, `${nome}--${rotulo}.png`);
        // Recorte nítido: aumenta o SVG `zoom` vezes e fotografa só a faixa
        await pagina.evaluate(([l, z]) => { const el = document.querySelector('#alvo svg'); el.setAttribute('width', l * z); el.setAttribute('height', el.getAttribute('height') * z); }, [+largura, +zoom]);
        await pagina.setViewportSize({ width: Math.ceil(+largura * zoom), height: Math.ceil(alturaPx * zoom) });
        await pagina.screenshot({ path: destino, clip: { x: Math.max(0, x * zoom), y: 0, width: Math.min(w * zoom, +largura * zoom - x * zoom), height: alturaPx * zoom } });
        await pagina.evaluate(([l, h]) => { const el = document.querySelector('#alvo svg'); el.setAttribute('width', l); el.setAttribute('height', h); }, [+largura, alturaPx]);
        await pagina.setViewportSize({ width: +largura, height: alturaPx });
        arquivos.push(destino);
      }
    }
    if (miniatura) {
      await pagina.evaluate((m) => { const el = document.querySelector('#alvo svg'); const r = el.getAttribute('height') / el.getAttribute('width'); el.setAttribute('width', m); el.setAttribute('height', m * r); }, +miniatura);
      const destino = join(saida, `${nome}--miniatura.png`);
      await pagina.screenshot({ path: destino, clip: { x: 0, y: 0, width: +miniatura, height: Math.ceil((+miniatura * info.h) / info.w) } });
      arquivos.push(destino);
    }
    return { arquivos, largura: +largura, altura: alturaPx, pxPorMetro: info.ppm };
  } finally {
    await fechar();
  }
}

if (executadoDireto(import.meta.url)) {
  const o = argumentos();
  if (!o._[0] || !o.saida) {
    console.log('Uso: node renderizar.mjs desenho.svg --saida <pasta> [--largura 1600] [--fundo claro|escuro|transparente] [--regioes "rotulo:x0,x1;…"] [--zoom 3] [--miniatura 240]');
    process.exit(1);
  }
  const r = await renderizar(o._[0], { saida: o.saida, largura: o.largura ?? 1600, fundo: o.fundo ?? 'claro', regioes: o.regioes, zoom: o.zoom ?? 3, miniatura: o.miniatura === 'nao' ? 0 : o.miniatura ?? 240 });
  for (const a of r.arquivos) console.log(a);
}
