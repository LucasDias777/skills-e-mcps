# Receitas que funcionaram

Soluções já testadas em modelos de caminhão reais. Ler a seção da tarefa antes de inventar outra.

## Vidro de cabine

Não é uma casca só, é um empilhamento. Todas as camadas: cor preta, metal 0, IOR 1,5, blend BLEND,
**backface culling ligado**, faces duplicadas e invertidas.

| onde | camadas | alpha | rugosidade | transmissão | espaçamento |
|---|---|---|---|---|---|
| janela lateral | 3 | 0,232 | 0,20 | ≈45 % | 0 / 9,6 / 20,0 mm |
| para-brisa | 2 | 0,409 (fora) / 0,232 (dentro) | 1,00 | ≈35 % | 0 / 5,7 mm |

- Transmissão = Π(1 − alpha) das faces de frente. Medir por interseção raio × triângulo, fora das
  arestas (o `ray_cast` normal não vê cascas coincidentes).
- **Vidro novo seguindo a lataria**: grade de raios de 1 cm + flood fill a partir do centro da janela →
  superfície ajustada por IRLS na face INTERNA da moldura → dilatar 1 célula → quads +
  `dissolve_limit` 1,5° → casca dupla → repetir nos espaçamentos da tabela.
- ⚠️ Em modelo de CAD, a borda opaca do para-brisa pode cobrir a quina inteira e, de fora, parecer uma
  placa preta. No caminhão real a quina é vidro com filete preto: tirar a faixa a mais de 2,5 cm da
  borda externa e pôr vidro só onde o vidro claro não cobre (senão ficam 4 camadas, mais escuro).

## Interior da cabine

- Cabine oca precisa de interior desenhado, não de vidro mais opaco: caixas `#0b0b0d` rugosidade 0,85
  (piso, painel, console, bancos, volante e **forro**, o que mais importa). O forro para na base da
  janela.
- **Separar carcaça e interior por ILHA**: se alguma face da ilha "escapa" (raio sem bater em nada) em
  ≥ 6 de 48 direções, fora da caixa do interior, a ilha é carcaça; os vidros entram como oclusores.
  Depois, teste de feixe (5 raios a 1,5 cm) nas lascas e teste de câmera. Em malha densa, raios densos
  (1.024 direções; 64 é esparso demais).
- 🚫 Não funciona: critério por normal da face (normais inconsistentes); "visível de fora" por raio (o
  raio entra pela janela e marca painel e bancos como carcaça); propagação por vizinhança (atravessa
  da casca externa para a interna).
- **Forro seguindo as linhas**: UMA pele radial a partir do centro da cabine, grade de 1,2° contra uma
  `BVHTree` só da carcaça e dos vidros. Bate em vidro = janela (furo); abaixo da base da janela = fora.
  Raio = MÍNIMO da vizinhança 3×3 − 3 cm (sem isso a pele corta os vincos do teto e aparece de fora).
  Borda por marching squares + bisseção de 7 raios, 2 mm além da quina (filete de vedação, sem
  serrilha). Zênite fechado com leque. Prova: `destacar` nas peças do interior, por fora, em 3 ângulos,
  nada aparecendo. Forro em várias grades separadas fura o teto.
- **Painel ajustado à cabine**: caixa reta deixa folga de ~10 cm até o para-brisa. Fazer por fatias de
  1,5 cm, com a base do vidro achada por raio em cada fatia, a borda da frente 4 mm abaixo dela e cada
  vértice preso à parede daquele ponto (pegar o mínimo da região inteira estreita o painel todo).
- Bancos espaçados ENTRE SI, não encostados nas portas; o volante acompanha o banco do motorista.
- Frestas do assoalho mostrando o que não deve: pele fina de 2 mm por baixo ou "tapete" 4 a 5 mm
  acima, em vez de repintar.
- Peça interna nasce ajustada por raio, e a conferência é com `olhar_de` de dentro da cabine.

## Luzes

- Farol principal com lente ESCURA (lente branca não lê como farol); auxiliares claros. Pisca: metade
  de cima âmbar, metade de baixo cristal.
