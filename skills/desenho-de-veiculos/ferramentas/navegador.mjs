// Chromium sem janela para renderizar e medir SVG/imagens, com TODA a rede bloqueada.
// Usa um Playwright já instalado e auditado (o da skill teardown, 1.58.2). Esta skill não baixa nada.
// Caminho alternativo: variável DV_PLAYWRIGHT apontando para o index.mjs de outro Playwright local.
import { existsSync, readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { extname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const CANDIDATOS = [
  process.env.DV_PLAYWRIGHT,
  join(homedir(), '.claude', 'skills', 'teardown', 'node_modules', 'playwright', 'index.mjs'),
].filter(Boolean);

export async function abrirNavegador({ largura = 1600, altura = 1000, escala = 1 } = {}) {
  const caminho = CANDIDATOS.find((c) => existsSync(c));
  if (!caminho) throw new Error('Playwright não encontrado. Instale a skill teardown (npm ci + npx playwright install chromium) ou defina DV_PLAYWRIGHT.');
  const { chromium } = await import(pathToFileURL(caminho).href);
  const navegador = await chromium.launch({ headless: true });
  const contexto = await navegador.newContext({ viewport: { width: largura, height: altura }, deviceScaleFactor: escala, javaScriptEnabled: true });
  await contexto.route('**/*', (rota) => (/^(data|blob|about):/.test(rota.request().url()) ? rota.continue() : rota.abort()));
  const pagina = await contexto.newPage();
  return { navegador, contexto, pagina, fechar: () => navegador.close() };
}

/** Remove do SVG o que poderia executar código ou buscar algo de fora (o SVG pode vir de terceiros). */
export function limparSvg(svg) {
  return String(svg)
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<foreignObject[\s\S]*?<\/foreignObject>/gi, '')
    .replace(/\son[a-z]+\s*=\s*("[^"]*"|'[^']*')/gi, '')
    .replace(/(href|xlink:href)\s*=\s*("|')(?!#|data:image\/)[^"']*\2/gi, '');
}

export function lerSvg(arquivo) {
  const svg = limparSvg(readFileSync(arquivo, 'utf8'));
  if (!/<svg[\s>]/i.test(svg)) throw new Error(`${arquivo} não contém <svg>.`);
  return svg;
}

const TIPOS = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.gif': 'image/gif', '.svg': 'image/svg+xml' };
/** Imagem do disco como data: URL (a página não tem acesso a arquivo nem rede). */
export function imagemComoDados(arquivo) {
  const tipo = TIPOS[extname(arquivo).toLowerCase()];
  if (!tipo) throw new Error(`Formato de imagem não suportado: ${arquivo}`);
  const dados = tipo === 'image/svg+xml' ? Buffer.from(limparSvg(readFileSync(arquivo, 'utf8'))) : readFileSync(arquivo);
  return `data:${tipo};base64,${dados.toString('base64')}`;
}

/** Lê argumentos "--chave valor" e "--bandeira"; o resto vira posicional. */
export function argumentos(lista = process.argv.slice(2)) {
  const opcoes = { _: [] };
  for (let i = 0; i < lista.length; i++) {
    const a = lista[i];
    if (a.startsWith('--')) {
      const chave = a.slice(2);
      const proximo = lista[i + 1];
      if (proximo === undefined || proximo.startsWith('--')) opcoes[chave] = true;
      else { opcoes[chave] = proximo; i++; }
    } else opcoes._.push(a);
  }
  return opcoes;
}

/** Verdadeiro quando o módulo foi chamado pela linha de comando (e não importado por outro). */
export const executadoDireto = (url) => Boolean(process.argv[1]) && resolve(process.argv[1]).toLowerCase() === fileURLToPath(url).toLowerCase();

/** PNG de um data: URL gerado no canvas → Buffer. */
export const pngDeDados = (dados) => Buffer.from(dados.replace(/^data:image\/png;base64,/, ''), 'base64');
