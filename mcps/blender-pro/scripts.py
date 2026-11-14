"""Scripts que o blender-pro roda dentro do Blender pelo comando execute_code do add-on.

Cada ferramenta junta COMUM (+ DESENHO, quando desenha) com o seu script. montar() embrulha tudo
numa função, para o script poder dar `return` cedo, e imprime uma linha MARCADOR + JSON com o
resultado, que ler_resultado() separa do resto do que o Blender imprimir.
"""

import json

MARCADOR = "__BLENDER_PRO__"


def montar(*partes: str, args: dict) -> str:
    corpo = "\n".join(p.strip("\n") for p in partes)
    corpo = "\n".join("    " + linha if linha.strip() else "" for linha in corpo.splitlines())
    return (
        "import json as _json\n"
        f"ARGS = _json.loads({json.dumps(json.dumps(args))})\n"
        f"def _main():\n{corpo}\n"
        "def _conv(o):\n"
        "    if hasattr(o, 'tolist'):\n"
        "        return o.tolist()\n"
        "    if hasattr(o, '__iter__'):\n"
        "        return list(o)\n"
        "    return str(o)\n"
        "try:\n"
        "    _r = _main()\n"
        "except Exception as _e:\n"
        "    import traceback as _tb\n"
        "    _r = {'erro': f'{type(_e).__name__}: {_e}', 'trace': _tb.format_exc()[-1500:]}\n"
        f"print({MARCADOR!r} + _json.dumps(_r, default=_conv))\n"
    )


def ler_resultado(saida: str) -> dict:
    for linha in reversed((saida or "").splitlines()):
        if linha.startswith(MARCADOR):
            return json.loads(linha[len(MARCADOR):])
    raise RuntimeError("O script terminou sem resultado. Saída do Blender:\n" + (saida or "")[-800:])


