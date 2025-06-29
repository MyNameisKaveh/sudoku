# This file makes the db directory a Python package.
# Database related functions will be added here later.

# Example:
# import sqlite3
# from ..config import DB_NAME

# def get_db_connection():
#     conn = sqlite3.connect(DB_NAME)
#     conn.row_factory = sqlite3.Row
#     return conn

# def init_db():
#     conn = get_db_connection()
#     # Create tables if they don't exist
#     # Example:
#     # conn.execute('''
#     # CREATE TABLE IF NOT EXISTS users (
#     #     id INTEGER PRIMARY KEY,
#     #     telegram_id INTEGER UNIQUE NOT NULL,
#     #     first_name TEXT,
#     #     username TEXT
#     # )
#     # ''')
#     # conn.execute('''
#     # CREATE TABLE IF NOT EXISTS scores (
#     #     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     #     user_id INTEGER NOT NULL,
#     #     difficulty TEXT NOT NULL,
#     #     time_taken INTEGER, -- seconds
#     #     solved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     #     FOREIGN KEY (user_id) REFERENCES users (id)
#     # )
#     # ''')
#     conn.commit()
#     conn.close()

# if __name__ == '__main__':
#     init_db() # Initialize DB if this script is run directly
#     print(f"Database {DB_NAME} initialized or already exists.")
