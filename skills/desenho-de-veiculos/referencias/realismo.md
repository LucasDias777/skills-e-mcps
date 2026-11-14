# Realismo em SVG ortográfico

Luz única para todas as vistas e todos os veículos: de CIMA (céu), um pouco da frente. Os materiais do
`kit/materiais.mjs` já seguem estas regras; use-os em vez de cor chapada (o inspetor avisa superfície grande chapada).

## Superfícies

- **Degradê de 4–8 paradas**, com leve variação de matiz; 2 paradas fica chapado. `color-interpolation="linearRGB"`
  (meio-tom sem escurecer). Paradas saem de uma regra (a curvatura/normal), não digitadas no olho; luminância
  monotônica, exceto cromo (que alterna claro/escuro de propósito).
- **Cinco zonas** num corpo curvo: especular (clara, quente) · luz · meio-tom (a cor verdadeira) · sombra própria
  (mais fria, NUNCA preta) · luz refletida na borda da sombra (10–20%).
- **Pintura brilhante em face vertical** (lateral da cabine, porta, baú): reflete o horizonte, mais clara e fria
  em cima (céu), transição suave a ~45% da altura, mais escura e quente embaixo (chão), uma faixa clara de luz
  refletida na borda de baixo. Forte demais vira "pintura de duas cores": manter a transição em 2–3% e o contraste baixo.
- **Face plana paralela à vista** tem um tom só; os tons mudam onde a superfície VIRA (raio do teto, quina da cabine,
  chanfro do para-choque). Vincos = linha de luz em cima + linha de sombra logo abaixo (`vinco`).
- **Cilindro deitado** (tanque, cilindro de ar, escape): faixa de brilho a ~25% da altura, escurece até ~85%, luz
  refletida na base; as pontas escurecem (a tampa vira para longe).
- **Cromo/metal polido**: bandas alternadas de alto contraste (#f6f8fa ↔ #56606b), filete quase branco nas arestas.
  **Aço/alumínio fosco**: monotônico, frio. **Borracha**: preto azulado com brilho mínimo em cima. **Plástico preto**:
  quase sem brilho, filete claro na aresta de cima.
- **Vidro**: base escura e fria, mais clara no alto; faixa de reflexo diagonal larga + uma fina (opacidade ~0,5),
  recortadas pelo vidro; borracha de vedação escura em volta.
- **Cavidades** (poço da roda, vão sob o chassi): conjunto de tons mais escuro, mas com volume (mais fundo no alto).
- **Sombras**: de contato sob cada pneu (elipse rasa) e sob o veículo inteiro, com degradê radial, não filtro
  (filtro em cada peça pesa: na galeria do Guelgi, 8 mil `feDropShadow` deixavam a página lenta). Cor fria, não preta.

## Peças

- **Roda de lado = peça torneada vista de frente**: anéis concêntricos (banda com ranhuras, ombro, flanco, aba do
  aro, disco abaulado com furos de mão, prato do cubo, porcas no círculo de furação, capa). Círculo é `<circle>` ou
  arco, nunca polígono (faceta aparece no zoom). Pneu achatado no chão.
- **Pneus duplos**: de lado, só o de fora aparece; de cima, dois corpos com folga visível entre eles.
- **Tubos** (linha de ar, escape, corrimão, para-choque tubular): corpo + faixa de brilho do lado da luz + sombra do
  outro lado; curva de raio ≥ 2,6× o raio do tubo; TODA ponta termina num conector, flange ou suporte; nada
  atravessa outra peça (manter ~1,5 raio de folga); onde algo abraça o tubo, o tubo se interrompe ali.
- **Texturas terminam numa aresta real** (ou esmaecem): barras da grade vão de moldura a moldura; frisos do baú de
  borda a borda; ranhuras do degrau fechadas; parafusos em fileiras completas. Nunca parar no meio da chapa.
- **Ordem de pintura**: de trás para a frente; peça que envolve outra (cinta do tanque, abraçadeira) é desenhada
  depois; peça que atravessa outra vira dois trechos. Recorte por `clip-path` é aresta: precisa de traço.
- **Contato**: tudo apoiado em algo (tanque na cinta, cinta no suporte, para-lama no chassi); nada flutua nem afunda.
- **Detalhe miúdo** dá densidade pela estrutura (parafusos, frestas, borrachas), não por textura de ruído.

## Lições (erros que já aconteceram)

- Em 1× parecia certo; no zoom, cabos atravessavam dutos → medir, não olhar só em 1×.
- Cores chapadas liam como grade/bloco listrado ao lado de desenhos com volume → volume desde a 1ª versão.
- Desenho fiel à planta mas fora da proporção da galeria ficou "desproporcional" → roda, para-lama e altura do chassi
  seguem os vizinhos do conjunto.
- Polígono de muitos lados ao lado de curva lisa parece entalhe; preenchimentos encostados deixam fresta (sobrepor ~0,5 px).
