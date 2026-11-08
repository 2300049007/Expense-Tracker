
import sqlite3
import os

def init_db(app):

    # Create the database folder if it doesn't exist
    os.makedirs(app.instance_path, exist_ok=True)

    # Database file location
    db_path = os.path.join(app.instance_path, "expenses.db")

    # Connect to SQLite
    connection = sqlite3.connect(db_path)

    # Create expenses table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    print("Database created successfully!")
    # Create income table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL UNIQUE,
            amount REAL NOT NULL
        )
    """)

    # Save changes and close connection
    connection.commit()
    connection.close()