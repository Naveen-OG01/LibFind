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
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Show book cover or placeholder
        if book.get("cover_image"):
            st.image(book["cover_image"], width=120)
        else:
            st.caption("📚 No cover available")

    
    with col2:
        st.markdown(f"**{book['title']}**")
        st.caption(f"by {book['author']}")
        
        if book.get("category_name"):
            st.caption(f"📂 {book['category_name']}")
        
        # Availability badge
        if book["available_copies"] > 0:
            st.success(f"✅ Available ({book['available_copies']} copies)")
        else:
            st.error("❌ Checked out")
        
        # Location
        if book.get("shelf") or book.get("rack"):
            st.caption(f"📍 Shelf: {book.get('shelf', 'N/A')} | Rack: {book.get('rack', 'N/A')}")
