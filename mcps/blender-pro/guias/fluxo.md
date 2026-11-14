# Fluxo para modelar um veículo real

Modelo inventado a partir de uma frase sai genérico. O mesmo esforço contra uma referência e números
de fábrica sai parecido com o real. Nunca pular os passos 1 e 2.

1. **Identificar o veículo exato**: marca, modelo, ano/geração, versão (ex.: Scania R 450 6x4 2024,
   cabine Highline). A geração muda grade, faróis e cabine.
2. **Juntar a referência** (ver `guia("referencias")`):
   - vista lateral, frontal, traseira e de cima, de preferência ortográficas (desenho do
     implementador, blueprint, "2d vetor");
   - 3–6 fotos de 3/4 e de detalhes (roda, farol, grade, degraus, tanque, para-lama);
   - **ficha técnica**: comprimento, largura, altura, entre-eixos, bitola, pneus, balanços.
   Anotar as medidas numa tabela antes de abrir o Blender.
3. **Montar a cena de referência**: `referencias_na_cena` com as imagens e uma medida real (ex.:
   comprimento). As imagens aparecem só nas vistas ortográficas, atrás do modelo.
4. **Blocagem com medidas reais** (sem detalhe):
   - rodas primeiro: diâmetro tirado da medida do pneu (`guia("rodas-e-pneus")`), na posição exata
     dos eixos, encostadas no chão (Z = 0);
   - caixas grandes: cabine, capô, carroceria, chassi, tanque;
   - conferir já aqui: `medir` (entre-eixos, balanços, altura) e `comparar_referencia` na lateral e
     na frente. Corrigir proporção agora sai barato; depois do detalhe sai caro.
5. **Formas secundárias**: recortes de porta, janelas recuadas, para-lamas com folga real, grade,
   faróis, para-choque, degraus, retrovisores (são grandes em caminhão e ônibus).
6. **Detalhe terciário**: maçanetas, parafusos de roda, frisos, palhetas, logotipo, bocal do tanque.
   Só onde aparece na distância em que o modelo vai ser visto.
7. **Materiais** (`guia("materiais")`): borracha, plástico preto, vidro, metal, pintura.
8. **Conferência** (`guia("conferencia")`) e só então mostrar ao usuário: renders de frente, lado,
   cima e um de dentro, perguntando se ficou bom. Exportar só depois do "pode".

Durante o trabalho: `checkpoint` antes de qualquer operação grande (separar malha, apagar peças,
aplicar modificador, booleana). Um passo por vez, conferindo com `look`/`vistas_tecnicas`.
