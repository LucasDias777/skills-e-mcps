# Roda dentro da instância de TESTE do Blender: tira o servidor do add-on da 9876, sobe na 9877 e
# importa um modelo numa cena vazia. Nada aqui é salvo.
import sys
import bpy

glb = sys.argv[sys.argv.index("--") + 1]
s = getattr(bpy.types, "blendermcp_server", None)
if s:
    s.stop()
import blender_mcp
bpy.types.blendermcp_server = blender_mcp.BlenderMCPServer(port=9877)
bpy.types.blendermcp_server.start()
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=glb)
print("TESTE PRONTO NA 9877")
