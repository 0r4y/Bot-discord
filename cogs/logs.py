import discord
from discord.ext import commands

from utils import embed, enviar_log, COR, COR_OK, COR_ERRO, COR_AVISO


class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, msg: discord.Message):
        if not msg.guild or msg.author.bot:
            return
        e = embed("🗑️ Mensagem apagada", msg.content[:4000] or "*(sem texto)*", COR_ERRO)
        e.add_field(name="Autor", value=msg.author.mention)
        e.add_field(name="Canal", value=msg.channel.mention)
        if msg.attachments:
            e.add_field(name="Anexos", value="\n".join(a.filename for a in msg.attachments), inline=False)
        await enviar_log(self.bot, msg.guild, e)

    @commands.Cog.listener()
    async def on_message_edit(self, antes: discord.Message, depois: discord.Message):
        if not antes.guild or antes.author.bot or antes.content == depois.content:
            return
        e = embed("✏️ Mensagem editada", f"[Ir para a mensagem]({depois.jump_url})", COR_AVISO)
        e.add_field(name="Autor", value=antes.author.mention)
        e.add_field(name="Canal", value=antes.channel.mention)
        e.add_field(name="Antes", value=antes.content[:1024] or "*(vazio)*", inline=False)
        e.add_field(name="Depois", value=depois.content[:1024] or "*(vazio)*", inline=False)
        await enviar_log(self.bot, antes.guild, e)

    @commands.Cog.listener()
    async def on_member_join(self, membro: discord.Member):
        e = embed("📥 Membro entrou", f"{membro.mention} (`{membro}`)", COR_OK)
        e.add_field(name="Conta criada", value=discord.utils.format_dt(membro.created_at, "R"))
        e.set_thumbnail(url=membro.display_avatar.url)
        await enviar_log(self.bot, membro.guild, e)

    @commands.Cog.listener()
    async def on_member_remove(self, membro: discord.Member):
        e = embed("📤 Membro saiu", f"{membro.mention} (`{membro}`)", COR_ERRO)
        if membro.joined_at:
            e.add_field(name="Entrou", value=discord.utils.format_dt(membro.joined_at, "R"))
        await enviar_log(self.bot, membro.guild, e)

    @commands.Cog.listener()
    async def on_member_update(self, antes: discord.Member, depois: discord.Member):
        if antes.nick != depois.nick:
            e = embed("📝 Apelido alterado", depois.mention, COR)
            e.add_field(name="Antes", value=antes.nick or "—")
            e.add_field(name="Depois", value=depois.nick or "—")
            await enviar_log(self.bot, depois.guild, e)

        adicionados = set(depois.roles) - set(antes.roles)
        removidos = set(antes.roles) - set(depois.roles)
        if adicionados or removidos:
            e = embed("🎭 Cargos alterados", depois.mention, COR)
            if adicionados:
                e.add_field(name="Adicionados", value=" ".join(r.mention for r in adicionados))
            if removidos:
                e.add_field(name="Removidos", value=" ".join(r.mention for r in removidos))
            await enviar_log(self.bot, depois.guild, e)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, canal):
        await enviar_log(self.bot, canal.guild, embed("📁 Canal criado", f"{canal.mention} (`{canal.name}`)", COR_OK))

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, canal):
        await enviar_log(self.bot, canal.guild, embed("📁 Canal apagado", f"`{canal.name}`", COR_ERRO))


async def setup(bot):
    await bot.add_cog(Logs(bot))