- **Textura de farol a partir de foto de frente**: recortar pelos 4 cantos da moldura e endireitar com
  `Image.transform(QUAD)` (PIL); UV por HOMOGRAFIA dos 4 cantos da lente vista de frente, com o lado
  externo em u = 0 nos dois faróis (a imagem espelha sozinha). Peças vizinhas da lente com a MESMA
  homografia, senão fica uma mancha clara. Foto CC BY-SA exige crédito e a mesma licença.
- Textura de 64×64 não serve para farol. Artefato em luz se corrige na geometria e nas normais, não
  trocando a textura.

## Logos e letreiros

- Logo oficial: SVG do Wikimedia Commons → PNG empacotado; material com cor + alfa; objeto fino 0,8 mm
  acima da superfície. ⚠️ Com a frente em +Y, a direita da tela é −X: u = (x1 − x)/L, senão sai
  espelhado.
- Letreiro em GEOMETRIA: apagar as letras, `text_add` → `convert(target='MESH')` → `transform_apply` →
  escalar os VÉRTICES (a `scale` do objeto não serve com a rotação de 90° em X).
- Emblema pequeno: relevo ao contrário (estrela clara saliente sobre miolo escuro).
- Logo ou escrita sobre chapa BRANCA tem de ser escuro (cromo claro some).
- 💡 Varrer escritas num modelo: as imagens da cena (texto em textura), os nomes de objeto fora do
  padrão e as vistas dos dois lados, frente, traseira e teto. Boa prática: nome de pessoa ou empresa
  sai, a marca do fabricante fica. Remover = mover para uma coleção `BK_*_REMOVIDOS` EXCLUÍDA da camada
  de vista (não exporta e dá para voltar).

## Pneus de malha do SketchUp

Pneus da mesma cor dos dois lados, com o estriado:

1. **Flanco**: faces escuras → material da gêmea cinza.
2. **Banda**: a textura da banda remapeada em cinza (gerada com PIL e EMPACOTADA), num material
   próprio (rugosidade 0,9, dupla face), nas DUAS camadas: a UV passa da face texturizada para a gêmea,
   casando face por centro e canto por posição.
3. **Disco do aro** escuro por dentro: gêmea escura × gêmea clara → trocar pela clara, nas rodas e nos
   estepes.
4. **Estepe espelhado escuro**: inverter os cantos contra a face (ver `guia("armadilhas")`).
5. **Conferência espelhada**: Workbench FLAT, ortogonal, lado +X espelhado sobre −X (errar o eixo em
   5 mm vira contorno), por fora, por dentro (`clip_start`) e nos estepes. Bom: ≈0,6 % de pixels
   diferentes. Para normais: STUDIO dos dois ângulos.

⚠️ Os nomes das peças (`ID1234` e afins) mudam de arquivo para arquivo, e um implemento sozinho pode
ter outra origem de coordenadas que o mesmo implemento dentro de um conjunto.

## Paleta de referência (cores lineares)

Lataria branca 0,888 rugosidade 0,4 (= `#f2f2f2`) · cinza de chassi e interior 0,227 · pneu 0,118
rugosidade 0,9 · aro 0,788 · borracha preta 0,03 rugosidade 0,85 · banco 0,019 rugosidade 0,55 ·
espelho 0,55/0,60/0,64, metal 0,3, rugosidade 0,08 · prata 0,654/0,685/0,701, metal 0,3, rugosidade
0,2 · tanque e escapamento `#c3c7cb`, metal 0,85, rugosidade 0,22 (no render; no three.js sem envMap,
metal ≤ 0,3).

- ⚠️ Peça que não é lataria não pode ter o material nem a cor da lataria: se o app repinta a lataria,
  ela vai junto (retrovisor, palhetas).
- Metades da cabine com tons diferentes: limpar (nunca inverter) as custom normals das peças com
  `determinant() < 0`. 🚫 Só em chapa de cabine; em pneu e roda cria manchas.
- Rodas boas para um modelo novo: copiar as de um modelo já aprovado, extraídas do GLB num Blender de
  fundo.

## Modelos que vêm de fora (DAE, STEP, JT, CAD)

- Listar o que tem dentro e mostrar antes de converter: capa de biblioteca mente. Mandar arquivo para
  um site externo: autorização a cada arquivo.
