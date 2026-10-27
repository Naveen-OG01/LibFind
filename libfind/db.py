"""SQLite connection and catalogue CRUD operations."""
import math 
from datetime import datetime
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
        fine_amount REAL DEFAULT 0,
        fine_paid INTEGER DEFAULT 0,
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (book_id) REFERENCES books(id)
    );

        CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

        CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        book_id INTEGER NOT NULL,
        reserve_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending',
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
        connection = self

        class _Cursor:
            def __init__(self):
                self._result = None

            def execute(self, sql, params=()):
                self._result = connection.execute(sql, params)
                return self

            def fetchone(self):
                return self._result.fetchone()

            def fetchall(self):
                return self._result.fetchall()

            @property
            def lastrowid(self):
                return self._result.lastrowid

            @property
            def description(self):
                return getattr(self._result, "description", None)

            def __getattr__(self, name):
                return getattr(self._result, name)

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
    import os
    from pathlib import Path
    
    # 1. Try to get Turso credentials from Environment Variables (Render) or Streamlit Secrets
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")

    if not turso_url:
        try:
            turso_url = st.secrets.get("TURSO_DATABASE_URL")
            turso_token = st.secrets.get("TURSO_AUTH_TOKEN")
        except Exception:
            pass

    # 2. If we have credentials, connect to Turso
    if turso_url and turso_token:
        try:
            return _TursoConnection(
                libsql.connect(database=turso_url, auth_token=turso_token)
            )
        except Exception as e:
            print(f"Turso connection failed: {e}")

    # 3. Fallback to local SQLite (or /tmp for Render)
    if os.environ.get("RENDER"):
        db_path = Path("/tmp/libfind.db")
    else:
        db_path = DB_PATH

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with closing(get_connection()) as conn:
        conn.executescript(SCHEMA)
        
        # Auto-migrate missing columns for Turso/Local
        migrations = [
            "ALTER TABLE books ADD COLUMN cover_image TEXT",
            "ALTER TABLE borrows ADD COLUMN renewals INTEGER DEFAULT 0",
            "ALTER TABLE borrows ADD COLUMN fine_amount REAL DEFAULT 0",
            "ALTER TABLE borrows ADD COLUMN fine_paid INTEGER DEFAULT 0",
            """CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                book_id INTEGER NOT NULL,
                reserve_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )"""
        ]
        
        for sql in migrations:
            try:
                conn.execute(sql)
            except Exception as exc:
                if "duplicate column" not in str(exc).lower():
                    pass # Ignore errors if column/table already exists
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
    """Return category id for `name`, creating it if needed. Robust against
    UNIQUE violations on categories.name."""
    name = (name or "").strip() or "General"

    # Try to find existing
    row = conn.execute(
        "SELECT id FROM categories WHERE name = ?",
        (name,),
    ).fetchone()

    if row is not None:
        # Handle both _Row (dict-like) and sqlite3.Row
        try:
            return row["id"]
        except (KeyError, TypeError):
            return row[0]

    # Insert if not found. Use INSERT OR IGNORE to avoid UNIQUE crash.
    conn.execute(
        "INSERT OR IGNORE INTO categories(name) VALUES (?)",
        (name,),
    )
    conn.commit()

    # Re-select
    row = conn.execute(
        "SELECT id FROM categories WHERE name = ?",
        (name,),
    ).fetchone()

    if row is None:
        raise RuntimeError("Could not create or find category: " + name)

    try:
        return row["id"]
    except (KeyError, TypeError):
        return row[0]

    
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
    if available_copies is None:
        available_copies = total_copies
    available_copies = max(0, min(int(available_copies), total_copies))
    isbn = (isbn or "").strip() or None

    with closing(get_connection()) as conn:
        category_id = get_or_create_category(conn, category_name)

        conn.execute(
            """INSERT INTO books (title, author, isbn, category_id, publisher,
               publication_year, total_copies, available_copies, shelf, rack, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title.strip(), author.strip(), isbn, category_id, publisher or "",
             publication_year, total_copies, available_copies, shelf or "",
             rack or "", description or ""),
        )
        conn.commit()

        row = conn.execute(
            "SELECT id FROM books ORDER BY id DESC LIMIT 1"
        ).fetchone()
        try:
            return row["id"]
        except (KeyError, TypeError):
            return row[0] if row else None

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


def delete_book(book_id):
    with closing(get_connection()) as conn:
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()

def update_book_cover(book_id, cover_url):
    with closing(get_connection()) as conn:
        conn.execute("UPDATE books SET cover_image = ? WHERE id = ?", (cover_url, book_id))
        conn.commit()
# ============================================================
# Borrowing rules & operations
# ============================================================

MAX_BOOKS_PER_STUDENT = 3
MAX_RENEWALS = 2
RENEWAL_DAYS = 14

_ensure_borrow_schema_done = False


def _ensure_borrow_schema():
    """Add missing columns once per process (idempotent)."""
    global _ensure_borrow_schema_done
    if _ensure_borrow_schema_done:
        return
    with closing(get_connection()) as conn:
        # Add renewals if missing
        try:
            conn.execute("ALTER TABLE borrows ADD COLUMN renewals INTEGER DEFAULT 0")
        except Exception:
            pass
        # Add fine tracking if missing
        try:
            conn.execute("ALTER TABLE borrows ADD COLUMN fine_amount REAL DEFAULT 0")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE borrows ADD COLUMN fine_paid INTEGER DEFAULT 0")
        except Exception:
            pass
    _ensure_borrow_schema_done = True


def borrow_book(student_name, student_email, roll_number, book_id, loan_days=14):
    """Register the student and borrow a book in one safe operation.

    Returns (True, due_date_iso) on success, or (False, error_message).
    """
    from datetime import datetime, timedelta

    name = (student_name or "").strip()
    email = (student_email or "").strip()
    roll = (roll_number or "").strip()

    if not name or not email or not roll:
        return False, "Student name, email and roll number are required."

    _ensure_borrow_schema()

    with closing(get_connection()) as conn:
        # Rule 1: loan limit per student
        row = conn.execute(
            """
            SELECT COUNT(*) FROM borrows
            WHERE status = 'borrowed'
              AND student_id = (SELECT id FROM students WHERE roll_number = ?)
            """,
            (roll,),
        ).fetchone()
        if row and int(row[0]) >= MAX_BOOKS_PER_STUDENT:
            return False, (
                f"Loan limit reached: a student can borrow at most "
                f"{MAX_BOOKS_PER_STUDENT} books."
            )

        # Rule 2: student must not already hold this title
        row = conn.execute(
            """
            SELECT COUNT(*) FROM borrows
            WHERE status = 'borrowed'
              AND book_id = ?
              AND student_id = (SELECT id FROM students WHERE roll_number = ?)
            """,
            (book_id, roll),
        ).fetchone()
        if row and int(row[0]) > 0:
            return False, "This student already has this book borrowed."

        # Rule 3: at least one copy must be available
        row = conn.execute(
            "SELECT available_copies FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        if not row:
            return False, "Book not found."
        if int(row[0]) <= 0:
            return False, "No copies available right now."

        
        # Require an existing student account
        
        # Look up the student by ID first to be 100% accurate, 
        # fallback to roll number if needed
        row = conn.execute(
            "SELECT id FROM students WHERE roll_number = ? COLLATE NOCASE",
            (roll,),
        ).fetchone()
        
        if not row:
            # As a fallback, auto-create the student so the borrow doesn't fail
            conn.execute(
                "INSERT INTO students (name, email, roll_number) VALUES (?, ?, ?)",
                (name, email, roll)
            )
            conn.commit()
            row = conn.execute(
                "SELECT id FROM students WHERE roll_number = ? COLLATE NOCASE",
                (roll,),
            ).fetchone()
            
        student_id = row["id"] if hasattr(row, "keys") else row[0]
        # Decrement availability (guarded against going below 0)
        conn.execute(
            "UPDATE books SET available_copies = available_copies - 1 "
            "WHERE id = ? AND available_copies > 0",
            (book_id,),
        )

        due_date = (datetime.now() + timedelta(days=int(loan_days))).isoformat()
        conn.execute(
            "INSERT INTO borrows (student_id, book_id, due_date) VALUES (?, ?, ?)",
            (student_id, book_id, due_date),
        )

        title_row = conn.execute(
            "SELECT title FROM books WHERE id = ?", (book_id,)
        ).fetchone()
        book_title = title_row["title"] if title_row else str(book_id)
        _log_activity(
            conn,
            "BORROW",
            f"{name} ({roll}) borrowed '{book_title}', due {str(due_date)[:10]}",
        )
        conn.commit()

    return True, due_date


def return_book(borrow_id, fine_paid=False):
    """Mark a borrow as returned, calculate fine, and record payment."""
    _ensure_borrow_schema()
    
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT book_id, status, due_date FROM borrows WHERE id = ?", 
            (borrow_id,)
        ).fetchone()
        
        if not row:
            return False, "Record not found."
        if row["status"] != "borrowed":
            return False, "This book has already been returned."

        # Calculate the fine based on the due date
        days_late, fine_amount = compute_fine(row["due_date"])
        
        # Update the borrow record
        conn.execute(
            """UPDATE borrows 
               SET status = 'returned', 
                   return_date = CURRENT_TIMESTAMP,
                   fine_amount = ?,
                   fine_paid = ?
               WHERE id = ?""",
            (fine_amount, 1 if fine_paid else 0, borrow_id),
        )
        
        # Put the book back on the shelf
        conn.execute(
            "UPDATE books SET available_copies = available_copies + 1 WHERE id = ?",
            (row["book_id"],),
        )
        
        _log_activity(conn, "RETURN", _loan_details(conn, borrow_id))
        conn.commit()

    if days_late > 0:
        if fine_paid:
            return True, f"Book returned. Fine of ₹{fine_amount} collected."
        else:
            return True, f"Book returned. ⚠️ ₹{fine_amount} fine is UNPAID."
    
    return True, "Book returned successfully on time!"

def renew_book(borrow_id, extra_days=RENEWAL_DAYS):
    """Extend the due date of an active borrow."""
    from datetime import datetime, timedelta

    _ensure_borrow_schema()

    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT status, renewals FROM borrows WHERE id = ?",
            (borrow_id,),
        ).fetchone()
        if not row:
            return False, "Record not found."
        if row["status"] != "borrowed":
            return False, "Only borrowed books can be renewed."

        renewals = int(row["renewals"] or 0)
        if renewals >= MAX_RENEWALS:
            return False, f"Renewal limit reached ({MAX_RENEWALS} renewals allowed)."

        new_due = (datetime.now() + timedelta(days=int(extra_days))).isoformat()
        conn.execute(
            "UPDATE borrows SET due_date = ?, renewals = ? WHERE id = ?",
            (new_due, renewals + 1, borrow_id),
        )
        _log_activity(conn, "RENEW", _loan_details(conn, borrow_id))
        conn.commit()

    return True, f"Renewed — now due {str(new_due)[:10]}"


def active_loans(roll_number=None):
    """Active borrow records, optionally filtered to one student."""
    _ensure_borrow_schema()

    sql = """
        SELECT b.id, s.name, s.roll_number, bk.title,
               b.borrow_date, b.due_date, b.renewals
        FROM borrows b
        JOIN students s ON b.student_id = s.id
        JOIN books bk ON b.book_id = bk.id
        WHERE b.status = 'borrowed'
    """
    params = []
    if roll_number:
        sql += " AND s.roll_number = ?"
        params.append((roll_number or "").strip())
    sql += " ORDER BY b.due_date ASC"

    with closing(get_connection()) as conn:
        try:
            rows = conn.execute(sql, tuple(params)).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"Error fetching active loans: {e}")
            return []
        
def borrow_history():
    """All borrow records, newest first."""
    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT s.name, s.roll_number, bk.title,
                   b.borrow_date, b.due_date, b.return_date, b.status,
                   b.fine_amount, b.fine_paid
            FROM borrows b
            JOIN students s ON b.student_id = s.id
            JOIN books bk ON b.book_id = bk.id
            ORDER BY b.borrow_date DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# Activity log
# ============================================================

def _log_activity(conn, action, details):
    """Insert one activity row on the given connection."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        "INSERT INTO activity_log (action, details) VALUES (?, ?)",
        (action, details),
    )


