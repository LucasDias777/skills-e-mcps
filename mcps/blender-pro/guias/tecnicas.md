# Técnicas de modelagem para ficar realista (Blender)

- **Medida real desde o começo**: unidade em metros, escala 1. Aplicar escala (`Ctrl+A`) antes de
  bevel/solidify, senão a espessura sai torta.
- **Espelho**: modificador Mirror no eixo lateral (X, com a frente em −Y) para tudo que é
  simétrico; aplicar só no fim. Detalhes assimétricos (escape, tanque, bocal, volante à esquerda no
  Brasil) entram depois, fora do espelho.
- **Nada tem quina viva**: Bevel (modificador) de 2–10 mm, 2–3 segmentos, limite por ângulo ≈30°,
  com "harden normals" ou Weighted Normal. É o que faz a luz desenhar a borda.
- **Lataria curva**: quads, Subdivision Surface nível 2 e loops de apoio perto das bordas; evitar
  n-gons em área curva. Para superfície grande e simples (caixa de carga, baú), malha baixa + bevel.
- **Folgas de painel**: porta, capô e tampa com vão de 3–5 mm (inset + extrude para dentro, ou
  peças separadas). Janelas recuadas 10–30 mm com borracha preta em volta.
- **Chapa**: Solidify de 1–3 mm em para-lama, saia e grade; nunca plano de espessura zero em peça
  vista dos dois lados.
- **Tubos, cabos, corrimãos, guidão, quadro de moto**: curva Bézier com Bevel Depth (raio real:
  corrimão ≈16 mm, cabo ≈3–5 mm). Converter em malha só no fim.
- **Repetição**: Array para parafusos (10 porcas da roda: Array com objeto vazio girando 36°),
  grelhas, degraus antiderrapantes, banda do pneu (Array + Curve ou Screw).
- **Booleana**: só para recorte que não dá para modelar; aplicar e limpar a malha logo depois.
- **Detalhe por camada**: forma primária (silhueta) → secundária (painéis, faróis) → terciária
  (parafusos, logos). Conferir a silhueta com `comparar_referencia` antes de ir para o detalhe.
- **Nomear as peças** com nomes que dizem o que são (`farol_esq`, `grade`, `pneu_tras_dir_ext`):
  `medir` usa os nomes para descobrir a frente e o usuário acha as peças.
- **Densidade**: gastar polígono onde a luz curva (roda, cabine, para-choque); caixa reta não
  precisa. Referência: um cavalo mecânico 6x4 detalhado tem ≈290 mil triângulos.
