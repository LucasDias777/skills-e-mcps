"""blender-pro: ferramentas extras para o MCP do Blender.

Conversa com o mesmo add-on do MCP oficial (BlenderMCP, porta 9876) pelo comando execute_code, sem
mexer no MCP oficial: ele continua se atualizando sozinho pelo uvx.
"""

import io
import json
import math
import os
import re
import shutil
import socket
import tempfile
from pathlib import Path

import numpy as np
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Image as ImagemMCP
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import scripts as S

BASE = Path(__file__).resolve().parent
GUIAS = BASE / "guias"
HOST = os.environ.get("BLENDER_HOST", "localhost")
PORTA = int(os.environ.get("BLENDER_PORT", "9876"))
PASTA_CHECKPOINTS = os.environ.get("BLENDER_PRO_CHECKPOINTS", str(Path.home() / "Documents" / "blender-checkpoints"))
VISTAS = ("frente", "tras", "direita", "esquerda", "cima", "baixo")
ANGULOS = VISTAS + ("tres_quartos", "tres_quartos_tras", "tres_quartos_esq")
OLHO = {"frente": "−Y", "tras": "+Y", "direita": "+X", "esquerda": "−X", "cima": "+Z", "baixo": "−Z"}
EIXO = "XYZ"
NOMES_COR = {(1.0, 0.35, 0.0): "laranja", (0.0, 0.45, 1.0): "azul", (0.1, 0.8, 0.2): "verde",
             (0.9, 0.0, 0.7): "magenta", (1.0, 0.85, 0.0): "amarelo", (0.0, 0.85, 0.85): "ciano",
             (0.85, 0.05, 0.05): "vermelho", (0.5, 0.2, 0.9): "roxo"}

INSTRUCOES = """blender-pro completa o MCP oficial do Blender (mesmo Blender, mesmo add-on na porta 9876).
Use os dois juntos: o oficial (execute_blender_code, look, get_scene_info) para editar e olhar; este
para medir, conferir e saber como as coisas são de verdade.

- Antes de modelar algo real: guia("fluxo") e o guia do tipo (caminhoes, onibus, motos, carros,
  rodas-e-pneus). Começar de referência e de medida de fábrica, nunca da imaginação.
- Antes de script grande, de exportar ou de editar malha importada: guia("armadilhas"). Vidro,
  interior, luzes, logos, conversão de DAE/STEP/JT e roteiro de export: guia("receitas").
- medir: dimensões, chão, eixos, entre-eixos, balanços, frente provável, simetria e avisos.
- vistas_tecnicas: vistas ortográficas na mesma escala, com grade de 1 m, cotas e eixos marcados.
- comparar_referencia: sobrepõe uma imagem de referência e mede onde o modelo difere dela.
- referencias_na_cena: põe blueprints na cena em escala real (coleção REFERENCIAS).
- destacar: pinta peças por nome, regex ou região, para identificar antes de mexer.
- checkpoint: salva uma cópia do .blend antes de operação grande (o arquivo aberto não muda).
- olhar_de: foto de qualquer ponto de vista (dentro da cabine, por baixo) ou da vista atual do usuário;
  aponta pixels e diz qual peça e material estão ali. Conferir do MESMO ângulo do print do usuário.
- sonda: peça mais perto de um ponto e folga de um trajeto de tubo/mangueira contra as peças.
- cruzamentos: peça atravessando peça (peça sobreposta costuma ser artefato).
- pre_exportar e comparar_glb: conferir antes de exportar e provar que o GLB saiu igual à cena.

Nada demorado no Blender aberto do usuário: sonda e cruzamentos trabalham numa região e param no limite de
tempo; análise pesada vai para um Blender de fundo sobre um checkpoint.

Eixos: Z para cima, metros; veículo com a frente em −Y. As vistas seguem o teclado
numérico: frente = olho em −Y, direita = olho em +X (mostra o lado esquerdo do veículo, com a frente
à esquerda da imagem), cima = olho em +Z. Nunca exportar por cima de um original sem o usuário
autorizar."""

mcp = FastMCP("blender-pro", instructions=INSTRUCOES)


class ErroBlender(Exception):
    pass


# ---------------------------------------------------------------- conexão com o add-on

