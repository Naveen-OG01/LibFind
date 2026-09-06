"""SQLite connection and catalogue CRUD operations."""
import sqlite3
from contextlib import closing
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "libfind.db"

SCHEMA = """
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        isbn TEXT,
        category_name TEXT,
        total_copies INTEGER DEFAULT 1,
        available_copies INTEGER DEFAULT 1,
        shelf TEXT,
        rack TEXT,
        description TEXT,
        publisher TEXT,
        publication_year INTEGER
    );

    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
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
    SELECT b.id, b.title, b.author, b.isbn, b.category_name,
           b.total_copies, b.available_copies, b.shelf, b.rack,
           b.description, b.publisher, b.publication_year
    FROM books b
"""


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with closing(get_connection()) as conn:
        conn.executescript(SCHEMA)
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
                f"Cannot delete '{name}': it contains {book_count} book(s). "
                "Move or delete those books first."
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
        row = conn.execute(
            BOOK_SELECT + " WHERE b.id = ?",
            (book_id,),
        ).fetchone()
        return dict(row) if row else None


def add_book(
    title,
    author,
    isbn=None,
    category_name="General",
    publisher="",
    publication_year=None,
    total_copies=1,
    available_copies=None,
    shelf="",
    rack="",
    description="",
):
    if not title or not title.strip():
        raise ValueError("Book title is required.")
    if not author or not author.strip():
        raise ValueError("Book author is required.")

    total_copies = int(total_copies or 1)
    if available_copies is None:
        available_copies = total_copies
    else:
        available_copies = int(available_copies)

    available_copies = max(0, min(available_copies, total_copies))

    isbn = (isbn or "").strip() or None
    publisher = publisher or ""
    shelf = shelf or ""
    rack = rack or ""
    description = description or ""

    with closing(get_connection()) as conn:
        category_id = get_or_create_category(conn, category_name)

        cur = conn.execute(
            """
            INSERT INTO books (
                title, author, isbn, category_id, publisher, publication_year,
                total_copies, available_copies, shelf, rack, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title.strip(),
                author.strip(),
                isbn,
                category_id,
                publisher,
                publication_year,
                total_copies,
                available_copies,
                shelf,
                rack,
                description,
            ),
        )
        conn.commit()
        return cur.lastrowid


def update_book(book_id, category_name=None, **fields):
    allowed = {
        "title",
        "author",
        "isbn",
        "publisher",
        "publication_year",
        "total_copies",
        "available_copies",
        "shelf",
        "rack",
        "description",
        "category_id",
    }

    if category_name:
        with closing(get_connection()) as conn:
            fields["category_id"] = get_or_create_category(conn, category_name)

    if "isbn" in fields:
        fields["isbn"] = (fields["isbn"] or "").strip() or None

    if (
        "available_copies" in fields
        and "total_copies" in fields
        and fields["available_copies"] > fields["total_copies"]
    ):
        fields["available_copies"] = fields["total_copies"]

    set_clause = []
    values = []

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

        conn.execute(
            """
            UPDATE books
            SET available_copies = total_copies
            WHERE id = ? AND available_copies > total_copies
            """,
            (book_id,),
        )

        conn.commit()


def delete_book(book_id):
    with closing(get_connection()) as conn:
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
