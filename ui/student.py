"""Student-facing search UI."""
import streamlit as st

from libfind import db, recommend, search


def _handle_reserve_callback(student_id, book_id):
    ok, msg = db.reserve_book(student_id, book_id)
    
    # Save the message to session_state so it survives the reload
    if ok:
        st.session_state["toast_msg"] = msg
        st.session_state["toast_icon"] = "✅"
    else:
        st.session_state["toast_msg"] = msg
        st.session_state["toast_icon"] = "⚠️"

def render():
    st.title("🔎 Student Book Search")
    st.caption("Search. Locate. Read.")


    if "toast_msg" in st.session_state:
        st.toast(st.session_state["toast_msg"], icon=st.session_state["toast_icon"])
        del st.session_state["toast_msg"]
        del st.session_state["toast_icon"]

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

        col3, col4 = st.columns(2)
        availability = col3.selectbox(
            "Availability",
            ["Any availability", "Available only", "Checked out"],
        )
        year = col4.number_input(
            "Publication year (0 = any)",
            min_value=0, max_value=2100, value=0, step=1,
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
    total_matches = len(results)

    # ---- extra filters ----
    if availability == "Available only":
        results = [b for b in results if int(b.get("available_copies") or 0) > 0]
    elif availability == "Checked out":
        results = [b for b in results if int(b.get("available_copies") or 0) <= 0]

    if year:
        results = [
            b for b in results
            if str(b.get("publication_year") or "") == str(year)
        ]

    st.subheader(f"Results — {len(results)} book(s) found")
        # Show any success/error message from the reserve button
    if "res_msg" in st.session_state:
        st.success(st.session_state["res_msg"])
        del st.session_state["res_msg"] # Clear it so it doesn't show forever
        # Show any success/error message from the callback
        
    st.subheader(f"Results — {len(results)} book(s) found")
    if not results:
        if total_matches:
            st.warning(
                f"{total_matches} match(es) found, but none match your "
                "availability / year filters. Loosen them and search again."
            )
            return

        st.warning("No exact / partial match found in the catalogue.")

        suggestions = search.fuzzy_title_suggestions(
            query,
            category=cat,
            limit=5,
        )

        if suggestions:
            st.success("Did you mean one of these titles?")
            for i, book in enumerate(suggestions):
                _book_card(book, index=f"fuzzy_{i}")
        else:
            st.info(
                "No close title match either. Try fewer keywords, "
                "check spelling, or search without a category filter."
            )
        return

    for i, book in enumerate(results[:50]):
        _book_card(book, index=i)

    # Similar-book suggestions using the result set.
    st.markdown("---")
    st.subheader("💡 Similar books you may also like")

    seen = {book["id"] for book in results}
    shown = False

    for i, book in enumerate(results[:5]):
        for j, similar in enumerate(recommend.similar_books(book["id"], limit=2)):
            if similar["id"] not in seen:
                _book_card(similar, index=f"sim_{i}_{j}")
                seen.add(similar["id"])
                shown = True
    if not shown:
        st.caption("No additional similar titles available right now.")


def _book_card(book, index=0):
    with st.container(border=True):
        col1, col2 = st.columns([1, 3])

    with col1:
        if book.get("cover_image"):
            st.image(book["cover_image"], width=120)
        else:
            st.caption("📚 No cover available")

    with col2:
        st.markdown(f"**{book['title']}**")
        st.caption(f"by {book['author']}")

        if book.get("category_name"):
            st.caption(f"📂 {book['category_name']}")

        if book["available_copies"] > 0:
            st.success(f"✅ Available ({book['available_copies']} copies)")
        else:
            st.error("❌ Checked out")
            student = st.session_state.get("student")
            
            unique_key = f"reserve_{book['id']}_{index}"
            
            if student:
                # Using on_click to guarantee it runs
                st.button(
                    "🔖 Reserve this book", 
                    key=unique_key,
                    on_click=_handle_reserve_callback,
                    args=(student["id"], book["id"])
                )
            else:
                st.caption("🔐 Log in to reserve this book.")