def _enviar(codigo: str) -> str:
    try:
        s = socket.create_connection((HOST, PORTA), timeout=5)
    except OSError:
        raise ErroBlender(f"O Blender não respondeu em {HOST}:{PORTA}. Abra o Blender (o add-on BlenderMCP "
                          "sobe o servidor sozinho) e tente de novo.")
    buf, resp = b"", None
    with s:
        s.sendall(json.dumps({"type": "execute_code", "params": {"code": codigo}}).encode("utf-8"))
        s.settimeout(300)
        while resp is None:
            try:
                parte = s.recv(1 << 16)
            except socket.timeout:
                raise ErroBlender("O Blender levou mais de 5 minutos para responder.")
            if not parte:
                break
            buf += parte
            try:
                resp = json.loads(buf.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
    if resp is None:
        raise ErroBlender("O Blender fechou a conexão sem responder.")
    if resp.get("status") == "error":
        raise ErroBlender("Erro no Blender: " + str(resp.get("message")))
    res = resp.get("result") or {}
    return res.get("result", "") if isinstance(res, dict) else str(res)


def _rodar(*partes: str, **args) -> dict:
    r = S.ler_resultado(_enviar(S.montar(*partes, args=args)))
    if r.get("erro"):
        trace = r.get("trace", "")
        detalhe = "\n" + trace[-700:] if trace and "ValueError" not in r["erro"] else ""
        raise ErroBlender(r["erro"] + detalhe)
    return r


# ---------------------------------------------------------------- texto

def n(v, c=2):
    return f"{v:.{c}f}".replace(".", ",").replace("-", "−")


def mil(v):
    return f"{int(v):,}".replace(",", ".")


def eixo_sinal(eixo, sinal):
    return ("+" if sinal > 0 else "−") + EIXO[eixo]


def _validar_frente(frente):
    if frente and not re.fullmatch(r"[+\-−]?[XYZxyz]", frente.strip()):
        raise ValueError("frente é um eixo com sinal, como '-Y' ou '+X'.")


def _linhas_eixos(r):
    lo, hi, iL = r["lo"], r["hi"], r["iL"]
    f = r.get("frente") or {}
    linhas = []
    if f.get("sinal"):
        ev = "; ".join(f.get("evidencias") or [])
        linhas.append(f"Frente: {eixo_sinal(f['eixo'], f['sinal'])} (confiança {f['confianca']}" + (f"; {ev}" if ev else "") + ")")
    else:
        ev = "; ".join(f.get("evidencias") or [])
        linhas.append(f"Frente: {f.get('confianca', 'indefinida')}" + (f" ({ev})" if ev else "")
                      + ". Passe frente='-Y' (por exemplo) se souber.")
    eixos = r.get("eixos") or []
    if not eixos:
        linhas.append("Eixos: nenhuma roda encostada no chão foi achada.")
        return linhas
    s = f.get("sinal") or -1
    ordem = sorted(eixos, key=lambda e: e["pos"] * (1 if s < 0 else -1))
    partes = []
    for e in ordem:
        d = f"Ø{n(e['diametro'])}" if e.get("diametro") else "Ø ?"
        tipo = "duplo" if e.get("duplo") else "simples"
        lados = "" if e.get("lados", 2) == 2 else ", só um lado"
        partes.append(f"{EIXO[iL]} {n(e['pos'])} ({d}, {tipo}{lados})")
    origem = "da frente para trás" if f.get("sinal") else f"em {EIXO[iL]} crescente"
    linhas.append(f"Eixos ({origem}), {len(eixos)} no total: " + ", ".join(partes) + f" [{r.get('metodo_rodas')}]")
    if len(ordem) >= 2:
        dist = [abs(ordem[i + 1]["pos"] - ordem[i]["pos"]) for i in range(len(ordem) - 1)]
        linhas.append("Entre-eixos: " + " + ".join(n(x) for x in dist) + f" m (1º ao último: {n(sum(dist))} m)")
    if f.get("sinal") and f.get("eixo") == iL:
        ponta_f = lo[iL] if f["sinal"] < 0 else hi[iL]
        ponta_t = hi[iL] if f["sinal"] < 0 else lo[iL]
        linhas.append(f"Balanços: dianteiro {n(abs(ordem[0]['pos'] - ponta_f))} m · traseiro "
                      f"{n(abs(ponta_t - ordem[-1]['pos']))} m")
    return linhas


def _texto_medir(r):
    lo, hi, iL, iW = r["lo"], r["hi"], r["iL"], r["iW"]
    dim = [hi[i] - lo[i] for i in range(3)]
    L = [f"Medição de {mil(r['objetos'])} objetos com geometria ({r['arquivo']})."]
    if r.get("chao_ignorado"):
        L.append("Chão ignorado na medida: " + ", ".join(r["chao_ignorado"]))
    L.append(f"Caixa: X {n(lo[0])} a {n(hi[0])} | Y {n(lo[1])} a {n(hi[1])} | Z {n(lo[2])} a {n(hi[2])}")
    L.append(f"Comprimento {n(dim[iL])} m (em {EIXO[iL]}) · largura {n(dim[iW])} m (em {EIXO[iW]}) · altura {n(dim[2])} m")
    chao = r["chao"]
    if abs(chao) < 0.002:
        L.append("Chão: Z mínimo 0 (apoiado)")
    elif abs(chao) < 0.02:
        L.append(f"Chão: Z mínimo {n(chao * 1000, 0)} mm (quase apoiado)")
    else:
        L.append(f"Chão: Z mínimo {n(chao, 3)} m ⚠️ não está apoiado em Z = 0")
    cW = (lo[iW] + hi[iW]) / 2
    L.append(f"Centro: {EIXO[iW]} {n(cW)} (lateral) · {EIXO[iL]} {n((lo[iL] + hi[iL]) / 2)} (comprimento)"
             + (f" ⚠️ fora do centro lateral ({EIXO[iW]} = 0)" if abs(cW) > 0.05 else ""))
    rodas = [e["w"] for e in r.get("eixos") or [] if e.get("w")]
    if rodas:
        L.append(f"Largura sobre as rodas: {n(max(w[1] for w in rodas) - min(w[0] for w in rodas))} m")
    ex = r.get("extremos_laterais") or []
    if ex:
        desc = " e ".join(f"{e['nome']} (Z {n(e['z'][0])} a {n(e['z'][1])}, {n(e['comp'])} m de comprimento)" for e in ex)
        altos = all(e["z"][0] > 0.8 and e["comp"] < 0.6 for e in ex)
        L.append(f"Quem define a largura total: {desc}" + (" (peças altas e curtas: provavelmente os retrovisores)" if altos else ""))
    L += _linhas_eixos(r)
    sm = r.get("simetria")
    if sm:
        txt = (f"Simetria no plano {EIXO[iW]} = {n(sm['plano'], 3)}: {round(sm['ate_1cm'] * 100)} % dos pontos têm par "
               f"a ≤ 1 cm ({round(sm['ate_3cm'] * 100)} % a ≤ 3 cm)")
        if sm.get("sem_par"):
            p = sm["sem_par"]
            txt += f"; os sem par se concentram perto de X {n(p[0])}, Y {n(p[1])}, Z {n(p[2])}"
        L.append(txt)
    L.append(f"{mil(r['triangulos'])} triângulos · {mil(r['materiais'])} materiais")
    if r.get("n_metal_alto"):
        mais = "…" if r["n_metal_alto"] > len(r["metal_alto"]) else ""
        L.append(f"⚠️ {r['n_metal_alto']} materiais com metal > 0,3 (three.js sem envMap pede ≤ 0,3): " + ", ".join(r["metal_alto"]) + mais)
    if r.get("escala_negativa"):
        L.append(f"⚠️ {r['escala_negativa']} objetos com escala negativa (espelhados; confira as normais)")
    if r.get("escala_nao_aplicada"):
        L.append(f"{r['escala_nao_aplicada']} objetos com escala diferente de 1 (aplicar antes de bevel/solidify)")
    if r.get("modo") and r["modo"] != "OBJECT":
        L.append(f"Modo atual do Blender: {r['modo']}")
    return "\n".join(L)


# ---------------------------------------------------------------- imagem

_FONTES = {}


def fonte(t, negrito=False):
    chave = (t, negrito)
    if chave not in _FONTES:
        nomes = ("segoeuib.ttf", "arialbd.ttf") if negrito else ("segoeui.ttf", "arial.ttf")
        for nome in nomes:
            p = os.path.join("C:/Windows/Fonts", nome)
            if os.path.exists(p):
                _FONTES[chave] = ImageFont.truetype(p, t)
                break
        else:
            _FONTES[chave] = ImageFont.load_default()
    return _FONTES[chave]


def _png(im):
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def _texto(d, xy, txt, t=12, cor=(0, 0, 0, 255), fundo=(255, 255, 255, 215), negrito=False):
    f = fonte(t, negrito)
    x0, y0, x1, y1 = d.textbbox(xy, txt, font=f)
    d.rectangle([x0 - 3, y0 - 2, x1 + 3, y1 + 2], fill=fundo)
    d.text(xy, txt, font=f, fill=cor)


def _x(t, v):
    ri, rs = t["r"]
    return (rs * v - (t["c_r"] - t["hw"])) * t["ppm_x"]


def _y(t, v):
    ui, us = t["u"]
    return ((t["c_u"] + t["hh"]) - us * v) * t["ppm_y"]


def _faixa(c, h, s):
    a, b = s * (c - h), s * (c + h)
    return min(a, b), max(a, b)


def _cota_h(d, x0, x1, y, txt, cor=(20, 20, 20, 255)):
    x0, x1 = sorted((x0, x1))
    d.line([(x0, y), (x1, y)], fill=cor, width=1)
    for x in (x0, x1):
        d.line([(x, y - 5), (x, y + 5)], fill=cor, width=1)
    f = fonte(12)
    w = d.textlength(txt, font=f)
    _texto(d, ((x0 + x1) / 2 - w / 2, y - 16), txt, cor=cor)


def _cota_v(d, x, y0, y1, txt, cor=(20, 20, 20, 255)):
    y0, y1 = sorted((y0, y1))
    d.line([(x, y0), (x, y1)], fill=cor, width=1)
    for y in (y0, y1):
        d.line([(x - 5, y), (x + 5, y)], fill=cor, width=1)
    _texto(d, (x + 6, (y0 + y1) / 2 - 8), txt, cor=cor)


def _anotar(im, t, r, grade, cotas):
    d = ImageDraw.Draw(im, "RGBA")
    w, h = im.size
    ri, rs = t["r"]
    ui, us = t["u"]
    lo, hi, iL, iW = r["lo"], r["hi"], r["iL"], r["iW"]
    ppm = t["ppm_x"]
    if grade:
        for passo, cor, minimo in ((0.1, (0, 0, 0, 16), 9), (0.5, (0, 0, 0, 34), 22), (1.0, (0, 0, 0, 75), 5)):
            if passo * ppm < minimo:
                continue
            a, b = _faixa(t["c_r"], t["hw"], rs)
            for v in np.arange(math.ceil(a / passo) * passo, b + 1e-9, passo):
                x = _x(t, v)
                d.line([(x, 0), (x, h)], fill=cor)
            a, b = _faixa(t["c_u"], t["hh"], us)
            for v in np.arange(math.ceil(a / passo) * passo, b + 1e-9, passo):
                y = _y(t, v)
                d.line([(0, y), (w, y)], fill=cor)
        passo_rot = 1 if ppm >= 28 else (2 if ppm >= 14 else 5)
        a, b = _faixa(t["c_r"], t["hw"], rs)
        for v in range(math.ceil(a / passo_rot) * passo_rot, math.floor(b) + 1, passo_rot):
            d.text((_x(t, v) + 2, h - 14), f"{v:g}", font=fonte(10), fill=(70, 70, 70, 255))
        a, b = _faixa(t["c_u"], t["hh"], us)
        for v in range(math.ceil(a / passo_rot) * passo_rot, math.floor(b) + 1, passo_rot):
            d.text((2, _y(t, v) - 12), f"{v:g}", font=fonte(10), fill=(70, 70, 70, 255))
    if ui == 2 and (grade or cotas):
        yc = _y(t, r["chao"])
        d.line([(0, yc), (w, yc)], fill=(130, 75, 20, 255), width=2)
        _texto(d, (w - 44, yc + 3), "chão", t=11, cor=(130, 75, 20, 255))
    if cotas:
        nome_eixo = {iL: "comprimento", iW: "largura", 2: "altura"}
        x0, x1 = sorted((_x(t, lo[ri]), _x(t, hi[ri])))
        y0, y1 = sorted((_y(t, lo[ui]), _y(t, hi[ui])))
        y_eixos = min(h - 34, y1 + 20)
        y_total = min(h - 18, y1 + 44)
        _cota_h(d, x0, x1, y_total, f"{nome_eixo[ri]} {n(hi[ri] - lo[ri])} m")
        _cota_v(d, max(8, x0 - 18), y0, y1, f"{nome_eixo[ui]} {n(hi[ui] - lo[ui])} m")
        eixos = r.get("eixos") or []
        vermelho = (215, 35, 35, 255)
        if eixos and ri == iL:
            xs = sorted(((_x(t, e["pos"]), e) for e in eixos), key=lambda p: p[0])
            for x, e in xs:
                if ui == 2 and e.get("diametro"):
                    rpx = e["diametro"] / 2 * ppm
                    cy = _y(t, r["chao"] + e["diametro"] / 2)
                    d.ellipse([x - rpx, cy - rpx, x + rpx, cy + rpx], outline=vermelho, width=2)
                    d.line([(x - 5, cy), (x + 5, cy)], fill=vermelho, width=2)
                    d.line([(x, cy - 5), (x, cy + 5)], fill=vermelho, width=2)
                    _texto(d, (x - 16, cy - rpx - 18), f"Ø{n(e['diametro'])}", t=11, cor=vermelho)
                else:
                    d.line([(x, 0), (x, h)], fill=(215, 35, 35, 130), width=1)
            for (xa, ea), (xb, eb) in zip(xs, xs[1:]):
                _cota_h(d, xa, xb, y_eixos, n(abs(eb["pos"] - ea["pos"])), cor=vermelho)
        if eixos and ui == iL:
            for e in eixos:
                y = _y(t, e["pos"])
                d.line([(0, y), (w, y)], fill=(215, 35, 35, 130), width=1)
        f = r.get("frente") or {}
        if f.get("sinal") and f.get("eixo") in (ri, ui):
            ponta = lo[f["eixo"]] if f["sinal"] < 0 else hi[f["eixo"]]
            azul = (20, 90, 200, 255)
            if f["eixo"] == ri:
                x = _x(t, ponta)
                lado = 1 if x > (x0 + x1) / 2 else -1
                ya = 30
                d.polygon([(x + lado * 14, ya), (x, ya - 7), (x, ya + 7)], fill=azul)
                tw = d.textlength("FRENTE", font=fonte(12, True))
                _texto(d, (x - tw - 4, ya + 9) if lado > 0 else (x + 4, ya + 9), "FRENTE", cor=azul, negrito=True)
            else:
                y = _y(t, ponta)
                lado = 1 if y > (y0 + y1) / 2 else -1
                xa = 30
                d.polygon([(xa, y + lado * 14), (xa - 7, y), (xa + 7, y)], fill=azul)
                _texto(d, (xa + 10, y - 8), "FRENTE", cor=azul, negrito=True)
    _texto(d, (6, 4), f"{t['vista'].upper()} · olho em {OLHO[t['vista']]} · → {eixo_sinal(ri, rs)}  ↑ {eixo_sinal(ui, us)}",
           t=13, negrito=True)


def _folha(imgs, titulo, max_lado=None):
    cols = 1 if len(imgs) == 1 else 2
    linhas = [imgs[i:i + cols] for i in range(0, len(imgs), cols)]
    gap, topo = 10, 30
    W = max(sum(im.width for im in ln) + gap * (len(ln) - 1) for ln in linhas) + 2 * gap
    H = topo + sum(max(im.height for im in ln) for ln in linhas) + gap * (len(linhas) + 1)
    folha = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(folha)
    d.text((gap, 7), titulo, font=fonte(14, True), fill=(0, 0, 0))
    y = topo + gap
    for ln in linhas:
        x = gap
        for im in ln:
            folha.paste(im, (x, y))
            d.rectangle([x - 1, y - 1, x + im.width, y + im.height], outline=(160, 160, 160))
            x += im.width + gap
        y += max(im.height for im in ln) + gap
    if max_lado and max(folha.size) > max_lado:
        folha.thumbnail((max_lado, max_lado), Image.LANCZOS)
    return folha


def _k(forma):
    return max(5, int(round(0.008 * max(forma))) | 1)


def _mascara(im, tol, k=None):
    a = np.asarray(im.convert("RGBA"), dtype=np.int16)
    if (a[..., 3] < 250).mean() > 0.02:
        m = a[..., 3] > 128
    else:
        rgb = a[..., :3]
        borda = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
        fundo = np.median(borda, axis=0)
        m = np.abs(rgb - fundo).max(axis=-1) > tol
    return _limpar(_fechar(m), k)


def _fechar(m):
    """Fecha frestas de poucos pixels (para-lama × pneu, vãos de painel)."""
    mi = Image.fromarray(m.astype(np.uint8) * 255)
    return np.asarray(mi.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))) > 127


