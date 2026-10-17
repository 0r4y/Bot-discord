import os
import logging
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from database import Database

PASTA = Path(__file__).parent
load_dotenv(PASTA / ".env")

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

COGS = [
    "seubot",
    "gifs",
    "historico",
    "configuracao",
    "moderacao",
    "boasvindas",
    "logs",
    "tickets",
    "cargos",
    "sorteios",
    "utilidades",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(PASTA / "bot.log", encoding="utf-8")],
)
log = logging.getLogger("seubot")


class SeuBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True  # ative também "Message Content Intent" no portal
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.db = Database()

    async def setup_hook(self):
        for cog in COGS:
            await self.load_extension(f"cogs.{cog}")
            log.info("Módulo carregado: %s", cog)

        self.tree.on_error = self.on_app_command_error

        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
        else:
            synced = await self.tree.sync()
        log.info("%d comandos / sincronizados", len(synced))

    async def on_ready(self):
        log.info("Logado como %s (%s)", self.user, self.user.id)
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="em silêncio | /comandos")
        )

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "Você não tem permissão para usar este comando."
        elif isinstance(error, app_commands.BotMissingPermissions):
            msg = "Eu não tenho permissão suficiente para fazer isso: " + ", ".join(error.missing_permissions)
        elif isinstance(error, app_commands.CommandOnCooldown):
            msg = f"Calma! Tente de novo em {error.retry_after:.0f}s."
        elif isinstance(error, app_commands.CheckFailure):
            msg = "Você não pode usar este comando aqui."
        else:
            log.exception("Erro no comando %s", interaction.command, exc_info=error)
            msg = "Ocorreu um erro inesperado ao executar o comando."

        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN não encontrado no arquivo .env")
    SeuBot().run(TOKEN, log_handler=None)
