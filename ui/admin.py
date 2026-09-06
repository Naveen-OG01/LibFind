"""Admin / library catalogue management UI."""
import streamlit as st
from libfind import db
from libfind.cloudinary_config import upload_cover


def render():
    # Simple login check
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    if not st.session_state.admin_logged_in:
        st.title("🔐 Admin Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if username == "admin" and password == "admin123":
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("Invalid credentials")
        return

    # Logout
    if st.sidebar.button("Logout"):
        st.session_state.admin_logged_in = False
        st.rerun()

    st.title("🛠 Admin / Library Interface")
    st.success("Logged in as library administrator")

    tab_add, tab_edit, tab_cat = st.tabs(["➕ Add Book", "✏️ Edit / Delete Book", "🏷️ Categories"])

    with tab_add:
        _add_book_tab()
    with tab_edit:
        _edit_delete_book_tab()
    with tab_cat:
        _categories_tab()


def _add_book_tab():
    categories = db.category_names()
    with st.form("add_book_form"):
        st.subheader("Add a new book")
        col1, col2 = st.columns(2)
        title = col1.text_input("Title *")
        author = col2.text_input("Author *")
        col3, col4 = st.columns(2)
        isbn = col3.text_input("ISBN")
        category = col4.selectbox("Category", categories)
        col5, col6 = st.columns(2)
        publisher = col5.text_input("Publisher")
        year = col6.number_input("Publication year", min_value=0, max_value=2100, value=2024)
        col7, col8 = st.columns(2)
        total_copies = col7.number_input("Total copies", min_value=1, value=1)
        available_copies = col8.number_input("Available copies", min_value=0, value=1)
        col9, col10 = st.columns(2)
        shelf = col9.text_input("Shelf")
        rack = col10.text_input("Rack")
        submitted = st.form_submit_button("Add book", type="primary")

    if submitted:
        if not title.strip() or not author.strip():
            st.error("Title and author required.")
        else:
            db.add_book(title=title, author=author, isbn=isbn or None, category_name=category,
                       publisher=publisher, publication_year=year or None,
                       total_copies=total_copies, available_copies=min(available_copies, total_copies),
                       shelf=shelf, rack=rack)
            st.success(f"Book '{title}' added!")
            st.rerun()


def _edit_delete_book_tab():
    books = db.get_all_books()
    if not books:
        st.info("No books yet.")
        return

    options = {f"#{b['id']} — {b['title']}": b["id"] for b in books}
    label = st.selectbox("Select book", list(options.keys()))
    book_id = options[label]
    book = db.get_book(book_id)

    if book.get("cover_image"):
        st.image(book["cover_image"], width=150, caption="Current cover")
    
    uploaded_cover = st.file_uploader("Upload cover", type=["png", "jpg", "jpeg"])

    categories = db.category_names()
    cat_idx = categories.index(book["category_name"]) if book["category_name"] in categories else 0

    with st.form("edit_form"):
        col1, col2 = st.columns(2)
        title = col1.text_input("Title", value=book["title"])
        author = col2.text_input("Author", value=book["author"])
        col3, col4 = st.columns(2)
        isbn = col3.text_input("ISBN", value=book["isbn"] or "")
        category = col4.selectbox("Category", categories, index=cat_idx)
        col5, col6 = st.columns(2)
        publisher = col5.text_input("Publisher", value=book["publisher"] or "")
        year = col6.number_input("Year", min_value=0, max_value=2100, value=book["publication_year"] or 2024)
        col7, col8 = st.columns(2)
        total_copies = col7.number_input("Total copies", min_value=1, value=int(book["total_copies"]))
        available_copies = col8.number_input("Available copies", min_value=0, value=int(book["available_copies"]))
        col9, col10 = st.columns(2)
        shelf = col9.text_input("Shelf", value=book["shelf"] or "")
        rack = col10.text_input("Rack", value=book["rack"] or "")
        submitted = st.form_submit_button("Save changes", type="primary")

    if submitted:
        if uploaded_cover:
            cover_url = upload_cover(uploaded_cover.read(), book_id)
            db.update_book_cover(book_id, cover_url)
        db.update_book(book_id, title=title, author=author, isbn=isbn, category_name=category,
                      publisher=publisher, publication_year=year, total_copies=total_copies,
                      available_copies=available_copies, shelf=shelf, rack=rack)
        st.success("Book updated!")
        st.rerun()

    if st.button("🗑 Delete this book"):
        db.delete_book(book_id)
        st.success("Deleted!")
        st.rerun()


def _categories_tab():
    with st.form("add_cat"):
        name = st.text_input("New category")
        if st.form_submit_button("Add"):
            if name.strip():
                db.add_category(name)
                st.success(f"Added '{name}'")
                st.rerun()

    categories = db.list_categories()
    if categories:
        st.dataframe([{"Category": c["name"], "Books": c["book_count"]} for c in categories],
                    use_container_width=True, hide_index=True)
        empty = [c["name"] for c in categories if c["book_count"] == 0]
        if empty:
            target = st.selectbox("Delete empty category", empty)
            if st.button("Delete"):
                db.delete_category_by_name(target)
                st.success("Deleted!")
                st.rerun()