def _loan_details(conn, borrow_id):
    row = conn.execute(
        """
        SELECT s.name, s.roll_number, bk.title
        FROM borrows b
        JOIN students s ON s.id = b.student_id
        JOIN books bk ON bk.id = b.book_id
        WHERE b.id = ?
        """,
        (borrow_id,),
    ).fetchone()
    if not row:
        return f"borrow id {borrow_id}"
    return f"{row['name']} ({row['roll_number']}) — {row['title']}"


def get_activity(limit=200):
    """Newest activity entries first."""
    with closing(get_connection()) as conn:
        try:
            rows = conn.execute(
                "SELECT action, details, created_at FROM activity_log "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

# ============================================================
# Overdue fines
# ============================================================

FINE_PER_DAY = 5  # rupees per day late


def compute_fine(due_date, on_date=None, fine_per_day=FINE_PER_DAY):
    """Fine owed for a loan due on `due_date`, as of `on_date`.

    Returns (days_overdue, fine_amount). Both are 0 when not late.
    """
    from datetime import datetime

    if not due_date:
        return 0, 0
    try:
        due = datetime.fromisoformat(str(due_date))
    except ValueError:
        return 0, 0

    now = on_date or datetime.now()
    if now <= due:
        return 0, 0

    days = math.ceil((now - due).total_seconds() / 86400)
    return days, days * fine_per_day


def overdue_summary():
    """All overdue loans with days late and fine owed (oldest overdue first)."""
    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT s.name, s.roll_number, bk.title, b.due_date
            FROM borrows b
            JOIN students s ON s.id = b.student_id
            JOIN books bk ON bk.id = b.book_id
            WHERE b.status = 'borrowed'
            ORDER BY b.due_date ASC
            """
        ).fetchall()

    overdue = []
    for r in rows:
        d = dict(r)
        days, fine = compute_fine(d["due_date"])
        if days > 0:
            d["days_overdue"] = days
            d["fine"] = fine
            overdue.append(d)
    return overdue

def reset_all_data():
    """DEV ONLY - wipes all data. Never call from production UI."""
    with closing(get_connection()) as conn:
        for table in ["borrows", "books", "students", "categories", "activity_log"]:
            try:
                conn.execute("DELETE FROM " + table)
            except Exception as exc:
                msg = str(exc).lower()
                if "no such table" not in msg:
                    print("Skipping " + table + ": " + str(exc))
        try:
            conn.execute("DELETE FROM sqlite_sequence")
        except Exception:
            pass
        conn.commit()

# ============================================================
# Students (auth)
# ============================================================

def get_student_by_roll(roll_number):
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT id, name, email, roll_number FROM students WHERE roll_number = ?",
            ((roll_number or "").strip().upper(),),
        ).fetchone()
        return dict(row) if row else None


def list_students(limit=500):
    with closing(get_connection()) as conn:
        rows = conn.execute(
            """SELECT s.id, s.name, s.email, s.roll_number,
                      (SELECT COUNT(*) FROM borrows b
                       WHERE b.student_id = s.id AND b.status = 'borrowed') AS active_loans
               FROM students s
               ORDER BY s.name COLLATE NOCASE
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    
def get_students_for_reminder(days_threshold=2):
    """
    Fetch students who have books overdue OR due within `days_threshold` days.
    Returns a list of dicts.
    """
    from datetime import datetime, timedelta
    
    target_date = (datetime.now() + timedelta(days=days_threshold)).isoformat()
    
    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT s.name, s.email, s.roll_number, bk.title, b.due_date, b.status
            FROM borrows b
            JOIN students s ON b.student_id = s.id
            JOIN books bk ON b.book_id = bk.id
            WHERE b.status = 'borrowed' 
              AND b.due_date <= ?
            ORDER BY b.due_date ASC
            """,
            (target_date,)
        ).fetchall()
        return [dict(r) for r in rows]

def delete_student(student_id):
    """Delete a student and their borrow history. Fails if they have active loans."""
    with closing(get_connection()) as conn:
        # 1. Check for active loans first
        active = conn.execute(
            "SELECT COUNT(*) FROM borrows WHERE student_id = ? AND status = 'borrowed'", 
            (student_id,)
        ).fetchone()[0]
        
        if active > 0:
            return False, "Cannot delete: This student still has books borrowed."
            
        # 2. Delete their borrow history (past records)
        conn.execute("DELETE FROM borrows WHERE student_id = ?", (student_id,))
        
        # 3. Delete the student
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        
        return True, "Student and their history deleted successfully."

# ============================================================
# Reservations
# ============================================================

def reserve_book(student_id, book_id):
    with closing(get_connection()) as conn:
        # 1. Ensure the table exists (just in case the Dev Tool reset missed it)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                book_id INTEGER NOT NULL,
                reserve_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        """)
        
        # 2. Check if already reserved
        existing = conn.execute(
            "SELECT id FROM reservations WHERE student_id = ? AND book_id = ? AND status = 'pending'",
            (student_id, book_id)
        ).fetchone()
        if existing:
            return False, "You have already reserved this book."
            
        # 3. Insert the reservation
        conn.execute(
            "INSERT INTO reservations (student_id, book_id) VALUES (?, ?)",
            (student_id, book_id)
        )
        conn.commit()
        return True, "✅ Book reserved! You will be notified when it is available."

