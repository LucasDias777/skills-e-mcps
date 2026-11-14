# Inspeção de qualidade

## Automático (`ferramentas/inspecionar.mjs`)

Mede no navegador, no espaço da raiz do SVG (considera `transform` e `clip-path`). ERRO reprova; AVISO tem de ser lido.

| Regra | Confere |
|---|---|
| estrutura | `<svg>` com `data-vista`, `data-px-por-metro`, `data-x0` (e `data-chao`/`data-meio`) |
| fora-do-quadro | toda `data-peca` dentro do viewBox (±1 px) |
| roda-no-chao | base do pneu (`data-parte="pneu"`) na linha do chão ±0,6 px |
| roda-concentrica | aro, cubo e porcas concêntricos ao pneu (±0,5 px) |
| contagem / posicao-do-eixo / raio-do-pneu | número de rodas, x de cada eixo (±1 cm) e raio (±1,5%) contra a especificação |
| pneus-do-eixo / simetria | de cima: 2 pneus (simples) ou 4 (duplo), espelhados no meio do veículo |
| entre-vistas | os eixos caem no mesmo x na lateral e na de cima (±1 cm) |
| abaixo-do-chao | nada além do pneu e da sombra passa do chão |
| para-lama | centrado sobre a roda do seu eixo (aviso) |
| ordem-de-pintura | em toda sobreposição, quem está na frente vem depois no SVG (padrão + `spec.ordem`) |
| inventario | peças obrigatórias da `spec.inventario[vista]` presentes |
| cor-chapada | superfície grande (> 1,5% do quadro) sem degradê (aviso) |
| circulo-poligonal | polígono imitando círculo (aviso) |

Ocupação do quadro sai no resumo (alvo 55–75%).

## Manual (olhando os PNGs)

Em 1× e na miniatura: lê como o veículo certo? Proporção cabine × chassi × rodas igual à referência?
Em 3×, região por região, procurar nesta ordem:
1. Peça faltando (comparar com o inventário).
2. Tubo/cabo atravessando peça, terminando no ar ou numa braçadeira.
3. Textura parando no meio da chapa; parafuso fora da fileira.
4. Fresta entre preenchimentos encostados; contorno serrilhado (costura desenhada depois do contorno).
5. Reflexo de vidro saindo do vidro; sombra preta pura; superfície grande chapada.
6. Peça flutuando (tanque sem cinta, para-lama sem suporte) ou afundada em outra.
7. Perspectiva misturada: em vista ortográfica nada mostra a face de cima ou o lado de dentro.
8. Detalhe da referência que mudou de lugar (porta, maçaneta, degraus, luzes): medir no recorte lado a lado.
