import sqlite3
from config import DATABASE


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hosts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            bio TEXT,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            location TEXT NOT NULL,
            max_guests INTEGER NOT NULL DEFAULT 1,
            social_link TEXT,
            password_hash TEXT NOT NULL DEFAULT '',
            photos TEXT DEFAULT '[]',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS volunteers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            password_hash TEXT NOT NULL DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            user_type TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at DATETIME NOT NULL,
            used INTEGER DEFAULT 0
        )
    ''')

    conn.commit()

    migrations = [
        ("hosts", "password_hash", "TEXT NOT NULL DEFAULT ''"),
        ("hosts", "photos", "TEXT DEFAULT '[]'"),
        ("hosts", "max_guests", "INTEGER NOT NULL DEFAULT 1"),
        ("volunteers", "password_hash", "TEXT NOT NULL DEFAULT ''"),
        ("hosts", "id_verified", "BOOLEAN NOT NULL DEFAULT 0"),
        ("hosts", "stripe_verification_id", "TEXT"),
        ("volunteers", "id_verified", "BOOLEAN NOT NULL DEFAULT 0"),
        ("volunteers", "stripe_verification_id", "TEXT"),
    ]
    for table, column, col_type in migrations:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            conn.commit()
        except Exception:
            pass

    conn.close()