# Medidas e análise geométrica. Z é o alto no Blender; o comprimento é o maior eixo horizontal.
COMUM = r'''
import bpy, math, os, re
import numpy as np
from mathutils import Vector, Matrix
scene = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()
GEOM = {"MESH", "CURVE", "SURFACE", "META", "FONT"}
RX_CHAO = re.compile(r"(^|[_\s.-])(ch[aã]o|ground|floor|piso|plane|plano)($|[_\s.\d-])", re.I)
RX_FRENTE = re.compile(r"grill|grelha|grade|farol|headl|windscreen|windshield|para.?brisa|front|dianteir|volante|steer|setir|dashboard|spion|retrovis|mirror|limpador|wiper", re.I)
RX_TRAS = re.compile(r"lantern|taillight|tail.?l|rear|traseir|quinta|fifth|backlight", re.I)
EIXOS = "XYZ"

def caixa(o):
    ev = o.evaluated_get(dg)
    try:
        cs = [ev.matrix_world @ Vector(c) for c in ev.bound_box]
    except Exception:
        cs = [o.matrix_world.translation.copy()]
    lo = Vector([min(c[i] for c in cs) for i in range(3)])
    hi = Vector([max(c[i] for c in cs) for i in range(3)])
    return lo, hi

def caixa_exata(o):
    """Caixa pelos vértices: a do bound_box infla quando a peça está girada."""
    if o.type == "MESH":
        v = vertices_mundo(o)
        if len(v):
            return Vector(v.min(axis=0).tolist()), Vector(v.max(axis=0).tolist())
    return caixa(o)

def eh_chao(o, lo, hi):
    ext = hi - lo
    if ext.z < 0.005 and max(ext.x, ext.y) > 15:
        return True
    return o.type == "MESH" and ext.z < 0.05 and max(ext.x, ext.y) > 6 and RX_CHAO.search(o.name) is not None

def resolver_alvos(nomes=None, padrao=None, regiao=None):
    objs, vistos = [], set()
    def add(o):
        if o.name in vistos:
            return
        vistos.add(o.name)
        objs.append(o)
        for c in o.children:
            add(c)
    if nomes:
        faltam = [n for n in nomes if n not in bpy.data.objects]
        if faltam:
            raise ValueError("Não existe objeto chamado " + ", ".join(repr(n) for n in faltam))
        for n in nomes:
            add(bpy.data.objects[n])
    else:
        for o in scene.objects:
            add(o)
    objs = [o for o in objs if o.name in scene.objects and o.visible_get()]
    if padrao:
        rx = re.compile(padrao, re.I)
        objs = [o for o in objs if rx.search(o.name)]
    if regiao:
        a, b = Vector(regiao[:3]), Vector(regiao[3:])
        def dentro(o):
            lo, hi = caixa(o)
            c = (lo + hi) / 2
            return all(min(a[i], b[i]) <= c[i] <= max(a[i], b[i]) for i in range(3))
        objs = [o for o in objs if dentro(o)]
    return objs

def geometria(objs):
    geo, chaos = [], []
    for o in objs:
        if o.type not in GEOM:
            continue
        if o.type == "MESH" and not len(o.evaluated_get(dg).data.polygons):
            continue
        lo, hi = caixa_exata(o)
        (chaos if eh_chao(o, lo, hi) else geo).append((o, lo, hi))
    return geo, chaos

def caixa_total(geo):
    lo = Vector([min(g[1][i] for g in geo) for i in range(3)])
    hi = Vector([max(g[2][i] for g in geo) for i in range(3)])
    return lo, hi

def vertices_mundo(o, limite=None):
    ev = o.evaluated_get(dg)
    temp = False
    if o.type == "MESH":
        me = ev.data
    else:
        try:
            me = ev.to_mesh()
            temp = True
        except Exception:
            return np.zeros((0, 3))
    n = len(me.vertices)
    co = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3).astype(np.float64)
    # Só vértices de face: aresta solta (as linhas do SketchUp) não aparece e infla a caixa.
    nl = len(me.loops)
    if nl:
        vi = np.empty(nl, dtype=np.int32)
        me.loops.foreach_get("vertex_index", vi)
        co = co[np.unique(vi)]
    else:
        co = co[:0]
    if temp:
        ev.to_mesh_clear()
    n = len(co)
    if limite and n > limite:
        co = co[:: max(1, n // limite)]
    M = np.array(ev.matrix_world, dtype=np.float64)
    return co @ M[:3, :3].T + M[:3, 3]

def agrupar(itens, folga):
    grupos = []
    for it in sorted(itens, key=lambda t: t[0]):
        if grupos and it[0] - grupos[-1][-1][0] <= folga:
            grupos[-1].append(it)
        else:
            grupos.append([it])
    return grupos

def eixo_comprimento(geo, chao, ext, frente=None):
    """Eixo do comprimento: o da `frente` informada; senão o que as rodas indicam (pneu é redondo
    no plano comprimento × altura e fino na lateral); senão o maior lado horizontal. Cabine solta é
    mais larga do que comprida, então o maior lado sozinho erra."""
    if frente:
        return "XYZ".index(frente.strip().upper()[-1])
    votos = [0, 0]
    for o, lo, hi in geo:
        e = hi - lo
        if lo.z - chao < 0.04 and 0.25 < e.z < 1.6:
            for i in (0, 1):
                if abs(e[i] - e.z) < 0.15 * e.z and e[1 - i] < 0.75 * e.z:
                    votos[i] += 1
    if votos[0] != votos[1]:
        return 0 if votos[0] > votos[1] else 1
    return 0 if ext.x >= ext.y else 1

def analisar_rodas(geo, iL, iW, chao, cW):
    """Eixos pelas peças de roda (caixa quase quadrada no plano comprimento × altura, encostada no
    chão) ou, em malha fundida, pelas pegadas dos pneus no chão."""
    cand = []
    for o, lo, hi in geo:
        e = hi - lo
        dZ, dL, dW = e.z, e[iL], e[iW]
        if lo.z - chao < 0.04 and 0.25 < dZ < 1.6 and abs(dL - dZ) < 0.15 * dZ and dW < 0.75 * dZ:
            c = (lo + hi) / 2
            cand.append((c[iL], {"w": c[iW], "d": (dL + dZ) / 2, "lw": lo[iW], "hw": hi[iW]}))
    eixos, metodo = [], None
    for g in agrupar(cand, 0.35):
        ds = sorted(x[1]["d"] for x in g)
        # Um pneu vem em muitas peças (banda, blocos, lateral, aro): o que separa simples de duplo é a
        # largura coberta de cada lado: um pneu ≈0,2–0,4 m; o par do duplo ≈0,6–0,7 m.
        cob = []
        for esquerdo in (True, False):
            xs = [x[1] for x in g if (x[1]["w"] < cW) == esquerdo]
            cob.append(max(x["hw"] for x in xs) - min(x["lw"] for x in xs) if xs else 0.0)
        eixos.append({"pos": sum(x[0] for x in g) / len(g), "diametro": ds[len(ds) // 2],
                      "pneus": sum(2 if c > 0.5 else 1 for c in cob if c > 0), "duplo": max(cob) > 0.5,
                      "lados": sum(1 for c in cob if c > 0),
                      "w": [min(x[1]["lw"] for x in g), max(x[1]["hw"] for x in g)]})
    if eixos:
        metodo = "peças das rodas"
    if len([e for e in eixos if e["lados"] == 2]) < 2:
        pts = []
        for o, lo, hi in geo:
            if lo.z - chao < 0.03:
                v = vertices_mundo(o, 400000)
                v = v[v[:, 2] < chao + 0.025]
                if len(v):
                    pts.append(v)
        if pts:
            p = np.concatenate(pts)
            p = p[:: max(1, len(p) // 20000)]
            novos = []
            for g in agrupar([(float(x[iL]), float(x[iW])) for x in p], 0.3):
                if len(g) < 3:
                    continue
                Ls = [x[0] for x in g]
                esq = [x[1] for x in g if x[1] < cW]
                dir_ = [x[1] for x in g if x[1] >= cW]
                larg = max((max(s) - min(s)) if s else 0.0 for s in (esq, dir_))
                n = {"pos": (min(Ls) + max(Ls)) / 2, "diametro": None, "pneus": None,
                     "duplo": bool(larg > 0.42), "lados": int(bool(esq)) + int(bool(dir_))}
                par = [e for e in eixos if abs(e["pos"] - n["pos"]) < 0.4]
                if par:
                    n["diametro"] = par[0]["diametro"]
                novos.append(n)
            if len(novos) >= len(eixos):
                eixos, metodo = novos, "pegadas dos pneus no chão"
    return eixos, metodo

def frente_de(valor, iL):
    if not valor:
        return None
    v = valor.strip().upper().replace("−", "-")
    sinal = -1 if v.startswith("-") else 1
    eixo = "XYZ".index(v[-1])
    return {"eixo": eixo, "sinal": sinal, "confianca": "informada", "evidencias": ["informada na chamada"]}

def nome_completo(o):
    """Nome do objeto e dos pais: em CAD/JT a malha é 'Mesh_123' e o nome útil está no grupo."""
    partes = []
    while o is not None and len(partes) < 6:
        partes.append(o.name)
        o = o.parent
    return " / ".join(partes)

def adivinhar_frente(geo, iL, eixos, cL):
    votos, ev = [], []
    nomes = [(nome_completo(o), ((lo + hi) / 2)[iL]) for o, lo, hi in geo]
    fr = [c for n, c in nomes if RX_FRENTE.search(n)]
    tr = [c for n, c in nomes if RX_TRAS.search(n)]
    mf = sum(fr) / len(fr) if fr else None
    mt = sum(tr) / len(tr) if tr else None
    if mf is not None and mt is not None and abs(mf - mt) > 0.3:
        votos.append(-1 if mf < mt else 1)
        ev.append(f"{len(fr)} peças com nome de frente em {EIXOS[iL]} {mf:+.2f} e {len(tr)} de traseira em {mt:+.2f}")
    elif mf is not None and mt is None and abs(mf - cL) > 0.3:
        votos.append(-1 if mf < cL else 1)
        ev.append(f"{len(fr)} peças com nome de frente em {EIXOS[iL]} {mf:+.2f}")
    elif mt is not None and mf is None and abs(mt - cL) > 0.3:
        votos.append(1 if mt < cL else -1)
        ev.append(f"{len(tr)} peças com nome de traseira em {EIXOS[iL]} {mt:+.2f}")
    if len(eixos) >= 2:
        a, b = sorted(eixos, key=lambda e: e["pos"])[0], sorted(eixos, key=lambda e: e["pos"])[-1]
        if a.get("duplo") is not None and a["duplo"] != b["duplo"]:
            votos.append(-1 if not a["duplo"] else 1)
            ev.append("rodado simples num extremo e duplo no outro (o simples é a frente)")
    if not votos:
        return {"eixo": iL, "sinal": 0, "confianca": "indefinida", "evidencias": []}
    s = sum(votos)
    if s == 0:
        return {"eixo": iL, "sinal": 0, "confianca": "conflitante", "evidencias": ev}
    return {"eixo": iL, "sinal": 1 if s > 0 else -1,
            "confianca": "alta" if len(votos) >= 2 and abs(s) == len(votos) else "média", "evidencias": ev}

def simetria(pts, iW):
    if len(pts) < 50:
        return None
    from mathutils.kdtree import KDTree
    p = pts[:: max(1, len(pts) // 30000)]
    a, b = np.percentile(p[:, iW], [0.5, 99.5])
    c = float((a + b) / 2)
    kd = KDTree(len(p))
    for i, v in enumerate(p.tolist()):
        kd.insert(v, i)
    kd.balance()
    m = p.copy()
    m[:, iW] = 2 * c - m[:, iW]
    d = np.array([kd.find(v)[2] for v in m.tolist()])
    sem = p[d > 0.03]
    return {"plano": c, "ate_1cm": float((d <= 0.01).mean()), "ate_3cm": float((d <= 0.03).mean()),
            "sem_par": np.median(sem, axis=0).tolist() if len(sem) > 20 else None}

def estatisticas(geo):
    tri, mats, neg, esc = 0, set(), 0, 0
    for o, lo, hi in geo:
        if o.type == "MESH":
            me = o.evaluated_get(dg).data
            lt = np.empty(len(me.polygons), dtype=np.int32)
            me.polygons.foreach_get("loop_total", lt)
            tri += int((lt - 2).sum())
        for s in o.material_slots:
            if s.material:
                mats.add(s.material)
        if o.matrix_world.determinant() < 0:
            neg += 1
        if any(abs(abs(v) - 1) > 1e-4 for v in o.scale):
            esc += 1
    metal = []
    for m in mats:
        nt = getattr(m, "node_tree", None)
        if nt is None:
            continue
        for n in nt.nodes:
            if n.type == "BSDF_PRINCIPLED":
                s = n.inputs.get("Metallic")
                if s is not None and not s.is_linked and s.default_value > 0.3:
                    metal.append(m.name)
                    break
    return tri, len(mats), neg, esc, metal
'''

