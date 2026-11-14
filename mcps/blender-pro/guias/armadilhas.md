# Armadilhas (API e geometria)

Erros que já custaram trabalho de verdade. Ler antes de um script grande, de exportar ou de editar
malha importada.

## API do Blender (5.2) pelo MCP

- Nó de shader se procura por TIPO (`n.type == "BSDF_PRINCIPLED"`), nunca por nome: a interface é
  localizada e `nodes["Principled BSDF"]` devolve None.
- Não fixar identificador de enum de cabeça: ler de `bl_rna.properties[...].enum_items`. No 5.2 o
  engine é `BLENDER_EEVEE`.
- Quebrar a tarefa em chamadas pequenas (importar / medir / pintar / exportar). GLB grande (15 MB+) ou
  script com mais de 1 milhão de raios estoura o retorno do MCP ("No data received"), mas o script
  termina: consultar o estado na chamada seguinte, não repetir.
- 🚫 **Nada demorado no Blender aberto do usuário** (~500 mil `scene.ray_cast` numa cena com dois
  caminhões, ~9.400 objetos, travaram o Blender por mais de 1 hora; script no add-on não se cancela
  de fora). Medir o custo com 100 iterações antes de um laço grande; raio em volume vai numa
  `BVHTree` só das malhas da região (como `sonda` e `cruzamentos` fazem; os mesmos 500 mil raios levam
  8 s); limite de tempo dentro do script; análise pesada num Blender de FUNDO
  (`blender -b <checkpoint> --python script.py`). Salvar `checkpoint` antes de conferência demorada.
- Exportar GLB no 5.2: `export_loglevel >= 0` quebra (KeyError 'loglevel'); para calar o log, usar
  `bpy.app.debug_value = 3` e devolver no fim. Exportar por seleção dos visíveis e devolver a seleção.
- **Export padrão**: `use_selection` dos visíveis da coleção do modelo, `export_apply`, `export_yup`.
  Esconder ou excluir antes as coleções de backup e de referência (`BK_*`, `REFERENCIAS`), porque o
  export pega os visíveis, e tirar atributos auxiliares criados por script.
- ⚠️ Cena com a frente em +Y: girar as raízes 180° em Z só durante o export e desfazer depois, senão
  o GLB sai de ré.
- ⚠️ O import glTF é Z-up: o comprimento, que no three.js é Z, vira Y.
- Medir na cena superestima o arquivo: o reimport recria custom normals em tudo. Conferir o GLB
  reimportado (ou `comparar_glb`), não a cena.
- ⚠️ O Workbench não mostra transparência: vidro se confere no EEVEE com luz. Render de conferência
  com a cena em EEVEE: trocar para `BLENDER_WORKBENCH` dentro do `try` e devolver no `finally`.
- ⚠️ `render.opengl(write_still=True)` fotografa o VIEWPORT: passar `view_context=False` e orientar a
  câmera por `to_track_quat('-Z', 'Y')`. Já fez concluir sobre um modelo olhando outro.
- ⚠️ Screenshot da viewport com o Blender minimizado devolve imagem velha: conferir por render de
  câmera (ou `olhar_de`).
- ⚠️ O modo Sólido e o Workbench mostram a cor de VIEWPORT (`diffuse_color`), não a Base Color: igualar
  as duas antes de conferir cor por eles.
- ⚠️ "Manchas" no modo Sólido podem ser o contorno de objeto nas emendas de uma malha cortada em várias
  (o import corta a cada 65.532 vértices): somem com `show_object_outline = False`.
- ⚠️ Textura de banda de pneu numa faixa lisa não aparece no modo Sólido: cor de viewport = Base Color
  (ou a média da imagem, convertida) e Solid › Color › **Texture**.
- ⚠️ `o.bound_box` é cache: depois de editar `v.co` por script, medir por `matrix_world @ v.co` e
  chamar `view_layer.update()`.
- 🚫 Objeto oculto (`hide_set`) não entra em `transform`, e o operador não reclama: reexibir antes e
  conferir a caixa depois.
- 🚫 `object.duplicate` + `translate` deixa a cópia parenteada, na origem: posicionar por
  `novo.matrix_world = Matrix.Translation(d) @ o.matrix_world` com `novo.parent = None`.
- ⚠️ `o.matrix_world.to_3x3() @ normal` inverte a normal em peça com escala negativa: usar a normal do
  `ray_cast` ou multiplicar pelo sinal do determinante.
- 🚫 `scene.ray_cast` devolve o índice do polígono TRIANGULADO: para saber se a face foi a primeira
  atingida, comparar a distância do acerto ao centro da face, não o índice.
