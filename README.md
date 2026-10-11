# 📚 LibFind — Search. Locate. Read.

A complete **Library Management System** for colleges, built with Streamlit.
Students can search the catalogue, see book covers and shelf locations, and
borrow books — while librarians manage inventory through a password-protected
admin panel with live analytics.

**🔗 Live demo:** https://libfind-tjcrkygdzvp3tofec2gcfd.streamlit.app/

---

## ✨ Features

### 🔎 Student Search
- Search by **title, author, ISBN, or category**
- Fuzzy matching powered by `rapidfuzz`
- Book cover images (Cloudinary CDN)
- Copy availability + exact **shelf / rack location**
- Similar-book recommendations based on category, author, year and title

### 🛠 Admin Interface
- Password-protected (`admin` / `admin123`)
- Add, edit, and delete books
- Upload book cover images
- Manage categories (with safe deletion rules)

### 📊 Library Analytics
- Collection summary (titles, copies, availability %)
- Category-wise copies chart (Plotly)
- Top authors chart
- Low-availability warnings

### 📖 Book Borrowing
- Register students (name, email, roll number)
- Borrow with configurable loan period
- Return books and auto-update availability
- Full borrow history with due dates

---

## 🖼 Screenshots

| Student Search | Admin Interface |
|---|---|
| ![Search](screenshots/search.png) | ![Admin](screenshots/admin.png) |

| Analytics | Borrowing |
|---|---|
| ![Analytics](screenshots/analytics.png) | ![Borrowing](screenshots/borrowing.png) |

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Frontend / UI | Streamlit |
| Charts | Plotly Express |
| Database | Turso (cloud SQLite via `libsql`) |
| Fuzzy search | RapidFuzz |
| Images | Cloudinary |
| Local fallback | SQLite (`data/libfind.db`) |

---

## 🚀 Run Locally

```bash
git clone https://github.com/Naveen-OG01/LibFind.git
cd LibFind
pip install -r requirements.txt
streamlit run app.py