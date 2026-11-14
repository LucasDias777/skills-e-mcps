<div align="center">

<h1>Skills e MCPs</h1>

<p>
  <strong>Skills para o Claude Code e servidores MCP que eu crio e uso no dia a dia, livres para uso pessoal e não comercial.</strong>
</p>

<p>
  Cada item mora na própria pasta, com tudo o que precisa para funcionar. Nenhum deles coleta dados ou guarda credencial: conversam só com programas que já estão no seu computador (o app do Codex, o Blender, um Chromium sem acesso à rede).
</p>

<br/>

<p>
  <a href="https://nodejs.org/"><img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/nodejs/nodejs-original.svg" height="50" alt="node.js logo" /></a>
  <img width="12" />
  <a href="https://www.python.org/"><img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg" height="50" alt="python logo" /></a>
  <img width="12" />
  <a href="https://www.blender.org/"><img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/blender/blender-original.svg" height="50" alt="blender logo" /></a>
  <img width="12" />
  <a href="https://learn.microsoft.com/windows/"><img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/windows11/windows11-original.svg" height="50" alt="windows logo" /></a>
</p>

<br/>

<p>
  <img alt="Skills do Claude Code" src="https://img.shields.io/badge/Claude_Code-skills-D97757?style=for-the-badge&logo=claude&logoColor=white" />
  <img alt="MCP do Blender" src="https://img.shields.io/badge/MCP-Blender-E87D0D?style=for-the-badge&logo=blender&logoColor=white" />
  <img alt="Licença PolyForm Noncommercial" src="https://img.shields.io/badge/Licen%C3%A7a-uso_n%C3%A3o_comercial-00c46a?style=for-the-badge" />
</p>

</div>

---

## Sumário

