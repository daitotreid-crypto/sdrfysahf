import os
import sqlite3
from typing import Optional

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

DATABASE_URL = os.getenv("DATABASE_URL")
DB_PATH = os.path.join(os.path.dirname(__file__), "applications.db")


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.database_url = DATABASE_URL
        self.use_postgres = bool(self.database_url and HAS_PSYCOPG2)
        
        if self.use_postgres:
            self._init_postgres()
        else:
            self._init_sqlite()

    def _get_postgres_conn(self):
        return psycopg2.connect(self.database_url)

    def _init_postgres(self):
        with self._get_postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS applications (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT UNIQUE NOT NULL,
                        username TEXT,
                        full_name TEXT,
                        answer_1 TEXT NOT NULL,
                        answer_2 TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            conn.commit()

    def _init_sqlite(self):
        with self._get_sqlite_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    full_name TEXT,
                    answer_1 TEXT NOT NULL,
                    answer_2 TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _get_sqlite_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def is_already_applied(self, user_id: int) -> bool:
        if self.use_postgres:
            with self._get_postgres_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM applications WHERE user_id = %s", (user_id,))
                    return cur.fetchone() is not None
        else:
            with self._get_sqlite_conn() as conn:
                row = conn.execute(
                    "SELECT 1 FROM applications WHERE user_id = ?", (user_id,)
                ).fetchone()
                return row is not None

    def save_application(
        self,
        user_id: int,
        username: Optional[str],
        full_name: Optional[str],
        answer_1: str,
        answer_2: str,
    ):
        if self.use_postgres:
            with self._get_postgres_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO applications (user_id, username, full_name, answer_1, answer_2)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (user_id, username, full_name, answer_1, answer_2),
                    )
                conn.commit()
        else:
            with self._get_sqlite_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO applications (user_id, username, full_name, answer_1, answer_2)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, username, full_name, answer_1, answer_2),
                )
                conn.commit()