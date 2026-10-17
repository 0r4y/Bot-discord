import asyncio
import logging
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from utils import embed

log = logging.getLogger("seubot.historico")
PASTA_AVATARES = Path(__file__).parent.parent / "historico_avatares"
PASTA_AVATARES.mkdir(exist_ok=True)

TIPOS_NOME = [
    ("usuario", "👤 Nomes de usuário"),
    ("nome", "🏷️ Nomes de exibição"),
    ("apelido", "📝 Apelidos neste servidor"),
]


def chave_avatar(asset: discord.Asset | None) -> str | None:
    return asset.key if asset else None


def arquivo_avatar(user_id: int, chave: str) -> Path:
    return PASTA_AVATARES / f"{user_id}_{chave}.png"


class PainelHistorico(discord.ui.View):
    def __init__(self, alvo: discord.abc.User, registros: list[dict], guild: discord.Guild):
        super().__init__(timeout=600)
        self.alvo = alvo
        self.guild = guild
        self.registros = registros
        self.avatares = [r for r in registros if r["tipo"] in ("avatar", "avatar_servidor")][::-1]  # mais novo primeiro
        self.indice = 0
        self.modo = "nomes"
        self.atualizar_botoes()

    # ---------- telas ----------
    def tela_nomes(self) -> discord.Embed:
        a = self.alvo
        e = embed(f"📜 Histórico de {a.display_name}", f"{a.mention} • `{a.id}`")
        e.set_thumbnail(url=a.display_avatar.url)
        e.add_field(name="📅 Conta criada", value=discord.utils.format_dt(a.created_at, "D"))
        membro = self.guild.get_member(a.id)
        if membro and membro.joined_at:
            e.add_field(name="📥 Entrou no servidor", value=discord.utils.format_dt(membro.joined_at, "D"))
        e.add_field(name="🖼️ Avatares registrados", value=str(len(self.avatares)))

        for tipo, titulo in TIPOS_NOME:
            itens = [r for r in self.registros if r["tipo"] == tipo][::-1]
            if not itens:
                continue
            linhas = []
            for i, r in enumerate(itens[:15]):
                valor = discord.utils.escape_markdown(r["valor"]) if r["valor"] else "*(removido)*"
                atual = " ← atual" if i == 0 else ""
                linhas.append(f"{valor} — <t:{r['created_at']}:d>{atual}")
            extra = f"\n*…e mais {len(itens) - 15}*" if len(itens) > 15 else ""
            e.add_field(name=f"{titulo} ({len(itens)})", value="\n".join(linhas) + extra, inline=False)

        primeiro = min((r["created_at"] for r in self.registros), default=None)
        if primeiro:
            e.add_field(name="🔎 Monitorado desde", value=f"<t:{primeiro}:f>", inline=False)
        e.set_footer(text="O bot só registra mudanças feitas enquanto está no servidor")
        return e

    def tela_avatar(self) -> tuple[discord.Embed, discord.File | None]:
        r = self.avatares[self.indice]
        local = "neste servidor" if r["tipo"] == "avatar_servidor" else "global"
        e = embed(f"🖼️ Avatar {self.indice + 1}/{len(self.avatares)} de {self.alvo.display_name}",
                  f"Avatar {local} • usado a partir de <t:{r['created_at']}:f>" + (" • **atual**" if self.indice == 0 else ""))
        caminho = arquivo_avatar(self.alvo.id, r["valor"])
        if caminho.exists():
            e.set_image(url="attachment://avatar.png")
            return e, discord.File(caminho, filename="avatar.png")
        e.description += "\n\n*A imagem deste avatar não pôde ser salva.*"
        return e, None

    # ---------- navegação ----------
    def atualizar_botoes(self):
        em_avatar = self.modo == "avatares"
        self.anterior.disabled = not em_avatar or self.indice == 0
        self.proximo.disabled = not em_avatar or self.indice >= len(self.avatares) - 1
        self.btn_nomes.style = discord.ButtonStyle.primary if not em_avatar else discord.ButtonStyle.secondary
        self.btn_avatares.style = discord.ButtonStyle.primary if em_avatar else discord.ButtonStyle.secondary
        self.btn_avatares.disabled = not self.avatares

    async def mostrar(self, interaction: discord.Interaction):
        self.atualizar_botoes()
        if self.modo == "nomes":
            await interaction.response.edit_message(embed=self.tela_nomes(), attachments=[], view=self)
        else:
            e, arquivo = self.tela_avatar()
            await interaction.response.edit_message(embed=e, attachments=[arquivo] if arquivo else [], view=self)

    @discord.ui.button(label="Nomes", emoji="📛")
    async def btn_nomes(self, interaction: discord.Interaction, _):
        self.modo = "nomes"
        await self.mostrar(interaction)

    @discord.ui.button(label="Avatares", emoji="🖼️")
    async def btn_avatares(self, interaction: discord.Interaction, _):
        self.modo, self.indice = "avatares", 0
        await self.mostrar(interaction)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def anterior(self, interaction: discord.Interaction, _):
        self.indice -= 1
        await self.mostrar(interaction)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def proximo(self, interaction: discord.Interaction, _):
        self.indice += 1
        await self.mostrar(interaction)


