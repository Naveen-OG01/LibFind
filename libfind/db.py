"""SQLite connection and catalogue CRUD operations."""

import streamlit as st
import libsql
import sqlite3
from contextlib import closing
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "libfind.db"

SCHEMA = """
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    isbn TEXT,
    category_id INTEGER,
    publisher TEXT DEFAULT '',
    publication_year INTEGER,
    total_copies INTEGER DEFAULT 1,
    available_copies INTEGER DEFAULT 1,
    shelf TEXT DEFAULT '',
    rack TEXT DEFAULT '',
    description TEXT DEFAULT '',
    cover_image TEXT,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        roll_number TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS borrows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        book_id INTEGER NOT NULL,
        borrow_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        due_date TIMESTAMP,
        return_date TIMESTAMP,
        status TEXT DEFAULT 'borrowed',
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (book_id) REFERENCES books(id)
    );
"""


BOOK_SELECT = """
SELECT
    b.id,
    b.title,
    b.author,
    b.isbn,
    c.name AS category_name,
    b.publisher,
    b.publication_year,
    b.total_copies,
    b.available_copies,
    b.shelf,
    b.rack,
    b.description,
    b.cover_image AS cover_image
FROM books b
LEFT JOIN categories c ON c.id = b.category_id
"""



class _Row(dict):
    """Works as both dict (row["name"]) and tuple (row[0])."""

    def __init__(self, cols, values):
        super().__init__(zip(cols, values))
        self._values = values

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


class _TursoCursor:
    def __init__(self, raw_conn, raw_cur):
        self._raw_conn = raw_conn
        self._raw = raw_cur

    def fetchone(self):
        row = self._raw.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in self._raw.description or []]
        return _Row(cols, row)

    def fetchall(self):
        cols = [d[0] for d in self._raw.description or []]
        return [_Row(cols, r) for r in self._raw.fetchall()]

    @property
    def lastrowid(self):
        try:
            if self._raw.lastrowid:
                return self._raw.lastrowid
        except Exception:
            pass
        row = self._raw_conn.execute("SELECT last_insert_rowid() AS id").fetchone()
        return row[0] if row else None

    def __getattr__(self, name):
        return getattr(self._raw, name)


class _TursoConnection:
    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql, params=()):
        if sql.lstrip().upper().startswith("PRAGMA"):
            class _Noop:
                description = None
                lastrowid = None
                def fetchone(self): return None
                def fetchall(self): return []
            return _Noop()
        return _TursoCursor(self._raw, self._raw.execute(sql, params))

    def cursor(self):
        conn = self
        class _Cursor:
            def execute(self, sql, params=()):
                return conn.execute(sql, params)
        return _Cursor()

    def executescript(self, script):
        for stmt in script.split(";"):
            if stmt.strip():
                self._raw.execute(stmt)

    def commit(self):
        self._raw.commit()

    def close(self):
        self._raw.close()


def get_connection():
    try:
        return _TursoConnection(
            libsql.connect(
                database=st.secrets["TURSO_DATABASE_URL"],
                auth_token=st.secrets["TURSO_AUTH_TOKEN"],
            )
        )
    except (FileNotFoundError, KeyError):
        # Fallback for local dev without Turso secrets
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with closing(get_connection()) as conn:
        conn.executescript(SCHEMA)
        try:
            conn.execute("ALTER TABLE books ADD COLUMN cover_image TEXT")
        except sqlite3.OperationalError:
            pass
        conn.commit()


def count_books():
    with closing(get_connection()) as conn:
        return conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]


def list_categories():
    sql = """
    SELECT c.id, c.name, COUNT(b.id) AS book_count
    FROM categories c
    LEFT JOIN books b ON b.category_id = c.id
    GROUP BY c.id, c.name
    ORDER BY c.name COLLATE NOCASE
    """
    with closing(get_connection()) as conn:
        return [dict(r) for r in conn.execute(sql).fetchall()]