def _limpar(m, k=None):
    """Tira da máscara o que não é o veículo: traço fino (linha de chão, cota, texto, grade) não
    sobrevive a uma abertura, e o que estiver solto do maior bloco fica de fora. Referência e modelo
    passam pelo mesmo filtro, então as peças finas (haste de retrovisor, antena) somem dos dois."""
    k = k or _k(m.shape)
    nucleo = np.asarray(Image.fromarray(m.astype(np.uint8) * 255)
                        .filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k))) > 127
    cx = _bloco(nucleo)
    if cx is None:
        return nucleo
    x0, y0, x1, y1 = cx
    f = np.zeros_like(m)
    f[y0:y1, x0:x1] = True
    return nucleo & f


def _preencher(m):
    """Fecha buracos (janelas, vãos internos) sem fechar o vão entre as rodas: o pixel vira objeto
    só se estiver entre o primeiro e o último pixel do objeto na linha E na coluna."""
    h, w = m.shape
    lin_ok, col_ok = m.any(axis=1), m.any(axis=0)
    ix, iy = np.arange(w), np.arange(h)
    a = np.argmax(m, axis=1)
    b = w - 1 - np.argmax(m[:, ::-1], axis=1)
    lin = (ix[None, :] >= a[:, None]) & (ix[None, :] <= b[:, None]) & lin_ok[:, None]
    a = np.argmax(m, axis=0)
    b = h - 1 - np.argmax(m[::-1, :], axis=0)
    col = (iy[:, None] >= a[None, :]) & (iy[:, None] <= b[None, :]) & col_ok[None, :]
    return m | (lin & col)


def _caixa(m, frac=0.003):
    cols = np.where(m.sum(axis=0) > max(1, frac * m.shape[0]))[0]
    rows = np.where(m.sum(axis=1) > max(1, frac * m.shape[1]))[0]
    if not len(cols) or not len(rows):
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def _abrir(m, k):
    im = Image.fromarray(m.astype(np.uint8) * 255)
    return np.asarray(im.filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k))) > 127


def _maior_faixa(proj, folga):
    """Maior trecho contínuo (em massa) de uma projeção, aceitando buracos de até `folga` posições."""
    on = np.flatnonzero(proj > 0)
    if not len(on):
        return None
    melhor, ini, ant = None, on[0], on[0]
    for i in list(on[1:]) + [None]:
        if i is not None and i - ant <= folga + 1:
            ant = i
            continue
        massa = proj[ini:ant + 1].sum()
        if melhor is None or massa > melhor[0]:
            melhor = (massa, ini, ant + 1)
        if i is not None:
            ini = ant = i
    return melhor[1], melhor[2]


def _bloco(m):
    """Caixa do maior bloco da máscara: o veículo, sem legenda, título ou cota separados dele."""
    if not m.any():
        return None
    folga = max(2, int(0.01 * max(m.shape)))
    y0, y1 = 0, m.shape[0]
    x0, x1 = 0, m.shape[1]
    for _ in range(2):
        fy = _maior_faixa(m[:, x0:x1].sum(axis=1), folga)
        if fy is None:
            return None
        y0, y1 = fy
        fx = _maior_faixa(m[y0:y1, :].sum(axis=0), folga)
        if fx is None:
            return None
        x0, x1 = fx
    return x0, y0, x1, y1


def _borda(m, esp=2):
    dentro = np.asarray(Image.fromarray(m.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(3))) > 127
    b = m & ~dentro
    if esp > 1:
        b = np.asarray(Image.fromarray(b.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(2 * esp - 1))) > 127
    return b


def _iou(a, b):
    return float((a & b).sum()) / max(1.0, float((a | b).sum()))


def _topos(m, x0, x1, bins):
    """Altura do topo da máscara (linha do primeiro pixel) em `bins` faixas de coluna."""
    out = []
    bordas = np.linspace(x0, x1, bins + 1).astype(int)
    for a, b in zip(bordas, bordas[1:]):
        fatia = m[:, a:max(b, a + 1)]
        tem = fatia.any(axis=0)
        if not tem.any():
            out.append(None)
            continue
        topo = np.argmax(fatia, axis=0)[tem]
        out.append(float(np.median(topo)))
    return bordas, out


# ---------------------------------------------------------------- ferramentas

@mcp.tool()
def guia(tema: str = "indice") -> str:
    """Guia de modelagem realista: como os veículos são de verdade (medidas, proporções, erros comuns)
    e o fluxo de trabalho. Temas: indice, fluxo, referencias, caminhoes, onibus, motos, carros,
    rodas-e-pneus, tecnicas, materiais, conferencia, receitas, armadilhas. Leia "fluxo" e o tema do
    veículo antes de começar um modelo."""
    tema = (tema or "indice").strip().lower().replace(" ", "-").replace("ô", "o").replace("ã", "a")
    arq = GUIAS / f"{tema}.md"
    if not arq.is_file():
        return f"Não há o tema '{tema}'. Temas: " + ", ".join(sorted(p.stem for p in GUIAS.glob("*.md")))
    return arq.read_text(encoding="utf-8")


