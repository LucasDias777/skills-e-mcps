# Método: da referência ao desenho fiel

Destilado do que funcionou (e do que deu errado) na galeria 2D do Guelgi, de set. a nov./2026.

## 1. Referência

- Melhor fonte: planta lateral do fabricante (desenho técnico com cotas), que dá forma E medida. Depois: foto de lado a
  90° (não de 3/4), longe, com teleobjetiva (pouca perspectiva). Vetor "2d" de banco de imagem serve para estilo e
  proporção, não para medida.
- "Igual à referência" = o veículo INTEIRO da figura, cabine inclusive. Não trocar parte da figura por peça da casa
  sem perguntar.
- Figuras da mesma prancha podem estar em escalas diferentes; print pode vir esticado (já veio 3,16% na vertical:
  roda oval). Conferir: as rodas têm de ser círculos (largura = altura na régua).
- Guardar a referência numa pasta de trabalho (scratchpad), nunca dentro do projeto nem desta skill.
- Para ilustração 2D, buscar no Pinterest "<veículo> 2d vetor" (ex.: "caminhão betoneira 2d vetor"): rende mais
  vetor no estilo certo que "desenho lateral" ou termos em inglês. A miniatura `i.pinimg.com/236x/<hash>` vira a
  original trocando `236x` por `originals` (ou `736x`). Montar uma folha de contato numerada para escolher.

## 2. Medir (a geometria sai da conta)

1. `medir.mjs regua ref.png --saida r.png --zoom "…"` com recortes 4× em cada roda, no nariz, no teto e na traseira.
2. Ler: centro de cada roda (cruzamento dos diâmetros), linha do chão (base achatada do pneu), nariz (ponto mais à
   frente), topo do teto, traseira.
3. Escala: `px/m = (cx da última roda − cx da primeira) ÷ entre-eixos da ficha`. Sem ficha, pelo diâmetro do pneu
   (código no flanco), menos preciso.
4. `medir.mjs perfil` com chão, nariz e px/m: topo e base da silhueta a cada 5 cm, em metros. Os pontos do contorno
   da cabine saem daí (simplificar para os vértices que mudam a forma; quinas vivas marcadas em `quinas`).
5. Detalhes internos (porta, janela, grade, degraus): medir na régua ampliada e converter com o mesmo px/m.

⚠️ Recorte "no olho" sai em escala diferente e engana (o retrovisor ajustado de olho não foi reconhecido; medido
pixel a pixel, sim).

## 3. Inventário por região (antes de desenhar)

Listar, região por região, CADA detalhe visível com posição e tamanho em metros:
frente (para-choque, grade, faróis, defletores, degrau frontal) · cabine (porta, janelas, maçaneta, vincos, saias,
entradas de ar, defletor do teto, para-sol) · retrovisores (principal, grande-angular, de calçada, braço) · arco e
para-lama dianteiro · degraus e corrimão · chassi (longarina, travessas visíveis) · tanques (combustível, Arla,
cilindros de ar), caixa de bateria, escapamento/silencioso · quinta roda / carroceria · para-lamas traseiros, apara-
barro · luzes laterais e lanternas · rodas (estilo do aro, porcas, capa do cubo).
No fim, marcar cada item presente/ausente com motivo. Detalhe esquecido é metade das reclamações.

## 4. Construir

- Especificação → `montarLayout` → `vistaLateral`/`vistaDeCima`. Peças do kit para o que é padrão (rodas, chassi,
  tanques, degraus, luzes, tubos, vidros); a casca da cabine é desenhada pelos pontos medidos (`caminhoSuave` com
  quinas), com o arco da roda aberto por arco SVG (subtrair círculo inteiro com evenodd pinta a parte que sai da
  casca; o poço escuro fica só no semicírculo de cima).
- Ordem: sombra → chassi → tanques/caixas → poço → rodas → para-lamas → cabine → vincos → vidros → acessórios.
- Toda peça em `<g data-peca="…">` (o inspetor e o comparador dependem disso).
- Volume desde a 1ª versão: "caminhão real" costuma querer dizer ilustração com volume, não ajuste fino; retoque
  sutil ninguém vê.
- Proporção do conjunto: desenho novo ao lado de um vizinho da mesma família na mesma escala (roda, para-lama,
  altura do chassi). Desenho mais longo sai menor no cartão.
- Um desenho por vez: pesquisar, desenhar, conferir, mostrar e esperar o ok antes do próximo.

## 5. Conferir

- `inspecionar.mjs` sem erro.
- `comparar.mjs` com as âncoras nas rodas: IoU global e por região. Referência de foto raramente passa de ~85–90%
  (perspectiva, sombra, fundo); o que importa é a região que destoa: abrir o recorte dela.
- Recorte por região (referência em cima, desenho embaixo) na MESMA escala: frente, cabine, chassi, rodas, traseira.
- Miniatura no tamanho de uso: tem de continuar lendo como o veículo.
