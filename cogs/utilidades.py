import asyncio
import csv
import io

import discord
from discord import app_commands
from discord.ext import commands

from utils import embed, parse_duracao, formatar_duracao, COR, COR_OK

NUMEROS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

POR_PAGINA = 5


def embed_membro(m: discord.Member, posicao: int, db) -> discord.Embed:
    e = discord.Embed(
        title=f"{posicao}. {m.display_name}",
        description=f"{m.mention} • `@{m.name}`" + (" • 🤖 Bot" if m.bot else ""),
        color=m.color if m.color.value else COR,
    )
    e.set_thumbnail(url=m.display_avatar.url)
    e.add_field(name="🆔 ID", value=f"`{m.id}`")
    e.add_field(name="📅 Conta criada", value=discord.utils.format_dt(m.created_at, "d"))
    e.add_field(name="📥 Entrou", value=discord.utils.format_dt(m.joined_at, "R") if m.joined_at else "—")
    if m.premium_since:
        e.add_field(name="💎 Booster desde", value=discord.utils.format_dt(m.premium_since, "d"))
    if not m.bot:
        seubot = db.get_membro(m.guild.id, m.id)
        if seubot:
            e.add_field(name="🕯️ SeuBot", value=f"{seubot['codename']} `#{seubot['number']:03d}`")
    cargos = [r.mention for r in reversed(m.roles) if not r.is_default()]
    if cargos:
        extra = f" +{len(cargos) - 6}" if len(cargos) > 6 else ""
        e.add_field(name=f"🎭 Cargos ({len(cargos)})", value=" ".join(cargos[:6]) + extra, inline=False)
    return e


class ListaMembros(discord.ui.View):
    def __init__(self, membros: list[discord.Member], db, titulo: str):
        super().__init__(timeout=600)
        self.membros = membros
        self.db = db
        self.titulo = titulo
        self.pagina = 0
        self.total_paginas = max(1, -(-len(membros) // POR_PAGINA))
        self.atualizar_botoes()

    def embeds(self) -> list[discord.Embed]:
        ini = self.pagina * POR_PAGINA
        lista = [embed_membro(m, ini + i + 1, self.db) for i, m in enumerate(self.membros[ini:ini + POR_PAGINA])]
        if lista:
            lista[-1].set_footer(text=f"{self.titulo} • Página {self.pagina + 1}/{self.total_paginas} • {len(self.membros)} membros")
        return lista

    def atualizar_botoes(self):
        self.primeira.disabled = self.anterior.disabled = self.pagina == 0
        self.ultima.disabled = self.proxima.disabled = self.pagina >= self.total_paginas - 1
        self.contador.label = f"{self.pagina + 1}/{self.total_paginas}"

    async def mostrar(self, interaction: discord.Interaction):
        self.atualizar_botoes()
        await interaction.response.edit_message(embeds=self.embeds(), view=self)

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary)
    async def primeira(self, interaction: discord.Interaction, _):
        self.pagina = 0
        await self.mostrar(interaction)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.primary)
    async def anterior(self, interaction: discord.Interaction, _):
        self.pagina -= 1
        await self.mostrar(interaction)

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.secondary, disabled=True)
    async def contador(self, interaction: discord.Interaction, _):
        pass

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary)
    async def proxima(self, interaction: discord.Interaction, _):
        self.pagina += 1
        await self.mostrar(interaction)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def ultima(self, interaction: discord.Interaction, _):
        self.pagina = self.total_paginas - 1
        await self.mostrar(interaction)

    @discord.ui.button(label="Baixar planilha", emoji="📄", style=discord.ButtonStyle.success, row=1)
    async def baixar(self, interaction: discord.Interaction, _):
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow(["Nome", "Usuario", "ID", "Bot", "Conta criada", "Entrou no servidor", "Codinome SeuBot", "Cargos", "Avatar"])
        for m in self.membros:
            seubot = self.db.get_membro(m.guild.id, m.id)
            w.writerow([
                m.display_name, m.name, m.id, "Sim" if m.bot else "Não",
                m.created_at.strftime("%d/%m/%Y"),
                m.joined_at.strftime("%d/%m/%Y %H:%M") if m.joined_at else "",
                seubot["codename"] if seubot else "",
                ", ".join(r.name for r in reversed(m.roles) if not r.is_default()),
                m.display_avatar.url,
            ])
        dados = io.BytesIO(buf.getvalue().encode("utf-8-sig"))  # BOM para o Excel ler acentos
        await interaction.response.send_message("Lista completa (abre no Excel):",
                                                file=discord.File(dados, filename="membros.csv"), ephemeral=True)