- **`.dae` do SketchUp / 3D Warehouse** (e "zip" que na verdade é COLLADA: ler o cabeçalho): o Blender
  5.2 não importa Collada. `npm i assimpjs` numa pasta FORA do projeto → `ConvertFileList` com o `.dae`
  e todos os arquivos referenciados, repetindo os caminhos relativos → copiar a pasta das texturas para
  junto do `.gltf` → `npx @gltf-transform/cli copy result.gltf saida.glb`. A polegada vira metro
  sozinha. O assimp funde as geometrias, mas a separação por material sobrevive. As linhas do SketchUp
  viram primitivas de LINHA → `delete_loose`.
- ⭐ **STEP** é o melhor caminho, 100 % local: `pip install cascadio`;
  `cascadio.step_to_glb(entrada, saida, tol_linear=1.0, tol_angular=0.5)`. `tol_linear` é em mm (o
  padrão 0,1 explode o arquivo); já converte mm em m; rodar em segundo plano. A estrutura de peças e a
  montagem sobrevivem. AP203 vem sem cor. Procurar sempre a versão STEP primeiro (o GrabCAD lista os
  formatos).
- **SolidWorks nativo**: não há leitor aberto. O convert3d.org converte em WASM no navegador (nada
  sobe), mas a montagem se perde (peças na origem de modelagem). Preferir STEP.
- **Creo nativo**: não há leitor aberto. O 3dencoder.com converte, mas manda o arquivo para fora:
  autorização a cada arquivo. `head -c 120` no `.prt` diz o CAD e a versão.
- **JT (Siemens)**: o Blender não lê. Listar os segmentos pela TOC (cabeçalho de 80 bytes, ordem de
  bytes, um int32 vazio e o offset da TOC; o tipo é o byte alto do `attr`): com `Shape LOD0` é malha
  pronta; só com `XT B-Rep` é Parasolid. Malha: `pip install aspose-3d` num venv fora do projeto →
  `Scene.from_file(jt).save(glb, FileFormat.GLTF2_BINARY)`. Ele copia o JT cru (mm, Z para cima, a
  frente depende do fabricante): corrigir sem tocar nos vértices com um nó-raiz `matrix`. Exemplo para
  frente em −X: `[0,0,-s,0, -s,0,0,0, 0,s,0,0, 0,0,0,1]` com s = 0,001 dá metros, Y para cima e frente
  em +Z.
- **GLB de site (meshopt + quantizado)**: `@gltf-transform/{core,extensions,functions}` +
  `meshoptimizer` numa pasta de trabalho → ler com `meshopt.decoder`, `dispose()` do
  `EXT_meshopt_compression`, `dequantize()`, `dispose()` do `KHR_mesh_quantization`,
  `clearNodeTransform` em cada nó com malha (a quantização guarda a escala no nó). Conferir a caixa por
  peça contra o original e importar num Blender de fundo (o 5.2 lê webp).
- 💡 Teste de integridade de modelo convertido: contar malhas com face cruzando o meio do comprimento
  (0 = modelo partido). O vão se mede por FACES, não por vértices.
- PDF de manual sem poppler: extrair as imagens varrendo os bytes `FFD8FF`…`FFD9`.

## Exportar e provar

- **Roteiro**: `comparar_glb` (cena × GLB a substituir) → `pre_exportar` → `checkpoint` → exportar para
  um arquivo TEMPORÁRIO → `comparar_glb` (GLB novo × cena) → backup `<nome>_ANTES.glb` → só então
  copiar por cima, e só com o "pode" do usuário.
- Validar por reimport num Blender de fundo: número de malhas e faces, caixa e pico da cabine iguais =
  sem giro.
- 💡 Medir GLB sem abrir o Blender: script Node que lê o chunk JSON, acumula as matrizes dos nós e usa
  `min`/`max` dos accessors de POSITION.
- **Otimizar para a web**, uma vez só e a partir do original:
  `npx @gltf-transform/cli optimize <original> <saida> --simplify false --compress meshopt --texture-compress false`.
  Simplificando: rodas vão inteiras (roda igual a outra vira nó reaproveitando a malha); `Permissive` +
  peso de normal 0,5 + erro de 3 a 5 mm; vértices na divisa de duas cores travados (senão o retalho de
  cor some).
- 💡 Modelo feio só num lugar (no app e não no Blender): renderizar nos dois e comparar.
