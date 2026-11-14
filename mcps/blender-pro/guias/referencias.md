# Onde achar referência e medida

Ordem de preferência (mais exato primeiro):

1. **Manual / portal do implementador** (body builder) da marca: desenho lateral e de cima do
   chassi e da cabine **cotados** (entre-eixos, balanços, altura do chassi, posição de tanque e
   bateria). Exemplos: DAF BBI (dafbbi.com: cabines em 3D, formato JT, e desenhos), portais de
   implementador de Mercedes-Benz, Scania, Volvo, VW Caminhões e Iveco. É a melhor referência de
   caminhão que existe: medida de fábrica e vista ortográfica de verdade.
2. **Ficha técnica / catálogo do fabricante** (PDF no site da marca): dimensões gerais, pneus,
   configurações de eixo. Às vezes traz um desenho cotado nas últimas páginas.
3. **Pinterest "<veículo> 2d vetor"**: silhuetas laterais limpas, boas para proporção. Trocar `236x`
   por `originals` na URL da imagem para pegar o original. Conferir a geração do veículo.
4. **Fotos reais** (sites de venda, fabricante): 3/4 e detalhes. Foto tem perspectiva: não usar
   para medir, só para forma e detalhe.
5. **Modelos prontos** (para estudar ou partir deles): GrabCAD (procurar STEP), Sketchfab
   (CC-BY exige crédito), dafbbi (JT). Conversão em `guia("armadilhas")`.

Cuidados:
- Blueprint de site de terceiros costuma vir distorcido: conferir a razão comprimento/altura com a
  ficha técnica antes de confiar.
- A foto lateral com lente grande angular encurta a traseira: preferir desenho ortográfico.
- Baixar a referência para uma pasta local (scratchpad) e passar o caminho para
  `comparar_referencia` / `referencias_na_cena`.
- Ver a imagem antes de usar (abrir com Read) para saber a vista, para que lado está a frente e
  se precisa de `recorte` ou `espelhar`.