def get_reservations(book_id=None):
    """Get pending reservations. If book_id is provided, filter by that book."""
    sql = """
        SELECT r.id, s.name, s.roll_number, bk.title, r.reserve_date
        FROM reservations r
        JOIN students s ON r.student_id = s.id
        JOIN books bk ON r.book_id = bk.id
        WHERE r.status = 'pending'
    """
    params = []
    if book_id:
        sql += " AND r.book_id = ?"
        params.append(book_id)
    sql += " ORDER BY r.reserve_date ASC"
    
    with closing(get_connection()) as conn:
        return [dict(row) for row in conn.execute(sql, tuple(params)).fetchall()]

def cancel_reservation(reservation_id):
    with closing(get_connection()) as conn:
        conn.execute("UPDATE reservations SET status = 'cancelled' WHERE id = ?", (reservation_id,))
        conn.commit()
        return True, "Reservation cancelled."

def get_admin_dashboard_stats():
    """Fetch key metrics for the Admin Dashboard."""
    with closing(get_connection()) as conn:
        # 1. Active Loans
        active_loans = conn.execute("SELECT COUNT(*) FROM borrows WHERE status = 'borrowed'").fetchone()[0]
        
        # 2. Overdue Books
        today = datetime.now().isoformat()
        overdue = conn.execute("SELECT COUNT(*) FROM borrows WHERE status = 'borrowed' AND due_date < ?", (today,)).fetchone()[0]
        
        # 3. Pending Fines
        unpaid_fines = conn.execute("SELECT COALESCE(SUM(fine_amount), 0) FROM borrows WHERE status = 'returned' AND fine_paid = 0").fetchone()[0]
        
        # 4. Active Reservations
        reservations = conn.execute("SELECT COUNT(*) FROM reservations WHERE status = 'pending'").fetchone()[0]
        
        # 5. Total Students
        students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        
    return {
        "active_loans": active_loans,
        "overdue": overdue,
        "unpaid_fines": unpaid_fines,
        "reservations": reservations,
        "students": students
    }