# Desenho offscreen com matrizes próprias (o mesmo caminho do `look` oficial). Tudo o que muda na
# viewport vai para SALVOS e volta em restaurar().
DESENHO = r'''
import gpu
SALVOS = []

def mudar(obj, attr, valor):
    if obj is None or not hasattr(obj, attr):
        return
    v = getattr(obj, attr)
    if not isinstance(v, (str, int, float, bool)) and hasattr(v, "__len__"):
        v = tuple(v)
    SALVOS.append((obj, attr, v))
    try:
        setattr(obj, attr, valor)
    except Exception:
        SALVOS.pop()

def restaurar():
    while SALVOS:
        obj, attr, v = SALVOS.pop()
        try:
            setattr(obj, attr, v)
        except Exception:
            pass

def area_3d():
    for win in bpy.context.window_manager.windows:
        for a in win.screen.areas:
            if a.type == "VIEW_3D":
                rg = next((r for r in a.regions if r.type == "WINDOW"), None)
                if rg is not None:
                    return a, a.spaces.active, rg
    return None, None, None

# nome: (do alvo para o olho, direita da imagem, cima da imagem). São as vistas do teclado numérico.
VISTAS = {
    "frente": ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
    "tras": ((0, 1, 0), (-1, 0, 0), (0, 0, 1)),
    "direita": ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    "esquerda": ((-1, 0, 0), (0, -1, 0), (0, 0, 1)),
    "cima": ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    "baixo": ((0, 0, -1), (1, 0, 0), (0, -1, 0)),
}

def orto(centro, raio, nome, hw, hh):
    d, r, u = [Vector(v) for v in VISTAS[nome]]
    dist = raio * 4 + 1
    olho = centro + d * dist
    rot = Matrix((r, u, d)).transposed().to_4x4()
    view = (Matrix.Translation(olho) @ rot).inverted()
    n, f = 0.01, dist + raio * 4
    proj = Matrix(((1 / hw, 0, 0, 0), (0, 1 / hh, 0, 0), (0, 0, -2 / (f - n), -(f + n) / (f - n)), (0, 0, 0, 1)))
    return view, proj

FOV = math.radians(35)
ANGULOS = {"frente": (0, -1, 0), "tras": (0, 1, 0), "direita": (1, 0, 0), "esquerda": (-1, 0, 0),
           "cima": (0, -0.001, 1), "baixo": (0, 0.001, -1), "tres_quartos": (1, -1, 0.7),
           "tres_quartos_tras": (-1, 1, 0.7), "tres_quartos_esq": (-1, -1, 0.7)}

def perspectiva(centro, raio, direcao, aspecto, distancia=None):
    d = Vector(direcao).normalized()
    fit = FOV / 2 if aspecto >= 1 else math.atan(math.tan(FOV / 2) * aspecto)
    dist = float(distancia or 0) or raio / math.sin(fit) * 1.1
    olho = centro + d * dist
    rot = (centro - olho).to_track_quat("-Z", "Y").to_matrix().to_4x4()
    view = (Matrix.Translation(olho) @ rot).inverted()
    near, far = max(dist - raio * 3, dist * 0.01), dist + raio * 3
    f = 1 / math.tan(FOV / 2)
    proj = Matrix(((f / aspecto, 0, 0, 0), (0, f, 0, 0),
                   (0, 0, (far + near) / (near - far), 2 * far * near / (near - far)), (0, 0, -1, 0)))
    return view, proj

def desenhar(space, region, view, proj, w, h):
    off = gpu.types.GPUOffScreen(w, h)
    try:
        off.draw_view3d(scene, bpy.context.view_layer, space, region, view, proj, do_color_management=True)
        buf = off.texture_color.read()
    finally:
        off.free()
    buf.dimensions = w * h * 4
    a = np.asarray(buf, dtype=np.float32).reshape(h, w, 4)
    if a.max() <= 1.0:
        a = a * 255.0
    return np.clip(a, 0, 255).astype(np.uint8)[::-1].copy()

def sombreamento(space, modo):
    sh, ov = space.shading, space.overlay
    mudar(ov, "show_overlays", False)
    mudar(sh, "type", "SOLID")
    mudar(sh, "show_xray", False)
    mudar(sh, "background_type", "VIEWPORT")
    if modo == "silhueta":
        mudar(sh, "light", "FLAT")
        mudar(sh, "color_type", "SINGLE")
        mudar(sh, "single_color", (0.0, 0.0, 0.0))
        mudar(sh, "background_color", (1.0, 1.0, 1.0))
        for a in ("show_cavity", "show_object_outline", "show_shadows", "show_specular_highlight"):
            mudar(sh, a, False)
        return
    mudar(sh, "light", "STUDIO")
    mudar(sh, "background_color", (0.93, 0.93, 0.93))
    mudar(sh, "show_cavity", True)
    mudar(sh, "show_object_outline", True)
    mudar(sh, "object_outline_color", (0.05, 0.05, 0.05))
    mudar(sh, "show_specular_highlight", True)
    if modo == "cinza":
        mudar(sh, "color_type", "SINGLE")
        mudar(sh, "single_color", (0.78, 0.78, 0.78))
    elif modo == "objeto":
        mudar(sh, "color_type", "OBJECT")
    else:
        mudar(sh, "color_type", "MATERIAL")

def isolar(objs):
    manter = {o.name for o in objs}
    ocultos = []
    for o in scene.objects:
        if o.name not in manter and o.visible_get():
            try:
                o.hide_set(True)
                ocultos.append(o)
            except Exception:
                pass
    bpy.context.view_layer.update()
    return ocultos

def mostrar(ocultos):
    for o in ocultos:
        try:
            o.hide_set(False)
        except Exception:
            pass
    if ocultos:
        bpy.context.view_layer.update()

def eixo_da(v):
    i = [k for k in range(3) if v[k]][0]
    return [i, int(v[i])]
'''

