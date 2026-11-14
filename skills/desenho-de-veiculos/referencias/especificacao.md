# Especificação do veículo (JSON, metros)

Um arquivo por veículo. É a fonte única das vistas 2D e do 3D: mudou uma medida, todas as vistas mudam juntas.

```json
{
  "nome": "Cavalo 4x2 teto alto (desenho próprio, sem marca)",
  "fontes": [
    { "medida": "entre-eixos", "valor": "3,80 m", "fonte": "ficha técnica do fabricante, PDF de 2020, p. 2" },
    { "medida": "altura", "valor": "3,95 m", "fonte": "estimada pela foto (escala pelo entre-eixos)" }
  ],
  "comprimento": 6.05, "largura": 2.49, "altura": 3.95,
  "eixos": [
    { "x": 1.43, "pneu": "315/80R22.5", "bitola": 2.05 },
    { "x": 5.23, "pneu": "315/70R22.5", "duplo": true, "bitola": 1.83 }
  ],
  "inventario": { "lateral": ["cabine", "vidro:2", "roda:2"], "cima": ["cabine", "rodas-de-cima:2"] },
  "ordem": [["cabine", "faixa-decorativa"]]
}
```

- `x` de cada eixo: metros do nariz (ponto mais à frente, para-choque) ao centro da roda.
- `pneu`: código métrico (`315/80R22.5`, `295/80R22.5`, `275/80R22.5`, `215/75R17.5`, `205/55R16`) → diâmetro pela
  conta `aro × 25,4 mm + 2 × largura × perfil`. Polegadas: só os da tabela do `kit/veiculo.mjs` (11R22.5, 12R22.5,
  1000R20, 1100R22…). Outro qualquer: informar `diametro` e `largura` (m) de ficha.
- `duplo`: rodado duplo (4 pneus no eixo). `bitola`: centro a centro dos pneus (no duplo, centro do par); sem ficha,
  o kit usa 2,05 (simples) e 1,82 (duplo). Anotar como estimado.
- `achatamento` (opcional, padrão 0,03): quanto o pneu amassa sob carga (o centro desce 3% do raio).
- `inventario.<vista>`: peças obrigatórias (`nome:mínimo`), conferidas pelo inspetor pelo `data-peca`.
- `ordem`: regras extras de quem fica atrás de quem (`[atrás, frente]`), somadas às padrão do inspetor.

## Medidas que costumam faltar (e onde achar)

| Medida | Onde |
|---|---|
| Entre-eixos, balanços, comprimento | Ficha/planta do fabricante (PDF "dimensions", "body builder", "Aufbaurichtlinien") |
| Altura da cabine, do chassi, da quinta roda | Planta do fabricante; guia do implementador (body builder guide) |
| Pneu de cada eixo | Ficha técnica; foto nítida do flanco (o código está escrito no pneu) |
| Bitola | Ficha técnica (track); senão, estimar e marcar |
| Largura | 2,49–2,55 m em pesado (limite legal 2,60 m no Brasil); confirmar na ficha |

Medida de foto vira número só depois de escalar pelo entre-eixos medido entre os centros das rodas, e conta como
"estimada pela foto" nas `fontes`.
