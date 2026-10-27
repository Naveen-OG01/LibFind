# 📚 LibFind — Smart Library Management System

A complete, cloud-hosted Library Management System built for colleges. It features a **React Student Portal**, a **Streamlit Admin App**, and a **FastAPI Backend**.

## 🔗 Live Links
- **Student Portal (React):** [https://libfind-frontend-kwou.vercel.app](https://libfind-frontend-kwou.vercel.app)
- **Admin App (Streamlit):** [https://libfind-tjcrkygdzvp3tofec2gcfd.streamlit.app](https://libfind-tjcrkygdzvp3tofec2gcfd.streamlit.app)

## ✨ Features
- **Student Portal:** Search catalog, borrow books, view due dates, reserve checked-out books, and check unpaid fines.
- **Librarian Dashboard:** Live metrics, overdue alerts, and reservation tracking.
- **Barcode Scanner:** Quick-checkout page for fast circulation.
- **Bulk Import:** Upload `.csv` files to add thousands of books or students at once.
- **Fine Management:** Automatically calculate ₹5/day fines and track payments.
- **Automated Emails:** Send overdue alerts directly to student emails.

## 🛠 Tech Stack
- **Frontend (Student):** React.js, Vercel
- **Frontend (Admin):** Streamlit
- **Backend API:** FastAPI, Render
- **Database:** Turso (Cloud SQLite), LibSQL
- **Security:** PBKDF2 SHA-256 Password Hashing
- **Mailing:** Python `smtplib`

## 🚀 Run Locally
1. Clone the repo: `git clone https://github.com/Naveen-OG01/LibFind.git`
2. Install Python requirements: `pip install -r requirements.txt`
3. Create `.streamlit/secrets.toml` and add your Turso/Gmail/Admin keys.
4. Run the Streamlit app: `streamlit run app.py`
5. Run the FastAPI backend: `uvicorn api:app --reload`
6. (Optional) Run the React app: `cd libfind-frontend && npm start`
