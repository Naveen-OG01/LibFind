"""Admin Reports & CSV Exports."""
import streamlit as st
from libfind import db

def render():
    st.title("📥 Export Reports")
    st.caption("Download CSV files for inventory, student data, and fine collections.")
    
    st.info("💡 These files can be opened in **Microsoft Excel** or **Google Sheets**.")

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("📚 Book Inventory")
        st.write("Download a full list of all books, total copies, and available stock.")
        if st.button("Generate Inventory CSV", use_container_width=True):
            with st.spinner("Generating..."):
                csv_data = db.export_full_inventory()
                st.download_button(
                    label="⬇️ Download Inventory.csv",
                    data=csv_data,
                    file_name="libfind_inventory.csv",
                    mime="text/csv",
                    use_container_width=True
                )

    with col2:
        st.subheader("🎓 Student List")
        st.write("Download a list of all registered students and their roll numbers.")
        if st.button("Generate Student CSV", use_container_width=True):
            with st.spinner("Generating..."):
                csv_data = db.export_all_students()
                st.download_button(
                    label="⬇️ Download Students.csv",
                    data=csv_data,
                    file_name="libfind_students.csv",
                    mime="text/csv",
                    use_container_width=True
                )

    with col3:
        st.subheader("💰 Fine Reports")
        st.write("Download a list of all fines, paid/unpaid statuses, and due dates.")
        if st.button("Generate Fines CSV", use_container_width=True):
            with st.spinner("Generating..."):
                csv_data = db.export_fine_report()
                st.download_button(
                    label="⬇️ Download Fines.csv",
                    data=csv_data,
                    file_name="libfind_fines.csv",
                    mime="text/csv",
                    use_container_width=True
                )