@mcp.tool()
def medir(alvo: list[str] | None = None, padrao: str | None = None, frente: str | None = None) -> str:
    """Mede e orienta o modelo: caixa em metros, comprimento/largura/altura, se está apoiado no chão,
    eixos (posição, diâmetro da roda, simples/duplo), entre-eixos e balanços, para que lado é a
    frente (com as evidências), simetria lateral, triângulos, materiais e avisos (metal > 0,3,
    escala negativa ou não aplicada).

    - alvo: nomes de objetos (os filhos entram junto). Padrão: tudo o que está visível.
    - padrao: regex no nome dos objetos (ex.: "pneu|roda").
    - frente: eixo da frente com sinal (ex.: "-Y"), se já souber; senão é deduzida.
    """
    _validar_frente(frente)
    r = _rodar(S.COMUM, S.MEDIR, alvo=alvo, padrao=padrao, frente=frente)
    return _texto_medir(r)


@mcp.tool()
def vistas_tecnicas(alvo: list[str] | None = None, padrao: str | None = None, vistas: list[str] | None = None,
                    sombreamento: str = "material", grade: bool = True, cotas: bool = True,
                    frente: str | None = None, tamanho: int = 1400):
    """Folha de vistas ortográficas, todas na MESMA escala, com grade métrica (1 m; 0,5 e 0,1 m quando
    cabe), linha do chão, cotas de comprimento/largura/altura, rodas e entre-eixos marcados e a seta
    da FRENTE. Serve para conferir proporção e alinhamento como num desenho técnico.

    - vistas: até 6 de frente, tras, direita, esquerda, cima, baixo (padrão: direita, frente, cima,
      tras). Teclado numérico: direita = olho em +X; com a frente em −Y ela mostra o lado esquerdo
      do veículo, frente à esquerda.
    - sombreamento: material (cores do material), cinza (forma pura), silhueta, objeto.
    - alvo/padrao: só esses objetos (os outros somem durante a foto). Padrão: tudo o que está visível.
    - frente: eixo da frente (ex.: "-Y") se a dedução errar.
    - tamanho: lado da folha em pixels (400–3000).
    Tudo o que muda na viewport para tirar a foto volta ao que era.
    """
    vistas = vistas or ["direita", "frente", "cima", "tras"]
    ruins = [v for v in vistas if v not in VISTAS]
    if ruins or not 1 <= len(vistas) <= 6:
        raise ValueError(f"Vistas válidas (1 a 6): {', '.join(VISTAS)}. Recebi: {vistas}")
    if sombreamento not in ("material", "cinza", "silhueta", "objeto"):
        raise ValueError("sombreamento: material, cinza, silhueta ou objeto.")
    _validar_frente(frente)
    pasta = tempfile.mkdtemp(prefix="blender_pro_")
    try:
        r = _rodar(S.COMUM, S.DESENHO, S.VISTAS_TECNICAS, alvo=alvo, padrao=padrao, vistas=vistas,
                   sombreamento=sombreamento, cotas=cotas, frente=frente,
                   tamanho=max(400, min(int(tamanho), 3000)), pasta=pasta)
        imgs = []
        for t in r["tiles"]:
            im = Image.fromarray(np.load(t["arquivo"]), "RGBA").convert("RGB")
            _anotar(im, t, r, grade, cotas)
            imgs.append(im)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
    ppm = r["tiles"][0]["ppm_x"]
    folha = _folha(imgs, f"Vistas técnicas · 1 m = {round(ppm)} px · {os.path.basename(r['arquivo'])}")
    lo, hi, iL, iW = r["lo"], r["hi"], r["iL"], r["iW"]
    linhas = [f"Comprimento {n(hi[iL] - lo[iL])} m (em {EIXO[iL]}) · largura {n(hi[iW] - lo[iW])} m · "
              f"altura {n(hi[2] - lo[2])} m · chão em Z {n(r['chao'], 3)} · {mil(r['objetos'])} objetos"]
    if cotas:
        linhas += _linhas_eixos(r)
    return [ImagemMCP(data=_png(folha), format="png"), "\n".join(linhas)]


@mcp.tool()
def comparar_referencia(imagem: str, vista: str = "direita", alvo: list[str] | None = None,
                        padrao: str | None = None, recorte: list[int] | None = None, espelhar: bool = False,
                        ajuste: str = "largura", tolerancia: int = 38, sombreamento: str = "material",
                        max_lado: int = 1500):
    """Compara o modelo com uma imagem de referência da mesma vista (desenho lateral, blueprint,
    "2d vetor", foto frontal). Renderiza o modelo em ortográfica, encaixa pela caixa do veículo na
    imagem (largura igual, chão alinhado) e devolve: a referência com o contorno do modelo em
    vermelho, o mapa de diferença (vermelho = só o modelo, azul = só a referência) e o modelo com o
    contorno da referência; mais o IoU (sobreposição 0–1), a diferença de proporção e onde o perfil
    de cima diverge, em metros.

    - imagem: caminho local da referência (baixe antes). Fundo liso ou transparente funciona sozinho;
      foto com fundo poluído pede `recorte`.
    - vista: frente, tras, direita, esquerda, cima, baixo (a mesma da imagem). Na direita (olho em +X)
      a frente do veículo (−Y) fica à ESQUERDA da imagem: se a referência olha para o outro
      lado, use espelhar=true.
    - recorte: [x0, y0, x1, y1] em pixels da imagem original, para isolar o veículo.
    - ajuste: "largura" (padrão: iguala a largura da imagem; a altura mostra o erro de proporção) ou
      "altura".
    - tolerancia: diferença de cor (0–255) para separar o veículo do fundo.
    """
    if vista not in VISTAS:
        raise ValueError(f"vista: {', '.join(VISTAS)}.")
    if ajuste not in ("largura", "altura"):
        raise ValueError("ajuste: largura ou altura.")
    if not os.path.isfile(imagem):
        raise ValueError(f"Não achei a imagem {imagem!r}.")
    ref = Image.open(imagem)
    ref.load()
    ref = ref.convert("RGBA")
    if recorte:
        ref = ref.crop(tuple(int(v) for v in recorte))
    if espelhar:
        ref = ref.transpose(Image.FLIP_LEFT_RIGHT)
    if max(ref.size) > 1600:
        ref.thumbnail((1600, 1600), Image.LANCZOS)
    W, H = ref.size
    k = _k((H, W))
    R = _preencher(_mascara(ref, tolerancia, k))
    cr = _caixa(R)
    if cr is None:
        raise ValueError("Não achei o veículo na referência (fundo não é liso?). Passe recorte=[x0,y0,x1,y1] "
                         "ou ajuste a tolerancia.")
    px_alvo = (cr[2] - cr[0]) if ajuste == "largura" else (cr[3] - cr[1])
    pasta = tempfile.mkdtemp(prefix="blender_pro_")
    try:
        r = _rodar(S.COMUM, S.DESENHO, S.COMPARAR, alvo=alvo, padrao=padrao, vista=vista, ajuste=ajuste,
                   px_alvo=px_alvo, sombreamento=sombreamento, pasta=pasta)
        sil = np.load(r["silhueta"])
        cor = np.load(r["cor"])
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
    Mt = _preencher(_limpar(_fechar(sil[..., :3].mean(axis=-1) < 128), k))
    cm = _caixa(Mt)
    if cm is None:
        raise ErroBlender("O modelo não apareceu na silhueta (está visível?).")
    s = (cr[2] - cr[0]) / (cm[2] - cm[0]) if ajuste == "largura" else (cr[3] - cr[1]) / (cm[3] - cm[1])
    plana = vista in ("cima", "baixo")
    ox = cr[0] - cm[0] * s
    oy = ((cr[1] + cr[3]) / 2 - (cm[1] + cm[3]) / 2 * s) if plana else (cr[3] - cm[3] * s)

    def colocar(img, fundo, reamostra):
        g = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), reamostra)
        tela = Image.new(img.mode, (W, H), fundo)
        tela.paste(g, (round(ox), round(oy)))
        return tela

    M = np.asarray(colocar(Image.fromarray(Mt.astype(np.uint8) * 255), 0, Image.NEAREST)) > 127
    cor_t = colocar(Image.fromarray(cor, "RGBA").convert("RGB"), (255, 255, 255), Image.LANCZOS)
    iou = _iou(R, M)
    desloc = cr[0] - (W - cr[2])
    Rf = np.zeros_like(R)
    if desloc >= 0:
        Rf[:, desloc:] = R[:, ::-1][:, :W - desloc]
    else:
        Rf[:, :W + desloc] = R[:, ::-1][:, -desloc:]
    iou_esp = _iou(Rf, M)

    mpp = 1 / (r["ppm_x"] * s)
    ri = r["r"][0]
    ui = r["u"][0]
    ext_r = r["hi"][ri] - r["lo"][ri]
    ext_u = r["hi"][ui] - r["lo"][ui]
    ref_w_m, ref_h_m = (cr[2] - cr[0]) * mpp, (cr[3] - cr[1]) * mpp
    linhas = [f"IoU (sobreposição das silhuetas): {n(iou)}  (≥ 0,90 bom; ≥ 0,95 ótimo)"]
    if iou_esp > iou + 0.05:
        linhas.append(f"⚠️ A referência espelhada casa melhor (IoU {n(iou_esp)}): repita com espelhar={str(not espelhar).lower()}.")
    linhas.append(f"Escala do encaixe: 1 px da referência = {n(mpp * 1000, 1)} mm. Na escala do modelo, a referência mede "
                  f"{n(ref_w_m)} × {n(ref_h_m)} m; o modelo, {n(ext_r)} × {n(ext_u)} m.")
    prop = ((cm[3] - cm[1]) / (cm[2] - cm[0])) / ((cr[3] - cr[1]) / (cr[2] - cr[0])) - 1
    if abs(prop) >= 0.01:
        dim = "alto" if not plana else "comprido no vertical"
        linhas.append(f"Proporção: o modelo está {n(abs(prop) * 100, 1)} % mais {dim if prop > 0 else ('baixo' if not plana else 'curto no vertical')} "
                      f"que a referência (altura/largura da silhueta).")
    else:
        linhas.append("Proporção altura/largura: igual à da referência (±1 %).")
    # Perfil sobre máscaras mais abertas: peça fina (prato da quinta roda de lado, borda de
    # para-lama) muda de espessura com o traço do desenho e não é diferença de forma.
    kp = 2 * k + 1
    bordas, tR = _topos(_abrir(R, kp), cr[0], cr[2], 40)
    _, tM = _topos(_abrir(M, kp), cr[0], cr[2], 40)
    brutas = [None if a is None or b is None else (a - b) * mpp for a, b in zip(tR, tM)]
    difs = []
    for i in range(len(brutas)):
        viz = [v for v in brutas[max(0, i - 1):i + 2] if v is not None]
        if brutas[i] is None or len(viz) < 2:
            continue
        dm = float(np.median(viz))  # pico de uma faixa só (peça fina) não conta
        meio = ((bordas[i] + bordas[i + 1]) / 2 - cr[0]) * mpp
        difs.append((abs(dm), dm, meio))
    grandes = []
    for d in sorted([d for d in difs if d[0] >= max(0.03, 0.01 * ref_h_m)], reverse=True):
        if all(abs(d[2] - g[2]) > 0.4 for g in grandes):  # um ponto por trecho
            grandes.append(d)
        if len(grandes) == 4:
            break
    if grandes:
        txt = "; ".join(f"a {n(d[2])} m da ponta esquerda o topo do modelo está {n(abs(d[1]) * 100, 0)} cm "
                        f"{'acima' if d[1] > 0 else 'abaixo'}" for d in grandes)
        linhas.append("Perfil de cima (onde mais diverge): " + txt + ".")
    else:
        linhas.append("Perfil de cima: dentro de 3 cm da referência em toda a extensão.")
    linhas.append("Olhe o mapa de diferença: vermelho = sobra no modelo, azul = falta no modelo.")

    base = Image.blend(ref.convert("RGB"), Image.new("RGB", (W, H), (255, 255, 255)), 0.35)
    a = np.asarray(base).copy()
    a[_borda(M)] = (230, 30, 30)
    painel_a = Image.fromarray(a)
    dif = np.full((H, W, 3), 255, dtype=np.uint8)
    dif[R & M] = (165, 165, 165)
    dif[R & ~M] = (40, 95, 235)
    dif[M & ~R] = (235, 55, 40)
    painel_b = Image.fromarray(dif)
    c = np.asarray(cor_t).copy()
    c[_borda(R)] = (30, 90, 235)
    painel_c = Image.fromarray(c)
    paineis = []
    for p, rot in ((painel_a, "referência + contorno do modelo (vermelho)"),
                   (painel_b, "diferença: vermelho = só o modelo · azul = só a referência"),
                   (painel_c, "modelo + contorno da referência (azul)")):
        d = ImageDraw.Draw(p, "RGBA")
        _texto(d, (6, 4), rot, t=13, negrito=True)
        paineis.append(p)
    gap = 8
    if W >= H:
        folha = Image.new("RGB", (W, 3 * H + 2 * gap), (255, 255, 255))
        for i, p in enumerate(paineis):
            folha.paste(p, (0, i * (H + gap)))
    else:
        folha = Image.new("RGB", (3 * W + 2 * gap, H), (255, 255, 255))
        for i, p in enumerate(paineis):
            folha.paste(p, (i * (W + gap), 0))
    if max(folha.size) > max_lado:
        folha.thumbnail((max_lado, max_lado), Image.LANCZOS)
    return [ImagemMCP(data=_png(folha), format="png"), "\n".join(linhas)]


