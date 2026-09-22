import sqlite3

DATABASE = "food_waste.db"


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():

    connection = get_db_connection()

    # ---------------- USERS ----------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT,
            role TEXT NOT NULL
        )
    """)


    # ---------------- FOOD DONATIONS ----------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS food_donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_id INTEGER NOT NULL,
            food_name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            description TEXT,
            prepared_time TEXT,
            available_until TEXT,
            location TEXT NOT NULL,
            status TEXT DEFAULT 'Available',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (donor_id)
            REFERENCES users(id)
        )
    """)


    # ---------------- FOOD REQUESTS ----------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS food_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            quantity_requested INTEGER NOT NULL,
            request_status TEXT DEFAULT 'Pending',
            request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (food_id)
            REFERENCES food_donations(id),

            FOREIGN KEY (receiver_id)
            REFERENCES users(id)
        )
    """)


    connection.commit()
    connection.close()
