# Chama as ferramentas do blender-pro direto (sem cliente MCP) contra o Blender de teste.
# Uso: uv run --directory <blender-pro> python testar.py <ferramenta> '<json de argumentos>'
import json
import os
import sys
import time

os.environ.setdefault("BLENDER_PORT", "9877")
sys.stdout.reconfigure(encoding="utf-8")  # o console do Windows (cp1252) não imprime "−" nem "✅"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server  # noqa: E402

nome, args = sys.argv[1], json.loads(sys.argv[2] if len(sys.argv) > 2 else "{}")
saida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saida")
os.makedirs(saida, exist_ok=True)
t = time.time()
r = getattr(server, nome)(**args)
print(f"[{nome} em {time.time() - t:.1f}s]")
itens = r if isinstance(r, list) else [r]
for i, it in enumerate(itens):
    if hasattr(it, "data") and it.data:
        p = os.path.join(saida, f"{nome}_{i}.png")
        open(p, "wb").write(it.data)
        print("IMAGEM", p)
    else:
        print(it)
