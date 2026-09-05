"""Seed the SQLite database with a realistic sample catalogue."""
from . import db

SAMPLE_BOOKS = [
    # (title, author, isbn, category, publisher, year, total, available, shelf, rack)
    ("Python Crash Course", "Eric Matthes", "9781593279288", "Computer Science", "No Starch Press", 2019, 8, 7, "CS-1", "R2"),
    ("Introduction to Algorithms", "Thomas H. Cormen", "9780262033848", "Computer Science", "MIT Press", 2009, 4, 3, "CS-1", "R1"),
    ("Clean Code", "Robert C. Martin", "9780132350884", "Computer Science", "Prentice Hall", 2008, 10, 8, "CS-2", "R1"),
    ("The Pragmatic Programmer", "Andrew Hunt", "9780201616224", "Computer Science", "Addison-Wesley", 1999, 5, 5, "CS-2", "R2"),
    ("Data Structures & Algorithms in Python", "Michael T. Goodrich", "9781118290279", "Computer Science", "Wiley", 2013, 6, 4, "CS-3", "R1"),
    ("Database System Concepts", "Abraham Silberschatz", "9780078022159", "Computer Science", "McGraw Hill", 2019, 3, 2, "CS-3", "R2"),
    ("Operating System Concepts", "Abraham Silberschatz", "9781119800361", "Computer Science", "Wiley", 2018, 3, 1, "CS-4", "R1"),
    ("Computer Networking: A Top-Down Approach", "James Kurose", "9780136681557", "Computer Science", "Pearson", 2021, 5, 5, "CS-4", "R2"),
    ("Machine Learning with PyTorch and Scikit-Learn", "Sebastian Raschka", "9781801819312", "Computer Science", "Packt", 2022, 8, 8, "CS-5", "R1"),
    ("Eloquent JavaScript", "Marijn Haverbeke", "9781593279509", "Computer Science", "No Starch Press", 2018, 4, 0, "JS-1", "R1"),

    ("Calculus: Early Transcendentals", "James Stewart", "9781285741550", "Mathematics", "Cengage", 2015, 5, 4, "MA-1", "R1"),
    ("Linear Algebra Done Right", "Sheldon Axler", "9783319110790", "Mathematics", "Springer", 2015, 4, 4, "MA-1", "R2"),
    ("Discrete Mathematics and Its Applications", "Kenneth H. Rosen", "9780073383095", "Mathematics", "McGraw Hill", 2012, 6, 3, "MA-2", "R1"),
    ("Introduction to Probability", "Dimitri P. Bertsekas", "9781886529236", "Mathematics", "Athena Scientific", 2008, 3, 3, "MA-2", "R2"),
    ("Mathematical Statistics with Applications", "Dennis Wackerly", "9780495110811", "Mathematics", "Cengage", 2007, 2, 1, "MA-3", "R1"),

    ("Concepts of Modern Physics", "Arthur Beiser", "9780070048140", "Physics", "McGraw Hill", 2003, 5, 5, "PH-1", "R1"),
    ("Classical Mechanics", "Herbert Goldstein", "9780201657029", "Physics", "Addison-Wesley", 2002, 3, 0, "PH-1", "R2"),
    ("University Physics with Modern Physics", "Hugh Young", "9780135159705", "Physics", "Pearson", 2019, 10, 7, "PH-2", "R1"),

    ("Microelectronic Circuits", "Adel S. Sedra", "9780199339136", "Electronics", "Oxford University Press", 2015, 6, 4, "EC-1", "R1"),
    ("Signals and Systems", "Alan V. Oppenheim", "9780138147570", "Electronics", "Pearson", 1997, 7, 5, "EC-2", "R1"),
    ("Electronic Devices and Circuit Theory", "Robert Boylestad", "9780135026496", "Electronics", "Pearson", 2009, 3, 1, "EC-2", "R2"),

    ("Pride and Prejudice", "Jane Austen", "9780141439518", "Literature", "Penguin Classics", 2002, 4, 3, "LIT-A", "R1"),
    ("1984", "George Orwell", "9780451524935", "Literature", "Signet", 1950, 8, 5, "LIT-A", "R2"),
    ("To Kill a Mockingbird", "Harper Lee", "9780061120084", "Literature", "Harper Perennial", 2006, 6, 6, "LIT-B", "R1"),
    ("The Great Gatsby", "F. Scott Fitzgerald", "9780743273565", "Literature", "Scribner", 2004, 4, 0, "LIT-B", "R2"),
    ("Harry Potter and the Philosopher's Stone", "J.K. Rowling", "9780747532699", "Literature", "Bloomsbury", 1997, 5, 4, "LIT-C", "R1"),
    ("The Alchemist", "Paulo Coelho", "9780062315007", "Literature", "HarperOne", 2014, 7, 4, "LIT-C", "R2"),

    ("Quantitative Aptitude for Competitive Examinations", "R.S. Aggarwal", "9789352833322", "Competitive Exams", "S. Chand", 2017, 15, 10, "COMP-1", "R1"),
    ("Word Power Made Easy", "Norman Lewis", "9788183071004", "Competitive Exams", "Goyal Publishers", 2009, 12, 8, "COMP-1", "R2"),
    ("A Modern Approach to Verbal & Non-Verbal Reasoning", "R.S. Aggarwal", "9788121905510", "Competitive Exams", "S. Chand", 2010, 9, 7, "COMP-2", "R1"),
    ("General Knowledge 2025", "Manohar Pandey", "9789355017103", "Competitive Exams", "Arihant", 2024, 11, 11, "COMP-2", "R2"),
]


def seed_if_empty():
    if db.count_books() > 0:
        return

    for book in SAMPLE_BOOKS:
        db.add_book(*book)
