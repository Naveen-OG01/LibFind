"""Admin Dashboard UI."""
import streamlit as st
from libfind import db

def render():
    st.title("📊 Library Dashboard")
    st.caption("Welcome back, Librarian. Here is the daily overview.")

    stats = db.get_admin_dashboard_stats()

    # Top Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📚 Books Borrowed", stats["active_loans"])
    col2.metric("⚠️ Overdue Books", stats["overdue"], delta="- Needs attention", delta_color="inverse")
    col3.metric("💰 Unpaid Fines", f"₹{stats['unpaid_fines']}")
    col4.metric("🔖 Reservations", stats["reservations"])

    st.divider()

    # Two-column layout for lists
    left, right = st.columns(2)

    with left:
        st.subheader("🚨 Overdue Alerts")
        overdue_books = db.get_students_for_reminder(days_threshold=0) # 0 means only overdue
        
        if not overdue_books:
            st.success("No overdue books! Great job.")
        else:
            for b in overdue_books:
                st.error(f"**{b['name']}** ({b['roll_number']}) - *{b['title']}*")
                st.caption(f"Due: {str(b['due_date'])[:10]}")

    with right:
        st.subheader("🔖 Pending Reservations")
        res = db.get_reservations()
        
        if not res:
            st.info("No pending reservations.")
        else:
            for r in res:
                st.warning(f"**{r['name']}** ({r['roll_number']}) wants *{r['title']}*")
                st.caption(f"Reserved on: {str(r['reserve_date'])[:10]}")

    st.divider()
       # Quick Actions
        # Quick Actions
    st.subheader("⚡ Quick Actions")
    qcol1, qcol2, qcol3 = st.columns(3)
    
    if qcol1.button("➕ Add New Book", use_container_width=True):
        st.query_params["page"] = "🛠 Admin Interface"
        st.query_params["tab"] = "add"
        st.rerun()
        
    if qcol2.button("👥 View Students", use_container_width=True):
        st.query_params["page"] = "🛠 Admin Interface"
        st.query_params["tab"] = "students"
        st.rerun()
        
    if qcol3.button("✉️ Send Emails", use_container_width=True):
        st.query_params["page"] = "🛠 Admin Interface"
        st.query_params["tab"] = "notify"
        st.rerun()