- ⚠️ `image.pixels` de imagem 8 bits sRGB (as dos GLB) vem codificado em sRGB, não linear (média 0,405
  = 0,137 linear): converter antes de comparar com Base Color. Imagem float (`is_float`) vem linear.
- ⚠️ No 5.2, input de modificador de nós se lê em `mod.properties.inputs.<identifier>.value`
  (`mod["Input_1"]` dá erro).
- 🚫 Ao limpar a cena (purge), tirar as câmeras das coleções antes: o purge leva junto.
- 🚫 Depois de trazer a cena por append, `matrix_world` das peças em coleção EXCLUÍDA vem zerado. Ler
  pela cadeia de pais (`mundo(o) = mundo(o.parent) @ o.matrix_parent_inverse @ o.matrix_basis`) ou
  tirar o `exclude`, chamar `view_layer.update()` e excluir de novo.
- ⚠️ Conferir peça refeita contra um checkpoint: `bpy.data.libraries.load(ck)` com
  `dst.meshes = [nome]`, comparar vértices ordenados e apagar a malha. O append duplica os materiais
  (`.001`): trocar pelos da cena e apagar.
- 💡 Backup de malha como `BK_<malha>_<motivo>` com fake user antes de cada mudança; guardar os
  índices de material num `.npy` antes de repintar.
- ⚠️ Script com caminho do Windows: usar strings `r'…'` (senão `\U` vira escape).
- O Blender 5.2 não importa Collada (.dae) nem JT: converter antes (`guia("receitas")`, seção
  "Modelos que vêm de fora").

## Geometria em geral

- 🚫 Apagar faces em EDIT MODE com vários objetos: a seleção propaga e apaga tudo. Uma peça por vez.
- 🚫 `make_single_user` antes de editar malha compartilhada (`users > 1`). Material usado por mais de
  um objeto: copiar antes de pintar.
- ⚠️ Nome mente (arquivo, peça, escrita): achar peça pela FORMA e pela posição e marcar com cor
  (`destacar`) antes de pintar ou apagar.
- ⚠️ O bbox cru mente quando há malha de anotação longe: usar percentis ou filtrar.
- ⚠️ A frente varia por arquivo: descobrir pelo perfil de altura máxima (a cabine é o pico). `medir`
  já faz isso e diz as evidências.
- 💡 Configuração de eixos em dois histogramas: vértices por faixa de comprimento abaixo da altura da
  roda, e centros das rodas na largura, por eixo (2 = simples, 4 = duplo).
- ⚠️ Z-fighting: face de outro objeto a menos de 0,8 mm e paralela (|n·n| > 0,99). Afastar ≥ 0,8 mm;
  folga de 1,5 mm é arriscada de longe, melhor recuar para trás da parede interna da peça oca. Peça
  enfiada 1 cm em outra dá manchas ovais escuras: afastar o conjunto.
- ⚠️ Espelhar peça inverte as normais: `reverse_faces` + limpar custom normals; conferir.

## Malha do SketchUp (3D Warehouse)

- **Face dupla**: cada superfície vem duas vezes, com winding oposto, gêmeas coincidentes SOLDADAS nos
  mesmos vértices, às vezes com materiais diferentes. 🚫 **Remover metade quebra o modelo** (a frente
  fica preta). Só é viável invertendo o winding das que ficaram para dentro; com materiais diferentes,
  a face de menor índice é a frontal; com material igual, manter a virada para fora (o teste pelo
  centroide falha em chapa plana).
- **Sem vértices soldados**: cada triângulo é uma ilha e `separate LOOSE` gera um objeto por face.
  Soldar antes (`remove_doubles` 1e-4) ou agrupar ilhas por posição arredondada.
- Os materiais não são por peça: pintar por ILHA + posição.
- ⚠️ A numeração de ilhas muda a cada `mesh.separate`: recalcular e reidentificar pela posição.
- 🚫 Pneu "cinza de um lado e preto do outro" = face dupla com materiais diferentes + lado espelhado,
  NÃO normal invertida (receita em `guia("receitas")`).
- 🚫 Nunca limpar custom normals de pneu, roda ou peça de face dupla: a média das normais opostas vira
  lixo e gera manchas junto ao aro. Se já limpou, restaurar do GLB original num Blender de fundo
  (`corner_normals` → `normals_split_custom_set`).
- ⚠️ Peça espelhada (det < 0) ESCURA com luz e igual com luz chapada = normais, não material. A fração
  de cantos com `normal · face < 0` sozinha não condena (toda peça com det < 0 dá ~100 %); quem decide
  é o render STUDIO dos dois ângulos espelhados. Corrigir invertendo só os cantos contra a face
  (`normals_split_custom_set`), nunca limpando.