def bulk_import_students(student_list, default_password=None):
    """
    Import a list of students. 
    student_list format: [{'name': '...', 'email': '...', 'roll_number': '...'}]
    """
    import hashlib
    import os
    import binascii
    from contextlib import closing
    from libfind.auth import ensure_auth_schema 

    ensure_auth_schema()  

    added = 0
    errors = []

    with closing(get_connection()) as conn:
        for i, s in enumerate(student_list):
            name = (s.get("name") or "").strip()
            email = (s.get("email") or "").strip().lower()
            roll = (s.get("roll_number") or "").strip().upper()
            
            # Password defaults to their Roll Number if not provided
            password = s.get("password") or default_password or roll

            if not name or not email or not roll:
                errors.append(f"Row {i+1}: Missing name, email, or roll number")
                continue

            # Check if student already exists
            existing = conn.execute(
                "SELECT id FROM students WHERE roll_number = ? OR email = ?",
                (roll, email)
            ).fetchone()
            
            if existing:
                errors.append(f"Row {i+1}: Student {roll} or {email} already exists")
                continue

            # Hash the password
            salt = os.urandom(16)
            dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
            salt_hex = binascii.hexlify(salt).decode()
            hash_hex = binascii.hexlify(dk).decode()

            try:
                conn.execute(
                    """INSERT INTO students 
                       (name, email, roll_number, password_salt, password_hash) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (name, email, roll, salt_hex, hash_hex)
                )
                added += 1
            except Exception as exc:
                errors.append(f"Row {i+1}: DB Error - {str(exc)}")
                
        conn.commit()

    return added, errors

# ============================================================
# Export Functions
# ============================================================

def export_full_inventory():
    """Returns a CSV string of all books in the library."""
    import csv
    import io
    
    with closing(get_connection()) as conn:
        rows = conn.execute("""
            SELECT b.id, b.title, b.author, b.isbn, c.name AS category, 
                   b.publisher, b.publication_year, b.total_copies, 
                   b.available_copies, b.shelf, b.rack
            FROM books b
            LEFT JOIN categories c ON b.category_id = c.id
            ORDER BY b.title
        """).fetchall()
        
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Book ID", "Title", "Author", "ISBN", "Category", "Publisher", "Year", "Total Copies", "Available", "Shelf", "Rack"])
    
    for r in rows:
        writer.writerow([r["id"], r["title"], r["author"], r["isbn"], r["category"], r["publisher"], r["publication_year"], r["total_copies"], r["available_copies"], r["shelf"], r["rack"]])
        
    return output.getvalue()

def export_all_students():
    """Returns a CSV string of all registered students."""
    import csv
    import io
    
    with closing(get_connection()) as conn:
        rows = conn.execute("""
            SELECT id, name, email, roll_number, created_at 
            FROM students ORDER BY name
        """).fetchall()
        
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID", "Name", "Email", "Roll Number", "Registered On"])
    
    for r in rows:
        writer.writerow([r["id"], r["name"], r["email"], r["roll_number"], r["created_at"]])
        
    return output.getvalue()

def export_fine_report():
    """Returns a CSV string of all overdue/unpaid fines."""
    import csv
    import io
    
    with closing(get_connection()) as conn:
        rows = conn.execute("""
            SELECT s.name, s.roll_number, bk.title, b.due_date, b.return_date, b.fine_amount, b.fine_paid
            FROM borrows b
            JOIN students s ON b.student_id = s.id
            JOIN books bk ON b.book_id = bk.id
            WHERE b.fine_amount > 0 OR b.status = 'borrowed'
            ORDER BY b.fine_amount DESC
        """).fetchall()
        
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student Name", "Roll Number", "Book Title", "Due Date", "Return Date", "Fine Amount (₹)", "Status"])
    
    for r in rows:
        status = "Paid" if r["fine_paid"] else ("Unpaid" if r["fine_amount"] > 0 else "None")
        writer.writerow([r["name"], r["roll_number"], r["title"], str(r["due_date"])[:10], str(r["return_date"])[:10] if r["return_date"] else "", r["fine_amount"], status])
        
    return output.getvalue()
