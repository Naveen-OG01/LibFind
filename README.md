# 📚 LibFind — Smart Library Management System

A cloud-hosted library management system for colleges, with a React portal for students and librarians, a Streamlit app, a FastAPI backend, and a shared Turso/LibSQL database.

## 🔗 Live Links
- **Student and Librarian Portal (React):** [https://libfind-frontend-kwou.vercel.app](https://libfind-frontend-kwou.vercel.app)
- **Admin App (Streamlit):** [https://libfind-tjcrkygdzvp3tofec2gcfd.streamlit.app](https://libfind-tjcrkygdzvp3tofec2gcfd.streamlit.app)
- **React source:** [Naveen-OG01/libfind-frontend](https://github.com/Naveen-OG01/libfind-frontend)

## ✨ Features
- **Student portal:** Search by title, author, ISBN, or category; filter by availability and year; see shelf/rack locations; borrow and reserve books; review loans, due dates, reservations, and fines; and browse similar titles.
- **Student accounts:** Register and sign in with a roll number and password.
- **Librarian portal:** Dashboard metrics, overdue alerts, reservations, catalogue and category management, student management, and password resets.
- **Circulation:** Quick-scan checkout, returns, renewals, loan history, and fine tracking.
- **Imports and reports:** Bulk CSV imports for books and students, plus inventory, student, fine, and borrowing exports.
- **Analytics and notifications:** Collection, category, author, borrowing, and low-stock reports; preview and send due-date and overdue email reminders.

## 🛠 Tech Stack
- **Frontend:** React.js, Vercel
- **Additional interface:** Streamlit
- **Backend API:** FastAPI, Render
- **Database:** Turso (Cloud SQLite), LibSQL
- **Security:** PBKDF2 SHA-256 Password Hashing
- **Mailing:** Python `smtplib`

## 🚀 Run Locally
1. Clone this repository and install backend dependencies: `pip install -r requirements-api.txt`.
2. Configure Turso credentials and librarian credentials as environment variables, or configure the applicable secrets for your deployment. Email reminders also require the sender credentials.
3. Start the API: `uvicorn api:app --reload`.
4. Start the Streamlit app separately: `pip install -r requirements.txt` then `streamlit run app.py`.
5. Clone [the React repository](https://github.com/Naveen-OG01/libfind-frontend), run `npm install`, and start it with `npm start`.
6. To point the React app at a different API, set `REACT_APP_API_URL` before building it. The default is the hosted LibFind API.