MEDIR = r'''
objs = resolver_alvos(ARGS.get("alvo"), ARGS.get("padrao"))
geo, chaos = geometria(objs)
if not geo:
    return {"erro": "Nada visível com geometria para medir (confira alvo/padrao e se os objetos estão visíveis)."}
lo, hi = caixa_total(geo)
ext = hi - lo
centro = (lo + hi) / 2
chao = lo.z
iL = eixo_comprimento(geo, chao, ext, ARGS.get("frente"))
iW = 1 - iL
eixos, metodo = analisar_rodas(geo, iL, iW, chao, centro[iW])
frente = frente_de(ARGS.get("frente"), iL) or adivinhar_frente(geo, iL, eixos, centro[iL])
lim = max(40, 40000 // len(geo))
pts = [vertices_mundo(o, lim) for o, _, _ in geo]
pts = [p for p in pts if len(p)]
sim = simetria(np.concatenate(pts), iW) if pts else None
tri, nmat, neg, esc, metal = estatisticas(geo)
extremos = []
for o, a, b in (min(geo, key=lambda g: g[1][iW]), max(geo, key=lambda g: g[2][iW])):
    extremos.append({"nome": o.name, "z": [a.z, b.z], "comp": b[iL] - a[iL]})
return {"objetos": len(geo), "chao_ignorado": [o.name for o, _, _ in chaos][:5], "extremos_laterais": extremos,
        "lo": list(lo), "hi": list(hi), "iL": iL, "iW": iW, "chao": chao,
        "eixos": eixos, "metodo_rodas": metodo, "frente": frente, "simetria": sim,
        "triangulos": tri, "materiais": nmat, "metal_alto": metal[:8], "n_metal_alto": len(metal),
        "escala_negativa": neg, "escala_nao_aplicada": esc,
        "arquivo": bpy.data.filepath or "(não salvo)", "modo": bpy.context.mode}
'''

VISTAS_TECNICAS = r'''
objs = resolver_alvos(ARGS.get("alvo"), ARGS.get("padrao"))
geo, chaos = geometria(objs)
if not geo:
    return {"erro": "Nada visível para desenhar (confira alvo/padrao)."}
area, space, region = area_3d()
if region is None:
    return {"erro": "Nenhuma janela 3D aberta no Blender."}
lo, hi = caixa_total(geo)
centro = (lo + hi) / 2
ext = hi - lo
raio = max(ext.length / 2, 0.05)
chao = lo.z
iL = eixo_comprimento(geo, chao, ext, ARGS.get("frente"))
iW = 1 - iL
eixos, metodo = analisar_rodas(geo, iL, iW, chao, centro[iW]) if ARGS.get("cotas", True) else ([], None)
frente = frente_de(ARGS.get("frente"), iL) or adivinhar_frente(geo, iL, eixos, centro[iL])
margem = max(0.1 * max(ext), 0.25)
plano = []
for nome in ARGS["vistas"]:
    d, r, u = VISTAS[nome]
    er = sum(abs(r[i]) * ext[i] for i in range(3))
    eu = sum(abs(u[i]) * ext[i] for i in range(3))
    plano.append((nome, er / 2 + margem, eu / 2 + margem))
cols = 1 if len(plano) == 1 else 2
linhas = [plano[i:i + cols] for i in range(0, len(plano), cols)]
larg = max(sum(2 * t[1] for t in ln) for ln in linhas)
alt = sum(max(2 * t[2] for t in ln) for ln in linhas)
tam = float(ARGS.get("tamanho") or 1400)
ppm = max(8.0, min(tam / larg, tam / alt))
ocultos = isolar(objs) if (ARGS.get("alvo") or ARGS.get("padrao")) else []
saida = []
try:
    sombreamento(space, ARGS.get("sombreamento") or "material")
    for nome, hw, hh in plano:
        d, r, u = VISTAS[nome]
        w = max(16, min(4096, int(round(2 * hw * ppm))))
        h = max(16, min(4096, int(round(2 * hh * ppm))))
        view, proj = orto(centro, raio, nome, hw, hh)
        img = desenhar(space, region, view, proj, w, h)
        arq = os.path.join(ARGS["pasta"], f"vista_{nome}.npy")
        np.save(arq, img)
        ri, rs = eixo_da(r)
        ui, us = eixo_da(u)
        saida.append({"vista": nome, "arquivo": arq, "w": w, "h": h, "ppm_x": w / (2 * hw), "ppm_y": h / (2 * hh),
                      "r": [ri, rs], "u": [ui, us], "c_r": centro[ri] * rs, "c_u": centro[ui] * us,
                      "hw": hw, "hh": hh})
finally:
    restaurar()
    mostrar(ocultos)
return {"tiles": saida, "lo": list(lo), "hi": list(hi), "chao": chao, "iL": iL, "iW": iW,
        "eixos": eixos, "metodo_rodas": metodo, "frente": frente, "objetos": len(geo),
        "arquivo": bpy.data.filepath or "(não salvo)"}
'''

COMPARAR = r'''
objs = resolver_alvos(ARGS.get("alvo"), ARGS.get("padrao"))
geo, chaos = geometria(objs)
if not geo:
    return {"erro": "Nada visível para comparar (confira alvo/padrao)."}
area, space, region = area_3d()
if region is None:
    return {"erro": "Nenhuma janela 3D aberta no Blender."}
lo, hi = caixa_total(geo)
centro = (lo + hi) / 2
ext = hi - lo
raio = max(ext.length / 2, 0.05)
nome = ARGS["vista"]
d, r, u = VISTAS[nome]
er = sum(abs(r[i]) * ext[i] for i in range(3))
eu = sum(abs(u[i]) * ext[i] for i in range(3))
margem = 0.04 * max(er, eu) + 0.05
hw, hh = er / 2 + margem, eu / 2 + margem
base = er if ARGS.get("ajuste", "largura") == "largura" else eu
ppm = max(20.0, min(float(ARGS["px_alvo"]) / max(base, 1e-3), 3000 / (2 * max(hw, hh))))
w, h = int(round(2 * hw * ppm)), int(round(2 * hh * ppm))
view, proj = orto(centro, raio, nome, hw, hh)
ocultos = isolar(objs) if (ARGS.get("alvo") or ARGS.get("padrao")) else []
arqs = {}
try:
    for chave, modo in (("silhueta", "silhueta"), ("cor", ARGS.get("sombreamento") or "material")):
        sombreamento(space, modo)
        img = desenhar(space, region, view, proj, w, h)
        restaurar()
        arqs[chave] = os.path.join(ARGS["pasta"], f"comparar_{chave}.npy")
        np.save(arqs[chave], img)
finally:
    restaurar()
    mostrar(ocultos)
ri, rs = eixo_da(r)
ui, us = eixo_da(u)
return {"silhueta": arqs["silhueta"], "cor": arqs["cor"], "w": w, "h": h, "ppm_x": w / (2 * hw), "ppm_y": h / (2 * hh),
        "r": [ri, rs], "u": [ui, us], "c_r": centro[ri] * rs, "c_u": centro[ui] * us, "hw": hw, "hh": hh,
        "lo": list(lo), "hi": list(hi)}
'''

