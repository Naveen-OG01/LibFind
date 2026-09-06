"""Admin / library catalogue management UI."""
import streamlit as st
from sqlite3 import IntegrityError

from libfind import db
from ui.auth import login, logout
import os
from pathlib import Path

COVERS_DIR = Path(__file__).resolve().parent.parent / "data" / "covers"
COVERS_DIR.mkdir(parents=True, exist_ok=True)

def admin_page():
    if not login():
        return  # Don't show admin page if not logged in
    
    logout()  # Show logout button in sidebar
    
    # ... rest of your existing admin page code ...



def render():
    st.title("🛠 Admin / Library Interface")

    if not st.session_state.get("admin_logged_in"):
        _login()
        return

    col1, col2 = st.columns([4, 1])
    col1.success("Logged in as library administrator")

    with col2:
        if st.button("Log out", use_container_width=True):
            st.session_state["admin_logged_in"] = False
            st.rerun()

    tab_add, tab_edit, tab_cat = st.tabs(
        ["➕ Add Book", "✏️ Edit / Delete Book", "🏷️ Categories"]
    )

    with tab_add:
        _add_book_tab()

    with tab_edit:
        _edit_delete_book_tab()

    with tab_cat:
        _categories_tab()


def _login():
    default_password = "admin123"

    try:
        correct_password = st.secrets.get("ADMIN_PASSWORD", default_password)
    except Exception:
        correct_password = default_password

    with st.form("admin_login_form"):
        st.subheader("Admin Login")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        if password == correct_password:
            st.session_state["admin_logged_in"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")


def _add_book_tab():
    categories = db.category_names()

    with st.form("add_book_form"):
        st.subheader("Add a new book to the catalogue")

        col1, col2 = st.columns(2)
        title = col1.text_input("Title *")
        author = col2.text_input("Author *")

        col3, col4 = st.columns(2)
        isbn = col3.text_input("ISBN")
        category = col4.selectbox("Category", categories)

        col5, col6 = st.columns(2)
        publisher = col5.text_input("Publisher")
        year = col6.number_input(
            "Publication year",
            min_value=0,
            max_value=2100,
            value=2024,
            step=1,
        )

        col7, col8 = st.columns(2)
        total_copies = col7.number_input(
            "Total copies",
            min_value=1,
            value=1,
            step=1,
        )
        available_copies = col8.number_input(
            "Available copies",
            min_value=0,
            value=total_copies,
            step=1,
        )

        col9, col10 = st.columns(2)
        shelf = col9.text_input("Shelf", placeholder="CS-1")
        rack = col10.text_input("Rack", placeholder="R2")

        submitted = st.form_submit_button(
            "Add book",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not title.strip() or not author.strip():
            st.error("Title and author are required.")
            return

        if available_copies > total_copies:
            available_copies = total_copies

        try:
            db.add_book(
                title=title,
                author=author,
                isbn=isbn.strip() or None,
                category_name=category,
                publisher=publisher,
                publication_year=year or None,
                total_copies=total_copies,
                available_copies=available_copies,
                shelf=shelf,
                rack=rack,
            )
            st.success(f"Book '{title.strip()}' added successfully.")
            st.rerun()
        except IntegrityError:
            st.error("Could not add book: ISBN already exists.")
        except Exception as exc:
            st.error(f"Could not add book: {exc}")


def _edit_delete_book_tab():
    books = db.get_all_books()

    if not books:
        st.info("No books in the catalogue yet.")
        return

    options = {
        f"#{book['id']} — {book['title']} ({book['author']})": book["id"]
        for book in books
    }

    label = st.selectbox("Select a book", list(options.keys()))
    book_id = options[label]
    book = db.get_book(book_id)

    if not book:
        st.warning("Book not found.")
        return

    categories = db.category_names()
    default_cat_idx = 0
    if book["category_name"] in categories:
        default_cat_idx = categories.index(book["category_name"])

    with st.form("edit_book_form"):
        st.subheader("Update book details")

        col1, col2 = st.columns(2)
        title = col1.text_input("Title *", value=book["title"])
        author = col2.text_input("Author *", value=book["author"])

        col3, col4 = st.columns(2)
        isbn = col3.text_input("ISBN", value=book["isbn"] or "")
        category = col4.selectbox(
            "Category",
            categories,
            index=default_cat_idx,
        )

        col5, col6 = st.columns(2)
        publisher = col5.text_input("Publisher", value=book["publisher"] or "")
        year = col6.number_input(
            "Publication year",
            min_value=0,
            max_value=2100,
            value=book["publication_year"] or 2024,
            step=1,
        )

        col7, col8 = st.columns(2)
        total_copies = col7.number_input(
            "Total copies",
            min_value=1,
            value=int(book["total_copies"]),
            step=1,
        )
        available_copies = col8.number_input(
            "Available copies",
            min_value=0,
            value=int(book["available_copies"]),
            step=1,
        )
        col9, col10 = st.columns(2)
        shelf = col9.text_input("Shelf", value=book["shelf"] or "")
        rack = col10.text_input("Rack", value=book["rack"] or "")

uploaded_cover = st.file_uploader("Book Cover Image", type=["png", "jpg", "jpeg"])
if uploaded_cover:
    cover_path = COVERS_DIR / f"book_{book_id}.png"
    cover_path.write_bytes(uploaded_cover.read())
    db.update_book_cover(book_id, str(cover_path))
    st.success("Cover uploaded!")
    submitted = st.form_submit_button(
            "Save changes",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not title.strip() or not author.strip():
            st.error("Title and author are required.")
        elif available_copies > total_copies:
            st.error("Available copies cannot exceed total copies.")
        else:
            db.update_book(
                book_id,
                title=title,
                author=author,
                isbn=isbn,
                category_name=category,
                publisher=publisher,
                publication_year=year or None,
                total_copies=total_copies,
                available_copies=available_copies,
                shelf=shelf,
                rack=rack,
            )
            st.success("Book updated.")
            st.rerun()

    st.divider()

    if st.button("🗑 Delete selected book", use_container_width=True):
        db.delete_book(book_id)
        st.success("Book deleted.")
        st.rerun()


def _categories_tab():
    st.markdown(
        "A category that still contains books cannot be deleted. "
        "First edit those books to a different category."
    )

    with st.form("add_category_form"):
        col1, col2 = st.columns([3, 1])
        name = col1.text_input("New category name")
        submitted = col2.form_submit_button("Add", use_container_width=True)

    if submitted:
        if name.strip():
            db.add_category(name)
            st.success(f"Category '{name.strip()}' added.")
            st.rerun()
        else:
            st.warning("Enter a category name.")

    st.divider()

    categories = db.list_categories()

    if categories:
        st.dataframe(
            [
                {"Category": c["name"], "Books": c["book_count"]}
                for c in categories
            ],
            use_container_width=True,
            hide_index=True,
        )

        empty = [c["name"] for c in categories if c["book_count"] == 0]

        if empty:
            target = st.selectbox("Empty category to delete", empty)

            if st.button("Delete selected category"):
                try:
                    db.delete_category_by_name(target)
                    st.success(f"Category '{target}' deleted.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        else:
            st.caption("No empty categories available to delete.")