class Historico(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.menu = app_commands.ContextMenu(name="Histórico", callback=self.ctx_historico)
        bot.tree.add_command(self.menu)
        self._baseline_feito = False

    async def cog_unload(self):
        self.bot.tree.remove_command(self.menu.name, type=self.menu.type)

    # ---------- registro ----------
    async def salvar_avatar(self, user_id: int, asset: discord.Asset | None):
        if not asset:
            return
        caminho = arquivo_avatar(user_id, asset.key)
        if caminho.exists():
            return
        try:
            dados = await asset.replace(size=256, format="png").read()
            await asyncio.to_thread(caminho.write_bytes, dados)
        except discord.HTTPException as e:
            log.debug("Não foi possível salvar avatar %s de %s: %s", asset.key, user_id, e)

    async def registrar_usuario(self, user: discord.abc.User, baixar: bool = True):
        db = self.bot.db
        db.add_historico(user.id, "usuario", user.name)
        db.add_historico(user.id, "nome", user.global_name)
        if user.avatar and db.add_historico(user.id, "avatar", user.avatar.key) and baixar:
            await self.salvar_avatar(user.id, user.avatar)

    async def registrar_membro(self, m: discord.Member, baixar: bool = True):
        await self.registrar_usuario(m, baixar)
        db = self.bot.db
        if m.nick or db.ultimo_historico(m.id, "apelido", m.guild.id) is not None:
            db.add_historico(m.id, "apelido", m.nick or "", m.guild.id)
        if m.guild_avatar and db.add_historico(m.id, "avatar_servidor", m.guild_avatar.key, m.guild.id) and baixar:
            await self.salvar_avatar(m.id, m.guild_avatar)

    @commands.Cog.listener()
    async def on_ready(self):
        if self._baseline_feito:
            return
        self._baseline_feito = True
        # Registra o estado atual de todos (nomes na hora; avatares baixados aos poucos)
        for guild in self.bot.guilds:
            for m in guild.members:
                await self.registrar_membro(m, baixar=False)
        total = 0
        for guild in self.bot.guilds:
            for m in guild.members:
                if m.avatar and not arquivo_avatar(m.id, m.avatar.key).exists():
                    await self.salvar_avatar(m.id, m.avatar)
                    total += 1
                    await asyncio.sleep(0.25)
                if m.guild_avatar and not arquivo_avatar(m.id, m.guild_avatar.key).exists():
                    await self.salvar_avatar(m.id, m.guild_avatar)
                    await asyncio.sleep(0.25)
        log.info("Histórico: estado inicial registrado (%d avatares baixados)", total)

    @commands.Cog.listener()
    async def on_user_update(self, antes: discord.User, depois: discord.User):
        # Garante que o avatar antigo esteja salvo antes de registrar o novo
        if antes.avatar and antes.avatar != depois.avatar:
            await self.salvar_avatar(antes.id, antes.avatar)
        await self.registrar_usuario(depois)

    @commands.Cog.listener()
    async def on_member_update(self, antes: discord.Member, depois: discord.Member):
        if antes.nick != depois.nick or antes.guild_avatar != depois.guild_avatar:
            if antes.guild_avatar and antes.guild_avatar != depois.guild_avatar:
                await self.salvar_avatar(antes.id, antes.guild_avatar)
            await self.registrar_membro(depois)

    @commands.Cog.listener()
    async def on_member_join(self, membro: discord.Member):
        await self.registrar_membro(membro)

    # ---------- comandos ----------
    async def mostrar(self, interaction: discord.Interaction, alvo: discord.abc.User):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if isinstance(alvo, discord.Member):
            await self.registrar_membro(alvo)
        else:
            await self.registrar_usuario(alvo)
        registros = self.bot.db.get_historico(alvo.id, interaction.guild_id)
        view = PainelHistorico(alvo, registros, interaction.guild)
        await interaction.followup.send(embed=view.tela_nomes(), view=view, ephemeral=True)

    @app_commands.command(name="historico", description="Nomes, apelidos e avatares antigos de um usuário")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    async def historico(self, interaction: discord.Interaction, usuario: discord.User):
        alvo = interaction.guild.get_member(usuario.id) or usuario
        await self.mostrar(interaction, alvo)

    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    async def ctx_historico(self, interaction: discord.Interaction, usuario: discord.User):
        alvo = interaction.guild.get_member(usuario.id) or usuario
        await self.mostrar(interaction, alvo)


async def setup(bot):
    await bot.add_cog(Historico(bot))