DESTACAR = r'''
todos, _ = geometria(resolver_alvos())
alvo = [o for o in resolver_alvos(ARGS.get("objetos"), ARGS.get("padrao"), ARGS.get("regiao")) if o.type in GEOM]
if not alvo:
    return {"erro": "Nenhuma peça visível casou com objetos/padrao/regiao."}
area, space, region = area_3d()
if region is None:
    return {"erro": "Nenhuma janela 3D aberta no Blender."}
enq = geometria(alvo)[0] if ARGS.get("enquadrar") == "alvo" else todos
enq = enq or todos
lo, hi = caixa_total(enq)
centro = (lo + hi) / 2
raio = max((hi - lo).length / 2, 0.05)
PALETA = [(1.0, 0.35, 0.0), (0.0, 0.45, 1.0), (0.1, 0.8, 0.2), (0.9, 0.0, 0.7), (1.0, 0.85, 0.0),
          (0.0, 0.85, 0.85), (0.85, 0.05, 0.05), (0.5, 0.2, 0.9)]
nomes_alvo = {o.name for o in alvo}
cores = {}
ocultos = []
saida = []
try:
    sombreamento(space, "objeto")
    for o, _, _ in todos:
        if o.name not in nomes_alvo:
            mudar(o, "color", (0.72, 0.72, 0.72, 1.0))
    for i, o in enumerate(alvo):
        c = PALETA[i % len(PALETA)] if len(alvo) <= len(PALETA) else PALETA[0]
        mudar(o, "color", (c[0], c[1], c[2], 1.0))
        cores[o.name] = c
    # A viewport desenha a cópia avaliada: sem isto as cores novas não aparecem.
    bpy.context.view_layer.update()
    contexto = ARGS.get("contexto") or "cinza"
    if contexto == "transparente":
        mudar(space.shading, "show_xray", True)
        mudar(space.shading, "xray_alpha", 0.25)
    elif contexto == "oculto":
        ocultos = isolar(alvo)
    tam = int(ARGS.get("tamanho") or 900)
    w, h = tam, int(tam * 0.7)
    for i, v in enumerate(ARGS.get("vistas") or ["tres_quartos", "direita"]):
        direcao = ANGULOS[v] if isinstance(v, str) else v
        view, proj = perspectiva(centro, raio, direcao, w / h, ARGS.get("distancia"))
        img = desenhar(space, region, view, proj, w, h)
        arq = os.path.join(ARGS["pasta"], f"destacar_{i}.npy")
        np.save(arq, img)
        saida.append({"vista": v if isinstance(v, str) else str(v), "arquivo": arq})
finally:
    restaurar()
    mostrar(ocultos)
    bpy.context.view_layer.update()
pecas = []
for o in alvo[:40]:
    a, b = caixa(o)
    pecas.append({"nome": o.name, "centro": list((a + b) / 2), "tam": list(b - a), "cor": cores.get(o.name)})
return {"tiles": saida, "pecas": pecas, "total": len(alvo)}
'''

REFERENCIAS = r'''
from mathutils import Euler
ROT = {"frente": (90, 0, 0), "tras": (90, 0, 180), "direita": (90, 0, 90), "esquerda": (90, 0, -90),
       "cima": (0, 0, 0), "baixo": (180, 0, 0)}
geo, _ = geometria(resolver_alvos(ARGS.get("alvo"), ARGS.get("padrao")))
lo, hi = caixa_total(geo) if geo else (None, None)
col = bpy.data.collections.get("REFERENCIAS")
if col is None:
    col = bpy.data.collections.new("REFERENCIAS")
    scene.collection.children.link(col)
feitos = []
for ref in ARGS["refs"]:
    nome = ref["vista"]
    d, r, u = [Vector(v) for v in VISTAS[nome]]
    img = bpy.data.images.load(ref["caminho"], check_existing=True)
    W, H = img.size
    mpp = float(ref["mpp"])
    obj_nome = f"REF_{nome}"
    velho = bpy.data.objects.get(obj_nome)
    if velho is not None:
        bpy.data.objects.remove(velho, do_unlink=True)
    e = bpy.data.objects.new(obj_nome, None)
    col.objects.link(e)
    e.empty_display_type = "IMAGE"
    e.data = img
    e.empty_display_size = max(W, H) * mpp
    e.rotation_euler = Euler([math.radians(a) for a in ROT[nome]], "XYZ")
    sx = -1.0 if ref.get("espelhar") else 1.0
    e.scale = (sx, 1.0, 1.0)
    x0, y0, x1, y1 = ref["caixa"]
    plana = nome in ("cima", "baixo")
    lx = ((x0 + x1) / 2 - W / 2) * mpp * sx
    ly = (H / 2 - ((y0 + y1) / 2 if plana else y1)) * mpp
    if lo is not None:
        c = (lo + hi) / 2
        alvo_r = c.dot(r)
        alvo_u = c.dot(u) if plana else lo.z
        meia = sum(abs(d[i]) * (hi[i] - lo[i]) for i in range(3)) / 2
        prof = c.dot(d) - meia - 0.3
    else:
        alvo_r, alvo_u = 0.0, 0.0
        prof = -0.05 if plana else -3.0
    e.location = r * (alvo_r - lx) + u * (alvo_u - ly) + d * prof
    e.empty_image_depth = "BACK"
    e.show_empty_image_perspective = bool(ref.get("perspectiva", False))
    e.show_empty_image_orthographic = True
    e.show_empty_image_only_axis_aligned = True
    e.use_empty_image_alpha = True
    e.color = (1.0, 1.0, 1.0, float(ref.get("opacidade", 0.5)))
    e.hide_select = True
    feitos.append({"objeto": e.name, "vista": nome, "imagem": img.name, "largura_m": W * mpp, "altura_m": H * mpp,
                   "veiculo_m": [(x1 - x0) * mpp, (y1 - y0) * mpp], "espelhada": sx < 0})
return {"feitos": feitos, "colecao": col.name, "modelo_na_cena": lo is not None}
'''

