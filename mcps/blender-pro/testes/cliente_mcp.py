# Sobe o blender-pro por stdio, como o Claude Code faz, e chama as ferramentas pelo protocolo MCP.
import asyncio
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    p = StdioServerParameters(
        command="uv",
        args=["run", "--directory", str(Path(__file__).resolve().parent.parent), "server.py"],
        env={**os.environ, "BLENDER_PORT": "9877"},
    )
    async with stdio_client(p) as (leitura, escrita):
        async with ClientSession(leitura, escrita) as s:
            ini = await s.initialize()
            print("servidor:", ini.serverInfo.name, "| instruções:", (ini.instructions or "")[:70], "...")
            print("ferramentas:", [t.name for t in (await s.list_tools()).tools])
            r = await s.call_tool("guia", {"tema": "rodas-e-pneus"})
            print("guia:", r.isError, r.content[0].text.splitlines()[0])
            r = await s.call_tool("medir", {})
            print("medir:", r.isError, " | ".join(r.content[0].text.splitlines()[2:4]))
            r = await s.call_tool("vistas_tecnicas", {"vistas": ["direita"], "tamanho": 600})
            print("vistas_tecnicas:", r.isError, [(c.type, getattr(c, "mimeType", "")) for c in r.content])
            r = await s.call_tool("destacar", {})
            print("destacar sem alvo:", r.isError, r.content[0].text[:110])


asyncio.run(main())
