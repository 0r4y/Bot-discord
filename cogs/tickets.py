import asyncio
import io

import discord
from discord import app_commands
from discord.ext import commands

from utils import embed, enviar_log, COR, COR_OK, COR_ERRO

ID_ABRIR = "geral:ticket:abrir"
ID_FECHAR = "geral:ticket:fechar"


class PainelTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Abrir ticket", emoji="🎫", style=discord.ButtonStyle.primary, custom_id=ID_ABRIR))


class FecharTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Fechar ticket", emoji="🔒", style=discord.ButtonStyle.danger, custom_id=ID_FECHAR))


def eh_ticket(canal) -> bool:
    return isinstance(canal, discord.TextChannel) and (canal.topic or "").startswith("ticket:")


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    ticket = app_commands.Group(name="ticket", description="Sistema de tickets de suporte", guild_only=True)

    @ticket.command(name="painel", description="Envia o painel para abrir tickets neste canal")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def painel(self, interaction: discord.Interaction, titulo: str = "Suporte", descricao: str = "Clique no botão abaixo para falar com a equipe."):
        await interaction.channel.send(embed=embed(f"🎫 {titulo}", descricao), view=PainelTicket())
        await interaction.response.send_message("Painel enviado.", ephemeral=True)

    @ticket.command(name="adicionar", description="Adiciona um membro a este ticket")
    async def adicionar(self, interaction: discord.Interaction, membro: discord.Member):
        if not eh_ticket(interaction.channel):
            return await interaction.response.send_message("Use isso dentro de um ticket.", ephemeral=True)
        await interaction.channel.set_permissions(membro, view_channel=True, send_messages=True, read_message_history=True)
        await interaction.response.send_message(f"{membro.mention} foi adicionado ao ticket.")

    @ticket.command(name="remover", description="Remove um membro deste ticket")
    async def remover(self, interaction: discord.Interaction, membro: discord.Member):
        if not eh_ticket(interaction.channel):
            return await interaction.response.send_message("Use isso dentro de um ticket.", ephemeral=True)
        await interaction.channel.set_permissions(membro, overwrite=None)
        await interaction.response.send_message(f"{membro.mention} foi removido do ticket.")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        cid = interaction.data.get("custom_id")
        if cid == ID_ABRIR:
            await self.abrir(interaction)
        elif cid == ID_FECHAR:
            await self.fechar(interaction)

    async def abrir(self, interaction: discord.Interaction):
        guild = interaction.guild
        cfg = self.bot.db.get_config(guild.id)
        categoria = guild.get_channel(cfg.get("ticket_category") or 0)
        equipe = guild.get_role(cfg.get("ticket_staff_role") or 0)
        if not categoria or not equipe:
            return await interaction.response.send_message(
                "Os tickets ainda não foram configurados. Um admin deve usar `/config tickets`.", ephemeral=True
            )

        existente = discord.utils.find(
            lambda c: c.topic == f"ticket:{interaction.user.id}", categoria.text_channels
        )
        if existente:
            return await interaction.response.send_message(f"Você já tem um ticket aberto: {existente.mention}", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True),
            equipe: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        canal = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}"[:90],
            category=categoria,
            overwrites=overwrites,
            topic=f"ticket:{interaction.user.id}",
        )
        e = embed("🎫 Ticket aberto", f"Olá {interaction.user.mention}! Descreva seu problema e a equipe {equipe.mention} responderá em breve.")
        await canal.send(content=f"{interaction.user.mention} {equipe.mention}", embed=e, view=FecharTicket())
        await interaction.followup.send(f"Ticket criado: {canal.mention}", ephemeral=True)
        await enviar_log(self.bot, guild, embed("🎫 Ticket aberto", f"{canal.mention} por {interaction.user.mention}", COR_OK))

    async def fechar(self, interaction: discord.Interaction):
        canal = interaction.channel
        if not eh_ticket(canal):
            return await interaction.response.send_message("Isso não é um ticket.", ephemeral=True)

        cfg = self.bot.db.get_config(interaction.guild_id)
        dono_id = int(canal.topic.split(":")[1])
        equipe = interaction.guild.get_role(cfg.get("ticket_staff_role") or 0)
        pode = (
            interaction.user.id == dono_id
            or (equipe and equipe in interaction.user.roles)
            or interaction.user.guild_permissions.manage_channels
        )
        if not pode:
            return await interaction.response.send_message("Você não pode fechar este ticket.", ephemeral=True)

        await interaction.response.send_message(embed=embed("🔒 Fechando ticket em 5 segundos...", cor=COR_ERRO))

        linhas = []
        async for m in canal.history(limit=None, oldest_first=True):
            linhas.append(f"[{m.created_at:%d/%m/%Y %H:%M}] {m.author}: {m.content}")
            for a in m.attachments:
                linhas.append(f"    [anexo] {a.url}")
        transcricao = discord.File(io.BytesIO("\n".join(linhas).encode("utf-8")), filename=f"{canal.name}.txt")

        e = embed("📕 Ticket fechado", f"`{canal.name}` fechado por {interaction.user.mention}\nAberto por <@{dono_id}>", COR)
        await enviar_log(self.bot, interaction.guild, e, transcricao)

        await asyncio.sleep(5)
        await canal.delete(reason=f"Ticket fechado por {interaction.user}")


async def setup(bot):
    await bot.add_cog(Tickets(bot))