@mcp.tool()
def destacar(objetos: list[str] | None = None, padrao: str | None = None, regiao: list[float] | None = None,
             vistas: list[str | list[float]] | None = None, contexto: str = "cinza", enquadrar: str = "tudo",
             distancia: float | None = None, tamanho: int = 900):
    """Pinta peças de cores fortes (o resto em cinza) e mostra de 1 a 4 ângulos, para identificar uma
    peça pela forma e posição antes de pintar, mover ou apagar. Até 8 peças ganham cores diferentes;
    mais que isso, todas em laranja. Devolve nome, centro e tamanho de cada peça.

    - objetos: nomes; padrao: regex no nome; regiao: [xmin, ymin, zmin, xmax, ymax, zmax] em metros
      (pega as peças cujo centro está dentro). Use um ou mais.
    - vistas: frente, tras, direita, esquerda, cima, baixo, tres_quartos, tres_quartos_tras,
      tres_quartos_esq ou [x, y, z] (direção do alvo para o olho). Padrão: tres_quartos e direita.
    - contexto: cinza (o resto em cinza), transparente (raio-X, para peça escondida) ou oculto (só as
      peças).
    - enquadrar: tudo (mostra onde a peça fica no veículo) ou alvo (aproxima nas peças).
    Nada muda na cena: cores e visibilidade voltam ao que eram.
    """
    if not (objetos or padrao or regiao):
        raise ValueError("Diga quais peças: objetos, padrao ou regiao.")
    if regiao is not None and len(regiao) != 6:
        raise ValueError("regiao: [xmin, ymin, zmin, xmax, ymax, zmax].")
    vistas = vistas or ["tres_quartos", "direita"]
    for v in vistas:
        if isinstance(v, str) and v not in ANGULOS:
            raise ValueError(f"Vista desconhecida {v!r}. Use {', '.join(ANGULOS)} ou [x, y, z].")
        if not isinstance(v, str) and (len(v) != 3 or not any(v)):
            raise ValueError("Uma direção é [x, y, z], não toda zero.")
    if contexto not in ("cinza", "transparente", "oculto"):
        raise ValueError("contexto: cinza, transparente ou oculto.")
    pasta = tempfile.mkdtemp(prefix="blender_pro_")
    try:
        r = _rodar(S.COMUM, S.DESENHO, S.DESTACAR, objetos=objetos, padrao=padrao, regiao=regiao,
                   vistas=vistas[:4], contexto=contexto, enquadrar=enquadrar, distancia=distancia,
                   tamanho=max(300, min(int(tamanho), 1600)), pasta=pasta)
        imgs = []
        for t in r["tiles"]:
            im = Image.fromarray(np.load(t["arquivo"]), "RGBA").convert("RGB")
            _texto(ImageDraw.Draw(im, "RGBA"), (6, 4), t["vista"], t=13, negrito=True)
            imgs.append(im)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
    folha = _folha(imgs, f"Destaque · {r['total']} peça(s)")
    linhas = [f"{r['total']} peça(s) destacada(s)" + (" (mostrando as 40 primeiras)" if r["total"] > 40 else "") + ":"]
    for p in r["pecas"]:
        cor = NOMES_COR.get(tuple(round(c, 2) for c in p["cor"]), "laranja") if p.get("cor") else ""
        c, t = p["centro"], p["tam"]
        linhas.append(f"- {p['nome']} [{cor}] centro ({n(c[0])}, {n(c[1])}, {n(c[2])}) · tamanho "
                      f"{n(t[0])} × {n(t[1])} × {n(t[2])} m")
    return [ImagemMCP(data=_png(folha), format="png"), "\n".join(linhas)]


