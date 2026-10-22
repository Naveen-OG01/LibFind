"""Book borrowing / returning UI."""
import math
from datetime import datetime
from contextlib import closing 

import pandas as pd
import streamlit as st

from libfind import db


def borrow_page():
    st.title("📚 Book Borrowing")
    is_admin = st.session_state.get("admin_logged_in", False)

    # Create 5 tabs now
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Borrow Book", "My Books", "My Reservations", "Return / Renew", "View Records"]
    )
    with tab1:
        _borrow_tab()
    with tab2:
        _my_books_tab()
    with tab3:
        _my_reservations_tab() # New Tab
    with tab4:
        if is_admin:
            _return_tab()
        else:
            _admin_required("Return / Renew", "return_renew")
    with tab5:
        if is_admin:
            _records_tab()
        else:
            _admin_required("View Records", "view_records")

def _admin_required(page_name, slug):
    """Login prompt shown when an admin-only tab is opened by a visitor."""
    st.subheader(f"🔒 {page_name}")
    st.info("Restricted to library administrators. Log in below.")

    with st.form(f"borrow_admin_login_{slug}"):
        username = st.text_input("Admin username")
        password = st.text_input("Admin password", type="password")
        submitted = st.form_submit_button("Login as admin", use_container_width=True)

    if submitted:
        try:
            expected_user = str(st.secrets.get("ADMIN_USERNAME", "admin")).strip()
            expected_pass = str(st.secrets.get("ADMIN_PASSWORD", "admin123")).strip()
        except Exception:
            expected_user, expected_pass = "admin", "admin123"

        if username.strip() == expected_user and password.strip() == expected_pass:
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.error("Invalid credentials")

# ---------- helpers ----------

def _due_info(due_date):
    """Return (is_overdue, days_overdue) for a stored due date."""
    if not due_date:
        return False, 0
    try:
        due = datetime.fromisoformat(str(due_date))
    except ValueError:
        return False, 0
    now = datetime.now()
    if now > due:
        days = math.ceil((now - due).total_seconds() / 86400)
        return True, days
    return False, 0


# ---------- tabs ----------

def _borrow_tab():
    st.subheader("Borrow a Book")

    student = st.session_state.get("student")

    if not student:
        st.info("🔐 Please log in first to borrow books.")

        tab_login, tab_register = st.tabs(["Login", "Register"])

        with tab_login:
            with st.form("student_login_form"):
                roll = st.text_input("Roll Number")
                pwd = st.text_input("Password", type="password")
                submit = st.form_submit_button("Log in", use_container_width=True)
            if submit:
                from libfind import auth
                ok, result = auth.login_student(roll, pwd)
                if ok:
                    st.session_state.student = result
                    st.success(f"Welcome, {result['name']}!")
                    st.rerun()
                else:
                    st.error(result)

        with tab_register:
            with st.form("student_register_form"):
                name = st.text_input("Full Name")
                email = st.text_input("Email")
                roll = st.text_input("Roll Number")
                pwd = st.text_input("Password (min 6 chars)", type="password")
                pwd2 = st.text_input("Confirm Password", type="password")
                submit = st.form_submit_button("Register", use_container_width=True)
            if submit:
                if pwd != pwd2:
                    st.error("Passwords do not match.")
                else:
                    from libfind import auth
                    ok, msg = auth.register_student(name, email, roll, pwd)
                    if ok:
                        st.success(msg + " Now switch to the Login tab.")
                    else:
                        st.error(msg)

        return

    # ---- Logged in: show borrow form ----
    st.success(f"👤 {student['name']} — Roll {student['roll_number']}")

    books = db.get_all_books()
    if not books:
        st.info("No books in the catalogue yet.")
        return

    book_options = {f"{b['title']} by {b['author']}": b["id"] for b in books}
    selected_book = st.selectbox(
        "Select Book", list(book_options.keys()), key="borrow_book"
    )
    due_days = st.number_input(
        "Loan Period (days)", min_value=1, max_value=30, value=14, key="borrow_days"
    )

    if st.button("Borrow Book", key="borrow_btn"):
        ok, result = db.borrow_book(
            student["name"], student["email"], student["roll_number"],
            book_options[selected_book], due_days,
        )
        if ok:
            st.success(f"✅ Borrowed! Due {str(result)[:10]}")
            st.balloons()
        else:
            st.error(result)

    st.divider()
    if st.button("Log out", key="student_logout"):
        st.session_state.student = None
        st.rerun()


