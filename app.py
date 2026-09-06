import streamlit as st
from libfind import db, seed
from ui import student, admin, analytics_page
from libfind.seed import seed_if_empty
from ui.borrow import borrow_page
from libfind.db import init_db


st.set_page_config(
    page_title="LibFind — Search. Locate. Read.",
    page_icon="📚",
    layout="wide",
)


@st.cache_resource
def bootstrap():
    db.init_db()
    seed.seed_if_empty()
    return True


bootstrap()


def main():
    init_db() 
    st.sidebar.title("📚 LibFind")
    st.sidebar.caption("Search. Locate. Read.")
    st.sidebar.caption("Library / Education Technology Mini Project")
    

    page = st.sidebar.radio(
        "Navigate",
        ["🔎 Student Search", "🛠 Admin Interface", "📊 Library Analytics","Book Borrowing"],

    )

    st.sidebar.divider()
    st.sidebar.markdown(
        "Search by **title**, **author**, **ISBN**, or **category**. "
        "Get copy availability and shelf/rack location instantly."
    )

    if page == "Student Search":
        from ui.student import student_page
        student_page()
    elif page == "Admin Interface":
         from ui.admin import admin_page
         admin_page()
    elif page == "Library Analytics":
        from ui.analytics_page import analytics_page
        analytics_page()
    elif page == "Book Borrowing":
        from ui.borrow import borrow_page
        borrow_page()

    if page.startswith("🔎"):
        student.render()
    elif page.startswith("🛠"):
        admin.render()
    else:
        analytics_page.render()


if __name__ == "__main__":
    main()
