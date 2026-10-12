"""Book borrowing / returning UI."""
import math
from datetime import datetime

import pandas as pd
import streamlit as st

from libfind import db


def borrow_page():
    st.title("📚 Book Borrowing")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Borrow Book", "My Books", "Return / Renew", "View Records"]
    )
    with tab1:
        _borrow_tab()
    with tab2:
        _my_books_tab()
    with tab3:
        _return_tab()
    with tab4:
        _records_tab()


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
    slip = st.session_state.pop("issue_slip", None)
    if slip:
        st.session_state["borrow_name"] = ""
        st.session_state["borrow_email"] = ""
        st.session_state["borrow_roll"] = ""
        with st.container(border=True):
            st.markdown("### 🧾 Issue Slip")
            st.markdown(f"**Student:** {slip['name']}  \n**Roll:** {slip['roll']}")
            st.markdown(f"**Book:** {slip['book']}")
            st.markdown(f"**Borrowed on:** {slip['borrowed']}")
            st.markdown(f"**Return by:** {slip['due']}")
            st.caption("Press Ctrl+P to print this slip.")
        st.divider()

    st.subheader("Borrow a Book")
    if ok:
            st.session_state["issue_slip"] = {
                "name": student_name.strip(),
                "roll": roll_number.strip(),
                "book": selected_book,
                "borrowed": datetime.now().strftime("%Y-%m-%d"),
                "due": str(result)[:10],
            }
            st.rerun()
    else:
            st.error(result)


def _my_books_tab():
    st.subheader("My Books")
    st.caption("Students can check their borrowed books and due dates here.")

    roll = st.text_input("Roll Number", key="mybooks_roll")
    if st.button("Show my books", key="mybooks_btn"):
        if roll.strip():
            st.session_state["mybooks_query"] = roll.strip()
        else:
            st.error("Enter a roll number.")

    query = st.session_state.get("mybooks_query")
    if not query:
        return

    loans = db.active_loans(query)
    if not loans:
        st.info(f"No active borrows for roll number {query}.")
        return

    st.caption(f"{len(loans)} active borrow(s) for {query}")
    for loan in loans:
        overdue, days = _due_info(loan["due_date"])
        if overdue:
            st.error(
                f"**{loan['title']}** — OVERDUE by {days} day(s) "
                f"(was due {str(loan['due_date'])[:10]})"
            )
        else:
            st.warning(
                f"**{loan['title']}** — due {str(loan['due_date'])[:10]}"
            )


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
            if overdue:
                st.error(f"Overdue by {days} day(s) — collect immediately.")

            col1, col2 = st.columns(2)
            if col1.button("↩ Mark Returned", key=f"return_{loan['id']}"):
                ok, msg = db.return_book(loan["id"])
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

        rows.append(
            {
                "Student": r["name"],
                "Roll No": r["roll_number"],
                "Book": r["title"],
                "Borrowed": r["borrow_date"],
                "Due": str(r["due_date"])[:19],
                "Returned": r["return_date"],
                "Status": status,
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
    