import datetime as dt

import discord
from discord import app_commands
from discord.ext import commands

from utils import embed, enviar_log, parse_duracao, formatar_duracao, COR_OK, COR_ERRO, COR_AVISO


def pode_moderar(interaction: discord.Interaction, alvo: discord.Member) -> str | None:
    """Retorna uma mensagem de erro se o autor/bot não puder agir sobre o alvo."""
    if alvo == interaction.user:
        return "Você não pode usar isso em si mesmo."
    if alvo == interaction.guild.owner:
        return "Não é possível punir o dono do servidor."
    if interaction.user != interaction.guild.owner and alvo.top_role >= interaction.user.top_role:
        return "Esse membro tem um cargo igual ou maior que o seu."
    if alvo.top_role >= interaction.guild.me.top_role:
        return "Esse membro tem um cargo igual ou maior que o meu."
    return None


class Moderacao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _log(self, guild, acao, alvo, moderador, motivo, cor=COR_ERRO, extra=None):
        e = embed(f"🔨 {acao}", cor=cor)
        e.add_field(name="Membro", value=f"{alvo.mention} (`{alvo.id}`)")
        e.add_field(name="Moderador", value=moderador.mention)
        if extra:
            e.add_field(name="Detalhes", value=extra)
        e.add_field(name="Motivo", value=motivo or "Não informado", inline=False)
        await enviar_log(self.bot, guild, e)

    async def _avisar_dm(self, membro, acao, guild, motivo):
        try:
            await membro.send(embed=embed(f"Você recebeu: {acao}", f"Servidor: **{guild.name}**\nMotivo: {motivo or 'Não informado'}", COR_AVISO))
        except discord.HTTPException:
            pass

    @app_commands.command(description="Bane um membro do servidor")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.describe(apagar_dias="Apagar mensagens dos últimos N dias (0-7)")
    async def ban(self, interaction: discord.Interaction, membro: discord.Member, motivo: str = None,
                  apagar_dias: app_commands.Range[int, 0, 7] = 0):
        if erro := pode_moderar(interaction, membro):
            return await interaction.response.send_message(erro, ephemeral=True)
        await self._avisar_dm(membro, "Banimento", interaction.guild, motivo)
        await membro.ban(reason=f"{interaction.user}: {motivo}", delete_message_seconds=apagar_dias * 86400)
        await interaction.response.send_message(embed=embed("Membro banido", f"{membro.mention} foi banido.\nMotivo: {motivo or 'Não informado'}", COR_ERRO))
        await self._log(interaction.guild, "Banimento", membro, interaction.user, motivo)

    @app_commands.command(description="Remove o banimento de um usuário pelo ID")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, usuario_id: str, motivo: str = None):
        try:
            user = await self.bot.fetch_user(int(usuario_id))
            await interaction.guild.unban(user, reason=f"{interaction.user}: {motivo}")
        except (ValueError, discord.NotFound):
            return await interaction.response.send_message("Usuário não encontrado ou não está banido.", ephemeral=True)
        await interaction.response.send_message(embed=embed("Desbanido", f"{user.mention} foi desbanido.", COR_OK))
        await self._log(interaction.guild, "Desbanimento", user, interaction.user, motivo, COR_OK)

    @app_commands.command(description="Expulsa um membro do servidor")
    @app_commands.guild_only()
    @app_commands.default_permissions(kick_members=True)
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.checks.bot_has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, membro: discord.Member, motivo: str = None):
        if erro := pode_moderar(interaction, membro):
            return await interaction.response.send_message(erro, ephemeral=True)
        await self._avisar_dm(membro, "Expulsão", interaction.guild, motivo)
        await membro.kick(reason=f"{interaction.user}: {motivo}")
        await interaction.response.send_message(embed=embed("Membro expulso", f"{membro.mention} foi expulso.\nMotivo: {motivo or 'Não informado'}", COR_ERRO))
        await self._log(interaction.guild, "Expulsão", membro, interaction.user, motivo)

    @app_commands.command(description="Silencia um membro por um tempo (ex: 10m, 1h, 2d)")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, membro: discord.Member, duracao: str, motivo: str = None):
        if erro := pode_moderar(interaction, membro):
            return await interaction.response.send_message(erro, ephemeral=True)
        segundos = parse_duracao(duracao)
        if not segundos or segundos > 28 * 86400:
            return await interaction.response.send_message("Duração inválida. Use algo como `10m`, `1h`, `2d` (máx. 28d).", ephemeral=True)
        await membro.timeout(dt.timedelta(seconds=segundos), reason=f"{interaction.user}: {motivo}")
        tempo = formatar_duracao(segundos)
        await interaction.response.send_message(embed=embed("Membro silenciado", f"{membro.mention} silenciado por **{tempo}**.\nMotivo: {motivo or 'Não informado'}", COR_AVISO))
        await self._avisar_dm(membro, f"Silenciamento ({tempo})", interaction.guild, motivo)
        await self._log(interaction.guild, "Silenciamento", membro, interaction.user, motivo, COR_AVISO, f"Duração: {tempo}")

    @app_commands.command(description="Remove o silenciamento de um membro")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, membro: discord.Member):
        await membro.timeout(None, reason=f"{interaction.user}: unmute")
        await interaction.response.send_message(embed=embed("Silenciamento removido", f"{membro.mention} pode falar novamente.", COR_OK))
        await self._log(interaction.guild, "Fim do silenciamento", membro, interaction.user, None, COR_OK)

    @app_commands.command(description="Apaga mensagens do canal")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(manage_messages=True, read_message_history=True)
    @app_commands.describe(quantidade="Quantas mensagens apagar (1-100)", membro="Apagar só mensagens deste membro")
    async def limpar(self, interaction: discord.Interaction, quantidade: app_commands.Range[int, 1, 100], membro: discord.Member = None):
        await interaction.response.defer(ephemeral=True)
        check = (lambda m: m.author == membro) if membro else None
        apagadas = await interaction.channel.purge(limit=quantidade, check=check)
        await interaction.followup.send(f"🧹 {len(apagadas)} mensagens apagadas.", ephemeral=True)
        e = embed("🧹 Limpeza de mensagens", f"{len(apagadas)} mensagens apagadas em {interaction.channel.mention} por {interaction.user.mention}", COR_AVISO)
        await enviar_log(self.bot, interaction.guild, e)

    @app_commands.command(description="Dá uma advertência a um membro")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, membro: discord.Member, motivo: str):
        if erro := pode_moderar(interaction, membro):
            return await interaction.response.send_message(erro, ephemeral=True)
        self.bot.db.add_warn(interaction.guild_id, membro.id, interaction.user.id, motivo)
        total = len(self.bot.db.get_warns(interaction.guild_id, membro.id))
        await interaction.response.send_message(embed=embed("⚠️ Advertência", f"{membro.mention} foi advertido.\nMotivo: {motivo}\nTotal de advertências: **{total}**", COR_AVISO))
        await self._avisar_dm(membro, "Advertência", interaction.guild, motivo)
        await self._log(interaction.guild, "Advertência", membro, interaction.user, motivo, COR_AVISO, f"Total: {total}")

    @app_commands.command(description="Lista as advertências de um membro")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    async def warns(self, interaction: discord.Interaction, membro: discord.Member):
        lista = self.bot.db.get_warns(interaction.guild_id, membro.id)
        if not lista:
            return await interaction.response.send_message(f"{membro.mention} não tem advertências.", ephemeral=True)
        e = embed(f"Advertências de {membro.display_name}", cor=COR_AVISO)
        for w in lista[-25:]:
            e.add_field(name=f"#{w['id']} • <t:{w['created_at']}:d>", value=f"{w['reason']}\nPor: <@{w['mod_id']}>", inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(description="Remove uma advertência pelo número (#)")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unwarn(self, interaction: discord.Interaction, numero: int):
        ok = self.bot.db.remove_warn(interaction.guild_id, numero)
        await interaction.response.send_message("Advertência removida." if ok else "Advertência não encontrada.", ephemeral=True)

    @app_commands.command(description="Apaga todas as advertências de um membro")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def limparwarns(self, interaction: discord.Interaction, membro: discord.Member):
        n = self.bot.db.clear_warns(interaction.guild_id, membro.id)
        await interaction.response.send_message(f"{n} advertências de {membro.mention} foram apagadas.", ephemeral=True)

    @app_commands.command(description="Define o modo lento do canal (0 desativa)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, segundos: app_commands.Range[int, 0, 21600]):
        await interaction.channel.edit(slowmode_delay=segundos)
        texto = f"Modo lento definido para **{segundos}s**." if segundos else "Modo lento desativado."
        await interaction.response.send_message(texto)

    @app_commands.command(description="Tranca o canal para @everyone")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    async def trancar(self, interaction: discord.Interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message("🔒 Canal trancado.")

    @app_commands.command(description="Destranca o canal para @everyone")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    async def destrancar(self, interaction: discord.Interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None)
        await interaction.response.send_message("🔓 Canal destrancado.")


async def setup(bot):
    await bot.add_cog(Moderacao(bot))