@mcp.tool()
def referencias_na_cena(referencias: list[dict], comprimento: float | None = None, largura: float | None = None,
                        altura: float | None = None, alvo: list[str] | None = None, padrao: str | None = None,
                        opacidade: float = 0.5, tolerancia: int = 38) -> str:
    """Põe imagens de referência (blueprints) na cena, em escala real, como vazios de imagem na
    coleção REFERENCIAS: cada uma atrás do modelo, alinhada à vista dela, visível só na vista
    ortográfica correspondente (numpad). É o jeito clássico de modelar por cima do desenho.

    - referencias: lista de {"vista": "direita"|"frente"|"tras"|"esquerda"|"cima"|"baixo",
      "imagem": "C:/.../lateral.png", "espelhar": false, "recorte": [x0, y0, x1, y1]}. O recorte
      só serve para achar o veículo na imagem (a imagem inteira vai para a cena).
    - comprimento / largura / altura: medidas reais em metros (ficha técnica). A escala sai do
      comprimento na lateral e no topo, e da altura na frente/trás (a largura da frente inclui os
      retrovisores). Sem medida, usa o tamanho do modelo que já está na cena.
    - opacidade: 0–1.
    O veículo da imagem é encaixado no centro do modelo e com a base no chão (vistas laterais e
    frontais). Na direita (olho em +X) a frente (−Y) fica à esquerda: espelhe a imagem se precisar.
    Chamar de novo com a mesma vista substitui a imagem anterior.
    """
    refs = []
    for ref in referencias:
        vista = ref.get("vista")
        if vista not in VISTAS:
            raise ValueError(f"vista: {', '.join(VISTAS)}.")
        caminho = os.path.abspath(ref.get("imagem") or "")
        if not os.path.isfile(caminho):
            raise ValueError(f"Não achei a imagem {caminho!r}.")
        im = Image.open(caminho)
        im.load()
        W, H = im.size
        if ref.get("recorte"):
            x0, y0, x1, y1 = (int(v) for v in ref["recorte"])
            sub = _caixa(_preencher(_mascara(im.crop((x0, y0, x1, y1)), tolerancia)))
            caixa = [x0 + sub[0], y0 + sub[1], x0 + sub[2], y0 + sub[3]] if sub else [x0, y0, x1, y1]
        else:
            sub = _caixa(_preencher(_mascara(im, tolerancia)))
            if sub is None:
                raise ValueError(f"Não achei o veículo em {caminho!r}: passe recorte=[x0,y0,x1,y1].")
            caixa = list(sub)
        if ref.get("espelhar"):
            caixa = [W - caixa[2], caixa[1], W - caixa[0], caixa[3]]
        pw, ph = caixa[2] - caixa[0], caixa[3] - caixa[1]
        if vista in ("direita", "esquerda"):
            mpp = comprimento / pw if comprimento else (altura / ph if altura else None)
        elif vista in ("frente", "tras"):
            mpp = altura / ph if altura else (largura / pw if largura else None)
        else:
            mpp = comprimento / ph if comprimento else (largura / pw if largura else None)
        refs.append({"vista": vista, "caminho": caminho, "mpp": mpp, "caixa": caixa,
                     "espelhar": bool(ref.get("espelhar")), "opacidade": max(0.05, min(float(opacidade), 1.0))})
    sem_escala = [x for x in refs if x["mpp"] is None]
    if sem_escala:
        r = _rodar(S.COMUM, S.MEDIR, alvo=alvo, padrao=padrao, frente=None)
        lo, hi = r["lo"], r["hi"]
        comp, larg, alt = hi[r["iL"]] - lo[r["iL"]], hi[r["iW"]] - lo[r["iW"]], hi[2] - lo[2]
        for x in sem_escala:
            pw, ph = x["caixa"][2] - x["caixa"][0], x["caixa"][3] - x["caixa"][1]
            x["mpp"] = comp / pw if x["vista"] in ("direita", "esquerda") else (alt / ph if x["vista"] in ("frente", "tras") else comp / ph)
    r = _rodar(S.COMUM, S.DESENHO, S.REFERENCIAS, refs=refs, alvo=alvo, padrao=padrao)
    linhas = [f"Na coleção {r['colecao']}" + ("" if r["modelo_na_cena"] else " (sem modelo na cena: centro na origem, base em Z = 0)") + ":"]
    for f in r["feitos"]:
        vm = f["veiculo_m"]
        linhas.append(f"- {f['objeto']} ({f['vista']}{', espelhada' if f['espelhada'] else ''}): imagem de "
                      f"{n(f['largura_m'])} × {n(f['altura_m'])} m; o veículo nela mede {n(vm[0])} × {n(vm[1])} m")
    linhas.append("Elas aparecem só na vista ortográfica alinhada (numpad 1/3/7 e Ctrl+). Para tirar: apagar a "
                  "coleção REFERENCIAS.")
    return "\n".join(linhas)


@mcp.tool()
def checkpoint(rotulo: str = "") -> str:
    """Salva uma CÓPIA do .blend aberto (com as mudanças ainda não salvas) em
    Documents/blender-checkpoints/<nome do arquivo>/<data>_<rotulo>.blend, antes de uma operação
    arriscada (separar malha, apagar peças, aplicar modificador, booleana, script grande). O arquivo
    aberto não muda de nome nem é salvo. Para voltar, o usuário abre a cópia (não abrir por conta
    própria: troca a cena dele).
    """
    r = _rodar(S.COMUM, S.CHECKPOINT, rotulo=rotulo, pasta=PASTA_CHECKPOINTS)
    mb = r["bytes"] / 1e6
    sujo = " (tem alterações ainda não salvas, que estão na cópia)" if r["sujo"] else ""
    ant = ", ".join(r["anteriores"][-5:])
    return f"Cópia salva: {r['destino']} ({n(mb, 1)} MB). Arquivo aberto: {r['arquivo_atual']}{sujo}.\nCheckpoints dele: {ant}"


# ---------------------------------------------------------------- conferência fina
# Para modelos grandes: foto de qualquer ângulo, folga entre peças, peça atravessando peça e o GLB.

def _p(v, c=3):
    return "(" + "; ".join(n(x, c) for x in v) + ")"


def _vetor(v, nome):
    if v is None or len(v) != 3:
        raise ValueError(f"{nome}: [x, y, z] em metros.")
    return [float(x) for x in v]


def _regiao(r):
    if r is not None and len(r) != 6:
        raise ValueError("regiao: [xmin, ymin, zmin, xmax, ymax, zmax].")
    return r


@mcp.tool()
def olhar_de(olho: list[float] | None = None, alvo: list[float] | None = None, lente: float = 35,
             vista_atual: bool = False, esconder: list[str] | None = None, esconder_padrao: str | None = None,
             esconder_colecoes: list[str] | None = None, esconder_regiao: list[float] | None = None,
             sombreamento: str = "material", apontar: list[list[float]] | None = None,
             tamanho: int = 1200, proporcao: float = 0.64):
    """Foto em perspectiva de QUALQUER ponto de vista: de dentro da cabine, por baixo do chassi, pelo
    arco da roda. É o jeito de conferir do MESMO ângulo do print do usuário (o `look` oficial não põe o
    olho dentro da cabine). Não mexe na vista nem na câmera dele.

    - olho / alvo: [x, y, z] em metros; lente em mm (sensor 36 mm: 18 grande-angular, 35 normal, 80 tele).
    - vista_atual: true usa a vista que está na janela 3D agora (o que o usuário está olhando) e devolve
      olho, alvo e lente para repetir depois com olho/alvo.
    - esconder / esconder_padrao (regex) / esconder_colecoes / esconder_regiao ([xmin, ymin, zmin, xmax,
      ymax, zmax], pelo centro da peça): somem só nesta foto (tirar roda, cabine ou o outro caminhão da
      frente).
    - sombreamento: material, cinza, objeto, silhueta ou vista (a aparência que ele usa).
    - apontar: [[px, py], ...] pixels da foto (origem no canto de cima à esquerda): diz qual peça e qual
      material estão em cada um, por raio. Use para identificar a peça antes de mexer.
    - tamanho: largura em px (400–2400); proporcao: altura/largura.
    """
    if not vista_atual:
        olho, alvo = _vetor(olho, "olho"), _vetor(alvo, "alvo")
    if sombreamento not in ("material", "cinza", "objeto", "silhueta", "vista"):
        raise ValueError("sombreamento: material, cinza, objeto, silhueta ou vista.")
    if not 4 <= float(lente) <= 500:
        raise ValueError("lente: de 4 a 500 mm.")
    apontar = [[float(p[0]), float(p[1])] for p in (apontar or [])[:20]]
    pasta = tempfile.mkdtemp(prefix="blender_pro_")
    try:
        r = _rodar(S.COMUM, S.DESENHO, S.OLHAR, olho=olho, alvo=alvo, lente=lente, vista_atual=vista_atual,
                   esconder=esconder, esconder_padrao=esconder_padrao, esconder_colecoes=esconder_colecoes,
                   esconder_regiao=_regiao(esconder_regiao), sombreamento=sombreamento, apontar=apontar,
                   tamanho=max(400, min(int(tamanho), 2400)), proporcao=max(0.3, min(float(proporcao), 2.0)),
                   pasta=pasta)
        im = Image.fromarray(np.load(r["arquivo"]), "RGBA").convert("RGB")
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
    d = ImageDraw.Draw(im, "RGBA")
    if r.get("alvo_px") and not vista_atual:
        x, y = r["alvo_px"]
        d.line([(x - 9, y), (x + 9, y)], fill=(255, 0, 90, 220), width=2)
        d.line([(x, y - 9), (x, y + 9)], fill=(255, 0, 90, 220), width=2)
    for p in r["pontos"]:
        x, y = p["px"]
        d.ellipse([x - 7, y - 7, x + 7, y + 7], outline=(255, 0, 90, 255), width=3)
        _texto(d, (x + 9, y - 9), str(p["n"]), t=13, negrito=True)
    lente_txt = f"lente {n(r['lente'], 1)} mm" if r.get("lente") else "vista ortográfica"
    linhas = [f"Olho {_p(r['olho'])} → alvo {_p(r['alvo'])} · {lente_txt} · proporção {n(r['proporcao'])}"
              + (f" · {r['escondidas']} peça(s) escondida(s) só na foto" if r["escondidas"] else "")]
    if vista_atual:
        linhas.append("Para repetir este ângulo: olhar_de(olho=…, alvo=…, lente=…, proporcao=…) com os valores acima.")
    for p in r["pontos"]:
        if p.get("nada"):
            linhas.append(f"{p['n']}. pixel {p['px']}: nada (fundo)")
        else:
            linhas.append(f"{p['n']}. pixel {p['px']}: {p['peca']} · material {p['material'] or 'nenhum'} · em "
                          f"{_p(p['loc'])} · {n(p['dist'])} m do olho")
    return [ImagemMCP(data=_png(im), format="png"), "\n".join(linhas)]