- 💡 Numa roda do SketchUp, face escura gêmea de uma face clara (aro) ou cinza (pneu) é a camada
  errada. Conferir por raio da câmera antes de mexer.
- Chapa quase plana feita de triângulos tortos: dar a todas a mesma normal média, não a da face.
- Material translúcido escondido: conferir o alpha dos materiais da peça.

## Conjuntos (cavalo + implemento)

- 🚫 O conjunto importado pode ter mais de uma raiz com o mesmo nome: apagar pela LISTA de nomes
  importados, nunca por padrão de nome (leva a outra unidade junto).
- 🚫 Reconciliar por nome acha falso positivo (peças com nome igual nas duas unidades): conferir a
  posição.
- 💡 Separar implemento de cavalo: a unidade seguinte é o gabarito (peça sem par é do cavalo); a
  suspensão fica no terço final; cortar exatamente no vale do perfil de altura.
- 🚫 Malha fundida por otimizador (`gltf-transform optimize`) não se separa por janela geométrica:
  partir do original.

## Editar geometria

- 🚫 Esticar ponta de peça: selecionar a ILHA da peça, nunca "vértices perto do eixo de outra peça"
  (se a peça está fora de centro, pega só parte do anel e entorta).
- ⚠️ `bisect` em quads grandes: selecionar por "algum vértice à frente do plano", nunca pelo centro da
  face.
- ⚠️ Classificar roda por raio: limitar também pela largura do pneu, senão pega molas, pedaleiras e
  parafusos.
- ⚠️ Endireitar roda é alinhar a NORMAL DO DISCO (autovetor de menor variância dos vértices do pneu),
  não zerar a rotação (deita a roda). Girar em torno do centroide, não da caixa.
- 💡 Alongar sem deformar = corte de estiramento entre duas nervuras, não escala.
- Girar peça: girar as custom normals junto (`normals_split_custom_set`).
- Espelhar peça: `w.x = 2·CX − w.x` em mundo + `reverse_faces` + limpar custom normals; conferir pela
  soma dos centros. Peça assimétrica de fábrica: `bisect` em X = CX e espelhar a metade boa
  (UV u → 1 − u).
- 💡 Rasgo em malha cortada: achatar os vértices não fecha; cobrir com chapa seguindo o contorno.
- 💡 Malha aberta: não remendar; montar peça nova copiando a que presta.
- **Reconstruir superfície**: seções + ajuste robusto (polinômio com descarte MAD, IRLS) + Hermite.
  Reamostrar borda por FRAÇÃO DE ARCO, não por ângulo (serrilha). 🚫 Puxar vértice a vértice para o
  "ponto mais próximo" de malha com poucas faces dá rugas; prender vértices numa curva amassa.
- Medir altura de arco: raio do centro do eixo para cima (amostrar vértices do para-lama pega as
  paredes). Folga pneu e para-lama: empurrar o arco radialmente.
- **Animação com roda girando**: na velocidade real a roda gira 137 a 153° por quadro e cria efeito
  estroboscópico (parece parada ou girando para trás). Usar ~22° por quadro e conferir 4 quadros
  seguidos sem motion blur.

## Malha de CAD (STEP, Sketchfab)

- Malha de CAD é limpa: os gotchas de SketchUp não valem para ela.
- 🚫 `remove_doubles` em malha com custom normals (`has_custom_normals`) rasga a peça. Mover vértice
  também invalida as normais. Preferir criar peça nova a editar a malha CAD; mover uma faixa de
  vértices ao longo do próprio plano preserva as normais.
- 💡 Sumir com rebaixo ou vinco da lataria: cobrir com uma tampa ajustada por IRLS, 1 mm à frente na
  borda e 2 mm no centro, sem mexer na malha.
- ⚠️ Raio cai DENTRO das cavidades de peças apagadas: amostrar em volta e ajustar a superfície (IRLS
  com peso de Tukey).
- 🚫 Modelo inclinado: corrigir GIRANDO, nunca com shear. Assinatura: média ponderada por área do
  ângulo das faces quase horizontais.
- 🚫 Trocar slot de material procurando pelo nome de outro modelo falha em silêncio: reler o material
  depois da troca.
- ⚠️ Slot de material existir não quer dizer que tem faces: achar a região por raio a partir do eixo e
  repintar.
- ⚠️ Simetria: medir o plano pela mediana dos pares de peças (rodas e chassi podem dar outro valor).
  Uma cópia de um lado pode ter sido transladada em vez de espelhada.
- Modelo assimétrico de fábrica: pintar pela posição da face, não o objeto inteiro.