CHECKPOINT = r'''
import time
atual = bpy.data.filepath
base = os.path.splitext(os.path.basename(atual))[0] if atual else "sem-nome"
pasta = os.path.join(ARGS["pasta"], base)
os.makedirs(pasta, exist_ok=True)
slug = re.sub(r"[^a-z0-9]+", "-", (ARGS.get("rotulo") or "").lower()).strip("-")[:40]
destino = os.path.join(pasta, time.strftime("%Y-%m-%d_%H%M%S") + (f"_{slug}" if slug else "") + ".blend")
win = bpy.context.window_manager.windows[0]
with bpy.context.temp_override(window=win):
    bpy.ops.wm.save_as_mainfile(filepath=destino, copy=True, check_existing=False, compress=True)
lista = sorted(f for f in os.listdir(pasta) if f.endswith(".blend"))
return {"destino": destino, "bytes": os.path.getsize(destino), "arquivo_atual": atual or "(não salvo)",
        "sujo": bpy.data.is_dirty, "anteriores": lista[-8:]}
'''

# Malhas como triângulos no mundo, numa árvore BVH só da REGIÃO pedida. Nunca a cena inteira nem
# scene.ray_cast em volume: em 12/11/2026 meio milhão de raios na cena do Axor + DAF (~9.400 objetos)
# travou o Blender aberto por mais de 1 hora. Tudo aqui para sozinho em LIMITE segundos.
MALHAS = r'''
import time
from mathutils.bvhtree import BVHTree
T0 = time.time()
LIMITE = max(2.0, min(float(ARGS.get("limite_s") or 15), 120.0))
MAX_TRI = 2500000

def esgotou():
    return time.time() - T0 > LIMITE

def cruza(lo, hi, a, b, folga=0.0):
    return all(hi[i] >= a[i] - folga and lo[i] <= b[i] + folga for i in range(3))

def triangulos(o):
    """(vértices no mundo, triângulos, material de cada triângulo) da malha avaliada."""
    ev = o.evaluated_get(dg)
    try:
        me = ev.to_mesh()
    except Exception:
        return None
    try:
        me.calc_loop_triangles()
        nv, nt = len(me.vertices), len(me.loop_triangles)
        if not nv or not nt:
            return None
        co = np.empty(nv * 3, dtype=np.float32)
        me.vertices.foreach_get("co", co)
        M = np.array(ev.matrix_world, dtype=np.float64)
        co = co.reshape(-1, 3).astype(np.float64) @ M[:3, :3].T + M[:3, 3]
        tr = np.empty(nt * 3, dtype=np.int32)
        me.loop_triangles.foreach_get("vertices", tr)
        mi = np.empty(nt, dtype=np.int32)
        me.loop_triangles.foreach_get("material_index", mi)
        return co, tr.reshape(-1, 3), mi
    finally:
        ev.to_mesh_clear()

def material_de(o, i):
    if 0 <= i < len(o.material_slots) and o.material_slots[i].material:
        return o.material_slots[i].material.name
    return None

class Arvore:
    """Uma BVH só com as malhas dadas; sabe de que peça e de que material é cada triângulo."""
    def __init__(self, objs):
        vs, ts, donos, mats = [], [], [], []
        self.objs, self.parou, self.n, base = [], False, 0, 0
        for o in objs:
            if esgotou() or self.n > MAX_TRI:
                self.parou = True
                break
            t = triangulos(o)
            if t is None:
                continue
            co, tr, mi = t
            donos.append(np.full(len(tr), len(self.objs), dtype=np.int32))
            self.objs.append(o)
            vs.append(co)
            ts.append(tr + base)
            mats.append(mi)
            base += len(co)
            self.n += len(tr)
        self.bvh = None
        if self.n:
            self.dono = np.concatenate(donos)
            self.mat = np.concatenate(mats)
            self.bvh = BVHTree.FromPolygons(np.concatenate(vs).tolist(), np.concatenate(ts).tolist())

    def quem(self, idx):
        o = self.objs[int(self.dono[idx])]
        return o, material_de(o, int(self.mat[idx]))
'''

SONDA = r'''
pontos = ARGS.get("pontos") or {}
caminhos = ARGS.get("caminhos") or {}
raio = float(ARGS.get("raio") or 0.5)
aviso = float(ARGS.get("aviso") or 0.012)
if ARGS.get("regiao"):
    r = ARGS["regiao"]
    a = Vector([min(r[i], r[i + 3]) for i in range(3)])
    b = Vector([max(r[i], r[i + 3]) for i in range(3)])
else:
    coords = [Vector(p) for p in pontos.values()] + [Vector(q) for c in caminhos.values() for q in c["pts"]]
    folga = raio + max([float(c.get("r", 0)) for c in caminhos.values()] + [0.0])
    a = Vector([min(p[i] for p in coords) - folga for i in range(3)])
    b = Vector([max(p[i] for p in coords) + folga for i in range(3)])
cand = []
for o in resolver_alvos(ARGS.get("alvo"), ARGS.get("padrao")):
    if o.type == "MESH":
        lo, hi = caixa(o)
        if cruza(lo, hi, a, b):
            cand.append(o)
arv = Arvore(cand)
if arv.bvh is None:
    return {"erro": "Nenhuma malha visível na região da sonda (confira pontos, regiao, alvo e padrao)."}
res_p = []
for nome, p in pontos.items():
    q = Vector(p)
    loc, nor, idx, d = arv.bvh.find_nearest(q, raio)
    if loc is None:
        res_p.append({"nome": nome, "nada": True})
        continue
    o, m = arv.quem(idx)
    res_p.append({"nome": nome, "peca": nome_completo(o), "material": m, "dist": d, "loc": list(loc),
                  "atras_da_face": d > 0.0005 and (q - loc).dot(nor) < 0})
res_c, parou = [], False
for nome, c in caminhos.items():
    if esgotou():
        parou = True
        break
    pts = [Vector(q) for q in c["pts"]]
    rc = float(c.get("r", 0))
    pior, perto = None, {}
    for p0, p1 in zip(pts, pts[1:]):
        nseg = max(2, int((p1 - p0).length / 0.01))
        for i in range(nseg + 1):
            q = p0.lerp(p1, i / nseg)
            loc, nor, idx, d = arv.bvh.find_nearest(q, raio + rc)
            if loc is None:
                continue
            f = d - rc
            o, m = arv.quem(idx)
            if pior is None or f < pior[0]:
                pior = [f, o.name, list(q)]
            if f < aviso and f < perto.get(o.name, (9e9,))[0]:
                perto[o.name] = (f, list(q))
    res_c.append({"nome": nome, "r": rc, "pior": pior,
                  "perto": sorted([[k, v[0], v[1]] for k, v in perto.items()], key=lambda t: t[1])[:12]})
return {"pontos": res_p, "caminhos": res_c, "malhas": len(arv.objs), "tri": arv.n, "candidatas": len(cand),
        "parou": parou or arv.parou, "regiao": [list(a), list(b)], "segundos": time.time() - T0}
'''

