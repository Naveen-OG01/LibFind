import streamlit as st
from libfind import db, seed
from ui import student, admin, analytics_page
from libfind.seed import seed_if_empty



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

    page = st.sidebar.radio(
        "Navigate",
        ["🔎 Student Search", "🛠 Admin Interface", "📊 Library Analytics"],
    )

    st.sidebar.divider()
    st.sidebar.markdown(
        "Search by **title**, **author**, **ISBN**, or **category**. "
        "Get copy availability and shelf/rack location instantly."
    )

    if page.startswith("🔎"):
        student.render()
    elif page.startswith("🛠"):
        admin.render()
    else:
        analytics_page.render()


if __name__ == "__main__":
    main()
