import asyncio

import discord
from discord import app_commands
from discord.ext import commands

import imagens

SEM_MENCAO = discord.AllowedMentions.none()


def _separar(rotulo: str) -> tuple[str, str]:
    emoji, _, nome = rotulo.partition(" ")
    return emoji, nome


class SeletorEfeito(discord.ui.View):
    """Menu para escolher o efeito do GIF."""

    def __init__(self, cog, alvo: discord.abc.User):
        super().__init__(timeout=120)
        self.cog = cog
        self.alvo = alvo
        opcoes = []
        for chave, (rotulo, desc, _) in imagens.EFEITOS.items():
            emoji, nome = _separar(rotulo)
            opcoes.append(discord.SelectOption(label=nome, value=chave, emoji=emoji, description=desc))
        select = discord.ui.Select(placeholder="Escolha o efeito...", options=opcoes)
        select.callback = self.escolher
        self.add_item(select)

    async def escolher(self, interaction: discord.Interaction):
        efeito = interaction.data["values"][0]
        await interaction.response.edit_message(content="Gerando...", view=None)
        await self.cog.publicar_gif(interaction.channel, interaction.user, self.alvo, efeito)
        await interaction.edit_original_response(content="Enviado.")


class Gifs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.menu = app_commands.ContextMenu(name="Gerar GIF", callback=self.ctx_gif)
        bot.tree.add_command(self.menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.menu.name, type=self.menu.type)

    async def publicar_gif(self, canal, autor: discord.abc.User, alvo: discord.abc.User, efeito: str):
        avatar = await alvo.display_avatar.replace(size=imagens.TAM, format="png").read()
        buf = await asyncio.to_thread(imagens.gerar_gif, efeito, avatar)
        nome = _separar(imagens.EFEITOS[efeito][0])[1]
        texto = f"**{nome}** · {alvo.mention}" + (f" · por {autor.mention}" if autor.id != alvo.id else "")
        await canal.send(texto, file=discord.File(buf, filename=f"seubot_{efeito}.gif"), allowed_mentions=SEM_MENCAO)

    @app_commands.command(name="gif", description="Gera um GIF temático da SeuBot com o avatar de alguém")
    @app_commands.describe(membro="De quem será o GIF (padrão: você)", efeito="Deixe vazio para escolher num menu")
    @app_commands.choices(efeito=[
        app_commands.Choice(name=_separar(v[0])[1], value=k) for k, v in imagens.EFEITOS.items()
    ])
    async def gif(self, interaction: discord.Interaction, membro: discord.User = None, efeito: str = None):
        alvo = membro or interaction.user
        if not efeito:
            return await interaction.response.send_message(
                f"Efeito para **{alvo.display_name}**:", view=SeletorEfeito(self, alvo), ephemeral=True)
        await interaction.response.defer(thinking=True, ephemeral=True)
        await self.publicar_gif(interaction.channel, interaction.user, alvo, efeito)
        await interaction.followup.send("Enviado.", ephemeral=True)

    @app_commands.command(name="gifsecreto", description="Gera um GIF de runas sendo decifradas em uma frase")
    @app_commands.describe(texto=f"Até {imagens.LIMITE_TEXTO} letras e números (quebra em várias linhas)")
    async def gifsecreto(self, interaction: discord.Interaction, texto: app_commands.Range[str, 1, imagens.LIMITE_TEXTO]):
        await interaction.response.defer(thinking=True)
        buf = await asyncio.to_thread(imagens.gif_decifrando, texto)
        await interaction.followup.send(file=discord.File(buf, filename="seubot_decifrando.gif"))

    @app_commands.guild_only()
    async def ctx_gif(self, interaction: discord.Interaction, membro: discord.User):
        await interaction.response.send_message(
            f"Efeito para **{membro.display_name}**:", view=SeletorEfeito(self, membro), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Gifs(bot))
