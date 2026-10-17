import discord
from discord import app_commands
from discord.ext import commands

from utils import embed, COR_OK

TIPOS_CANAL = {
    "boas-vindas": "welcome_channel",
    "saida": "leave_channel",
    "logs": "log_channel",
    "sugestoes": "suggestion_channel",
}


@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
class Configuracao(commands.GroupCog, group_name="config", group_description="Configurações do bot no servidor"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="canal", description="Define um canal usado pelo bot")
    @app_commands.describe(tipo="Para que serve o canal", canal="Canal (deixe vazio para desativar)")
    @app_commands.choices(tipo=[app_commands.Choice(name=k, value=k) for k in TIPOS_CANAL])
    async def canal(self, interaction: discord.Interaction, tipo: str, canal: discord.TextChannel = None):
        self.bot.db.set_config(interaction.guild_id, TIPOS_CANAL[tipo], canal.id if canal else None)
        texto = f"Canal de **{tipo}** definido para {canal.mention}." if canal else f"Canal de **{tipo}** desativado."
        await interaction.response.send_message(embed=embed("Configuração salva", texto, COR_OK), ephemeral=True)

    @app_commands.command(name="mensagem", description="Mensagem de boas-vindas. Use {user}, {nome}, {server} e {count}")
    async def mensagem(self, interaction: discord.Interaction, texto: str):
        self.bot.db.set_config(interaction.guild_id, "welcome_message", texto)
        await interaction.response.send_message(
            embed=embed("Mensagem de boas-vindas salva", texto, COR_OK), ephemeral=True
        )

    @app_commands.command(name="autorole", description="Cargo dado automaticamente a quem entra")
    @app_commands.describe(cargo="Cargo (deixe vazio para desativar)")
    async def autorole(self, interaction: discord.Interaction, cargo: discord.Role = None):
        if cargo and cargo >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                "Esse cargo está acima do meu. Mova meu cargo para cima dele.", ephemeral=True
            )
        self.bot.db.set_config(interaction.guild_id, "autorole", cargo.id if cargo else None)
        texto = f"Autorole definido para {cargo.mention}." if cargo else "Autorole desativado."
        await interaction.response.send_message(embed=embed("Configuração salva", texto, COR_OK), ephemeral=True)

    @app_commands.command(name="tickets", description="Configura a categoria e o cargo da equipe dos tickets")
    async def tickets(self, interaction: discord.Interaction, categoria: discord.CategoryChannel, cargo_equipe: discord.Role):
        self.bot.db.set_config(interaction.guild_id, "ticket_category", categoria.id)
        self.bot.db.set_config(interaction.guild_id, "ticket_staff_role", cargo_equipe.id)
        await interaction.response.send_message(
            embed=embed("Tickets configurados", f"Categoria: **{categoria.name}**\nEquipe: {cargo_equipe.mention}", COR_OK),
            ephemeral=True,
        )

    @app_commands.command(name="ver", description="Mostra a configuração atual")
    async def ver(self, interaction: discord.Interaction):
        cfg = self.bot.db.get_config(interaction.guild_id)

        def canal(key):
            return f"<#{cfg[key]}>" if cfg.get(key) else "—"

        def cargo(key):
            return f"<@&{cfg[key]}>" if cfg.get(key) else "—"

        e = embed("Configuração do servidor")
        e.add_field(name="Boas-vindas", value=canal("welcome_channel"))
        e.add_field(name="Saída", value=canal("leave_channel"))
        e.add_field(name="Logs", value=canal("log_channel"))
        e.add_field(name="Sugestões", value=canal("suggestion_channel"))
        e.add_field(name="Autorole", value=cargo("autorole"))
        e.add_field(name="Categoria de tickets", value=canal("ticket_category"))
        e.add_field(name="Equipe de tickets", value=cargo("ticket_staff_role"))
        e.add_field(name="Mensagem de boas-vindas", value=cfg.get("welcome_message") or "Padrão", inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Configuracao(bot))