@mcp.tool()
def sonda(pontos: dict[str, list[float]] | None = None, caminhos: dict[str, dict] | None = None,
          regiao: list[float] | None = None, alvo: list[str] | None = None, padrao: str | None = None,
          raio: float = 0.5, aviso: float = 0.012, limite_s: float = 15) -> str:
    """Folga e vizinhança, só leitura: qual peça está mais perto de um ponto e a que distância, e a
    folga de um TRAJETO (tubo, mangueira, cabo, escape) contra as peças em volta. Serve para encaixar
    peça nova sem atravessar nada e para saber o que existe num ponto antes de mexer.

    - pontos: {"nome": [x, y, z]}.
    - caminhos: {"nome": {"r": raio_do_tubo, "pts": [[x, y, z], ...]}}: amostra a cada 1 cm; folga
      negativa = o tubo encosta ou entra na peça.
    - regiao: [xmin, ymin, zmin, xmax, ymax, zmax] onde procurar (padrão: em volta dos pontos + raio).
    - alvo / padrao: limita as peças consideradas. aviso: folga (m) abaixo da qual a peça é listada.
    - limite_s: para sozinho nesse tempo (2–120 s) e diz que parou.
    A distância é até a SUPERFÍCIE: um ponto bem dentro de uma peça maciça pode parecer longe; o aviso
    "atrás da face" indica que o ponto está do lado de dentro.
    """
    if not (pontos or caminhos):
        raise ValueError("Passe pontos ou caminhos.")
    for k, c in (caminhos or {}).items():
        if not isinstance(c, dict) or len(c.get("pts") or []) < 2:
            raise ValueError(f"caminho {k!r}: {{'r': raio, 'pts': [[x,y,z], [x,y,z], ...]}} com 2 pontos ou mais.")
    pontos = {k: _vetor(v, f"ponto {k!r}") for k, v in (pontos or {}).items()}
    r = _rodar(S.COMUM, S.MALHAS, S.SONDA, pontos=pontos, caminhos=caminhos or {}, regiao=_regiao(regiao),
               alvo=alvo, padrao=padrao, raio=raio, aviso=aviso, limite_s=limite_s)
    linhas = [f"Árvore com {mil(r['tri'])} triângulos de {r['malhas']} peça(s) na região "
              f"{_p(r['regiao'][0], 2)} a {_p(r['regiao'][1], 2)} · {n(r['segundos'], 1)} s"
              + (" · ⚠️ PAROU no limite de tempo/tamanho: restrinja a região ou o padrão" if r["parou"] else "")]
    for p in r["pontos"]:
        if p.get("nada"):
            linhas.append(f"- {p['nome']}: nenhuma peça a {n(raio)} m")
        else:
            dentro = " · ⚠️ atrás da face (do lado de dentro da peça)" if p["atras_da_face"] else ""
            linhas.append(f"- {p['nome']}: {n(p['dist'] * 1000, 0)} mm de {p['peca']} (material "
                          f"{p['material'] or 'nenhum'}) no ponto {_p(p['loc'])}{dentro}")
    for c in r["caminhos"]:
        if not c["pior"]:
            linhas.append(f"- {c['nome']} (r {n(c['r'] * 1000, 0)} mm): livre a {n(raio)} m")
            continue
        f, peca, q = c["pior"]
        linhas.append(f"- {c['nome']} (r {n(c['r'] * 1000, 0)} mm): folga mínima {n(f * 1000, 0)} mm com {peca} em {_p(q)}")
        for nome, folga, q in c["perto"]:
            linhas.append(f"    {nome}: {n(folga * 1000, 0)} mm em {_p(q)}")
    return "\n".join(linhas)


@mcp.tool()
def cruzamentos(objetos: list[str] | None = None, padrao: str | None = None, regiao: list[float] | None = None,
                contra_padrao: str | None = None, ignorar_padrao: str | None = None, limite_s: float = 20) -> str:
    """Peça atravessando peça, só leitura. Peça sobreposta costuma ser ARTEFATO: rode nas peças novas
    ou mexidas antes de mostrar. Compara cada peça do alvo com as visíveis cuja caixa encosta nela e
    conta os pares de triângulos que se cortam, com o lugar do cruzamento.

    - objetos / padrao (regex) / regiao ([xmin, ymin, zmin, xmax, ymax, zmax], pelo centro): as peças a
      conferir (até 400).
    - contra_padrao: só contra estas (ex.: "longarina|travessa"); ignorar_padrao: estas não contam
      (ex.: a cabine, quando o que interessa é o chassi).
    - limite_s: para sozinho nesse tempo (2–120 s) e diz até onde foi.
    Poucos pares podem ser só face encostando na outra; muitos pares, ou espalhados, é atravessar.
    """
    if not (objetos or padrao or regiao):
        raise ValueError("Diga quais peças conferir: objetos, padrao ou regiao.")
    r = _rodar(S.COMUM, S.MALHAS, S.CRUZAMENTOS, objetos=objetos, padrao=padrao, regiao=_regiao(regiao),
               contra_padrao=contra_padrao, ignorar_padrao=ignorar_padrao, limite_s=limite_s)
    cab = (f"{r['verificadas']} de {r['alvo']} peça(s) conferidas em {n(r['segundos'], 1)} s"
           + (" · ⚠️ PAROU no limite de tempo: o resto não foi conferido" if r["parou"] else ""))
    if not r["resultado"]:
        return cab + "\nNenhum cruzamento."
    linhas = [cab, f"{len(r['resultado'])} peça(s) cruzam outras:"]
    for x in r["resultado"]:
        linhas.append(f"- {x['peca']}")
        for c in x["cruza"]:
            linhas.append(f"    × {c['com']}: {mil(c['pares'])} par(es) · em torno de {_p(c['centro'])} "
                          f"(de {_p(c['de'], 2)} a {_p(c['ate'], 2)})")
    return "\n".join(linhas)