def _my_books_tab():
    st.subheader("My Books")
    student = st.session_state.get("student")
    if not student:
        st.info("🔐 Log in on the 'Borrow Book' tab to see your books.")
        return

    loans = db.active_loans(student["roll_number"])
    if not loans:
        st.info("You have no active borrows.")
    else:
        for loan in loans:
            overdue, days = _due_info(loan["due_date"])
            if overdue:
                st.error(f"**{loan['title']}** — OVERDUE by {days}d (was due {str(loan['due_date'])[:10]})")
            else:
                st.warning(f"**{loan['title']}** — due {str(loan['due_date'])[:10]}")

    
    
def _return_tab():
    st.subheader("Return / Renew Books")

    loans = db.active_loans()
    if not loans:
        st.info("No books currently borrowed.")
        return

    for loan in loans:
        overdue, days = _due_info(loan["due_date"])
        label = f"{loan['name']} — {loan['title']}"
        if overdue:
            label += f"  ⚠️ OVERDUE {days}d"

        with st.expander(label, expanded=overdue):
            st.write(f"Roll: {loan['roll_number']}")
            st.write(f"Borrowed: {loan['borrow_date']}")
            st.write(f"Due: {str(loan['due_date'])[:19]}")
            st.write(f"Renewals used: {loan['renewals'] or 0} / {db.MAX_RENEWALS}")
            
            fine_paid = False
            if overdue:
                fine = days * db.FINE_PER_DAY
                st.error(f"Overdue by {days} day(s) — Fine owed: ₹{fine}")
                fine_paid = st.checkbox(
                    f"✅ Mark ₹{fine} fine as PAID", 
                    key=f"paid_{loan['id']}"
                )
            else:
                st.success("On time — no fine.")

            col1, col2 = st.columns(2)
            
            if col1.button("↩ Mark Returned", key=f"return_{loan['id']}"):
                ok, msg = db.return_book(loan["id"], fine_paid=fine_paid)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
                    
            if col2.button("🔄 Renew (+14 days)", key=f"renew_{loan['id']}"):
                ok, msg = db.renew_book(loan["id"])
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


def _records_tab():
    st.subheader("All Borrowing Records")

    records = db.borrow_history()
    if not records:
        st.info("No records yet.")
        return

    rows = []
    for r in records:
        if r["status"] == "borrowed":
            overdue, _ = _due_info(r["due_date"])
            status = "⚠️ OVERDUE" if overdue else "borrowed"
        else:
            status = r["status"]

        fine_display = ""
        if r.get("fine_amount") and r["fine_amount"] > 0:
            if r["fine_paid"]:
                fine_display = f"₹{r['fine_amount']} (Paid)"
            else:
                fine_display = f"₹{r['fine_amount']} (UNPAID)"

        rows.append(
            {
                "Student": r["name"],
                "Roll No": r["roll_number"],
                "Book": r["title"],
                "Borrowed": str(r["borrow_date"])[:10],
                "Due": str(r["due_date"])[:10],
                "Returned": str(r["return_date"])[:10] if r["return_date"] else "",
                "Status": status,
                "Fine": fine_display,
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇️ Download records as CSV",
        df.to_csv(index=False),
        file_name="libfind_borrow_records.csv",
        mime="text/csv",
    )

def _my_reservations_tab():
    st.subheader("🔖 My Reservations")
    student = st.session_state.get("student")
    if not student:
        st.info("🔐 Log in on the 'Borrow Book' tab to see your reservations.")
        return

    with closing(db.get_connection()) as conn:
        res = conn.execute(
            """
            SELECT bk.title, r.reserve_date 
            FROM reservations r
            JOIN books bk ON r.book_id = bk.id
            WHERE r.student_id = ? AND r.status = 'pending'
            """, (student["id"],)
        ).fetchall()
        
    if not res:
        st.info("You have no active book reservations.")
    else:
        for r in res:
            st.info(f"**{r['title']}** — Reserved on {str(r['reserve_date'])[:10]}. We will notify you when it's available!")