CRUZAMENTOS = r'''
alvo = [o for o in resolver_alvos(ARGS.get("objetos"), ARGS.get("padrao"), ARGS.get("regiao")) if o.type == "MESH"]
if not alvo:
    return {"erro": "Nenhuma malha visível casou com objetos/padrao/regiao."}
if len(alvo) > 400:
    return {"erro": f"{len(alvo)} peças no alvo: restrinja (objetos, padrao ou regiao) a no máximo 400."}
rx_contra = re.compile(ARGS["contra_padrao"], re.I) if ARGS.get("contra_padrao") else None
rx_ign = re.compile(ARGS["ignorar_padrao"], re.I) if ARGS.get("ignorar_padrao") else None
outras = []
for o in resolver_alvos():
    if o.type != "MESH" or (rx_ign and rx_ign.search(o.name)):
        continue
    if rx_contra and not rx_contra.search(o.name) and o not in alvo:
        continue
    lo, hi = caixa(o)
    outras.append((o, lo, hi))
cache = {}
def arvore(o):
    if o.name not in cache:
        t = triangulos(o)
        cache[o.name] = None if t is None else (BVHTree.FromPolygons(t[0].tolist(), t[1].tolist()), t[0], t[1])
    return cache[o.name]
res, vistos, parou, feitas = [], set(), False, 0
for o in alvo:
    if esgotou():
        parou = True
        break
    lo, hi = caixa(o)
    a = arvore(o)
    feitas += 1
    if a is None:
        continue
    achados = []
    for q, qlo, qhi in outras:
        if q is o or (q.name, o.name) in vistos or not cruza(lo, hi, qlo, qhi, 0.0005):
            continue
        if esgotou():
            parou = True
            break
        b = arvore(q)
        if b is None:
            continue
        par = a[0].overlap(b[0])
        if par:
            vistos.add((o.name, q.name))
            ids = np.array([i for i, _ in par[:3000]], dtype=np.int64)
            cen = a[1][a[2][ids]].mean(axis=1)
            achados.append({"com": q.name, "pares": len(par), "centro": cen.mean(axis=0).tolist(),
                            "de": cen.min(axis=0).tolist(), "ate": cen.max(axis=0).tolist()})
    if achados:
        res.append({"peca": o.name, "cruza": sorted(achados, key=lambda x: -x["pares"])[:12]})
return {"resultado": res, "alvo": len(alvo), "verificadas": feitas, "parou": parou, "segundos": time.time() - T0}
'''

PRE_EXPORTAR = r'''
def tem_textura(m):
    nt = getattr(m, "node_tree", None)
    return bool(nt) and any(n.type == "TEX_IMAGE" and n.image and any(s.is_linked for s in n.outputs) for n in nt.nodes)

def metal(m):
    nt = getattr(m, "node_tree", None)
    b = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None) if nt else None
    if b is None:
        return 0.0
    e = b.inputs.get("Metallic")
    return 0.0 if e is None else (1.0 if e.is_linked else float(e.default_value))

if ARGS.get("colecao"):
    col = bpy.data.collections.get(ARGS["colecao"])
    if col is None:
        return {"erro": f"Não existe a coleção {ARGS['colecao']!r}. Algumas: " +
                ", ".join(sorted(c.name for c in bpy.data.collections)[:30])}
    objs = list(col.all_objects)
    if ARGS.get("padrao"):
        rx = re.compile(ARGS["padrao"], re.I)
        objs = [o for o in objs if rx.search(o.name)]
else:
    objs = resolver_alvos(ARGS.get("alvo"), ARGS.get("padrao"))
if not objs:
    return {"erro": "Nada para conferir (coleção vazia ou nada visível casou)."}
vis = [o for o in objs if o.visible_get()]
nomes = {o.name for o in vis}
malhas = [o for o in vis if o.type == "MESH"]
faces = tri = 0
vazias, mods, neg, sem_mat, sem_uv, attrs, usados = [], [], [], [], [], {}, {}
for o in malhas:
    me = o.data
    nf = len(me.polygons)
    faces += nf
    if not nf:
        vazias.append(o.name)
        continue
    lt = np.empty(nf, dtype=np.int32)
    me.polygons.foreach_get("loop_total", lt)
    tri += int((lt - 2).sum())
    if o.modifiers:
        mods.append([o.name, [m.type for m in o.modifiers]])
    if o.matrix_world.determinant() < 0:
        neg.append(o.name)
    uvs = set(me.uv_layers.keys())
    for at in me.attributes:
        if not at.is_internal and not at.name.startswith(".") and at.name not in uvs and \
                at.name not in ("position", "sharp_face", "material_index", "sharp_edge"):
            attrs[at.name] = attrs.get(at.name, 0) + 1
    mi = np.empty(nf, dtype=np.int32)
    me.polygons.foreach_get("material_index", mi)
    for i in np.unique(mi).tolist():
        m = o.material_slots[i].material if i < len(o.material_slots) else None
        if m is None:
            sem_mat.append(o.name)
            continue
        usados.setdefault(m.name, []).append(o.name)
        if not uvs and tem_textura(m):
            sem_uv.append([o.name, m.name])
mats = [bpy.data.materials[n] for n in usados]
imagens = set()
for m in mats:
    nt = getattr(m, "node_tree", None)
    for n in (nt.nodes if nt else []):
        if n.type == "TEX_IMAGE" and n.image:
            imagens.add(n.image)
geo, _ = geometria(vis)
lo, hi = caixa_total(geo) if geo else (Vector(), Vector())
return {
    "objetos": len(objs), "visiveis": len(vis), "malhas": len(malhas), "faces": faces, "triangulos": tri,
    "tipos": sorted({o.type for o in vis}), "ocultos": [o.name for o in objs if not o.visible_get()][:30],
    "n_ocultos": sum(1 for o in objs if not o.visible_get()),
    "pai_fora": [[o.name, o.parent.name] for o in vis if o.parent and o.parent.name not in nomes][:20],
    "modificadores": mods[:20], "n_modificadores": len(mods), "vazias": vazias[:20], "n_vazias": len(vazias),
    "escala_negativa": neg[:10], "n_escala_negativa": len(neg),
    "sem_material": sorted(set(sem_mat))[:20], "n_sem_material": len(set(sem_mat)),
    "textura_sem_uv": sem_uv[:20], "n_textura_sem_uv": len(sem_uv),
    "materiais": len(mats), "com_textura": sum(1 for m in mats if tem_textura(m)),
    "dupla_face": sum(1 for m in mats if not m.use_backface_culling),
    "metal_alto": sorted([[m.name, round(metal(m), 2), len(usados[m.name])] for m in mats if metal(m) > 0.3],
                         key=lambda t: -t[2])[:15],
    "duplicados": [n for n in usados if re.search(r"\.\d{3}$", n) and n[:-4] in usados][:20],
    "atributos": attrs, "propriedades": sorted({k for o in vis for k in o.keys() if not k.startswith("_")})[:20],
    "imagens": len(imagens), "maior_imagem": max([list(i.size) for i in imagens], key=lambda s: s[0] * s[1], default=None),
    "caixa": [list(lo), list(hi)], "arquivo": bpy.data.filepath or "(não salvo)",
}
'''

