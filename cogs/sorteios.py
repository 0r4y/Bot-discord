import random
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils import embed, parse_duracao, COR_OK

ID_PARTICIPAR = "geral:sorteio:participar"


def view_participar(total: int = 0) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label=f"Participar ({total})", style=discord.ButtonStyle.secondary, custom_id=ID_PARTICIPAR))
    return view


def embed_sorteio(g: dict) -> discord.Embed:
    e = embed("Sorteio", f"**{g['prize']}**")
    e.add_field(name="Termina", value=f"<t:{g['end_at']}:R>")
    e.add_field(name="Vencedores", value=str(g["winners"]))
    e.add_field(name="Organizado por", value=f"<@{g['host_id']}>")
    return e


class Sorteios(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.verificar.start()

    def cog_unload(self):
        self.verificar.cancel()

    sorteio = app_commands.Group(
        name="sorteio",
        description="Criar e gerenciar sorteios",
        guild_only=True,
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @sorteio.command(name="criar", description="Cria um sorteio neste canal")
    @app_commands.describe(duracao="Ex: 30m, 2h, 1d", vencedores="Número de vencedores")
    async def criar(self, interaction: discord.Interaction, premio: str, duracao: str, vencedores: app_commands.Range[int, 1, 20] = 1):
        segundos = parse_duracao(duracao)
        if not segundos:
            return await interaction.response.send_message("Duração inválida. Use algo como `30m`, `2h`, `1d`.", ephemeral=True)
        g = {"prize": premio, "end_at": int(time.time()) + segundos, "winners": vencedores, "host_id": interaction.user.id}
        await interaction.response.send_message("Sorteio criado!", ephemeral=True)
        msg = await interaction.channel.send(embed=embed_sorteio(g), view=view_participar())
        self.bot.db.add_giveaway(msg.id, msg.channel.id, interaction.guild_id, interaction.user.id, premio, vencedores, g["end_at"])

    @sorteio.command(name="encerrar", description="Encerra um sorteio agora")
    async def encerrar(self, interaction: discord.Interaction, mensagem_id: str):
        g = self.bot.db.get_giveaway(int(mensagem_id)) if mensagem_id.isdigit() else None
        if not g or g["ended"]:
            return await interaction.response.send_message("Sorteio não encontrado ou já encerrado.", ephemeral=True)
        await interaction.response.send_message("Encerrando...", ephemeral=True)
        await self.finalizar(g)

    @sorteio.command(name="resortear", description="Sorteia novos vencedores de um sorteio encerrado")
    async def resortear(self, interaction: discord.Interaction, mensagem_id: str):
        g = self.bot.db.get_giveaway(int(mensagem_id)) if mensagem_id.isdigit() else None
        if not g or not g["ended"]:
            return await interaction.response.send_message("Sorteio não encontrado ou ainda ativo.", ephemeral=True)
        participantes = self.bot.db.get_entries(g["message_id"])
        if not participantes:
            return await interaction.response.send_message("Ninguém participou desse sorteio.", ephemeral=True)
        ganhadores = random.sample(participantes, min(g["winners"], len(participantes)))
        await interaction.response.send_message(
            f"Novo sorteio de **{g['prize']}**. Vencedores: " + ", ".join(f"<@{u}>" for u in ganhadores)
        )

    @tasks.loop(seconds=15)
    async def verificar(self):
        for g in self.bot.db.due_giveaways():
            await self.finalizar(g)

    @verificar.before_loop
    async def antes(self):
        await self.bot.wait_until_ready()

    async def finalizar(self, g: dict):
        self.bot.db.end_giveaway(g["message_id"])
        canal = self.bot.get_channel(g["channel_id"])
        if not canal:
            return
        participantes = self.bot.db.get_entries(g["message_id"])
        ganhadores = random.sample(participantes, min(g["winners"], len(participantes)))

        e = embed("Sorteio encerrado", f"**{g['prize']}**")
        e.add_field(name="Vencedores", value=", ".join(f"<@{u}>" for u in ganhadores) or "Sem participantes")
        e.add_field(name="Participantes", value=str(len(participantes)))
        try:
            msg = await canal.fetch_message(g["message_id"])
            await msg.edit(embed=e, view=None)
        except discord.HTTPException:
            msg = None

        if ganhadores:
            texto = f"Vencedores de **{g['prize']}**: {', '.join(f'<@{u}>' for u in ganhadores)}"
        else:
            texto = f"O sorteio de **{g['prize']}** terminou sem participantes."
        await canal.send(texto, reference=msg if msg else None)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component or interaction.data.get("custom_id") != ID_PARTICIPAR:
            return
        g = self.bot.db.get_giveaway(interaction.message.id)
        if not g or g["ended"]:
            return await interaction.response.send_message("Esse sorteio já terminou.", ephemeral=True)
        entrou = self.bot.db.toggle_entry(g["message_id"], interaction.user.id)
        total = len(self.bot.db.get_entries(g["message_id"]))
        await interaction.response.edit_message(view=view_participar(total))
        await interaction.followup.send(
            "Participação registrada." if entrou else "Participação removida.", ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Sorteios(bot))
