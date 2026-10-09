"""Book borrowing / returning UI."""
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from libfind import db


def borrow_page():
    st.title("📚 Book Borrowing")

    tab1, tab2, tab3 = st.tabs(["Borrow Book", "Return Book", "View Records"])

    with tab1:
        _borrow_tab()

    with tab2:
        _return_tab()

    with tab3:
        _records_tab()


def _borrow_tab():
    st.subheader("Borrow a Book")

    student_name = st.text_input("Student Name", key="borrow_name")
    student_email = st.text_input("Email", key="borrow_email")
    roll_number = st.text_input("Roll Number", key="borrow_roll")

    books = db.get_all_books()
    if not books:
        st.info("No books in the catalogue yet.")
        return

    book_options = {f"{b['title']} by {b['author']}": b["id"] for b in books}
    selected_book = st.selectbox("Select Book", list(book_options.keys()), key="borrow_book")
    due_days = st.number_input(
        "Loan Period (days)", min_value=1, max_value=30, value=14, key="borrow_days"
    )

    if st.button("Borrow Book", key="borrow_btn"):
        missing = [
            label
            for label, value in [
                ("Student Name", student_name),
                ("Email", student_email),
                ("Roll Number", roll_number),
                ("Select Book", selected_book),
            ]
            if not (value or "").strip()
        ]

        if missing:
            st.error("Please fill: " + ", ".join(missing))
            return

        book_id = book_options[selected_book]
        roll = roll_number.strip()

        conn = db.get_connection()
        cur = conn.cursor()

        cur.execute(
            "INSERT OR IGNORE INTO students (name, email, roll_number) VALUES (?, ?, ?)",
            (student_name.strip(), student_email.strip(), roll),
        )
        conn.commit()

        cur.execute("SELECT id FROM students WHERE roll_number = ?", (roll,))
        row = cur.fetchone()
        if row is None:
            st.error("Could not register the student record. Check the roll number/email.")
            conn.close()
            return
        student_id = row[0]

        due_date = (datetime.now() + timedelta(days=due_days)).isoformat()

        cur.execute(
            "INSERT INTO borrows (student_id, book_id, due_date) VALUES (?, ?, ?)",
            (student_id, book_id, due_date),
        )
        cur.execute(
            "UPDATE books SET available_copies = available_copies - 1 "
            "WHERE id = ? AND available_copies > 0",
            (book_id,),
        )
        conn.commit()
        conn.close()

        st.success("Book borrowed successfully!")
        st.rerun()


def _return_tab():
    st.subheader("Return a Book")

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.id, s.name, s.roll_number, bk.title,
               b.borrow_date, b.due_date
        FROM borrows b
        JOIN students s ON b.student_id = s.id
        JOIN books bk ON b.book_id = bk.id
        WHERE b.status = 'borrowed'
        ORDER BY b.borrow_date DESC
        """
    )
    records = cur.fetchall()
    conn.close()

    if not records:
        st.info("No books currently borrowed")
        return

    for record in records:
        with st.expander(f"{record[1]} — {record[3]}"):
            st.write(f"Roll: {record[2]}")
            st.write(f"Borrowed: {record[4]}")
            st.write(f"Due: {record[5]}")

            if st.button("Mark Returned", key=f"return_{record[0]}"):
                conn = db.get_connection()
                cur = conn.cursor()
                cur.execute(
                    "UPDATE borrows SET status = 'returned', "
                    "return_date = CURRENT_TIMESTAMP WHERE id = ?",
                    (record[0],),
                )
                cur.execute(
                    "UPDATE books SET available_copies = available_copies + 1 "
                    "WHERE id = (SELECT book_id FROM borrows WHERE id = ?)",
                    (record[0],),
                )
                conn.commit()
                conn.close()
                st.success("Book returned!")
                st.rerun()


def _records_tab():
    st.subheader("All Borrowing Records")

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT s.name, s.roll_number, bk.title,
               b.borrow_date, b.due_date, b.return_date, b.status
        FROM borrows b
        JOIN students s ON b.student_id = s.id
        JOIN books bk ON b.book_id = bk.id
        ORDER BY b.borrow_date DESC
        """
    )
    records = cur.fetchall()
    conn.close()

    if not records:
        st.info("No records yet")
        return

    df = pd.DataFrame(
        [
            {
                "Student": r["name"],
                "Roll No": r["roll_number"],
                "Book": r["title"],
                "Borrowed": r["borrow_date"],
                "Due": r["due_date"],
                "Returned": r["return_date"],
                "Status": r["status"],
            }
            for r in records
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    