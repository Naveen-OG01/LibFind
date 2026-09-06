import streamlit as st
from libfind import db
from libfind.cloudinary_config import upload_cover

def render():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("Admin Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            if u == "admin" and p == "admin123":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Wrong username or password")
        return

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    st.title("Admin Interface")
    tab1, tab2, tab3 = st.tabs(["Add Book", "Edit Book", "Categories"])
    with tab1:
        _add()
    with tab2:
        _edit()
    with tab3:
        _cats()

def _add():
    cats = db.category_names()
    with st.form("f1"):
        t = st.text_input("Title")
        a = st.text_input("Author")
        c = st.selectbox("Category", cats)
        y = st.number_input("Year", 0, 2100, 2024)
        n = st.number_input("Copies", 1, 100, 1)
        s = st.text_input("Shelf")
        r = st.text_input("Rack")
        if st.form_submit_button("Add"):
            if t and a:
                db.add_book(title=t, author=a, category_name=c, publication_year=y, total_copies=n, available_copies=n, shelf=s, rack=r)
                st.success("Added!")
                st.rerun()

def _edit():
    books = db.get_all_books()
    if not books:
        st.info("No books")
        return
    opts = {f"{b['id']}: {b['title']}": b['id'] for b in books}
    sel = st.selectbox("Pick book", list(opts.keys()))
    bid = opts[sel]
    book = db.get_book(bid)
    if book.get("cover_image"):
        st.image(book["cover_image"], width=100)
    up = st.file_uploader("Cover", type=["png","jpg"])
    cats = db.category_names()
    with st.form("f2"):
        t = st.text_input("Title", book["title"])
        a = st.text_input("Author", book["author"])
        c = st.selectbox("Category", cats)
        if st.form_submit_button("Save"):
            if up:
                url = upload_cover(up.read(), bid)
                db.update_book_cover(bid, url)
            db.update_book(bid, title=t, author=a, category_name=c)
            st.success("Saved!")
            st.rerun()

def _cats():
    cats = db.list_categories()
    if cats:
        st.dataframe([{"Name": c["name"], "Books": c["book_count"]} for c in cats])
