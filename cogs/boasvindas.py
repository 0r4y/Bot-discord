import discord
from discord.ext import commands

from utils import embed, COR_OK, COR_ERRO

MENSAGEM_PADRAO = "{user} cruzou o limiar de **{server}**.\nRegistro nº **{count}**. Observe, escute e aguarde."


def formatar(texto: str, membro: discord.Member) -> str:
    return (
        texto.replace("{user}", membro.mention)
        .replace("{nome}", membro.display_name)
        .replace("{server}", membro.guild.name)
        .replace("{count}", str(membro.guild.member_count))
    )


class BoasVindas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, membro: discord.Member):
        cfg = self.bot.db.get_config(membro.guild.id)

        if cfg.get("autorole"):
            cargo = membro.guild.get_role(cfg["autorole"])
            if cargo:
                try:
                    await membro.add_roles(cargo, reason="Autorole")
                except discord.HTTPException:
                    pass

        canal = membro.guild.get_channel(cfg.get("welcome_channel") or 0)
        if canal:
            e = embed("Nova presença", formatar(cfg.get("welcome_message") or MENSAGEM_PADRAO, membro), COR_OK)
            e.set_thumbnail(url=membro.display_avatar.url)
            await canal.send(content=membro.mention, embed=e)

    @commands.Cog.listener()
    async def on_member_remove(self, membro: discord.Member):
        cfg = self.bot.db.get_config(membro.guild.id)
        canal = membro.guild.get_channel(cfg.get("leave_channel") or 0)
        if canal:
            e = embed("Partida", f"**{membro}** deixou o servidor. Restam **{membro.guild.member_count}**.", COR_ERRO)
            e.set_thumbnail(url=membro.display_avatar.url)
            await canal.send(embed=e)


async def setup(bot):
    await bot.add_cog(BoasVindas(bot))
