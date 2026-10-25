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
    # Inject custom CSS for the frontend look
    st.markdown("""
        <style>
        .hero-banner {
            background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
            padding: 40px;
            border-radius: 12px;
            text-align: center;
            color: white;
            margin-bottom: 30px;
            box-shadow: 0 10px 25px rgba(59, 130, 246, 0.3);
        }
        .hero-banner h1 {
            font-size: 3rem;
            margin-bottom: 10px;
            color: white !important;
        }
        .hero-banner p {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        .section-title {
            font-size: 1.8rem;
            color: #38bdf8;
            margin-top: 30px;
            margin-bottom: 20px;
            border-bottom: 2px solid #334155;
            padding-bottom: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- HERO BANNER ---
    if "searched" not in st.session_state:
        st.markdown("""
            <div class="hero-banner">
                <h1>📚 Welcome to LibFind</h1>
                <p>Discover, Reserve, and Read. Your entire college library, now in your pocket.</p>
            </div>
        """, unsafe_allow_html=True)

    # Search Form (keep your existing form code here)
    categories = ["All"] + db.category_names()
    with st.form("student_search_form"):
        col1, col2 = st.columns([3, 1])
        query = col1.text_input("Search text", placeholder="Search by title, author, or ISBN...")
        category = col2.selectbox("Category filter", categories)
        
        # ... rest of your search form inputs (Search in, Availability, Year) ...
        field = st.radio("Search in", ["Everywhere", "Title", "Author", "ISBN", "Category"], horizontal=True)
        col3, col4 = st.columns(2)
        availability = col3.selectbox("Availability", ["Any availability", "Available only", "Checked out"])
        year = col4.number_input("Publication year (0 = any)", min_value=0, max_value=2100, value=0, step=1)
        
        submitted = st.form_submit_button("🔍 Search books", use_container_width=True)

    # If user hasn't searched, show the beautiful Top Books grid
    if not submitted and not query.strip():
        st.markdown('<div class="section-title">🔥 Trending Books</div>', unsafe_allow_html=True)
        
        # Fetch top 3 books from the database
        books = db.get_all_books()[:3]  # For demo, just grab the first 3
        
        cols = st.columns(3)
        for i, book in enumerate(books):
            with cols[i]:
                with st.container(border=True):
                    if book.get("cover_image"):
                        st.image(book["cover_image"], use_column_width=True)
                    else:
                        st.info("📚 No Cover")
                    st.subheader(book["title"])
                    st.caption(f"by {book['author']}")
                    if book["available_copies"] > 0:
                        st.success(f"✅ {book['available_copies']} copies available")
                    else:
                        st.error("❌ Checked out")
        return

    # ... [Keep your existing search logic for displaying results here] ...


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