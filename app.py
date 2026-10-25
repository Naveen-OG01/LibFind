import streamlit as st

from libfind import db, seed


st.set_page_config(
    page_title="LibFind — Search. Locate. Read.",
    page_icon="📚",
    layout="wide",
)

# ==========================================
# 🎨 CUSTOM CSS FOR PREMIUM LOOK
# ==========================================
def local_css():
    css = """
    <style>
    /* Main Background */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #e2e8f0;
    }
    
    /* Sidebar Background */
    [data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #334155;
    }

    /* Headers and Text */
    h1, h2, h3 {
        color: #38bdf8 !important;
        font-family: 'Inter', sans-serif;
    }
    p, span, div {
        font-family: 'Inter', sans-serif;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(59, 130, 246, 0.4);
    }

    /* Form Submit Buttons */
    .stFormSubmitButton > button {
        background: linear-gradient(90deg, #10b981 0%, #059669 100%);
        width: 100%;
    }

    /* Input Fields */
    .stTextInput > div > div > input, .stSelectbox > div > div > div {
        background-color: #1e293b;
        color: #f8fafc;
        border: 1px solid #334155;
        border-radius: 6px;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b;
        border-radius: 8px 8px 0 0;
        border: 1px solid #334155;
        padding: 10px 20px;
        color: #94a3b8;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
    }

    /* Hide Streamlit Default Menus (For production look) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background-color: transparent !important;}
    </style>
    """
    # THIS IS THE MOST IMPORTANT LINE. MAKE SURE IT SAYS unsafe_allow_html=True
    st.markdown(css, unsafe_allow_html=True)

# Apply the CSS
local_css()

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
        pages = ["📊 Dashboard", "📷 Quick Scan", "🔎 Student Search", "📊 Library Analytics", "Book Borrowing", "🛠 Admin Interface"]
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