# ------------------------------------------------------------------ /comandos (gerado automaticamente)

NOMES_MODULOS = {
    "SeuBot": ("🕯️", "Sociedade SeuBot"),
    "Gifs": ("🎞️", "GIFs"),
    "Historico": ("📜", "Histórico"),
    "Moderacao": ("🛡️", "Moderação"),
    "Configuracao": ("⚙️", "Configuração"),
    "Tickets": ("🎫", "Tickets"),
    "Cargos": ("🎭", "Cargos"),
    "Sorteios": ("🎉", "Sorteios"),
    "Utilidades": ("🔧", "Utilidades"),
}

AUTOMATICO = [
    ("👋 Boas-vindas e saída", "Envia uma mensagem quando alguém entra ou sai, e dá o cargo automático (`/config`)."),
    ("📋 Logs", "Registra mensagens apagadas e editadas, entradas e saídas, apelidos, cargos, canais e punições no canal de logs."),
    ("📜 Histórico", "Grava cada troca de nome de usuário, nome de exibição, apelido e avatar para consulta com `/historico`."),
    ("🎉 Sorteios", "Encerra os sorteios sozinho na hora marcada e anuncia os vencedores."),
    ("🔘 Botões permanentes", "Os painéis da SeuBot, tickets, cargos e sorteios continuam funcionando mesmo após o bot reiniciar."),
]

POR_PAGINA_CMD = 8


def _modulo_de(cmd) -> str:
    binding = getattr(cmd, "binding", None)
    if binding is None and isinstance(cmd, app_commands.Group):
        binding = next((c.binding for c in cmd.walk_commands() if getattr(c, "binding", None)), None)
    return type(binding).__name__ if binding else "Outros"


def _restrito(cmd) -> bool:
    for alvo in (cmd, cmd.root_parent):
        perms = getattr(alvo, "default_permissions", None)
        if perms and perms.value:
            return True
    return False


def _campo_comando(cmd) -> tuple[str, str]:
    nome = f"/{cmd.qualified_name}" + ("  🔒" if _restrito(cmd) else "")
    linhas = [cmd.description]
    for p in cmd.parameters:
        desc = "" if p.description in ("…", "...") else f" — {p.description}"
        opcional = "" if p.required else " *(opcional)*"
        linhas.append(f"› `{p.display_name}`{opcional}{desc}")
    return nome, "\n".join(linhas)[:1024]


def montar_categorias(bot) -> list[tuple[str, str, list[tuple[str, str]]]]:
    """Retorna [(emoji, nome, [(campo_nome, campo_valor), ...]), ...]"""
    grupos: dict[str, list] = {}
    for cmd in bot.tree.get_commands(type=discord.AppCommandType.chat_input):
        folhas = list(cmd.walk_commands()) if isinstance(cmd, app_commands.Group) else [cmd]
        grupos.setdefault(_modulo_de(cmd), []).extend(_campo_comando(c) for c in folhas)

    categorias = []
    for chave, (emoji, nome) in NOMES_MODULOS.items():
        if chave in grupos:
            categorias.append((emoji, nome, grupos.pop(chave)))
    for chave, campos in grupos.items():
        categorias.append(("📦", chave, campos))

    menus = []
    for tipo, alvo in ((discord.AppCommandType.user, "um usuário"), (discord.AppCommandType.message, "uma mensagem")):
        for m in bot.tree.get_commands(type=tipo):
            restrito = m.default_permissions and m.default_permissions.value
            menus.append((m.name + ("  🔒" if restrito else ""), f"Clique com o botão direito em {alvo} → **Apps** → **{m.name}**"))
    if menus:
        categorias.append(("🖱️", "Clique direito", menus))
    categorias.append(("⚡", "Automático", AUTOMATICO))
    return categorias


