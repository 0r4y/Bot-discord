import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "dados.db"

# Colunas de configuração que podem ser alteradas pelos comandos /config
CONFIG_KEYS = {
    "welcome_channel",
    "welcome_message",
    "leave_channel",
    "log_channel",
    "autorole",
    "ticket_category",
    "ticket_staff_role",
    "level_channel",
    "suggestion_channel",
    "seubot_role",
    "seubot_request_channel",
    "seubot_whisper_channel",
}

# Colunas adicionadas depois da primeira versão (migração automática)
NOVAS_COLUNAS = ("seubot_role", "seubot_request_channel", "seubot_whisper_channel")


def xp_para_proximo(level: int) -> int:
    """XP necessário para sair do nível atual para o próximo."""
    return 5 * level ** 2 + 50 * level + 100


class Database:
    def __init__(self, path: Path = DB_PATH):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._setup()

    def _setup(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INTEGER PRIMARY KEY,
                welcome_channel INTEGER,
                welcome_message TEXT,
                leave_channel INTEGER,
                log_channel INTEGER,
                autorole INTEGER,
                ticket_category INTEGER,
                ticket_staff_role INTEGER,
                level_channel INTEGER,
                suggestion_channel INTEGER
            );
            CREATE TABLE IF NOT EXISTS levels (
                guild_id INTEGER,
                user_id INTEGER,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                total_xp INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS level_rewards (
                guild_id INTEGER,
                level INTEGER,
                role_id INTEGER,
                PRIMARY KEY (guild_id, level)
            );
            CREATE TABLE IF NOT EXISTS warns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                mod_id INTEGER,
                reason TEXT,
                created_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS giveaways (
                message_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                guild_id INTEGER,
                host_id INTEGER,
                prize TEXT,
                winners INTEGER,
                end_at INTEGER,
                ended INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS giveaway_entries (
                message_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (message_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS user_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                tipo TEXT,
                valor TEXT,
                created_at INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_hist_user ON user_history (user_id, tipo);
            CREATE TABLE IF NOT EXISTS seubot_members (
                guild_id INTEGER,
                user_id INTEGER,
                codename TEXT,
                number INTEGER,
                missions INTEGER DEFAULT 0,
                last_mission INTEGER DEFAULT 0,
                joined_at INTEGER,
                PRIMARY KEY (guild_id, user_id)
            );
            """
        )
        colunas_seubot = {r[1] for r in self.conn.execute("PRAGMA table_info(seubot_members)")}
        if "grau" not in colunas_seubot:
            self.conn.execute("ALTER TABLE seubot_members ADD COLUMN grau INTEGER DEFAULT 0")
        colunas = {r[1] for r in self.conn.execute("PRAGMA table_info(guild_config)")}
        for col in NOVAS_COLUNAS:
            if col not in colunas:
                self.conn.execute(f"ALTER TABLE guild_config ADD COLUMN {col} INTEGER")
        self.conn.commit()

    # ---------- Configuração ----------
    def get_config(self, guild_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)
        ).fetchone()
        return dict(row) if row else {}

    def set_config(self, guild_id: int, key: str, value):
        if key not in CONFIG_KEYS:
            raise ValueError(f"Chave inválida: {key}")
        self.conn.execute(
            "INSERT OR IGNORE INTO guild_config (guild_id) VALUES (?)", (guild_id,)
        )
        self.conn.execute(
            f"UPDATE guild_config SET {key} = ? WHERE guild_id = ?", (value, guild_id)
        )
        self.conn.commit()

    # ---------- Níveis ----------
    def get_level(self, guild_id: int, user_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM levels WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ).fetchone()
        if row:
            return dict(row)
        return {"guild_id": guild_id, "user_id": user_id, "xp": 0, "level": 0, "total_xp": 0}

    def add_xp(self, guild_id: int, user_id: int, amount: int) -> tuple[int, bool]:
        """Adiciona XP e retorna (nível atual, subiu_de_nivel)."""
        data = self.get_level(guild_id, user_id)
        xp = data["xp"] + amount
        level = data["level"]
        subiu = False
        while xp >= xp_para_proximo(level):
            xp -= xp_para_proximo(level)
            level += 1
            subiu = True
        self.conn.execute(
            """INSERT INTO levels (guild_id, user_id, xp, level, total_xp)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(guild_id, user_id)
               DO UPDATE SET xp = excluded.xp, level = excluded.level, total_xp = excluded.total_xp""",
            (guild_id, user_id, xp, level, data["total_xp"] + amount),
        )
        self.conn.commit()
        return level, subiu

    def get_rank_position(self, guild_id: int, user_id: int) -> int:
        data = self.get_level(guild_id, user_id)
        row = self.conn.execute(
            "SELECT COUNT(*) FROM levels WHERE guild_id = ? AND total_xp > ?",
            (guild_id, data["total_xp"]),
        ).fetchone()
        return row[0] + 1

    def top_levels(self, guild_id: int, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM levels WHERE guild_id = ? ORDER BY total_xp DESC LIMIT ?",
            (guild_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def set_reward(self, guild_id: int, level: int, role_id: int):
        self.conn.execute(
            "INSERT OR REPLACE INTO level_rewards (guild_id, level, role_id) VALUES (?, ?, ?)",
            (guild_id, level, role_id),
        )
        self.conn.commit()

    def remove_reward(self, guild_id: int, level: int) -> bool:
        cur = self.conn.execute(
            "DELETE FROM level_rewards WHERE guild_id = ? AND level = ?", (guild_id, level)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def get_rewards(self, guild_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM level_rewards WHERE guild_id = ? ORDER BY level", (guild_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ---------- Advertências ----------
    def add_warn(self, guild_id: int, user_id: int, mod_id: int, reason: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO warns (guild_id, user_id, mod_id, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, mod_id, reason, int(time.time())),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_warns(self, guild_id: int, user_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM warns WHERE guild_id = ? AND user_id = ? ORDER BY id",
            (guild_id, user_id),
        ).fetchall()
        return [dict(r) for r in rows]

    def remove_warn(self, guild_id: int, warn_id: int) -> bool:
        cur = self.conn.execute(
            "DELETE FROM warns WHERE guild_id = ? AND id = ?", (guild_id, warn_id)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def clear_warns(self, guild_id: int, user_id: int) -> int:
        cur = self.conn.execute(
            "DELETE FROM warns WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        )
        self.conn.commit()
        return cur.rowcount

    # ---------- Sorteios ----------
    def add_giveaway(self, message_id, channel_id, guild_id, host_id, prize, winners, end_at):
        self.conn.execute(
            """INSERT INTO giveaways (message_id, channel_id, guild_id, host_id, prize, winners, end_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (message_id, channel_id, guild_id, host_id, prize, winners, end_at),
        )
        self.conn.commit()

    def get_giveaway(self, message_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM giveaways WHERE message_id = ?", (message_id,)
        ).fetchone()
        return dict(row) if row else None

    def due_giveaways(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM giveaways WHERE ended = 0 AND end_at <= ?", (int(time.time()),)
        ).fetchall()
        return [dict(r) for r in rows]

    def end_giveaway(self, message_id: int):
        self.conn.execute("UPDATE giveaways SET ended = 1 WHERE message_id = ?", (message_id,))
        self.conn.commit()

    def toggle_entry(self, message_id: int, user_id: int) -> bool:
        """Entra/sai do sorteio. Retorna True se entrou."""
        cur = self.conn.execute(
            "DELETE FROM giveaway_entries WHERE message_id = ? AND user_id = ?",
            (message_id, user_id),
        )
        if cur.rowcount == 0:
            self.conn.execute(
                "INSERT INTO giveaway_entries (message_id, user_id) VALUES (?, ?)",
                (message_id, user_id),
            )
            self.conn.commit()
            return True
        self.conn.commit()
        return False

    def get_entries(self, message_id: int) -> list[int]:
        rows = self.conn.execute(
            "SELECT user_id FROM giveaway_entries WHERE message_id = ?", (message_id,)
        ).fetchall()
        return [r[0] for r in rows]

    # ---------- SeuBot (sociedade secreta) ----------
    def get_membro(self, guild_id: int, user_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM seubot_members WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        ).fetchone()
        return dict(row) if row else None

    def codinome_existe(self, guild_id: int, codename: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM seubot_members WHERE guild_id = ? AND codename = ?", (guild_id, codename)
        ).fetchone()
        return row is not None

    def add_membro(self, guild_id: int, user_id: int, codename: str) -> dict:
        numero = self.conn.execute(
            "SELECT COALESCE(MAX(number), 0) + 1 FROM seubot_members WHERE guild_id = ?", (guild_id,)
        ).fetchone()[0]
        self.conn.execute(
            """INSERT INTO seubot_members (guild_id, user_id, codename, number, joined_at)
               VALUES (?, ?, ?, ?, ?)""",
            (guild_id, user_id, codename, numero, int(time.time())),
        )
        self.conn.commit()
        return self.get_membro(guild_id, user_id)

    def remove_membro(self, guild_id: int, user_id: int) -> bool:
        cur = self.conn.execute(
            "DELETE FROM seubot_members WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def listar_membros(self, guild_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM seubot_members WHERE guild_id = ? ORDER BY number", (guild_id,)
        ).fetchall()
        return [dict(r) for r in rows]


    # ---------- Histórico de nomes/avatares ----------
    def ultimo_historico(self, user_id: int, tipo: str, guild_id: int | None = None) -> str | None:
        row = self.conn.execute(
            """SELECT valor FROM user_history WHERE user_id = ? AND tipo = ? AND guild_id IS ?
               ORDER BY id DESC LIMIT 1""",
            (user_id, tipo, guild_id),
        ).fetchone()
        return row[0] if row else None

    def add_historico(self, user_id: int, tipo: str, valor: str | None, guild_id: int | None = None) -> bool:
        """Registra o valor se for diferente do último. Retorna True se gravou."""
        if valor is None or self.ultimo_historico(user_id, tipo, guild_id) == valor:
            return False
        self.conn.execute(
            "INSERT INTO user_history (user_id, guild_id, tipo, valor, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, guild_id, tipo, valor, int(time.time())),
        )
        self.conn.commit()
        return True

    def get_historico(self, user_id: int, guild_id: int) -> list[dict]:
        rows = self.conn.execute(
            """SELECT * FROM user_history WHERE user_id = ? AND (guild_id IS NULL OR guild_id = ?)
               ORDER BY created_at, id""",
            (user_id, guild_id),
        ).fetchall()
        return [dict(r) for r in rows]
