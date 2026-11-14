# Guia de modelagem realista: índice

Temas (`guia(tema)`):

- **fluxo**: o passo a passo para modelar um veículo real (referência → medidas → blocagem → detalhe → material → conferência). Ler antes de começar qualquer modelo.
- **referencias**: onde achar referência e medida de fábrica (implementador, ficha técnica, Pinterest, CAD).
- **caminhoes**: cavalos, rígidos, implementos, limites legais do Brasil, chassi, quinta roda.
- **onibus**: urbano, rodoviário, double-decker, micro, articulado.
- **motos**: street, motoneta, scooter, trail, motofrete.
- **carros**: hatch, sedã, SUV, picape, van.
- **rodas-e-pneus**: como ler a medida do pneu e virar diâmetro, aros, rodado duplo.
- **tecnicas**: como modelar no Blender para ficar realista (bevel, subdivisão, curvas, espelho).
- **materiais**: valores de material realistas e o limite de metal no three.js.
- **conferencia**: a lista de checagem antes de mostrar ao usuário, com as ferramentas certas, e as regras de trabalho.
- **receitas**: vidro, interior da cabine, luzes, logos, pneus, paleta, conversão de DAE/STEP/JT/CAD e o roteiro de export.
- **armadilhas**: erros de API e de geometria que já custaram trabalho (SketchUp, CAD, conjuntos, edição).

Ferramentas do blender-pro: `medir`, `vistas_tecnicas`, `comparar_referencia`, `destacar`,
`referencias_na_cena`, `checkpoint`, `guia`, `olhar_de`, `sonda`,
`cruzamentos`, `pre_exportar` e `comparar_glb`. Para editar e olhar, use o MCP oficial
(`execute_blender_code`, `look`, `get_scene_info`).

- `olhar_de`: foto de qualquer ponto de vista (dentro da cabine, por baixo, pelo arco da roda) ou da
  vista atual do usuário; `apontar` diz qual peça e material estão em cada pixel.
- `sonda`: peça mais perto de um ponto; folga de um trajeto de tubo, mangueira ou escape.
- `cruzamentos`: peça atravessando peça.
- `pre_exportar`: o que vai sair diferente no GLB (ocultos, metal, textura sem UV, espelhadas).
- `comparar_glb`: cena × GLB peça por peça, antes de substituir e depois de exportar.

Convenção de eixos (Blender): Z para cima, metros. Veículo com a **frente em −Y**. Assim a
vista `frente` (olho em −Y) mostra a frente do veículo; a vista `direita` (olho em +X) mostra o lado
**esquerdo** do veículo (o do motorista no Brasil), com a frente à **esquerda** da imagem.