def category_names():
    return [c["name"] for c in list_categories()]


def add_category(name):
    name = (name or "").strip()
    if not name:
        return
    with closing(get_connection()) as conn:
        conn.execute("INSERT OR IGNORE INTO categories(name) VALUES (?)", (name,))
        conn.commit()


def delete_category_by_name(name):
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT id FROM categories WHERE name = ? COLLATE NOCASE",
            (name,),
        ).fetchone()
        if not row:
            return
        book_count = conn.execute(
            "SELECT COUNT(*) FROM books WHERE category_id = ?",
            (row["id"],),
        ).fetchone()[0]
        if book_count:
            raise ValueError(
                f"Cannot delete '{name}': it contains {book_count} book(s)."
            )
        conn.execute("DELETE FROM categories WHERE id = ?", (row["id"],))
        conn.commit()


def get_or_create_category(conn, name):
    name = (name or "").strip() or "General"
    row = conn.execute(
        "SELECT id FROM categories WHERE name = ? COLLATE NOCASE",
        (name,),
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO categories(name) VALUES (?)", (name,))
    return cur.lastrowid


def get_all_books(category=None):
    sql = BOOK_SELECT
    params = []
    if category:
        sql += " WHERE c.name = ? COLLATE NOCASE"
        params.append(category)
    sql += " ORDER BY b.title COLLATE NOCASE LIMIT 500"
    with closing(get_connection()) as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_book(book_id):
    with closing(get_connection()) as conn:
        row = conn.execute(BOOK_SELECT + " WHERE b.id = ?", (book_id,)).fetchone()
        return dict(row) if row else None


def add_book(title, author, isbn=None, category_name="General", publisher="",
             publication_year=None, total_copies=1, available_copies=None,
             shelf="", rack="", description=""):
    if not title or not title.strip():
        raise ValueError("Book title is required.")
    if not author or not author.strip():
        raise ValueError("Book author is required.")
    total_copies = int(total_copies or 1)
    available_copies = int(available_copies) if available_copies is not None else total_copies
    available_copies = max(0, min(available_copies, total_copies))
    isbn = (isbn or "").strip() or None

    with closing(get_connection()) as conn:
        category_id = get_or_create_category(conn, category_name)
        cur = conn.execute(
            """INSERT INTO books (title, author, isbn, category_id, publisher,
               publication_year, total_copies, available_copies, shelf, rack, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title.strip(), author.strip(), isbn, category_id, publisher or "",
             publication_year, total_copies, available_copies, shelf or "",
             rack or "", description or ""),
        )
        conn.commit()
        return cur.lastrowid


def update_book(book_id, category_name=None, **fields):
    allowed = {"title", "author", "isbn", "publisher", "publication_year",
               "total_copies", "available_copies", "shelf", "rack",
               "description", "category_id"}
    if category_name:
        with closing(get_connection()) as conn:
            fields["category_id"] = get_or_create_category(conn, category_name)
    if "isbn" in fields:
        fields["isbn"] = (fields["isbn"] or "").strip() or None
    set_clause, values = [], []
    for field, value in fields.items():
        if field in allowed:
            set_clause.append(f"{field} = ?")
            values.append(value)
    if not set_clause:
        return
    values.append(book_id)
    with closing(get_connection()) as conn:
        conn.execute(
            f"UPDATE books SET {', '.join(set_clause)} WHERE id = ?",
            values,
        )
        conn.commit()

def update_book_cover(book_id, cover_url):
    with closing(get_connection()) as conn:
        conn.execute("UPDATE books SET cover_image = ? WHERE id = ?", (cover_url, book_id))
        conn.commit()


def delete_book(book_id):
    with closing(get_connection()) as conn:
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()

def update_book_cover(book_id, cover_url):
    with closing(get_connection()) as conn:
        conn.execute("UPDATE books SET cover_image = ? WHERE id = ?", (cover_url, book_id))
        conn.commit()
