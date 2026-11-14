# Conferência antes de mostrar ao usuário

1. **`medir`**:
   - dimensões contra a ficha técnica (±2 %);
   - nº de eixos, entre-eixos e balanços; diâmetro das rodas contra a medida do pneu;
   - "apoiado no chão" (Z mínimo = 0) e frente para o lado certo (−Y por convenção);
   - simetria ≥ 95 % a 1 cm em veículo simétrico (as diferenças devem ser os detalhes reais:
     escape, tanque, volante);
   - avisos: metal > 0,3, escala negativa, escala não aplicada.
2. **`vistas_tecnicas`** (lado, frente, cima, trás): silhueta, proporção e alinhamento na grade;
   eixos e cotas batem com a ficha.
3. **`comparar_referencia`** na lateral e na frente: IoU ≥ 0,90 é bom; ≥ 0,95 é ótimo. Olhar o
   perfil de cima (onde o modelo está mais alto/baixo) e corrigir o que passar de ≈3–5 cm.
4. **`look`** (MCP oficial): 3/4 com material, wireframe (topologia) e closes de roda, farol,
   grade e interior. Procurar face preta (normal invertida), z-fighting, peça flutuando.
5. **`destacar`** nas peças que mudaram, para confirmar que mexeu só nelas.
6. **`cruzamentos`** nas peças novas ou mexidas: peça sobreposta costuma ser artefato. Em peça
   nova encaixada entre outras (tubo, mangueira, escape), **`sonda`** com o trajeto dá a folga.
7. **`olhar_de`** do MESMO ângulo do print do usuário (muitas vezes de dentro da cabine ou pelo arco da
   roda), com `apontar` no lugar que ele marcou, antes de dizer "corrigi". Conferir só por fora já
   fez entregar errado duas vezes.
8. Renders de frente, lado, cima e um de dentro → perguntar ao usuário se ficou bom e se pode
   exportar. Pergunta dele não é aprovação. **Nunca exportar por cima do original sem o "pode"**;
   antes, copiar para `<nome>_ANTES.glb`.
9. Exportar: **`pre_exportar`** na coleção; exportar num arquivo TEMPORÁRIO; **`comparar_glb`** entre
   a cena e esse arquivo (tem de dar "batem peça por peça"); e também entre a cena e o original, para
   ver o que vai mudar (peça "só no GLB" some se for por cima). Só então copiar por cima.

## Regras de trabalho

- 🚫 **Nunca mexer em área que o usuário não apontou.** Restringir por caixa e comparar antes e depois,
  de cima E de baixo (filtro só por altura já pintou teto e encostos por engano).
- 🚫 **Peça sobreposta é artefato.** Para completar peça quebrada: cortar a original num ponto inteiro e
  CONTINUAR a mesma malha a partir da borda do corte. Nunca cobrir uma peça com outra.
- 🚫 **Fechar abertura não é pôr tampa.** Antes de fechar um vão, ler na malha as linhas que as peças
  vizinhas já têm (vértices da borda, planos, material) e continuar essas linhas: mesmas facetas, mesmo
  plano, mesma cor. Chapa encaixada, forro de outra cor e arco liso sobre peça facetada destoam.
- 🚫 **Para-lama acompanha a roda por igual**: "seguir a linha do antigo" é DESLOCAR a peça inteira,
  não deformar.
- Quando a reconstrução não converge, voltar ao original costuma ser melhor. Continuar uma borda de
  corte dá certo; fechar vão entre duas peças sem aresta comum, não. Se o usuário reprovar duas versões
  de uma forma, pedir que ele desenhe por cima de um print.
- ⚠️ **Pedido de cor ou de tamanho ambíguo: confirmar a leitura antes de aplicar** ("mais largo" pode
  querer dizer mais comprido). Perguntar antes de mudar escala.
- 💡 A seleção do usuário no Blender tira a ambiguidade (`bpy.context.selected_objects`); nomes ditados
  vêm truncados pelo outliner.
- 💡 Pesquisa de referência (manual, diagrama de peças, fotos, logo oficial) rende bem num subagente.
- **Um modelo por vez**: terminar, conferir, mostrar e esperar o ok antes de começar o próximo.
