# Materiais realistas

Valores em cor **linear** (o que vai no Principled BSDF). Cor pura (0 ou 1) não existe no mundo
real: preto ≈0,02–0,04; branco ≈0,75–0,85.

| material | base color (linear) | metal | rugosidade | nota |
|---|---|---|---|---|
| borracha de pneu | 0,025–0,04 | 0 | 0,85–0,95 | lateral um pouco mais clara que a banda |
| plástico preto (para-choque, grade) | 0,02–0,04 | 0 | 0,45–0,7 | texturizado = rugosidade alta |
| pintura sólida | a cor | 0 | 0,25–0,4 | no Blender: Coat 1,0 / rugosidade 0,03 dá o verniz |
| pintura metálica | a cor | ≤0,3 (three.js) | 0,3–0,4 | no render puro do Blender pode ir a 0,6–0,9 |
| cromado / alumínio polido | 0,6–0,8 | ≤0,3 (three.js) | 0,15–0,3 | no render do Blender: metal 1, rugosidade 0,05 |
| aço da roda (pintado) | cinza 0,3–0,5 | 0 | 0,4–0,5 | |
| vidro escuro | 0,02–0,05 | 0 | 0,05–0,1 | |
| lente de farol | transparente | 0 | 0,02 | refletor atrás (cinza claro, rugosidade baixa) |
| luz acesa (DRL, lanterna) | a cor | 0 | não se aplica | Emission, num material próprio |

## Modelo para three.js (mapa ou app web)
- **Metal ≤ 0,3** quando a cena não tem envMap: metal alto fica preto ou some em peça pequena.
  `medir` avisa quais materiais passam disso.
- Se o app troca a cor da lataria (pelo estado do veículo, por exemplo), deixar a lataria branca e
  num material próprio.
- Textura só quando necessário (logos, letreiros); cor sólida é mais leve e aceita troca de cor.
