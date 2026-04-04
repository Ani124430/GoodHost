import psycopg2
import psycopg2.extras
from config import DATABASE_URL


class _Cursor:
    """Обвива psycopg2 курсор и добавя lastrowid."""

    def __init__(self, pg_cursor, lastrowid=None):
        self._cur = pg_cursor
        self.lastrowid = lastrowid

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()


class _Connection:
    """Обвива psycopg2 connection и предоставя SQLite-съвместим интерфейс."""

    def __init__(self, pg_conn):
        self._conn = pg_conn

    def execute(self, sql, params=None):
        # PostgreSQL използва %s вместо ?
        sql = sql.replace('?', '%s')

        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        is_insert = sql.strip().upper().startswith('INSERT')
        if is_insert and 'RETURNING' not in sql.upper():
            sql = sql.rstrip().rstrip(';') + ' RETURNING id'

        cur.execute(sql, params)

        lastrowid = None
        if is_insert:
            row = cur.fetchone()
            if row:
                lastrowid = row['id']

        return _Cursor(cur, lastrowid)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_db():
    url = DATABASE_URL
    # Railway дава postgres://, psycopg2 иска postgresql://
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    conn = psycopg2.connect(url)
    return _Connection(conn)


def init_db():
    conn = get_db()

    conn.execute('''
        CREATE TABLE IF NOT EXISTS hosts (
            id SERIAL PRIMARY KEY,
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
            id_verified BOOLEAN NOT NULL DEFAULT FALSE,
            stripe_verification_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS volunteers (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            password_hash TEXT NOT NULL DEFAULT '',
            id_verified BOOLEAN NOT NULL DEFAULT FALSE,
            stripe_verification_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id SERIAL PRIMARY KEY,
            email TEXT NOT NULL,
            user_type TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS host_reviews (
            id SERIAL PRIMARY KEY,
            volunteer_id INTEGER NOT NULL,
            host_id INTEGER NOT NULL,
            rating INTEGER,
            comment TEXT,
            review_token TEXT UNIQUE NOT NULL,
            token_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(volunteer_id, host_id)
        )
    ''')

    conn.execute("ALTER TABLE hosts ADD COLUMN IF NOT EXISTS help_needed TEXT")

    conn.execute('''
        CREATE TABLE IF NOT EXISTS host_busy_days (
            id SERIAL PRIMARY KEY,
            host_id INTEGER NOT NULL,
            date DATE NOT NULL,
            UNIQUE(host_id, date)
        )
    ''')

    conn.commit()
    conn.close()