CAIXAS = r'''
if ARGS.get("colecao"):
    col = bpy.data.collections.get(ARGS["colecao"])
    if col is None:
        return {"erro": f"Não existe a coleção {ARGS['colecao']!r}."}
    objs = list(col.all_objects)
    if ARGS.get("padrao"):
        rx = re.compile(ARGS["padrao"], re.I)
        objs = [o for o in objs if rx.search(o.name)]
else:
    objs = resolver_alvos(ARGS.get("alvo"), ARGS.get("padrao"))
caixas, ocultas = {}, []
for o in objs:
    if o.type != "MESH":
        continue
    if not o.visible_get():
        ocultas.append(o.name)
        continue
    ev = o.evaluated_get(dg)
    if not len(ev.data.vertices):
        continue
    # 8 cantos da caixa LOCAL levados ao mundo, como o GLB guarda (min/max do POSITION + nó):
    # a caixa exata no mundo daria diferença falsa em peça girada.
    cs = np.array([list(ev.matrix_world @ Vector(c)) for c in ev.bound_box])
    caixas[o.name] = [cs.min(axis=0).tolist(), cs.max(axis=0).tolist()]
return {"caixas": caixas, "ocultas": ocultas[:40], "n_ocultas": len(ocultas)}
'''

OLHAR = r'''
area, space, region = area_3d()
if region is None:
    return {"erro": "Nenhuma janela 3D aberta no Blender."}
tam = int(ARGS.get("tamanho") or 1200)
if ARGS.get("vista_atual"):
    r3d = space.region_3d
    view = r3d.view_matrix.copy()
    proj = r3d.window_matrix.copy()
    w, h = tam, max(200, int(tam * region.height / max(region.width, 1)))
    cam = view.inverted()
    olho = cam.translation.copy()
    alvo_v = r3d.view_location.copy()
    modo = r3d.view_perspective
else:
    olho, alvo_v = Vector(ARGS["olho"]), Vector(ARGS["alvo"])
    d = alvo_v - olho
    if d.length < 1e-4:
        return {"erro": "olho e alvo no mesmo ponto."}
    if abs(d.normalized().z) > 0.999:
        alvo_v.y += 0.001 * d.length
    w = tam
    h = max(200, int(tam * float(ARGS.get("proporcao") or 0.64)))
    rot = (alvo_v - olho).to_track_quat("-Z", "Y").to_matrix().to_4x4()
    view = (Matrix.Translation(olho) @ rot).inverted()
    fx = float(ARGS.get("lente") or 35) / 18.0      # sensor de 36 mm na horizontal, como a câmera do Blender
    fy = fx * w / h
    near, far = 0.02, 1000.0
    proj = Matrix(((fx, 0, 0, 0), (0, fy, 0, 0),
                   (0, 0, (far + near) / (near - far), 2 * far * near / (near - far)), (0, 0, -1, 0)))
    modo = "PERSP"
esconder = []
if ARGS.get("esconder"):
    faltam = [n for n in ARGS["esconder"] if n not in bpy.data.objects]
    if faltam:
        return {"erro": "Não existe objeto chamado " + ", ".join(repr(n) for n in faltam)}
    esconder += resolver_alvos(ARGS["esconder"])
if ARGS.get("esconder_padrao"):
    rx = re.compile(ARGS["esconder_padrao"], re.I)
    esconder += [o for o in scene.objects if o.visible_get() and rx.search(o.name)]
for nome in ARGS.get("esconder_colecoes") or []:
    c = bpy.data.collections.get(nome)
    if c is None:
        return {"erro": f"Não existe a coleção {nome!r}."}
    esconder += [o for o in c.all_objects if o.visible_get()]
if ARGS.get("esconder_regiao"):
    esconder += resolver_alvos(regiao=ARGS["esconder_regiao"])
ocultos = []
try:
    for o in {x.name: x for x in esconder}.values():
        try:
            o.hide_set(True)
            ocultos.append(o)
        except Exception:
            pass
    bpy.context.view_layer.update()
    if ARGS.get("sombreamento") == "vista":
        mudar(space.overlay, "show_overlays", False)
    else:
        sombreamento(space, ARGS.get("sombreamento") or "material")
    img = desenhar(space, region, view, proj, w, h)
    arq = os.path.join(ARGS["pasta"], "olhar.npy")
    np.save(arq, img)
    # Pixels apontados: raio da câmera pelo pixel; peças escondidas na foto não contam.
    escondidas = {o.name for o in ocultos}
    dg2 = bpy.context.evaluated_depsgraph_get()
    inv = (proj @ view).inverted()
    pontos = []
    for k, (px, py) in enumerate(ARGS.get("apontar") or []):
        x, y = 2 * (px + 0.5) / w - 1, 1 - 2 * (py + 0.5) / h
        p0, p1 = inv @ Vector((x, y, -1, 1)), inv @ Vector((x, y, 1, 1))
        p0, p1 = p0.xyz / p0.w, p1.xyz / p1.w
        direcao = (p1 - p0).normalized()
        origem, hit = p0.copy(), None
        for _ in range(30):
            ok, loc, nor, idx, ob, _m = scene.ray_cast(dg2, origem, direcao, distance=1000.0)
            if not ok:
                break
            if ob is not None and ob.name in escondidas:
                origem = loc + direcao * 1e-4
                continue
            hit = (loc, ob, idx)
            break
        if hit is None:
            pontos.append({"n": k + 1, "px": [px, py], "nada": True})
            continue
        loc, ob, idx = hit
        mat = None
        try:
            mi = ob.evaluated_get(dg2).data.polygons[idx].material_index
            slot = ob.material_slots[mi] if mi < len(ob.material_slots) else None
            mat = slot.material.name if slot and slot.material else None
        except Exception:
            pass
        pontos.append({"n": k + 1, "px": [px, py], "peca": nome_completo(ob), "material": mat, "loc": list(loc),
                       "dist": (loc - olho).length})
finally:
    restaurar()
    mostrar(ocultos)
    bpy.context.view_layer.update()
c = proj @ view @ Vector((alvo_v.x, alvo_v.y, alvo_v.z, 1.0))
alvo_px = [(c.x / c.w + 1) / 2 * w, (1 - c.y / c.w) / 2 * h] if c.w > 0 else None
return {"arquivo": arq, "w": w, "h": h, "olho": list(olho), "alvo": list(alvo_v), "modo": modo,
        "lente": proj[0][0] * 18.0 if modo == "PERSP" else None, "proporcao": h / w,
        "escondidas": len(ocultos), "pontos": pontos, "alvo_px": alvo_px}
'''
