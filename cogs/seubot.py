import asyncio
import random
import unicodedata

import discord
from discord import app_commands
from discord.ext import commands

import imagens
from utils import embed, enviar_log, COR_OK, COR_ERRO

P = "seubot:"  # prefixo dos botões persistentes
SOMBRA = discord.Color.from_rgb(20, 16, 28)

ANIMAIS = ["Corvo", "Lobo", "Serpente", "Coruja", "Raposa", "Falcão", "Escorpião", "Pantera",
           "Mariposa", "Víbora", "Fênix", "Lince", "Aranha", "Morcego", "Chacal", "Gato"]
ORIGENS = ["de Cinzas", "de Prata", "de Ônix", "da Meia-Noite", "do Eclipse", "das Sombras",
           "de Obsidiana", "do Véu", "da Névoa", "de Ferro", "do Abismo", "da Lua Negra"]

# Cifra: Vigenère sobre as letras + troca por runas
CHAVE = "SOCIEDADE"
RUNAS = imagens.RUNAS


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def cifrar(texto: str) -> str:
    saida, k = [], 0
    for c in _sem_acento(texto).upper():
        if "A" <= c <= "Z":
            desloc = ord(CHAVE[k % len(CHAVE)]) - 65
            saida.append(RUNAS[(ord(c) - 65 + desloc) % 26])
            k += 1
        else:
            saida.append(c)
    return "".join(saida)


def decifrar(texto: str) -> str:
    saida, k = [], 0
    for c in texto:
        if c in RUNAS:
            desloc = ord(CHAVE[k % len(CHAVE)]) - 65
            saida.append(chr((RUNAS.index(c) - desloc) % 26 + 65))
            k += 1
        else:
            saida.append(c)
    return "".join(saida)


# ------------------------------------------------------------------ Componentes

class PainelSeuBot(discord.ui.View):
    """Painel principal. Os botões são tratados no on_interaction do cog (funcionam após reiniciar)."""

    def __init__(self):
        super().__init__(timeout=None)
        botoes = [
            ("Solicitar iniciação", discord.ButtonStyle.secondary, "iniciar", 0),
            ("Credencial", discord.ButtonStyle.secondary, "credencial", 0),
            ("Irmandade", discord.ButtonStyle.secondary, "membros", 0),
            ("Mensagem cifrada", discord.ButtonStyle.secondary, "cifrar", 1),
            ("Sussurro anônimo", discord.ButtonStyle.secondary, "sussurro", 1),
        ]
        for label, estilo, acao, linha in botoes:
            self.add_item(discord.ui.Button(label=label, style=estilo, custom_id=P + acao, row=linha))


class ModalIniciacao(discord.ui.Modal, title="Solicitação de iniciação"):
    motivo = discord.ui.TextInput(label="Por que deseja entrar?", style=discord.TextStyle.paragraph, max_length=500)
    contribuir = discord.ui.TextInput(label="O que oferece à sociedade?", style=discord.TextStyle.paragraph,
                                      max_length=500, required=False)
    indicacao = discord.ui.TextInput(label="Quem o indicou? (opcional)", max_length=100, required=False)

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        cfg = self.cog.bot.db.get_config(interaction.guild_id)
        canal = interaction.guild.get_channel(cfg.get("seubot_request_channel") or 0)
        if not canal:
            return await interaction.response.send_message("As solicitações estão fechadas no momento.", ephemeral=True)

        e = embed("Solicitação de iniciação", f"{interaction.user.mention} (`{interaction.user}`)", SOMBRA)
        e.set_thumbnail(url=interaction.user.display_avatar.url)
        e.add_field(name="Motivo", value=self.motivo.value, inline=False)
        if self.contribuir.value:
            e.add_field(name="O que oferece", value=self.contribuir.value, inline=False)
        if self.indicacao.value:
            e.add_field(name="Indicação", value=self.indicacao.value, inline=False)
        e.add_field(name="Conta criada", value=discord.utils.format_dt(interaction.user.created_at, "D"))
        if interaction.user.joined_at:
            e.add_field(name="No servidor desde", value=discord.utils.format_dt(interaction.user.joined_at, "D"))

        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(label="Aceitar", style=discord.ButtonStyle.success, custom_id=f"{P}aceitar:{interaction.user.id}"))
        view.add_item(discord.ui.Button(label="Recusar", style=discord.ButtonStyle.danger, custom_id=f"{P}recusar:{interaction.user.id}"))
        await canal.send(embed=e, view=view)
        await interaction.response.send_message("Sua solicitação foi entregue ao conselho. Aguarde.", ephemeral=True)


