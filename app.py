import streamlit as st

from libfind import db, seed


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
    st.sidebar.title("📚 LibFind")
    st.sidebar.caption("Search. Locate. Read.")
    st.sidebar.caption("Library / Education Technology Mini Project")

    is_admin = st.session_state.get("admin_logged_in", False)
    
    pages = ["🔎 Student Search", "📊 Library Analytics", "Book Borrowing", "🛠 Admin Interface"]
    if is_admin:
        pages = ["📊 Dashboard", "📷 Quick Scan"] + pages 
        st.sidebar.success("👑 Logged in as Admin")
        if st.sidebar.button("Logout", use_container_width=True):
            st.session_state.admin_logged_in = False
            st.rerun()

    # Read the URL
    query_page = st.query_params.get("page", None)
    
    if query_page in pages:
        default_index = pages.index(query_page)
        # Clean up the URL immediately so the next button click works
        del st.query_params["page"]
    else:
        default_index = 0

    page = st.sidebar.radio("Navigate", pages, index=default_index)

    st.sidebar.divider()
    st.sidebar.markdown(
        "Search by **title**, **author**, **ISBN**, or **category**. "
        "Get copy availability and shelf/rack location instantly."
    )

    if page == "📊 Dashboard":
        from ui.dashboard import render as dash_render
        dash_render()
    elif page == "📷 Quick Scan":
        from ui.scanner import render as scan_render # <--- ADD THIS
        scan_render()
    elif page == "🔎 Student Search":
        from ui.student import render as student_render
        student_render()
    elif page == "🛠 Admin Interface":
        from ui.admin import render as admin_render
        admin_render()
    elif page == "📊 Library Analytics":
        from ui.analytics_page import render as analytics_render
        analytics_render()
    elif page == "Book Borrowing":
        from ui.borrow import borrow_page
        borrow_page()
if __name__ == "__main__":
    main()