@mcp.tool()
def pre_exportar(colecao: str | None = None, alvo: list[str] | None = None, padrao: str | None = None) -> str:
    """Conferência antes de exportar para GLB, só leitura: o que vai sair diferente do que se vê. Ocultos
    (não vão no export dos visíveis), pai fora do conjunto, modificadores (viram geometria), malha
    vazia, escala negativa, metal > 0,3 (fica escuro no three.js sem envMap), textura
    em malha sem UV (sai sem TEXCOORD_0), peça sem material, materiais .001 duplicados, atributos
    extras (custom_normal), imagens e a caixa final.

    - colecao: nome da coleção a exportar (inclui as filhas e as ocultas, para avisar).
    - alvo / padrao: sem coleção, as peças visíveis por nome ou regex.
    Exportar continua sendo só depois do "pode" do usuário, num arquivo temporário, e validar com
    comparar_glb antes de copiar por cima do original.
    """
    r = _rodar(S.COMUM, S.PRE_EXPORTAR, colecao=colecao, alvo=alvo, padrao=padrao)
    lo, hi = r["caixa"]
    ext = [hi[i] - lo[i] for i in range(3)]
    linhas = [f"{mil(r['visiveis'])} de {mil(r['objetos'])} objetos visíveis · {mil(r['malhas'])} malhas · "
              f"{mil(r['triangulos'])} triângulos · {r['materiais']} materiais ({r['com_textura']} com textura, "
              f"{r['dupla_face']} dupla face) · {r['imagens']} imagens"
              + (f" (maior {r['maior_imagem'][0]}×{r['maior_imagem'][1]})" if r["maior_imagem"] else ""),
              f"Caixa {n(ext[0])} × {n(ext[1])} × {n(ext[2])} m, de {_p(lo, 2)} a {_p(hi, 2)} · tipos {', '.join(r['tipos'])}"]
    avisos = []
    if r["n_ocultos"]:
        avisos.append(f"{r['n_ocultos']} oculto(s), ficam fora do export dos visíveis: {', '.join(r['ocultos'][:10])}")
    if r["metal_alto"]:
        avisos.append("metal > 0,3 (escuro sem envMap): " + ", ".join(f"{m} ({n(v)}, {q} peças)" for m, v, q in r["metal_alto"]))
    if r["n_textura_sem_uv"]:
        avisos.append(f"{r['n_textura_sem_uv']} peça(s) com textura e sem UV: " + ", ".join(f"{o} [{m}]" for o, m in r["textura_sem_uv"][:8]))
    if r["n_sem_material"]:
        avisos.append(f"{r['n_sem_material']} peça(s) sem material (saem no cinza padrão): " + ", ".join(r["sem_material"][:10]))
    if r["n_vazias"]:
        avisos.append(f"{r['n_vazias']} malha(s) vazia(s): " + ", ".join(r["vazias"][:10]))
    if r["pai_fora"]:
        avisos.append("pai fora do conjunto (a peça vira raiz no GLB): " + ", ".join(f"{a} ← {b}" for a, b in r["pai_fora"][:8]))
    if r["n_modificadores"]:
        avisos.append(f"{r['n_modificadores']} peça(s) com modificador (com export_apply viram geometria): "
                      + ", ".join(f"{o} {m}" for o, m in r["modificadores"][:6]))
    if r["n_escala_negativa"]:
        avisos.append(f"{r['n_escala_negativa']} peça(s) com escala negativa (espelhadas): o reimport recria custom "
                      "normals e o lado espelhado pode escurecer; medir no GLB reimportado, não na cena")
    if r["duplicados"]:
        avisos.append("materiais duplicados .00x em uso junto com o original: " + ", ".join(r["duplicados"][:10]))
    linhas += (["Avisos:"] + [f"- ⚠️ {a}" for a in avisos]) if avisos else ["Sem avisos."]
    if r["atributos"]:
        linhas.append("Atributos extras de malha: " + ", ".join(f"{k} ({v})" for k, v in sorted(r["atributos"].items())))
    if r["propriedades"]:
        linhas.append("Propriedades custom (saem como extras só com export_extras): " + ", ".join(r["propriedades"]))
    return "\n".join(linhas)


def _glb_caixas(caminho: str) -> dict:
    """Caixa no mundo de cada nó com malha do GLB, já no Z-up do Blender: min/max do POSITION (o glTF
    exige) levados pelos nós até a raiz. Só lê o JSON do arquivo; nada é importado."""
    with open(caminho, "rb") as f:
        cab = f.read(20)
        if len(cab) < 20 or cab[:4] != b"glTF":
            raise ValueError(f"{caminho!r} não é um .glb.")
        tam = int.from_bytes(cab[12:16], "little")
        if cab[16:20] != b"JSON":
            raise ValueError("GLB sem o bloco JSON no começo.")
        g = json.loads(f.read(tam).decode("utf-8"))
    nos, malhas, acc = g.get("nodes", []), g.get("meshes", []), g.get("accessors", [])

    def local(nd):
        if "matrix" in nd:
            return np.array(nd["matrix"], dtype=float).reshape(4, 4).T
        x, y, z, w = nd.get("rotation", [0, 0, 0, 1])
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        M = np.eye(4)
        M[:3, :3] = R * np.array(nd.get("scale", [1, 1, 1]), dtype=float)
        M[:3, 3] = nd.get("translation", [0, 0, 0])
        return M

    pai = {c: i for i, nd in enumerate(nos) for c in nd.get("children", [])}
    mundo = {}

    def mw(i):
        if i not in mundo:
            mundo[i] = (mw(pai[i]) @ local(nos[i])) if i in pai else local(nos[i])
        return mundo[i]

    Y_PARA_Z = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=float)   # (x, y, z) glTF → (x, −z, y) Blender
    out, sem_minmax = {}, 0
    for i, nd in enumerate(nos):
        if "mesh" not in nd:
            continue
        lo = hi = None
        for prim in malhas[nd["mesh"]].get("primitives", []):
            a = acc[prim.get("attributes", {}).get("POSITION", -1)] if "POSITION" in prim.get("attributes", {}) else {}
            if "min" not in a or "max" not in a:
                sem_minmax += 1
                continue
            mn, mx = np.array(a["min"], float), np.array(a["max"], float)
            lo = mn if lo is None else np.minimum(lo, mn)
            hi = mx if hi is None else np.maximum(hi, mx)
        if lo is None:
            continue
        cantos = np.array([[hi[0] if k & 1 else lo[0], hi[1] if k & 2 else lo[1], hi[2] if k & 4 else lo[2]] for k in range(8)])
        M = mw(i)
        w = (cantos @ M[:3, :3].T + M[:3, 3]) @ Y_PARA_Z.T
        nome = nd.get("name") or malhas[nd["mesh"]].get("name") or f"no_{i}"
        out[nome] = (w.min(axis=0), w.max(axis=0))
    return {"caixas": out, "sem_minmax": sem_minmax}


@mcp.tool()
def comparar_glb(arquivo: str, colecao: str | None = None, alvo: list[str] | None = None, padrao: str | None = None,
                 tolerancia_mm: float = 1.5) -> str:
    """Compara a CENA com um arquivo .glb peça por peça, pelo nome (caixa de cada peça no mundo), só
    leitura. Dois usos: (1) antes de substituir um original, ver o que a cena tem de diferente dele (em
    12/11/2026 foi assim que apareceu um ajuste de 26/09 que a cena não tinha); (2) depois de exportar
    num arquivo temporário, provar que o GLB saiu igual à cena antes de copiar por cima.

    - arquivo: caminho do .glb (o arquivo não é importado; só o cabeçalho é lido).
    - colecao: coleção da cena que corresponde ao GLB; sem ela, alvo/padrao ou tudo o que está visível.
    - tolerancia_mm: diferença de caixa acima da qual a peça conta como "mudou".
    """
    caminho = os.path.abspath(arquivo)
    if not os.path.isfile(caminho):
        raise ValueError(f"Não achei {caminho!r}.")
    glb = _glb_caixas(caminho)
    r = _rodar(S.COMUM, S.CAIXAS, colecao=colecao, alvo=alvo, padrao=padrao)
    cena, velho = r["caixas"], glb["caixas"]
    tol = float(tolerancia_mm) / 1000
    so_glb = sorted(k for k in velho if k not in cena)
    so_cena = sorted(k for k in cena if k not in velho)
    mudou = []
    for k, (mn, mx) in cena.items():
        if k not in velho:
            continue
        vmn, vmx = velho[k]
        mn, mx = np.array(mn), np.array(mx)
        d = float(max(np.abs(mn - vmn).max(), np.abs(mx - vmx).max()))
        if d > tol:
            mudou.append((d, k, ((mn + mx) / 2 - (vmn + vmx) / 2).tolist(), ((mn + mx) / 2).tolist()))
    mudou.sort(reverse=True)
    linhas = [f"Cena: {mil(len(cena))} malhas visíveis · GLB ({os.path.basename(caminho)}): {mil(len(velho))} nós com malha"
              + (f" · {r['n_ocultas']} malha(s) oculta(s) na cena ficaram de fora" if r["n_ocultas"] else "")]
    if glb["sem_minmax"]:
        linhas.append(f"⚠️ {glb['sem_minmax']} primitiva(s) do GLB sem min/max no POSITION: não comparadas.")
    iguais = len(cena) - len(so_cena) - len(mudou)
    linhas.append(f"Iguais (até {n(tolerancia_mm, 1)} mm): {mil(iguais)} · só no GLB: {len(so_glb)} · só na cena: "
                  f"{len(so_cena)} · mesmo nome em outro lugar/tamanho: {len(mudou)}")
    if so_glb:
        linhas.append("Só no GLB (sumiriam se a cena for exportada por cima): " + ", ".join(so_glb[:40])
                      + (" …" if len(so_glb) > 40 else ""))
    if so_cena:
        linhas.append("Só na cena (entram no export): " + ", ".join(so_cena[:40]) + (" …" if len(so_cena) > 40 else ""))
    for d, k, dc, c in mudou[:40]:
        linhas.append(f"- {k}: dif. máx. {n(d * 1000, 1)} mm · centro andou {_p(dc)} · centro na cena {_p(c, 2)}")
    if len(mudou) > 40:
        linhas.append(f"… e mais {len(mudou) - 40}.")
    if not (so_glb or so_cena or mudou):
        linhas.append("✅ A cena e o GLB batem peça por peça.")
    return "\n".join(linhas)


if __name__ == "__main__":
    mcp.run()
