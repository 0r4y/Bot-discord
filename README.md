<div align="center">

# 🕯️ SeuBot

**Bot de comunidade completo para Discord, com um toque de sociedade secreta.**

Moderação, tickets, sorteios, logs, boas-vindas, histórico de usuários
e imagens/GIFs gerados na hora — tudo com comandos `/`.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/discord.py-2.4+-5865F2?logo=discord&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-local-003B57?logo=sqlite&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-imagens-8A2BE2)
![License](https://img.shields.io/badge/licen%C3%A7a-MIT-D4AF37)

*Veritas in umbra.*

</div>

---

## 📌 Sobre

O **SeuBot** junta num só lugar as ferramentas que um servidor de Discord costuma precisar
— moderação, tickets, logs, sorteios, boas-vindas — e adiciona uma camada de diversão:
uma **sociedade secreta** com iniciação, credenciais personalizadas, mensagens cifradas em
runas, sussurros anônimos e GIFs temáticos feitos a partir do avatar dos membros.

Ele foi feito em **Python** com **discord.py 2**, guarda tudo num banco **SQLite** local
(sem precisar configurar servidor de banco de dados) e é dividido em módulos (`cogs`),
então é fácil ligar, desligar ou criar novas funções.

### Destaques

- ⚡ **100% comandos `/`** e menus de clique direito — nada de decorar prefixo
- 🔘 **Botões permanentes** — painéis de tickets, cargos, sorteios e da sociedade continuam funcionando mesmo depois de reiniciar o bot
- 🎨 **Imagens geradas na hora** — credenciais de membro e GIFs animados com Pillow
- 🗃️ **Zero configuração de banco** — o `dados.db` é criado sozinho na primeira execução
- 🛠️ **Configurável por servidor** — cada servidor tem seus próprios canais, cargos e mensagens

## ✨ Funcionalidades

| Módulo | O que faz |
|---|---|
| 🕯️ **Sociedade secreta** | Painel com botões de iniciação, credencial de membro (imagem gerada), irmandade, mensagens cifradas em runas e sussurros anônimos |
| 🎞️ **GIFs** | GIFs temáticos com o avatar de alguém e runas sendo decifradas em uma frase |
| 🔎 **Histórico** | Registra nomes, apelidos e avatares antigos dos membros |
| 🛡️ **Moderação** | Ban, kick, mute, advertências, limpeza de mensagens, slowmode e trancar canal |
| 👋 **Boas-vindas** | Mensagens de entrada/saída personalizáveis e cargo automático |
| 📜 **Logs** | Mensagens apagadas/editadas, entradas, saídas, apelidos e cargos |
| 🎫 **Tickets** | Painel de suporte com canais privados e transcrição |
| 🏷️ **Cargos** | Painel de botões para membros pegarem cargos |
| 🎉 **Sorteios** | Criar, encerrar e resortear |
| 🧰 **Utilidades** | Enquete, sugestão, lembrete, anúncio, userinfo, serverinfo e lista de membros (com exportação CSV) |

## 🚀 Instalação

**Requisitos:** Python 3.10 ou mais novo e uma aplicação criada no
[Discord Developer Portal](https://discord.com/developers/applications).

```bash
git clone https://github.com/0r4y/Bot-discord.git
cd Bot-discord
pip install -r requirements.txt
```

### 1. Configure o token

Copie `.env.example` para `.env` e preencha:

```env
DISCORD_TOKEN=seu_token_aqui
GUILD_ID=id_do_servidor   # opcional: faz os comandos aparecerem na hora nesse servidor
```

> ⚠️ **Nunca compartilhe o seu `.env`.** Ele já está no `.gitignore`. Se o token vazar,
> gere outro em *Developer Portal → Bot → Reset Token*.

### 2. Ative as intents

No Developer Portal → **Bot**, ative:
- **Server Members Intent**
- **Message Content Intent**

### 3. Convide o bot

Em **OAuth2 → URL Generator**, marque os escopos `bot` e `applications.commands` e a
permissão **Administrator** (ou só as que você for usar). Abra o link gerado e escolha o servidor.

### 4. Inicie

```bash
python bot.py
```

No Windows também dá para dar dois cliques em `iniciar.bat`.

## ⚙️ Primeiros passos no servidor

| Comando | Para quê |
|---|---|
| `/config canal` | Define canais de boas-vindas, saída, logs e sugestões |
| `/config mensagem` | Texto de boas-vindas — aceita `{user}`, `{nome}`, `{server}`, `{count}` |
| `/config autorole` | Cargo dado automaticamente a quem entra |
| `/config tickets` | Categoria e cargo da equipe; depois use `/ticket painel` |
| `/seubot configurar` | Canal de pedidos, canal de sussurros e cargo da irmandade |
| `/seubot painel` | Envia o painel da sociedade no canal |
| `/config ver` | Mostra a configuração atual |

## 📖 Comandos

<details>
<summary><b>🕯️ Sociedade secreta</b></summary>

`/seubot painel` · `/seubot configurar` · `/seubot credencial` · `/seubot recrutar` · `/seubot expulsar` ·
`/seubot cifrar` · `/seubot sussurro` · `/seubot irmandade` · menu **Credencial SeuBot**
</details>

<details>
<summary><b>🎞️ GIFs e histórico</b></summary>

`/gif` · `/gifsecreto` · `/historico` · menus **Gerar GIF** e **Histórico**
</details>

<details>
<summary><b>🛡️ Moderação</b></summary>

`/ban` · `/unban` · `/kick` · `/mute` · `/unmute` · `/limpar` · `/warn` · `/warns` ·
`/unwarn` · `/limparwarns` · `/slowmode` · `/trancar` · `/destrancar`
</details>

<details>
<summary><b>🎫 Tickets, cargos e sorteios</b></summary>

`/ticket painel` · `/ticket adicionar` · `/ticket remover` · `/painelcargos` ·
`/sorteio criar` · `/sorteio encerrar` · `/sorteio resortear`
</details>

<details>
<summary><b>🧰 Utilidades</b></summary>

`/comandos` · `/ping` · `/userinfo` · `/serverinfo` · `/avatar` · `/membros` ·
`/enquete` · `/sugestao` · `/lembrete` · `/anunciar`
</details>

Dentro do Discord, `/comandos` mostra a lista completa com explicações.

## 🗂️ Estrutura

```
├── bot.py            # ponto de entrada: carrega os módulos e sincroniza os comandos
├── database.py       # camada SQLite (dados.db)
├── imagens.py        # geração de GIFs e credenciais com Pillow
├── utils.py          # embeds, cores e helpers de duração
├── iniciar.bat       # atalho para rodar no Windows
└── cogs/             # um arquivo por módulo
    ├── seubot.py  gifs.py  historico.py  moderacao.py  boasvindas.py
    └── logs.py  tickets.py  cargos.py  sorteios.py  configuracao.py  utilidades.py
```

## 🎨 Personalizando

- **Cor dos embeds:** `COR` em `utils.py` (padrão: dourado).
- **Status do bot:** `change_presence` em `bot.py`.
- **Desligar um módulo:** remova o nome dele da lista `COGS` em `bot.py`.
- **Criar um módulo novo:** crie `cogs/meu_modulo.py` com uma função `async def setup(bot)` e adicione `"meu_modulo"` em `COGS`.

## 📄 Licença

Distribuído sob a licença [MIT](LICENSE) — use, modifique e compartilhe à vontade.
