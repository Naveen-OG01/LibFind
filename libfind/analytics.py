"""Library analytics queries for charts and reports."""
from contextlib import closing

from . import db


def collection_summary():
    with closing(db.get_connection()) as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_titles,
                COALESCE(SUM(total_copies), 0) AS total_copies,
                COALESCE(SUM(available_copies), 0) AS available_copies
            FROM books
            """
        ).fetchone()

    data = dict(row)
    if data["total_copies"]:
        data["percent_available"] = round(
            data["available_copies"] / data["total_copies"] * 100, 1
        )
    else:
        data["percent_available"] = 0.0

    return data


def category_stats():
    with closing(db.get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT
                c.name AS category_name,
                COUNT(b.id) AS total_titles,
                COALESCE(SUM(b.total_copies), 0) AS total_copies,
                COALESCE(SUM(b.available_copies), 0) AS available_copies,
                COALESCE(
                    SUM(CASE WHEN b.available_copies > 0 THEN 1 ELSE 0 END), 0
                ) AS available_titles
            FROM categories c
            LEFT JOIN books b ON b.category_id = c.id
            GROUP BY c.id, c.name
            ORDER BY total_copies DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def top_authors(limit=8):
    with closing(db.get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT
                author,
                COUNT(*) AS titles,
                COALESCE(SUM(total_copies), 0) AS copies
            FROM books
            GROUP BY author
            ORDER BY copies DESC, titles DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def low_stock(limit=10):
    with closing(db.get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT
                b.id,
                b.title,
                b.total_copies,
                b.available_copies,
                c.name AS category_name,
                b.shelf,
                b.rack
            FROM books b
            JOIN categories c ON c.id = b.category_id
            WHERE b.available_copies < b.total_copies
            ORDER BY CAST(b.available_copies AS REAL) / b.total_copies ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
