import discord
from discord import app_commands
from discord.ext import commands

from utils import embed

PREFIXO = "geral:cargo:"


class Cargos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="painelcargos", description="Cria um painel de botões para os membros pegarem cargos")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    async def painelcargos(
        self,
        interaction: discord.Interaction,
        titulo: str,
        cargo1: discord.Role,
        cargo2: discord.Role = None,
        cargo3: discord.Role = None,
        cargo4: discord.Role = None,
        cargo5: discord.Role = None,
        descricao: str = "Clique nos botões para pegar ou remover um cargo.",
    ):
        cargos = [c for c in (cargo1, cargo2, cargo3, cargo4, cargo5) if c]
        altos = [c for c in cargos if c >= interaction.guild.me.top_role or c.managed]
        if altos:
            return await interaction.response.send_message(
                "Não consigo gerenciar: " + ", ".join(c.mention for c in altos) + ". Mova meu cargo para cima deles.",
                ephemeral=True,
            )

        view = discord.ui.View(timeout=None)
        for c in cargos:
            view.add_item(discord.ui.Button(label=c.name[:80], style=discord.ButtonStyle.secondary, custom_id=f"{PREFIXO}{c.id}"))

        lista = "\n".join(f"• {c.mention}" for c in cargos)
        await interaction.channel.send(embed=embed(titulo, f"{descricao}\n\n{lista}"), view=view)
        await interaction.response.send_message("Painel criado.", ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        cid = interaction.data.get("custom_id", "")
        if not cid.startswith(PREFIXO):
            return

        cargo = interaction.guild.get_role(int(cid.removeprefix(PREFIXO)))
        if not cargo:
            return await interaction.response.send_message("Esse cargo não existe mais.", ephemeral=True)
        try:
            if cargo in interaction.user.roles:
                await interaction.user.remove_roles(cargo, reason="Painel de cargos")
                await interaction.response.send_message(f"Cargo {cargo.mention} removido.", ephemeral=True)
            else:
                await interaction.user.add_roles(cargo, reason="Painel de cargos")
                await interaction.response.send_message(f"Cargo {cargo.mention} adicionado!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Não tenho permissão para gerenciar esse cargo.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Cargos(bot))
