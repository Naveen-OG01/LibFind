# 📚 LibFind — Smart Library Management System

A complete cloud-hosted Library Management System built for colleges. LibFind allows students to search, locate, and reserve books, while giving librarians a powerful dashboard to manage circulation, fines, and inventory.

**🔗 Live Demo:** [Insert your Streamlit Link Here]

## ✨ Features
- **Student Portal:** Secure login, live book search, reserve checked-out books.
- **Librarian Dashboard:** Live metrics, overdue alerts, and reservation tracking.
- **Barcode Scanner:** Quick-checkout page for fast circulation.
- **Bulk Import:** Upload `.csv` files to add thousands of books or students at once.
- **Fine Management:** Automatically calculate ₹5/day fines and track payments.
- **Automated Emails:** Send overdue alerts directly to student emails.
- **Cloud Database:** Powered by Turso (SQLite) for permanent cloud storage.

## 🛠 Tech Stack
- **Frontend:** Streamlit
- **Database:** Turso (Cloud SQLite), LibSQL
- **Security:** PBKDF2 SHA-256 Password Hashing
- **Charts:** Plotly Express
- **Mailing:** Python `smtplib`

## 🚀 Run Locally
1. Clone the repo: `git clone https://github.com/Naveen-OG01/LibFind.git`
2. Install requirements: `pip install -r requirements.txt`
3. Create `.streamlit/secrets.toml` and add your Turso/Gmail keys.
4. Run the app: `streamlit run app.py`