- [O que tem aqui](#o-que-tem-aqui)
- [Como instalar uma skill](#como-instalar-uma-skill)
- [ligar-ao-codex](#ligar-ao-codex)
- [desenho-de-veiculos](#desenho-de-veiculos)
- [blender-pro](#blender-pro)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Licença](#licença)

## O que tem aqui

| Nome | Tipo | O que faz | Precisa de |
|---|---|---|---|
| **[ligar-ao-codex](#ligar-ao-codex)** | Skill do Claude Code | Liga o Claude Code ao app do Codex aberto na tela: delega tarefas com o modelo e o esforço que você escolher, espera o Codex terminar e revisa o resultado | Windows, app do Codex, Node.js 20+ |
| **[desenho-de-veiculos](#desenho-de-veiculos)** | Skill do Claude Code | Desenha veículos com medidas reais, em SVG nas vistas ortográficas e em 3D pelo Blender, com ferramentas que medem a referência, inspecionam e comparam o desenho | Node.js 20+, Playwright com Chromium |
| **[blender-pro](#blender-pro)** | Servidor MCP | Completa o MCP do Blender com ferramentas para medir o modelo, gerar vistas técnicas, comparar com a referência e conferir o GLB antes de exportar | Blender 5 com o add-on BlenderMCP, Python 3.11+, uv |

## Como instalar uma skill

Uma skill do Claude Code é uma pasta com um `SKILL.md`. Copie a pasta para `~/.claude/skills/` (no Windows, `%USERPROFILE%\.claude\skills\`) e abra uma sessão nova do Claude Code: a skill aparece sozinha e entra em ação quando o pedido combina com a descrição dela.

```bash
git clone https://github.com/LucasDias777/skills-e-mcps.git
cp -r skills-e-mcps/skills/ligar-ao-codex ~/.claude/skills/
```

No PowerShell:

```powershell
Copy-Item -Recurse skills-e-mcps\skills\ligar-ao-codex "$env:USERPROFILE\.claude\skills\"
```

---

## ligar-ao-codex

<p>
  <img alt="Windows 10 e 11" src="https://img.shields.io/badge/Windows-10_|_11-0078D4?style=for-the-badge" />
  <img alt="Node.js 20+" src="https://img.shields.io/badge/Node.js-20+-5FA04E?style=for-the-badge&logo=nodedotjs&logoColor=white" />
  <img alt="Skill do Claude Code" src="https://img.shields.io/badge/Skill-Claude_Code-D97757?style=for-the-badge&logo=claude&logoColor=white" />
</p>

Liga o Claude Code ao app do Codex (o ChatGPT para Windows) que está aberto na tela. Você pede ao Claude, ele escreve a tarefa, manda para um chat do Codex com o modelo e o esforço que você escolheu, espera o Codex avisar que terminou e revisa o que ele fez antes de te contar. Também lista, cria, abre, lê, renomeia, arquiva e apaga chats do Codex, e tudo aparece **na hora** na janela do app.

### Como funciona

O app do Codex abre um pipe local (`\\.\pipe\codex-app-tools-*`), o mesmo canal que o MCP embutido dele usa. A skill fala por esse pipe, então quem executa as ações é o próprio app: a barra lateral e o chat atualizam sem fechar nem recarregar nada. O que o pipe não oferece (lista de modelos, apagar de vez) vai por um `codex app-server` com o mesmo binário do app, para ter sempre a mesma versão.

### O que dá para pedir

| Você diz ao Claude | O que acontece |
|---|---|
| "Manda o Codex revisar o módulo de login" | Pergunta chat, modelo e esforço (ou usa o padrão salvo), cria o chat com a tarefa e espera o fim em segundo plano |
| "O que o Codex fez no chat X?" | Lê os últimos turnos do chat |
| "Renomeia, arquiva ou apaga o chat X" | Faz no app, na hora |
| "Quanto do limite do Codex eu já usei?" | Mostra a janela de 5 horas e a semanal |
| "Usa sempre o modelo M com esforço alto" | Grava o padrão da ponte, sem mexer no padrão do app |

Por baixo, tudo passa por `scripts/codex.mjs`:

| Comando | O que faz |
|---|---|
| `status` | App aberto?, padrão salvo e último chat usado |
| `modelos` | Modelos do Codex e os esforços que cada um aceita |
| `chats` | Chats recentes, com id, título, estado e pasta |
| `criar` / `enviar` | Chat novo com a tarefa, ou tarefa nova num chat que já existe |
| `esperar` | Espera o Codex terminar e imprime o relatório final dele |
| `ler`, `abrir`, `renomear`, `arquivar`, `apagar` | Gerenciam os chats |
| `uso` | Limites de uso da conta |
| `padrao` | Mostra, grava ou apaga o modelo e o esforço padrão |

### Requisitos

- Windows 10 ou 11 com o app do Codex instalado e logado (pacote `OpenAI.Codex`, aparece como ChatGPT no Menu Iniciar).
- Node.js 20 ou mais novo.
- O Claude Code roda o script pelo Bash (Git Bash no Windows). Se o app estiver fechado, o script abre sozinho.

### Segurança e o que a skill grava

| Ponto | Como a skill trata |
|---|---|
| **Credenciais** | Não lê nem guarda token, senha ou login. Quem fala com a OpenAI é o próprio app do Codex |
| **Estado local** | Grava `estado.json` na pasta da skill: o id do chat da ponte, o padrão de modelo e esforço e o último chat usado. Fica só no seu computador e está no `.gitignore` |
| **Chat da ponte** | O app só aceita chamadas em nome de um chat real, então a skill cria um chat "Claude Code (ponte)", sem mensagens e arquivado |
| **Pastas confiáveis** | Ao abrir uma pasta no Codex, a skill grava `trust_level = "trusted"` para ela no `~/.codex/config.toml`, a mesma chave que o botão "Confiar" do app grava. Só passe à skill pastas em que você confia |
| **Envio de tarefas** | O Claude só manda mensagem a um chat do Codex quando você pede |
| **Apagar** | `apagar` é irreversível; havendo dúvida sobre qual chat é, a skill confirma antes |

---

## desenho-de-veiculos

<p>
  <img alt="Node.js 20+" src="https://img.shields.io/badge/Node.js-20+-5FA04E?style=for-the-badge&logo=nodedotjs&logoColor=white" />
  <img alt="SVG e 3D" src="https://img.shields.io/badge/SVG_e_3D-vistas_ortogr%C3%A1ficas-8A4FFF?style=for-the-badge" />
  <img alt="Skill do Claude Code" src="https://img.shields.io/badge/Skill-Claude_Code-D97757?style=for-the-badge&logo=claude&logoColor=white" />
</p>

Desenha veículos e implementos (caminhão, cavalo mecânico, carreta, ônibus, van, carro, máquina pesada) com realismo e medidas corretas, a partir de referência real: foto, planta ou ficha técnica. Gera SVG em vistas ortográficas (lateral, de cima, frente, traseira) e guia o modelo 3D no Blender junto com o [blender-pro](#blender-pro). Kit e ferramentas próprios, sem código de terceiros.

### O fluxo

1. **Especificação** em JSON, em metros: comprimento, largura, altura e os eixos, cada medida com a fonte dela.
2. **Medir a referência**: escala pelo entre-eixos da ficha e silhueta em metros, coluna por coluna.
3. **Inventário por região**: frente, cabine, chassi, tanques, rodas e traseira, cada detalhe medido.
4. **Construir** com o kit: a mesma especificação gera todas as vistas.
5. **Olhar, inspecionar e comparar** com a referência na mesma escala, até a inspeção passar e as regiões baterem.

### Ferramentas

| Para | Comando (da pasta da skill) |
|---|---|
| Medir a referência | `node ferramentas/medir.mjs regua ref.png --saida out/regua.png` |
| Silhueta em metros | `node ferramentas/medir.mjs perfil ref.png --chao 812 --nariz 64 --px-por-metro 118.4 --saida out/perfil` |
| Renderizar e recortar | `node ferramentas/renderizar.mjs lateral.svg --saida out` |
| Inspecionar | `node ferramentas/inspecionar.mjs lateral.svg --spec veiculo.json --outra cima.svg` |
| Comparar com a referência | `node ferramentas/comparar.mjs --desenho lateral.svg --referencia ref.png --saida out` |
| Exemplo completo | `node exemplos/cavalo-4x2/desenhar.mjs out` |
| Testes | `node --test testes/` |

### Requisitos

- Node.js 20 ou mais novo.
- Um Playwright com Chromium, para renderizar e medir. A skill não baixa nada: ela usa o Playwright da skill [teardown](https://github.com/elvarofficial/teardown), que também gera a página 3D interativa do veículo. Instale a teardown uma vez:

```bash
npx skills add elvarofficial/teardown -g -a claude-code
cd ~/.claude/skills/teardown && npm install && npx playwright install chromium
```

Para usar outro Playwright, aponte a variável `DV_PLAYWRIGHT` para o `index.mjs` dele:

```bash
mkdir ~/playwright-local && cd ~/playwright-local
npm init -y && npm i playwright && npx playwright install chromium
export DV_PLAYWRIGHT=~/playwright-local/node_modules/playwright/index.mjs
```

- Para o 3D, o [blender-pro](#blender-pro) e o BlenderMCP.

### Segurança

- O Chromium abre com **toda a rede bloqueada** (só `data:`, `blob:` e `about:` passam), e o SVG é limpo de `<script>`, eventos e links externos antes de abrir.
- As ferramentas só leem os arquivos passados e só gravam na pasta `--saida`.
- Desenho próprio, sem marca nem logotipo de montadora.

---

## blender-pro

<p>
  <img alt="Blender 5" src="https://img.shields.io/badge/Blender-5.x-E87D0D?style=for-the-badge&logo=blender&logoColor=white" />
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img alt="Servidor MCP" src="https://img.shields.io/badge/Servidor-MCP-444444?style=for-the-badge" />
</p>

Completa o [BlenderMCP](https://github.com/ahujasid/blender-mcp), o MCP comunitário que cria e edita geometria no Blender. Os dois trabalham juntos: o BlenderMCP edita e olha (`execute_blender_code`, `look`, `get_scene_info`); o blender-pro mede, confere e ensina como os veículos são de verdade. Ele conversa com o mesmo add-on, na mesma porta, sem mexer nele.

### Ferramentas

| Ferramenta | O que faz | Mexe na cena? |
|---|---|---|
| `guia` | Guias de modelagem realista: fluxo, referências, caminhões, ônibus, motos, carros, rodas e pneus, técnicas, materiais, conferência, receitas (vidro, interior, luzes, logos, conversão de DAE, STEP e JT, export) e armadilhas da API e da geometria | Não |
| `medir` | Caixa em metros, apoio no chão, eixos, entre-eixos, balanços, frente provável, simetria e avisos | Não |
| `vistas_tecnicas` | Vistas ortográficas na mesma escala, com grade de 1 m, cotas e a seta da frente | Não |
| `comparar_referencia` | Sobrepõe uma imagem de referência e mede onde o modelo difere dela (IoU e perfil) | Não |
| `destacar` | Pinta peças por nome, regex ou região para identificá-las antes de mexer | Não, as cores voltam |
| `olhar_de` | Foto de qualquer ponto de vista (dentro da cabine, por baixo) e qual peça está em cada pixel | Não |
| `sonda` | Peça mais perto de um ponto e folga de um trajeto de tubo ou mangueira | Não |
| `cruzamentos` | Peça atravessando peça, com o lugar do cruzamento | Não |
| `pre_exportar` | O que vai sair diferente no GLB: ocultos, modificadores, metal alto, textura sem UV | Não |
| `comparar_glb` | Cena contra um arquivo GLB, peça por peça | Não |
| `referencias_na_cena` | Põe blueprints na cena em escala real, na coleção `REFERENCIAS` | Sim, cria a coleção |
| `checkpoint` | Salva uma cópia do `.blend` antes de uma operação grande | Grava uma cópia; o arquivo aberto não muda |

Convenção de eixos: Z para cima, metros, veículo com a frente em −Y. As vistas seguem o teclado numérico do Blender.

### Requisitos

- Blender 5 (testado no 5.2) com o add-on do [BlenderMCP](https://github.com/ahujasid/blender-mcp) instalado (testado com o add-on 1.8) e o servidor dele ligado.
- Python 3.11 ou mais novo e o [uv](https://docs.astral.sh/uv/).

### Instalação

```bash
git clone https://github.com/LucasDias777/skills-e-mcps.git
cd skills-e-mcps/mcps/blender-pro
uv sync
```

No Claude Code:

```bash
claude mcp add blender-pro -- uv run --directory /caminho/para/skills-e-mcps/mcps/blender-pro server.py
```

No Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.blender-pro]
command = "uv"
args = ["run", "--directory", "/caminho/para/skills-e-mcps/mcps/blender-pro", "server.py"]
```

| Variável | Padrão | Para quê |
|---|---|---|
| `BLENDER_HOST` | `localhost` | Onde o add-on do BlenderMCP está ouvindo |
| `BLENDER_PORT` | `9876` | Porta do add-on |
| `BLENDER_PRO_CHECKPOINTS` | `~/Documents/blender-checkpoints` | Pasta das cópias do `checkpoint` |

### Segurança

- As ferramentas mandam código Python ao add-on do BlenderMCP, pelo mesmo canal que ele já usa. Nada vai para a internet.
- Fora `referencias_na_cena` e `checkpoint`, tudo é só leitura: o que muda para tirar uma foto ou pintar uma peça volta ao que era.
- `sonda` e `cruzamentos` trabalham numa região e param sozinhos no limite de tempo, para não travar o Blender aberto.
- Nenhuma ferramenta exporta nem salva por cima de um arquivo seu.

### Testes

`testes/abrir_teste.py` roda dentro de um Blender de teste e sobe o add-on na porta 9877 com um modelo importado numa cena vazia, sem tocar no Blender em que você trabalha. `testes/testar.py` e `testes/cliente_mcp.py` chamam as ferramentas contra ele, direto ou pelo protocolo MCP.

```bash
blender --python testes/abrir_teste.py -- caminho/do/modelo.glb
uv run python testes/testar.py medir '{}'
uv run python testes/testar.py vistas_tecnicas '{"vistas": ["direita", "frente", "cima"]}'
```

As imagens vão para `testes/saida/`.

---

## Estrutura do repositório

```bash
skills-e-mcps/
├── skills/
│   ├── ligar-ao-codex/         # SKILL.md e scripts/codex.mjs
│   └── desenho-de-veiculos/    # SKILL.md, kit, ferramentas, referências, exemplo e testes
└── mcps/
    └── blender-pro/            # server.py, scripts.py, guias e testes
```

## Licença

[PolyForm Noncommercial 1.0.0](LICENSE): **uso pessoal e não comercial**.

| Pode | Não pode |
|---|---|
| Usar no seu computador para estudo, hobby, projetos pessoais e testes | Vender as skills e o MCP, ou um produto ou serviço feito com eles |
| Adaptar e compartilhar, mantendo esta licença e o aviso de copyright | Usar no trabalho pago ou dentro de uma empresa |
| Usar em escola, ONG, instituição de pesquisa ou órgão público | Tirar o aviso de copyright ou trocar a licença |

O texto oficial, em inglês, está em [LICENSE](LICENSE) e vale sobre este resumo. Para uso comercial, peça autorização ao autor.
