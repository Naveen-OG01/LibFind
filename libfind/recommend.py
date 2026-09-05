"""Similar-book recommendation engine."""
from rapidfuzz import fuzz

from . import db


def similar_books(book_id, limit=4):
    """Score other books using category, author, year, and title similarity."""
    target = db.get_book(book_id)
    if not target:
        return []

    target_author = (target["author"] or "").strip().lower()
    target_category = (target["category_name"] or "").strip().lower()
    target_year = target.get("publication_year")

    scored = []

    for book in db.get_all_books():
        if book["id"] == target["id"]:
            continue

        score = 0.0

        if (book["category_name"] or "").strip().lower() == target_category:
            score += 2.0

        if (book["author"] or "").strip().lower() == target_author:
            score += 3.0

        if target_year and book.get("publication_year"):
            if abs(int(book["publication_year"]) - int(target_year)) <= 3:
                score += 0.5

        score += (
            fuzz.WRatio(
                target["title"] or "",
                book["title"] or "",
            )
            / 100.0
            * 1.5
        )

        if score > 0:
            scored.append((score, book))

    scored.sort(key=lambda item: (-item[0], (item[1]["title"] or "").lower()))
    return [book for _, book in scored[:limit]]
