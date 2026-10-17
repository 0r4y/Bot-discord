"""Geração de imagens e GIFs com Pillow. Tudo aqui é síncrono: chame via asyncio.to_thread."""
import io
import math
import random
import textwrap
import datetime as dt

from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageOps

DOURADO = (212, 175, 55)
DOURADO_ESCURO = (120, 95, 30)
FUNDO = (13, 11, 20)
ROXO = (60, 30, 90)
TAM = 256  # lado dos GIFs de avatar, em pixels

RUNAS = "ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈᛉᛊᛏᛒᛖᛗᛚᛜᛞᛟᚫᚣ"


def fonte(tamanho: int, estilo: str = "titulo") -> ImageFont.FreeTypeFont:
    nomes = {
        "titulo": ("georgiab.ttf", "timesbd.ttf", "arialbd.ttf"),
        "texto": ("georgia.ttf", "times.ttf", "arial.ttf"),
        "runas": ("seguihis.ttf", "seguisym.ttf"),
        "mono": ("consolab.ttf", "consola.ttf", "arial.ttf"),
    }[estilo]
    for nome in nomes:
        try:
            return ImageFont.truetype(nome, tamanho)
        except OSError:
            continue
    return ImageFont.load_default(tamanho)


def _abrir_avatar(dados: bytes, tamanho: int = TAM) -> Image.Image:
    return Image.open(io.BytesIO(dados)).convert("RGBA").resize((tamanho, tamanho), Image.LANCZOS)


def _mascara_circulo(tamanho: int) -> Image.Image:
    m = Image.new("L", (tamanho * 4, tamanho * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, tamanho * 4 - 1, tamanho * 4 - 1), fill=255)
    return m.resize((tamanho, tamanho), Image.LANCZOS)


def _circular(img: Image.Image) -> Image.Image:
    out = img.copy()
    out.putalpha(_mascara_circulo(img.width))
    return out


def desenhar_olho(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, cor=DOURADO, largura: int = 4):
    """Desenha o símbolo da SeuBot: triângulo com o olho que tudo vê."""
    pontos = [
        (cx, cy - r),
        (cx - r * 0.866, cy + r / 2),
        (cx + r * 0.866, cy + r / 2),
    ]
    draw.polygon(pontos, outline=cor, width=largura)
    ey = cy + r * 0.08
    draw.ellipse((cx - r * 0.42, ey - r * 0.17, cx + r * 0.42, ey + r * 0.17), outline=cor, width=max(2, largura - 1))
    draw.ellipse((cx - r * 0.11, ey - r * 0.11, cx + r * 0.11, ey + r * 0.11), fill=cor)
    for ang in range(-150, -20, 26):
        a = math.radians(ang)
        draw.line(
            (cx + math.cos(a) * r * 1.12, cy + math.sin(a) * r * 1.12, cx + math.cos(a) * r * 1.35, cy + math.sin(a) * r * 1.35),
            fill=cor, width=max(1, largura - 2),
        )


def _texto_centro(draw, y, texto, f, cor, largura_total):
    w = draw.textlength(texto, font=f)
    draw.text(((largura_total - w) / 2, y), texto, font=f, fill=cor)


def _salvar_gif(frames: list[Image.Image], duracao) -> io.BytesIO:
    buf = io.BytesIO()
    convertidos = [f.convert("RGB").quantize(colors=128, method=Image.Quantize.MEDIANCUT) for f in frames]
    convertidos[0].save(buf, format="GIF", save_all=True, append_images=convertidos[1:], duration=duracao, loop=0, disposal=2)
    buf.seek(0)
    return buf


# ------------------------------------------------------------------ Efeitos de GIF
# Os valores foram desenhados para 256px; k() converte para o tamanho atual (TAM).


def k(valor: float) -> int:
    return int(round(valor * TAM / 256))


def _glitch(av):
    rgb = av.convert("RGB")
    r, g, b = rgb.split()
    frames = []
    for i in range(18):
        if i % 6 == 0:
            frames.append(rgb.copy())
            continue
        dx = random.randint(k(4), k(14))
        f = Image.merge("RGB", (r.transform(r.size, Image.AFFINE, (1, 0, dx, 0, 1, 0)), g,
                                b.transform(b.size, Image.AFFINE, (1, 0, -dx, 0, 1, 0))))
        for _ in range(random.randint(2, 6)):
            y = random.randint(0, TAM - k(20))
            h = random.randint(k(4), k(20))
            faixa = f.crop((0, y, TAM, y + h))
            f.paste(faixa, (random.randint(-k(30), k(30)), y))
        d = ImageDraw.Draw(f)
        for y in range(0, TAM, k(3)):
            d.line((0, y, TAM, y), fill=(0, 0, 0), width=max(1, k(1)))
        frames.append(f)
    return frames, 70


