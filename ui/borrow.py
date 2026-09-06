import streamlit as st
from datetime import datetime, timedelta
from libfind import db

def borrow_page():
    st.title("📚 Book Borrowing")
    
    tab1, tab2, tab3 = st.tabs(["Borrow Book", "Return Book", "View Records"])
    
    with tab1:
        st.subheader("Borrow a Book")
        
        # Student info
        student_name = st.text_input("Student Name")
        student_email = st.text_input("Email")
        roll_number = st.text_input("Roll Number")
        
        # Book selection
        books = db.get_all_books()
        book_options = {f"{b['title']} by {b['author']}": b['id'] for b in books}
        selected_book = st.selectbox("Select Book", list(book_options.keys()))
        
        due_days = st.number_input("Loan Period (days)", min_value=1, max_value=30, value=14)
        
        if st.button("Borrow Book"):
            if student_name and student_email and roll_number:
                conn = db.get_connection()
                cur = conn.cursor()
                
                # Create student if not exists
                cur.execute(
                    "INSERT OR IGNORE INTO students (name, email, roll_number) VALUES (?, ?, ?)",
                    (student_name, student_email, roll_number)
                )
                
                # Get student ID
                cur.execute("SELECT id FROM students WHERE roll_number = ?", (roll_number,))
                student_id = cur.fetchone()[0]
                
                # Add borrow record
                due_date = datetime.now() + timedelta(days=due_days)
                cur.execute(
                    "INSERT INTO borrows (student_id, book_id, due_date) VALUES (?, ?, ?)",
                    (student_id, book_options[selected_book], due_date)
                )
                
                # Update available copies
                cur.execute(
                    "UPDATE books SET available_copies = available_copies - 1 WHERE id = ?",
                    (book_options[selected_book],)
                )
                
                conn.commit()
                conn.close()
                st.success("Book borrowed successfully!")
                st.rerun()
            else:
                st.error("Please fill all fields")
    
    with tab2:
        st.subheader("Return a Book")
        
        conn = db.get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT b.id, s.name, s.roll_number, bk.title, b.borrow_date, b.due_date
            FROM borrows b
            JOIN students s ON b.student_id = s.id
            JOIN books bk ON b.book_id = bk.id
            WHERE b.status = 'borrowed'
        """)
        
        records = cur.fetchall()
        
        if records:
            for record in records:
                with st.expander(f"{record[1]} - {record[3]}"):
                    st.write(f"Roll: {record[2]}")
                    st.write(f"Borrowed: {record[4]}")
                    st.write(f"Due: {record[5]}")
                    
                    if st.button("Mark Returned", key=f"return_{record[0]}"):
                        cur.execute(
                            "UPDATE borrows SET status = 'returned', return_date = CURRENT_TIMESTAMP WHERE id = ?",
                            (record[0],)
                        )
                        cur.execute(
                            "UPDATE books SET available_copies = available_copies + 1 WHERE id = (SELECT book_id FROM borrows WHERE id = ?)",
                            (record[0],)
                        )
                        conn.commit()
                        st.success("Book returned!")
                        st.rerun()
        else:
            st.info("No books currently borrowed")
        
        conn.close()
    
    with tab3:
        st.subheader("All Borrowing Records")
        
        conn = db.get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT s.name, s.roll_number, bk.title, b.borrow_date, b.due_date, b.return_date, b.status
            FROM borrows b
            JOIN students s ON b.student_id = s.id
            JOIN books bk ON b.book_id = bk.id
            ORDER BY b.borrow_date DESC
        """)
        
        records = cur.fetchall()
        conn.close()
        
        if records:
            import pandas as pd
            df = pd.DataFrame(records, columns=["Student", "Roll No", "Book", "Borrowed", "Due", "Returned", "Status"])
            st.dataframe(df)
        else:
            st.info("No records yet")
