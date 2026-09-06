"""Student-facing search UI."""
import streamlit as st
from pathlib import Path

from libfind import db, recommend, search


def render():
    st.title("🔎 Student Book Search")
    st.caption("Search. Locate. Read.")

    categories = ["All"] + db.category_names()

    with st.form("student_search_form"):
        col1, col2 = st.columns([3, 1])
        query = col1.text_input(
            "Search text",
            placeholder="e.g. Python, Clean Code, 9780132350884, Mathematics",
        )
        category = col2.selectbox("Category filter", categories)

        field = st.radio(
            "Search in",
            ["Everywhere", "Title", "Author", "ISBN", "Category"],
            horizontal=True,
        )

        submitted = st.form_submit_button(
            "🔍 Search books",
            use_container_width=True,
        )

    if not submitted:
        st.info("Enter a book title, author, ISBN, or category to begin.")
        return

    search_field = "all" if field == "Everywhere" else field.lower()
    cat = None if category == "All" else category

    if not query.strip() and cat is None:
        st.warning("Type something or choose a category.")
        return

    results = search.search_books(query, field=search_field, category=cat)

    st.subheader(f"Results — {len(results)} book(s) found")

    if not results:
        st.warning("No exact / partial match found in the catalogue.")

        suggestions = search.fuzzy_title_suggestions(
            query,
            category=cat,
            limit=5,
        )

        if suggestions:
            st.success("Did you mean one of these titles?")
            for book in suggestions:
                _book_card(book)
        else:
            st.info(
                "No close title match either. Try fewer keywords, "
                "check spelling, or search without a category filter."
            )
        return

    for book in results[:50]:
        _book_card(book)

    # Similar-book suggestions using the result set.
    st.markdown("---")
    st.subheader("💡 Similar books you may also like")

    seen = {book["id"] for book in results}
    shown = False

    for book in results[:5]:
        for similar in recommend.similar_books(book["id"], limit=2):
            if similar["id"] not in seen:
                _book_card(similar)
                seen.add(similar["id"])
                shown = True

    if not shown:
        st.caption("No additional similar titles available right now.")


def _book_card(book):
    status = "✅ Available" if book["available_copies"] > 0 else "❌ Unavailable"

    with st.container(border=True):
        col_title, col_status = st.columns([4, 1])
        col_title.markdown(
            f"**{book['title']}**  \n"
            f"*{book['author']}* — {book['category_name']}"
        )
        col_status.markdown(f"### {status}")

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(
            f"**Copies**  \n{book['available_copies']} / {book['total_copies']} available"
        )
        c2.markdown(f"**Shelf**  \n{book.get('shelf') or '—'}")
        c3.markdown(f"**Rack**  \n{book.get('rack') or '—'}")
        c4.markdown(
            f"**ISBN / Year**  \n{book.get('isbn') or '—'} ({book.get('publication_year') or '—'})"
        )
def _book_card(book):
    # Show cover if exists
    if book.get("cover_image"):
        cover_path = Path(book["cover_image"])
        if cover_path.exists():
            st.image(str(cover_path), width=150)
    
    st.write(f"**{book['title']}**")
    st.write(f"by {book['author']}")
    # ... rest of card