class MenuComandos(discord.ui.View):
    def __init__(self, categorias):
        super().__init__(timeout=600)
        self.categorias = categorias
        self.cat = 0
        self.pagina = 0
        self.total_cmds = sum(len(c[2]) for c in categorias if c[1] not in ("Automático", "Clique direito"))
        select = discord.ui.Select(
            placeholder="Escolha uma categoria...",
            options=[
                discord.SelectOption(label=nome, value=str(i), emoji=emoji, description=f"{len(campos)} itens")
                for i, (emoji, nome, campos) in enumerate(categorias)
            ][:25],
            row=0,
        )
        select.callback = self.trocar_categoria
        self.add_item(select)
        self.atualizar()

    def paginas(self) -> int:
        return max(1, -(-len(self.categorias[self.cat][2]) // POR_PAGINA_CMD))

    def tela(self) -> discord.Embed:
        emoji, nome, campos = self.categorias[self.cat]
        e = embed(f"{emoji} {nome}")
        ini = self.pagina * POR_PAGINA_CMD
        for n, v in campos[ini:ini + POR_PAGINA_CMD]:
            e.add_field(name=n, value=v, inline=False)
        e.set_footer(text=f"Categoria {self.cat + 1}/{len(self.categorias)} • Página {self.pagina + 1}/{self.paginas()} • 🔒 = só equipe")
        return e

    def atualizar(self):
        self.anterior.disabled = self.cat == 0 and self.pagina == 0
        self.proximo.disabled = self.cat == len(self.categorias) - 1 and self.pagina >= self.paginas() - 1

    async def mostrar(self, interaction: discord.Interaction):
        self.atualizar()
        await interaction.response.edit_message(embed=self.tela(), view=self)

    async def trocar_categoria(self, interaction: discord.Interaction):
        self.cat, self.pagina = int(interaction.data["values"][0]), 0
        await self.mostrar(interaction)

    @discord.ui.button(emoji="◀️", label="Anterior", style=discord.ButtonStyle.secondary, row=1)
    async def anterior(self, interaction: discord.Interaction, _):
        if self.pagina > 0:
            self.pagina -= 1
        else:
            self.cat -= 1
            self.pagina = self.paginas() - 1
        await self.mostrar(interaction)

    @discord.ui.button(emoji="▶️", label="Próximo", style=discord.ButtonStyle.secondary, row=1)
    async def proximo(self, interaction: discord.Interaction, _):
        if self.pagina < self.paginas() - 1:
            self.pagina += 1
        else:
            self.cat, self.pagina = self.cat + 1, 0
        await self.mostrar(interaction)


class Utilidades(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="comandos", description="Lista todos os comandos do bot e explica o que cada um faz")
    async def comandos(self, interaction: discord.Interaction):
        categorias = montar_categorias(self.bot)
        view = MenuComandos(categorias)
        capa = embed(
            "Comandos da SeuBot",
            f"O bot tem **{view.total_cmds} comandos**, separados em **{len(categorias)} categorias**.\n\n"
            + "\n".join(f"{e} **{n}** — {len(c)} itens" for e, n, c in categorias)
            + "\n\nUse o menu ou os botões para navegar.\n🔒 = só para quem tem permissão de equipe.",
        )
        await interaction.response.send_message(embed=capa, view=view, ephemeral=True)

    @app_commands.command(description="Mostra a latência do bot")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🏓 Pong! `{round(self.bot.latency * 1000)}ms`")

    @app_commands.command(description="Informações sobre um membro")
    @app_commands.guild_only()
    async def userinfo(self, interaction: discord.Interaction, membro: discord.Member = None):
        m = membro or interaction.user
        e = embed(str(m), cor=m.color if m.color.value else None)
        e.set_thumbnail(url=m.display_avatar.url)
        e.add_field(name="ID", value=m.id)
        e.add_field(name="Apelido", value=m.nick or "—")
        e.add_field(name="Bot", value="Sim" if m.bot else "Não")
        e.add_field(name="Conta criada", value=discord.utils.format_dt(m.created_at, "R"))
        e.add_field(name="Entrou no servidor", value=discord.utils.format_dt(m.joined_at, "R") if m.joined_at else "—")
        cargos = [r.mention for r in reversed(m.roles) if r != interaction.guild.default_role]
        e.add_field(name=f"Cargos ({len(cargos)})", value=" ".join(cargos[:20]) or "Nenhum", inline=False)
        await interaction.response.send_message(embed=e)

    @app_commands.command(description="Informações sobre o servidor")
    @app_commands.guild_only()
    async def serverinfo(self, interaction: discord.Interaction):
        g = interaction.guild
        e = embed(g.name, g.description)
        if g.icon:
            e.set_thumbnail(url=g.icon.url)
        e.add_field(name="Dono", value=f"<@{g.owner_id}>")
        e.add_field(name="Membros", value=g.member_count)
        e.add_field(name="Bots", value=sum(m.bot for m in g.members))
        e.add_field(name="Canais de texto", value=len(g.text_channels))
        e.add_field(name="Canais de voz", value=len(g.voice_channels))
        e.add_field(name="Cargos", value=len(g.roles))
        e.add_field(name="Boosts", value=f"{g.premium_subscription_count} (nível {g.premium_tier})")
        e.add_field(name="Criado", value=discord.utils.format_dt(g.created_at, "R"))
        await interaction.response.send_message(embed=e)

    @app_commands.command(description="Mostra o avatar de um usuário")
    async def avatar(self, interaction: discord.Interaction, usuario: discord.User = None):
        u = usuario or interaction.user
        e = embed(f"Avatar de {u.display_name}")
        e.set_image(url=u.display_avatar.with_size(1024).url)
        await interaction.response.send_message(embed=e)

    @app_commands.command(description="Lista os membros com foto e dados")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(ordem="Como ordenar a lista", mostrar="Quem mostrar", cargo="Mostrar só quem tem este cargo")
    @app_commands.choices(
        ordem=[
            app_commands.Choice(name="Entrada no servidor (mais antigos primeiro)", value="entrada"),
            app_commands.Choice(name="Entrada no servidor (mais novos primeiro)", value="recentes"),
            app_commands.Choice(name="Nome (A-Z)", value="nome"),
            app_commands.Choice(name="Idade da conta", value="conta"),
        ],
        mostrar=[
            app_commands.Choice(name="Só pessoas", value="humanos"),
            app_commands.Choice(name="Todos", value="todos"),
            app_commands.Choice(name="Só bots", value="bots"),
        ],
    )
    async def membros(self, interaction: discord.Interaction, ordem: str = "entrada", mostrar: str = "humanos",
                      cargo: discord.Role = None):
        lista = list(cargo.members if cargo else interaction.guild.members)
        if mostrar == "humanos":
            lista = [m for m in lista if not m.bot]
        elif mostrar == "bots":
            lista = [m for m in lista if m.bot]

        agora = discord.utils.utcnow()
        chaves = {
            "entrada": lambda m: m.joined_at or agora,
            "recentes": lambda m: m.joined_at or agora,
            "nome": lambda m: m.display_name.lower(),
            "conta": lambda m: m.created_at,
        }
        lista.sort(key=chaves[ordem], reverse=ordem == "recentes")

        if not lista:
            return await interaction.response.send_message("Nenhum membro encontrado com esses filtros.", ephemeral=True)

        titulo = f"Membros de {interaction.guild.name}" + (f" • {cargo.name}" if cargo else "")
        view = ListaMembros(lista, self.bot.db, titulo)
        await interaction.response.send_message(embeds=view.embeds(), view=view, ephemeral=True)

    @app_commands.command(description="Cria uma enquete. Separe as opções com ;")
    @app_commands.guild_only()
    @app_commands.describe(opcoes="Ex: Pizza; Hambúrguer; Sushi (deixe vazio para Sim/Não)")
    async def enquete(self, interaction: discord.Interaction, pergunta: str, opcoes: str = None):
        lista = [o.strip() for o in (opcoes or "").split(";") if o.strip()]
        if len(lista) > 10:
            return await interaction.response.send_message("No máximo 10 opções.", ephemeral=True)
        if len(lista) == 1:
            return await interaction.response.send_message("Coloque pelo menos 2 opções.", ephemeral=True)

        if lista:
            emojis = NUMEROS[: len(lista)]
            descricao = "\n".join(f"{emojis[i]} {o}" for i, o in enumerate(lista))
        else:
            emojis = ["👍", "👎"]
            descricao = "👍 Sim\n👎 Não"
        e = embed(f"📊 {pergunta}", descricao)
        e.set_footer(text=f"Enquete de {interaction.user.display_name}")
        await interaction.response.send_message(embed=e)
        msg = await interaction.original_response()
        for em in emojis:
            await msg.add_reaction(em)

    @app_commands.command(description="Envia uma sugestão para a equipe")
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 300)
    async def sugestao(self, interaction: discord.Interaction, texto: str):
        cfg = self.bot.db.get_config(interaction.guild_id)
        canal = interaction.guild.get_channel(cfg.get("suggestion_channel") or 0)
        if not canal:
            return await interaction.response.send_message("O canal de sugestões não foi configurado.", ephemeral=True)
        e = embed("💡 Nova sugestão", texto)
        e.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        msg = await canal.send(embed=e)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await interaction.response.send_message(f"Sugestão enviada em {canal.mention}!", ephemeral=True)

    @app_commands.command(description="Cria um lembrete (ex: 10m, 2h)")
    async def lembrete(self, interaction: discord.Interaction, tempo: str, texto: str):
        segundos = parse_duracao(tempo)
        if not segundos or segundos > 7 * 86400:
            return await interaction.response.send_message("Tempo inválido. Use algo como `10m`, `2h` (máx. 7d).", ephemeral=True)
        await interaction.response.send_message(f"⏰ Ok! Vou te lembrar em **{formatar_duracao(segundos)}**.", ephemeral=True)
        await asyncio.sleep(segundos)
        try:
            await interaction.user.send(f"⏰ Lembrete: {texto}")
        except discord.HTTPException:
            await interaction.channel.send(f"⏰ {interaction.user.mention}, lembrete: {texto}")

    @app_commands.command(description="Envia um anúncio em embed em um canal")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(mencionar="Mencionar @everyone?")
    async def anunciar(self, interaction: discord.Interaction, canal: discord.TextChannel, titulo: str, mensagem: str, mencionar: bool = False):
        e = embed(f"📢 {titulo}", mensagem.replace("\\n", "\n"), COR_OK)
        e.set_footer(text=f"Por {interaction.user.display_name}")
        await canal.send(
            content="@everyone" if mencionar else None,
            embed=e,
            allowed_mentions=discord.AllowedMentions(everyone=mencionar),
        )
        await interaction.response.send_message(f"Anúncio enviado em {canal.mention}.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Utilidades(bot))