def _revelar(av):
    preto = Image.new("RGBA", (TAM, TAM), (0, 0, 0, 255))
    f_txt = fonte(k(22))
    frames, duracoes = [], []
    for i in range(26):
        alpha = min(1.0, i / 18)
        f = Image.blend(preto, av, alpha)
        if i >= 18:
            d = ImageDraw.Draw(f)
            d.rectangle((0, TAM - k(40), TAM, TAM), fill=(0, 0, 0))
            _texto_centro(d, TAM - k(34), "IDENTIDADE REVELADA", f_txt, DOURADO, TAM)
        frames.append(f)
        duracoes.append(1500 if i == 25 else 80)
    return frames, duracoes


def _olho(av):
    escuro = ImageEnhance.Brightness(av).enhance(0.45)
    frames = []
    for i in range(24):
        intensidade = (math.sin(i / 24 * 2 * math.pi) + 1) / 2
        camada = Image.new("RGBA", (TAM, TAM), (0, 0, 0, 0))
        cor = tuple(int(c * (0.5 + intensidade * 0.5)) for c in DOURADO) + (255,)
        desenhar_olho(ImageDraw.Draw(camada), TAM / 2, TAM / 2 + k(10), k(80 + intensidade * 10), cor, k(5))
        brilho = camada.filter(ImageFilter.GaussianBlur(k(6 + intensidade * 6)))
        f = escuro.copy()
        f.alpha_composite(brilho)
        f.alpha_composite(brilho)
        f.alpha_composite(camada)
        frames.append(f)
    return frames, 60


