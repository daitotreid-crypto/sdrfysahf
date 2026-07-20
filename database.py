import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "applications.db")


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self._get_connection() as conn:
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

    def is_already_applied(self, user_id: int) -> bool:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM applications WHERE user_id = ?", (user_id,)
            ).fetchone()
            return row is not None

    def save_application(
        self,
        user_id: int,
        username: str | None,
        full_name: str | None,
        answer_1: str,
        answer_2: str,
    ):
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO applications (user_id, username, full_name, answer_1, answer_2)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, username, full_name, answer_1, answer_2),
            )
            conn.commit()
