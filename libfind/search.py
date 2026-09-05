"""Student-facing search: fast partial + fuzzy matching helpers."""
from contextlib import closing

from rapidfuzz import fuzz

from . import db


def search_books(query="", field="all", category=None):
    """Return books matching keyword / partial / exact search.

    field can be: all, title, author, isbn, category
    """
    field = field.lower()
    if field not in {"all", "title", "author", "isbn", "category"}:
        field = "all"

    query = (query or "").strip()
    category = category.strip() if category else None

    column_map = {
        "title": "b.title",
        "author": "b.author",
        "category": "c.name",
        "isbn": "b.isbn",
    }

    with closing(db.get_connection()) as conn:
        cat_sql = ""
        cat_params = []
        if category:
            cat_sql = " AND c.name = ? COLLATE NOCASE"
            cat_params = [category]

        # Browse mode: no query, but maybe a category filter.
        if not query:
            sql = db.BOOK_SELECT + " WHERE 1=1" + cat_sql
            sql += " ORDER BY b.title COLLATE NOCASE LIMIT 100"
            return [dict(r) for r in conn.execute(sql, cat_params).fetchall()]

        # ISBN: exact match first, then partial match.
        if field == "isbn":
            row = conn.execute(
                db.BOOK_SELECT
                + " WHERE b.isbn = ? COLLATE NOCASE "
                + cat_sql
                + " LIMIT 1",
                [query] + cat_params,
            ).fetchone()
            if row:
                return [dict(row)]

            term = f"%{query}%"
            rows = conn.execute(
                db.BOOK_SELECT
                + " WHERE b.isbn LIKE ?"
                + cat_sql
                + " ORDER BY b.title COLLATE NOCASE LIMIT 50",
                [term] + cat_params,
            ).fetchall()
            return [dict(r) for r in rows]

        # Search everywhere: title / author / ISBN / category
        if field == "all":
            term = f"%{query}%"
            rows = conn.execute(
                db.BOOK_SELECT
                + " WHERE (b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ? OR c.name LIKE ?)"
                + cat_sql
                + " ORDER BY b.title COLLATE NOCASE LIMIT 100",
                [term] * 4 + cat_params,
            ).fetchall()
            return [dict(r) for r in rows]

        # Field-specific partial search.
        column = column_map[field]
        term = f"%{query}%"
        rows = conn.execute(
            db.BOOK_SELECT
            + f" WHERE {column} LIKE ?"
            + cat_sql
            + " ORDER BY b.title COLLATE NOCASE LIMIT 100",
            [term] + cat_params,
        ).fetchall()
        return [dict(r) for r in rows]


def fuzzy_title_suggestions(query, category=None, limit=5):
    """When no normal match exists, show closest book-title matches."""
    query = (query or "").strip()
    if not query:
        return []

    scored = []
    for book in db.get_all_books(category):
        score = fuzz.WRatio(query, book.get("title") or "")
        if score >= 45:
            scored.append((score, book))

    scored.sort(key=lambda item: (-item[0], (item[1]["title"] or "").lower()))
    return [book for _, book in scored[:limit]]