def _ritual(av):
    tam_av = k(150)
    base = _circular(av.resize((tam_av, tam_av), Image.LANCZOS))
    anel = Image.new("RGBA", (TAM, TAM), (0, 0, 0, 0))
    d = ImageDraw.Draw(anel)
    d.ellipse((k(6), k(6), TAM - k(6), TAM - k(6)), outline=DOURADO, width=k(3))
    d.ellipse((k(34), k(34), TAM - k(34), TAM - k(34)), outline=DOURADO_ESCURO, width=k(2))
    f_runa = fonte(k(20), "runas")
    for i, runa in enumerate(RUNAS[:20]):
        a = i / 20 * 2 * math.pi
        x = TAM / 2 + math.cos(a) * k(106) - k(7)
        y = TAM / 2 + math.sin(a) * k(106) - k(12)
        d.text((x, y), runa, font=f_runa, fill=DOURADO)
    frames = []
    for i in range(30):
        brilho = (math.sin(i / 30 * 2 * math.pi) + 1) / 2
        f = Image.new("RGBA", (TAM, TAM), tuple(int(c * (0.6 + 0.4 * brilho)) for c in ROXO) + (255,))
        f.alpha_composite(anel.rotate(i * 12, resample=Image.BICUBIC))
        f.alpha_composite(base, ((TAM - tam_av) // 2, (TAM - tam_av) // 2))
        frames.append(f)
    return frames, 60


VERMELHO = (170, 25, 25)


def _vigilancia(av):
    """Câmera de segurança: P&B, varredura, REC piscando e alvo identificado."""
    cinza = ImageEnhance.Contrast(av.convert("L")).enhance(1.3).convert("RGBA")
    verde = Image.new("RGBA", (TAM, TAM), (40, 70, 40, 60))
    base = Image.alpha_composite(cinza, verde)
    linhas = Image.new("RGBA", (TAM, TAM), (0, 0, 0, 0))
    dl = ImageDraw.Draw(linhas)
    for y in range(0, TAM, k(2)):
        dl.line((0, y, TAM, y), fill=(0, 0, 0, 70))
    f_mono, f_alvo = fonte(k(12), "mono"), fonte(k(13), "mono")
    branco = (230, 230, 230)
    n = 30
    frames, duracoes = [], []
    for i in range(n):
        f = base.copy()
        d = ImageDraw.Draw(f)
        for _ in range(k(140)):  # ruído
            x, y = random.randrange(TAM), random.randrange(TAM)
            c = random.randint(90, 200)
            d.point((x, y), fill=(c, c, c))
        yv = int(i / n * TAM)
        d.rectangle((0, yv, TAM, yv + k(3)), fill=(200, 255, 200, 255))
        f.alpha_composite(linhas)
        d = ImageDraw.Draw(f)
        m, t = k(10), k(22)  # cantos do visor
        for cx, cy, sx, sy in ((m, m, 1, 1), (TAM - m, m, -1, 1), (m, TAM - m, 1, -1), (TAM - m, TAM - m, -1, -1)):
            d.line((cx, cy, cx + t * sx, cy), fill=branco, width=k(2))
            d.line((cx, cy, cx, cy + t * sy), fill=branco, width=k(2))
        if i % 10 < 6:
            d.ellipse((k(18), k(18), k(28), k(28)), fill=(220, 30, 30))
        d.text((k(33), k(16)), "REC", font=f_mono, fill=branco)
        d.text((TAM - k(70), k(16)), "CAM 07", font=f_mono, fill=branco)
        d.text((k(18), TAM - k(30)), f"23:59:{i * 2 % 60:02d}", font=f_mono, fill=branco)
        if i >= n * 2 // 3:
            r = k(60)
            c = TAM // 2
            d.rectangle((c - r, c - r, c + r, c + r), outline=(220, 30, 30), width=k(2))
            d.line((c - r - k(8), c, c - r + k(8), c), fill=(220, 30, 30), width=k(2))
            d.line((c + r - k(8), c, c + r + k(8), c), fill=(220, 30, 30), width=k(2))
            d.rectangle((0, TAM - k(56), TAM, TAM - k(38)), fill=(150, 0, 0))
            _texto_centro(d, TAM - k(55), "ALVO IDENTIFICADO", f_alvo, (255, 255, 255), TAM)
        frames.append(f)
        duracoes.append(1400 if i == n - 1 else 80)
    return frames, duracoes


def _carimbo(texto: str, cor, tamanho: int) -> Image.Image:
    f = fonte(tamanho)
    larg = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(texto, font=f))
    img = Image.new("RGBA", (larg + k(24), tamanho + k(22)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((k(2), k(2), img.width - k(3), img.height - k(3)), outline=cor, width=k(3))
    d.text((k(12), k(6)), texto, font=f, fill=cor)
    return img.rotate(18, expand=True, resample=Image.BICUBIC)


def _confidencial(av):
    """Dossiê: foto, linhas censuradas e carimbo CONFIDENCIAL."""
    papel = (226, 214, 186)
    tinta = (60, 50, 40)
    base = Image.new("RGBA", (TAM, TAM), papel + (255,))
    d = ImageDraw.Draw(base)
    f_mono = fonte(k(11), "mono")
    d.text((k(12), k(10)), f"DOSSIÊ Nº {random.randint(100, 999)}", font=f_mono, fill=tinta)
    d.text((TAM - k(78), k(10)), "SEUBOT // ARQ.", font=f_mono, fill=tinta)
    d.line((k(12), k(27), TAM - k(12), k(27)), fill=tinta, width=1)
    foto_t = k(100)
    foto = ImageOps.colorize(av.convert("L").resize((foto_t, foto_t)), (40, 30, 20), (235, 220, 190)).convert("RGBA")
    base.alpha_composite(foto, (k(14), k(38)))
    d.rectangle((k(14), k(38), k(14) + foto_t, k(38) + foto_t), outline=tinta, width=1)
    linhas = []
    for li in range(13):
        y = k(40) + li * k(15)
        x0 = k(124) if y < k(38) + foto_t + k(4) else k(14)
        x1 = TAM - k(14) - random.randint(0, k(40))
        linhas.append((x0, y, x1))
        for x in range(x0, x1, k(7)):
            d.line((x, y + k(5), x + k(4), y + k(5)), fill=(120, 105, 85), width=k(2))
    censurar = random.sample(range(len(linhas)), 8)
    carimbo = _carimbo("CONFIDENCIAL", VERMELHO, k(25))
    frames, duracoes = [], []
    for i in range(len(censurar) + 7):
        f = base.copy()
        d = ImageDraw.Draw(f)
        for li in censurar[: min(i + 1, len(censurar))]:
            x0, y, x1 = linhas[li]
            d.rectangle((x0, y, x1, y + k(10)), fill=(15, 15, 15))
        passo = i - len(censurar)
        if passo >= 0:
            escala = max(1.0, 1.7 - passo * 0.25)
            alfa = min(1.0, 0.35 + passo * 0.25)
            c = carimbo.resize((int(carimbo.width * escala), int(carimbo.height * escala)), Image.LANCZOS)
            c.putalpha(c.getchannel("A").point(lambda a, al=alfa: int(a * al * 0.9)))
            dx = random.randint(-k(3), k(3)) if passo in (3, 4) else 0
            f.alpha_composite(c, ((TAM - c.width) // 2 + dx, (TAM - c.height) // 2 + k(30)))
        frames.append(f)
        duracoes.append(2200 if i == len(censurar) + 6 else 130)
    return frames, duracoes


def _selo(av):
    """Selo de lacre vermelho com o avatar, carimbado."""
    t = k(220)
    selo = Image.new("RGBA", (t, t), (0, 0, 0, 0))
    d = ImageDraw.Draw(selo)
    cera, cera_escura = (150, 20, 25), (95, 10, 15)
    c = t / 2
    rnd = random.Random(7)
    for a in range(0, 360, 12):  # borda irregular de cera
        rr = t * 0.44 + rnd.uniform(-k(4), k(5))
        x, y = c + math.cos(math.radians(a)) * rr, c + math.sin(math.radians(a)) * rr
        b = rnd.uniform(k(9), k(14))
        d.ellipse((x - b, y - b, x + b, y + b), fill=cera)
    d.ellipse((c - t * 0.44, c - t * 0.44, c + t * 0.44, c + t * 0.44), fill=cera)
    d.ellipse((c - t * 0.36, c - t * 0.36, c + t * 0.36, c + t * 0.36), outline=cera_escura, width=k(3))
    f_letra = fonte(k(13))
    frase = "SOCIEDADE • SECRETA • SEUBOT • "
    for i, ch in enumerate(frase):
        a = i / len(frase) * 2 * math.pi - math.pi / 2
        d.text((c + math.cos(a) * t * 0.40 - k(4), c + math.sin(a) * t * 0.40 - k(8)), ch, font=f_letra, fill=(210, 150, 140))
    av_t = int(t * 0.62)
    tingido = ImageOps.colorize(av.convert("L").resize((av_t, av_t)), (60, 0, 5), (235, 120, 110)).convert("RGBA")
    selo.alpha_composite(_circular(tingido), (int(c - av_t / 2), int(c - av_t / 2)))
    d = ImageDraw.Draw(selo)
    d.ellipse((c - av_t / 2, c - av_t / 2, c + av_t / 2, c + av_t / 2), outline=cera_escura, width=k(3))

    escalas = [1.9, 1.6, 1.35, 1.15, 1.0, 0.96, 1.0, 1.0]
    frames, duracoes = [], []
    for i in range(22):
        f = Image.new("RGBA", (TAM, TAM), FUNDO + (255,))
        esc = escalas[i] if i < len(escalas) else 1.0
        tt = int(t * esc)
        img = selo.resize((tt, tt), Image.LANCZOS)
        if i < 4:
            img.putalpha(img.getchannel("A").point(lambda a, al=0.4 + i * 0.15: int(a * al)))
        dx = random.randint(-k(4), k(4)) if 4 <= i <= 6 else 0
        if i >= 4:  # sombra
            sombra = Image.new("RGBA", (TAM, TAM), (0, 0, 0, 0))
            ImageDraw.Draw(sombra).ellipse((TAM / 2 - t * 0.46, TAM / 2 - t * 0.42, TAM / 2 + t * 0.48, TAM / 2 + t * 0.52), fill=(0, 0, 0, 160))
            f.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(k(8))))
        f.alpha_composite(img, ((TAM - tt) // 2 + dx, (TAM - tt) // 2))
        if i >= 8:  # brilho passando
            brilho = Image.new("RGBA", (TAM, TAM), (0, 0, 0, 0))
            x = int((i - 8) / 13 * TAM * 1.6) - k(60)
            ImageDraw.Draw(brilho).polygon([(x, 0), (x + k(30), 0), (x - k(70), TAM), (x - k(100), TAM)], fill=(255, 220, 210, 45))
            mascara = Image.new("L", (TAM, TAM), 0)
            mascara.paste(img.getchannel("A"), ((TAM - tt) // 2, (TAM - tt) // 2))
            brilho.putalpha(Image.composite(brilho.getchannel("A"), Image.new("L", (TAM, TAM), 0), mascara))
            f.alpha_composite(brilho)
        frames.append(f)
        duracoes.append(1500 if i == 21 else 70)
    return frames, duracoes


def _chuva_runas(av):
    """Runas caindo sobre o avatar, como em Matrix."""
    base = ImageEnhance.Brightness(av).enhance(0.35)
    f_runa = fonte(k(15), "runas")
    passo = k(16)
    colunas = TAM // passo
    n = 24
    rnd = random.Random()
    gotas = [(rnd.randrange(TAM + k(120)), rnd.choice((1, 2, 3)), rnd.randint(5, 10)) for _ in range(colunas)]
    simbolos = [[rnd.choice(RUNAS) for _ in range(TAM // passo + 12)] for _ in range(colunas)]
    frames = []
    for i in range(n):
        f = base.copy()
        camada = Image.new("RGBA", (TAM, TAM), (0, 0, 0, 0))
        d = ImageDraw.Draw(camada)
        for col, (ini, vel, rastro) in enumerate(gotas):
            ciclo = TAM + rastro * passo
            cabeca = (ini + i * vel * (ciclo // n)) % ciclo
            for j in range(rastro):
                y = cabeca - j * passo
                if 0 <= y < TAM:
                    if j == 0:
                        cor = DOURADO + (255,)
                    else:
                        cor = (140, 90, 200, int(220 * (1 - j / rastro)))
                    d.text((col * passo + k(2), y), simbolos[col][(y // passo) % len(simbolos[col])], font=f_runa, fill=cor)
        f.alpha_composite(camada)
        frames.append(f)
    return frames, 70


def _velas(av):
    """Avatar iluminado por velas tremulando no escuro."""
    quente = Image.blend(av, Image.new("RGBA", (TAM, TAM), (255, 150, 60, 255)), 0.25)
    vinheta = Image.radial_gradient("L").resize((TAM, TAM))  # 0 no centro, 255 nas bordas
    rnd = random.Random()
    n = 24
    brilhos = [0.8 + 0.2 * math.sin(i / n * 2 * math.pi) + rnd.uniform(-0.08, 0.08) for i in range(n)]
    frames = []
    for i in range(n):
        f = ImageEnhance.Brightness(quente).enhance(0.55 + 0.45 * brilhos[i])
        intensidade = 1.25 - 0.35 * brilhos[i]
        escuro = Image.new("RGBA", (TAM, TAM), (0, 0, 0, 255))
        escuro.putalpha(vinheta.point(lambda v, it=intensidade: min(255, int(v * it))))
        f.alpha_composite(escuro)
        d = ImageDraw.Draw(f)
        for cx in (k(34), TAM - k(34)):
            d.rectangle((cx - k(9), TAM - k(62), cx + k(9), TAM), fill=(235, 225, 200))
            d.line((cx, TAM - k(62), cx, TAM - k(68)), fill=(40, 30, 20), width=k(2))
            h = k(20) + rnd.randint(-k(3), k(4))
            oscila = rnd.randint(-k(2), k(2))
            halo = Image.new("RGBA", (TAM, TAM), (0, 0, 0, 0))
            ImageDraw.Draw(halo).ellipse((cx - k(30), TAM - k(108), cx + k(30), TAM - k(48)), fill=(255, 170, 60, 70))
            f.alpha_composite(halo.filter(ImageFilter.GaussianBlur(k(10))))
            d = ImageDraw.Draw(f)
            d.ellipse((cx - k(6) + oscila, TAM - k(66) - h, cx + k(6) + oscila, TAM - k(64)), fill=(255, 150, 40))
            d.ellipse((cx - k(3) + oscila, TAM - k(64) - h * 0.6, cx + k(3) + oscila, TAM - k(66)), fill=(255, 240, 180))
        frames.append(f)
    return frames, 80


def _sigilo(av):
    """Símbolo geométrico dourado sendo desenhado ao redor do avatar."""
    c = TAM / 2
    av_t = k(104)
    base = Image.new("RGBA", (TAM, TAM), (16, 10, 24, 255))
    base.alpha_composite(_circular(ImageEnhance.Brightness(av.resize((av_t, av_t), Image.LANCZOS)).enhance(0.9)),
                         (int(c - av_t / 2), int(c - av_t / 2)))

    def circulo(r, partes=48):
        pts = [(c + math.cos(a) * r, c + math.sin(a) * r) for a in (j / partes * 2 * math.pi - math.pi / 2 for j in range(partes + 1))]
        return list(zip(pts, pts[1:]))

    def poligono(r, lados, giro):
        pts = [(c + math.cos(giro + j / lados * 2 * math.pi) * r, c + math.sin(giro + j / lados * 2 * math.pi) * r) for j in range(lados + 1)]
        return list(zip(pts, pts[1:]))

    r1, r2 = k(118), k(100)
    segmentos = (circulo(r1) + circulo(r2) + poligono(r2, 3, -math.pi / 2) + poligono(r2, 3, math.pi / 2)
                 + poligono(k(60), 6, 0) + circulo(k(56)))
    for j in range(6):  # raios
        a = j / 6 * 2 * math.pi
        segmentos.append(((c + math.cos(a) * k(60), c + math.sin(a) * k(60)), (c + math.cos(a) * r2, c + math.sin(a) * r2)))
    desenho_frames, brilho_frames = 22, 10
    frames, duracoes = [], []
    for i in range(desenho_frames + brilho_frames):
        camada = Image.new("RGBA", (TAM, TAM), (0, 0, 0, 0))
        d = ImageDraw.Draw(camada)
        feitos = len(segmentos) if i >= desenho_frames else int(len(segmentos) * (i + 1) / desenho_frames)
        for a, b in segmentos[:feitos]:
            d.line((a, b), fill=DOURADO + (255,), width=k(2))
        f = base.copy()
        pulso = 1.0 if i < desenho_frames else 0.5 + 0.5 * math.sin((i - desenho_frames) / brilho_frames * 2 * math.pi)
        brilho = camada.filter(ImageFilter.GaussianBlur(k(4)))
        brilho.putalpha(brilho.getchannel("A").point(lambda v, p=pulso: int(v * p)))
        f.alpha_composite(brilho)
        f.alpha_composite(brilho)
        f.alpha_composite(camada)
        frames.append(f)
        duracoes.append(60)
    return frames, duracoes


EFEITOS = {
    "ritual": ("🔯 Ritual", "Círculo de runas ao redor do avatar", _ritual),
    "olho": ("👁️ Olho que tudo vê", "O selo da SeuBot sobre o avatar", _olho),
    "sigilo": ("✴️ Sigilo", "Símbolo dourado sendo desenhado", _sigilo),
    "selo": ("🔴 Selo de cera", "Avatar carimbado em lacre vermelho", _selo),
    "confidencial": ("📁 Confidencial", "Dossiê censurado e carimbado", _confidencial),
    "vigilancia": ("📹 Vigilância", "Câmera de segurança: alvo identificado", _vigilancia),
    "runas": ("🌧️ Chuva de runas", "Runas caindo sobre o avatar", _chuva_runas),
    "velas": ("🕯️ Luz de velas", "Iluminado por velas no escuro", _velas),
    "revelar": ("🎭 Identidade revelada", "Surge das sombras", _revelar),
    "glitch": ("📡 Sinal interceptado", "Transmissão corrompida", _glitch),
}


def gerar_gif(efeito: str, avatar: bytes) -> io.BytesIO:
    frames, duracao = EFEITOS[efeito][2](_abrir_avatar(avatar))
    return _salvar_gif(frames, duracao)


LIMITE_TEXTO = 200   # caracteres aceitos no /gifsecreto
LETRAS_POR_LINHA = 24


def gif_decifrando(texto: str) -> io.BytesIO:
    """Texto que começa em runas e vai sendo decifrado letra por letra (quebra em várias linhas)."""
    texto = " ".join(texto.upper().split())[:LIMITE_TEXTO]
    linhas = textwrap.wrap(texto, LETRAS_POR_LINHA, break_long_words=True) or [""]
    f_letra = fonte(40, "mono")
    f_runa = fonte(40, "runas")
    f_rodape = fonte(14, "texto")
    celula, altura_linha = 30, 54
    maior = max(len(l) for l in linhas)
    largura = max(360, maior * celula + 60)
    altura = 30 + len(linhas) * altura_linha + 50

    # posição (linha, coluna) de cada caractere visível, na ordem de leitura
    posicoes = [(li, ci, ch) for li, l in enumerate(linhas) for ci, ch in enumerate(l) if ch != " "]
    total = len(posicoes)
    por_frame = max(1, math.ceil(total / 30))  # ~30 quadros de animação, qualquer tamanho
    passos = math.ceil(total / por_frame)

    frames, duracoes = [], []
    for passo in range(passos + 1):
        revelados = passo * por_frame
        f = Image.new("RGB", (largura, altura), FUNDO)
        d = ImageDraw.Draw(f)
        d.rectangle((4, 4, largura - 5, altura - 5), outline=DOURADO_ESCURO, width=2)
        for n, (li, ci, ch) in enumerate(posicoes):
            x = (largura - len(linhas[li]) * celula) / 2 + ci * celula
            y = 30 + li * altura_linha
            if n < revelados:
                d.text((x, y + 2), ch, font=f_letra, fill=DOURADO)
            else:
                d.text((x, y), random.choice(RUNAS), font=f_runa, fill=(110, 80, 150))
        fim_anim = revelados >= total
        _texto_centro(d, altura - 34, "MENSAGEM DECIFRADA" if fim_anim else "DECIFRANDO...", f_rodape, DOURADO_ESCURO, largura)
        frames.append(f)
        duracoes.append(3500 if fim_anim else 110)
    return _salvar_gif(frames, duracoes)


# ------------------------------------------------------------------ Carteirinha

def carteirinha(avatar: bytes, nome: str, codinome: str, numero: int,
                desde: int, servidor: str) -> io.BytesIO:
    W, H = 900, 500
    img = Image.new("RGBA", (W, H), FUNDO)
    d = ImageDraw.Draw(img)

    # Fundo com runas apagadas
    f_runa_bg = fonte(26, "runas")
    rnd = random.Random(numero)
    for y in range(10, H, 38):
        linha = "".join(rnd.choice(RUNAS) + " " for _ in range(40))
        d.text((10, y), linha, font=f_runa_bg, fill=(24, 20, 34))

    # Bordas
    d.rectangle((12, 12, W - 13, H - 13), outline=DOURADO, width=4)
    d.rectangle((24, 24, W - 25, H - 25), outline=DOURADO_ESCURO, width=1)

    # Cabeçalho
    _texto_centro(d, 42, "SOCIEDADE SECRETA SEUBOT", fonte(38), DOURADO, W)
    _texto_centro(d, 88, "CREDENCIAL DE MEMBRO", fonte(16, "texto"), DOURADO_ESCURO, W)
    d.line((60, 118, W - 60, 118), fill=DOURADO_ESCURO, width=1)

    # Avatar
    av = _circular(_abrir_avatar(avatar, 210))
    d.ellipse((58, 148, 282, 372), outline=DOURADO, width=5)
    img.alpha_composite(av, (65, 155))

    # Dados
    f_rot = fonte(15, "texto")
    f_val = fonte(30)
    campos = [
        ("CODINOME", codinome),
        ("Nº DE REGISTRO", f"#{numero:03d}"),
        ("INICIADO EM", dt.datetime.fromtimestamp(desde).strftime("%d/%m/%Y")),
    ]
    y = 170
    for rotulo, valor in campos:
        d.text((330, y), rotulo, font=f_rot, fill=DOURADO_ESCURO)
        d.text((330, y + 18), valor, font=f_val, fill=(235, 225, 200))
        y += 70

    # Símbolo
    desenhar_olho(d, 770, 240, 62, DOURADO, 4)
    _texto_centro_em(d, 770, 320, "VERITAS IN UMBRA", fonte(16, "texto"), DOURADO)

    # Rodapé
    d.line((60, 410, W - 60, 410), fill=DOURADO_ESCURO, width=1)
    _texto_centro(d, 422, "O QUE É VISTO AQUI, AQUI PERMANECE.", fonte(18, "texto"), DOURADO_ESCURO, W)
    _texto_centro(d, 448, f"{nome}  •  {servidor}"[:70], fonte(13, "texto"), (90, 80, 100), W)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf


def _texto_centro_em(draw, cx, y, texto, f, cor):
    w = draw.textlength(texto, font=f)
    draw.text((cx - w / 2, y), texto, font=f, fill=cor)