class ModalCifrar(discord.ui.Modal, title="Mensagem cifrada"):
    texto = discord.ui.TextInput(label="Mensagem", style=discord.TextStyle.paragraph, max_length=1000)

    async def on_submit(self, interaction: discord.Interaction):
        await enviar_cifrada(interaction, self.texto.value)


class ModalSussurro(discord.ui.Modal, title="Sussurro anônimo"):
    texto = discord.ui.TextInput(label="Mensagem", style=discord.TextStyle.paragraph, max_length=1000)

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        cfg = self.cog.bot.db.get_config(interaction.guild_id)
        canal = interaction.guild.get_channel(cfg.get("seubot_whisper_channel") or 0) or interaction.channel
        e = embed("Sussurro", self.texto.value, SOMBRA)
        e.set_footer(text="Autor desconhecido")
        await canal.send(embed=e)
        await interaction.response.send_message(f"Deixado em {canal.mention}.", ephemeral=True)
        # A equipe pode ver o autor nos logs, para evitar abuso
        log = embed("Sussurro enviado", self.texto.value[:1000])
        log.add_field(name="Autor", value=interaction.user.mention)
        log.add_field(name="Canal", value=canal.mention)
        await enviar_log(self.cog.bot, interaction.guild, log)


class PaginasIrmandade(discord.ui.View):
    POR_PAGINA = 30

    def __init__(self, cargo: discord.Role, linhas: list[str]):
        super().__init__(timeout=300)
        self.cargo = cargo
        self.linhas = linhas
        self.pagina = 0
        self.total = max(1, -(-len(linhas) // self.POR_PAGINA))
        self.atualizar()

    def tela(self) -> discord.Embed:
        ini = self.pagina * self.POR_PAGINA
        e = embed("Irmandade da SeuBot", "\n".join(self.linhas[ini:ini + self.POR_PAGINA]), SOMBRA)
        rodape = f"{len(self.linhas)} membros com o cargo {self.cargo.name}"
        if self.total > 1:
            rodape += f" • Página {self.pagina + 1}/{self.total}"
        e.set_footer(text=rodape)
        return e

    def atualizar(self):
        self.anterior.disabled = self.pagina == 0
        self.proxima.disabled = self.pagina >= self.total - 1

    async def mudar(self, interaction: discord.Interaction, delta: int):
        self.pagina += delta
        self.atualizar()
        await interaction.response.edit_message(embed=self.tela(), view=self)

    @discord.ui.button(label="Anterior", style=discord.ButtonStyle.secondary)
    async def anterior(self, interaction: discord.Interaction, _):
        await self.mudar(interaction, -1)

    @discord.ui.button(label="Próxima", style=discord.ButtonStyle.secondary)
    async def proxima(self, interaction: discord.Interaction, _):
        await self.mudar(interaction, 1)


async def enviar_cifrada(interaction: discord.Interaction, texto: str):
    e = embed("Mensagem cifrada", cifrar(texto), SOMBRA)
    e.set_footer(text="Somente membros da SeuBot podem decifrar")
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Decifrar", style=discord.ButtonStyle.secondary, custom_id=P + "decifrar"))
    await interaction.channel.send(embed=e, view=view)
    await interaction.response.send_message("Mensagem enviada.", ephemeral=True)


# ------------------------------------------------------------------ Cog

@app_commands.guild_only()
class SeuBotCog(commands.GroupCog, group_name="seubot", group_description="Sociedade Secreta SeuBot"):
    def __init__(self, bot):
        self.bot = bot
        self.menu_credencial = app_commands.ContextMenu(name="Credencial SeuBot", callback=self.ctx_credencial)
        bot.tree.add_command(self.menu_credencial)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.menu_credencial.name, type=self.menu_credencial.type)

    # ---------- helpers ----------
    def membro(self, guild_id: int, user_id: int) -> dict | None:
        return self.bot.db.get_membro(guild_id, user_id)

    def gerar_codinome(self, guild_id: int) -> str:
        for _ in range(50):
            nome = f"{random.choice(ANIMAIS)} {random.choice(ORIGENS)}"
            if not self.bot.db.codinome_existe(guild_id, nome):
                return nome
        return f"{random.choice(ANIMAIS)} {random.randint(100, 999)}"

    async def admitir(self, guild: discord.Guild, alvo: discord.Member) -> dict:
        m = self.bot.db.add_membro(guild.id, alvo.id, self.gerar_codinome(guild.id))
        try:
            await alvo.send(embed=embed(
                "Sociedade Secreta SeuBot",
                f"Sua iniciação em **{guild.name}** foi aprovada.\n\n"
                f"Codinome: **{m['codename']}**\nRegistro: **#{m['number']:03d}**\n\n"
                "*O que é visto aqui, aqui permanece.*",
                SOMBRA,
            ))
        except discord.HTTPException:
            pass
        return m

    async def credencial_file(self, guild: discord.Guild, alvo: discord.Member) -> discord.File | None:
        m = self.membro(guild.id, alvo.id)
        if not m:
            return None
        avatar = await alvo.display_avatar.replace(size=256, format="png").read()
        buf = await asyncio.to_thread(
            imagens.carteirinha, avatar, alvo.name, m["codename"], m["number"], m["joined_at"], guild.name,
        )
        return discord.File(buf, filename="credencial_seubot.png")

    async def responder_credencial(self, interaction: discord.Interaction, alvo: discord.Member, ephemeral: bool):
        await interaction.response.defer(ephemeral=ephemeral, thinking=True)
        arquivo = await self.credencial_file(interaction.guild, alvo)
        if not arquivo:
            quem = "Você não é" if alvo == interaction.user else f"{alvo.mention} não é"
            return await interaction.followup.send(f"{quem} membro da SeuBot.", ephemeral=True)
        await interaction.followup.send(file=arquivo, ephemeral=ephemeral)

    def cargo_irmandade(self, guild: discord.Guild) -> discord.Role | None:
        """Cargo configurado em /seubot configurar ou, se não houver, o cargo chamado "seubot"."""
        cfg = self.bot.db.get_config(guild.id)
        return guild.get_role(cfg.get("seubot_role") or 0) or discord.utils.find(
            lambda r: r.name.strip().lower() == "seubot", guild.roles)

    def irmandade(self, guild: discord.Guild) -> tuple[discord.Embed, discord.ui.View | None]:
        cargo = self.cargo_irmandade(guild)
        if not cargo:
            return embed("Irmandade", "Cargo da SeuBot não encontrado. Defina em `/seubot configurar`.", COR_ERRO), None
        membros = sorted((m for m in cargo.members if not m.bot), key=lambda m: m.display_name.lower())
        if not membros:
            return embed("Irmandade", f"Ninguém tem o cargo {cargo.mention}.", SOMBRA), None
        linhas = []
        for m in membros:
            reg = self.membro(guild.id, m.id)
            linhas.append(f"{m.mention}" + (f" · *{reg['codename']}*" if reg else ""))
        view = PaginasIrmandade(cargo, linhas)
        return view.tela(), (view if view.total > 1 else None)

    # ---------- comandos ----------
    @app_commands.command(name="painel", description="Envia o painel da SeuBot neste canal")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def painel(self, interaction: discord.Interaction):
        e = embed(
            "SOCIEDADE SECRETA SEUBOT",
            "*O que é visto aqui, aqui permanece.*\n\n"
            "**Solicitar iniciação**: envie seu pedido ao conselho\n"
            "**Credencial**: sua identificação de membro\n"
            "**Irmandade**: todos os membros da SeuBot\n"
            "**Mensagem cifrada**: texto em runas, legível apenas por membros\n"
            "**Sussurro anônimo**: uma mensagem sem autor",
            SOMBRA,
        )
        await interaction.channel.send(embed=e, view=PainelSeuBot())
        await interaction.response.send_message("Painel enviado.", ephemeral=True)

    @app_commands.command(name="configurar", description="Define os canais da SeuBot e o cargo da irmandade")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(canal_pedidos="Onde chegam as solicitações de iniciação",
                           canal_sussurros="Onde aparecem os sussurros anônimos",
                           cargo_irmandade="Quem tem este cargo aparece na irmandade (padrão: cargo \"seubot\")")
    async def configurar(self, interaction: discord.Interaction,
                         canal_pedidos: discord.TextChannel = None, canal_sussurros: discord.TextChannel = None,
                         cargo_irmandade: discord.Role = None):
        db = self.bot.db
        if cargo_irmandade:
            db.set_config(interaction.guild_id, "seubot_role", cargo_irmandade.id)
        if canal_pedidos:
            db.set_config(interaction.guild_id, "seubot_request_channel", canal_pedidos.id)
        if canal_sussurros:
            db.set_config(interaction.guild_id, "seubot_whisper_channel", canal_sussurros.id)

        cfg = db.get_config(interaction.guild_id)
        e = embed("Configuração da SeuBot", cor=COR_OK)
        e.add_field(name="Canal de pedidos", value=f"<#{cfg['seubot_request_channel']}>" if cfg.get("seubot_request_channel") else "—")
        e.add_field(name="Canal de sussurros", value=f"<#{cfg['seubot_whisper_channel']}>" if cfg.get("seubot_whisper_channel") else "Canal atual")
        cargo = self.cargo_irmandade(interaction.guild)
        e.add_field(name="Cargo da irmandade", value=cargo.mention if cargo else "—")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="credencial", description="Mostra a credencial de membro da SeuBot")
    async def credencial(self, interaction: discord.Interaction, membro: discord.Member = None):
        await self.responder_credencial(interaction, membro or interaction.user, ephemeral=False)

    @app_commands.guild_only()
    async def ctx_credencial(self, interaction: discord.Interaction, membro: discord.Member):
        await self.responder_credencial(interaction, membro, ephemeral=False)

    @app_commands.command(name="recrutar", description="Admite alguém diretamente na SeuBot")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    async def recrutar(self, interaction: discord.Interaction, membro: discord.Member):
        if membro.bot:
            return await interaction.response.send_message("Bots não podem ser admitidos.", ephemeral=True)
        if self.membro(interaction.guild_id, membro.id):
            return await interaction.response.send_message(f"{membro.mention} já pertence à SeuBot.", ephemeral=True)
        m = await self.admitir(interaction.guild, membro)
        await interaction.response.send_message(embed=embed(
            "Admissão", f"{membro.mention} foi admitido como **{m['codename']}** (#{m['number']:03d}).", SOMBRA))

    @app_commands.command(name="expulsar", description="Remove alguém da SeuBot")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    async def expulsar(self, interaction: discord.Interaction, membro: discord.Member):
        if not self.bot.db.remove_membro(interaction.guild_id, membro.id):
            return await interaction.response.send_message(f"{membro.mention} não pertence à SeuBot.", ephemeral=True)
        await interaction.response.send_message(embed=embed("Expulsão", f"{membro.mention} não pertence mais à sociedade.", COR_ERRO))

    @app_commands.command(name="cifrar", description="Envia uma mensagem em runas que só membros conseguem ler")
    async def cmd_cifrar(self, interaction: discord.Interaction, mensagem: str):
        await enviar_cifrada(interaction, mensagem)

    @app_commands.command(name="sussurro", description="Deixa uma mensagem anônima")
    async def cmd_sussurro(self, interaction: discord.Interaction):
        await self.sussurro(interaction)

    @app_commands.command(name="irmandade", description="Lista todos os membros com o cargo da SeuBot")
    async def cmd_irmandade(self, interaction: discord.Interaction):
        e, view = self.irmandade(interaction.guild)
        await interaction.response.send_message(embed=e, **({"view": view} if view else {}))

    async def sussurro(self, interaction: discord.Interaction):
        if not self.membro(interaction.guild_id, interaction.user.id):
            return await interaction.response.send_message("Apenas membros da SeuBot.", ephemeral=True)
        await interaction.response.send_modal(ModalSussurro(self))

    # ---------- botões persistentes ----------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        cid = interaction.data.get("custom_id", "")
        if not cid.startswith(P):
            return
        acao, _, arg = cid.removeprefix(P).partition(":")

        if acao == "iniciar":
            if self.membro(interaction.guild_id, interaction.user.id):
                return await interaction.response.send_message("Você já pertence à SeuBot.", ephemeral=True)
            await interaction.response.send_modal(ModalIniciacao(self))
        elif acao == "credencial":
            await self.responder_credencial(interaction, interaction.user, ephemeral=True)
        elif acao == "cifrar":
            await interaction.response.send_modal(ModalCifrar())
        elif acao == "sussurro":
            await self.sussurro(interaction)
        elif acao == "membros":
            e, view = self.irmandade(interaction.guild)
            await interaction.response.send_message(embed=e, ephemeral=True, **({"view": view} if view else {}))
        elif acao == "decifrar":
            await self.botao_decifrar(interaction)
        elif acao in ("aceitar", "recusar"):
            await self.decidir_pedido(interaction, acao == "aceitar", int(arg))
        elif acao == "missao":  # botão de painéis antigos
            await interaction.response.send_message("Esta função foi descontinuada. Peça um novo painel à liderança.", ephemeral=True)

    async def botao_decifrar(self, interaction: discord.Interaction):
        pode = self.membro(interaction.guild_id, interaction.user.id) or interaction.user.guild_permissions.manage_guild
        if not pode:
            return await interaction.response.send_message("As runas não fazem sentido para você.", ephemeral=True)
        texto = interaction.message.embeds[0].description if interaction.message.embeds else ""
        await interaction.response.send_message(embed=embed("Mensagem decifrada", decifrar(texto), SOMBRA), ephemeral=True)

    async def decidir_pedido(self, interaction: discord.Interaction, aceitar: bool, user_id: int):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message("Apenas o conselho pode decidir.", ephemeral=True)
        alvo = interaction.guild.get_member(user_id)
        e = interaction.message.embeds[0] if interaction.message.embeds else embed("Solicitação de iniciação")

        if aceitar and alvo and not self.membro(interaction.guild_id, user_id):
            m = await self.admitir(interaction.guild, alvo)
            e.color = COR_OK
            e.add_field(name="Decisão", value=f"Aceito por {interaction.user.mention}\nCodinome: **{m['codename']}**", inline=False)
        elif aceitar and not alvo:
            e.color = COR_ERRO
            e.add_field(name="Decisão", value="O solicitante deixou o servidor.", inline=False)
        elif aceitar:
            e.add_field(name="Decisão", value="Já era membro.", inline=False)
        else:
            e.color = COR_ERRO
            e.add_field(name="Decisão", value=f"Recusado por {interaction.user.mention}", inline=False)
            if alvo:
                try:
                    await alvo.send(embed=embed("Sociedade Secreta SeuBot", f"Sua solicitação em **{interaction.guild.name}** não foi aceita.", SOMBRA))
                except discord.HTTPException:
                    pass
        await interaction.response.edit_message(embed=e, view=None)


async def setup(bot):
    await bot.add_cog(SeuBotCog(bot))
