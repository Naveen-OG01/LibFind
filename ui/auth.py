import streamlit as st

# Default admin credentials (change these!)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

def login():
    """Show login form and return True if logged in."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        return True

    st.title("🔐 Admin Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid credentials")
    
    return False

def logout():
    """Logout button."""
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
