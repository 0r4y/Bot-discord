import re
import datetime as dt

import discord

COR = discord.Color.from_rgb(212, 175, 55)  # dourado SeuBot
COR_OK = discord.Color.green()
COR_ERRO = discord.Color.red()
COR_AVISO = discord.Color.orange()

_DURACAO = re.compile(r"(\d+)\s*([smhdw])", re.IGNORECASE)
_UNIDADES = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def parse_duracao(texto: str) -> int | None:
    """Converte '1h30m', '10m', '2d' em segundos. Retorna None se inválido."""
    partes = _DURACAO.findall(texto)
    if not partes or _DURACAO.sub("", texto).strip():
        return None
    return sum(int(n) * _UNIDADES[u.lower()] for n, u in partes)


def formatar_duracao(segundos: int) -> str:
    return str(dt.timedelta(seconds=segundos))


def embed(titulo: str = None, descricao: str = None, cor: discord.Color = COR) -> discord.Embed:
    e = discord.Embed(title=titulo, description=descricao, color=cor)
    e.timestamp = discord.utils.utcnow()
    return e


async def enviar_log(bot, guild: discord.Guild, e: discord.Embed, arquivo: discord.File = None):
    """Envia um embed para o canal de logs configurado, se houver."""
    canal_id = bot.db.get_config(guild.id).get("log_channel")
    if not canal_id:
        return
    canal = guild.get_channel(canal_id)
    if canal:
        try:
            await canal.send(embed=e, file=arquivo)
        except discord.HTTPException:
            pass
