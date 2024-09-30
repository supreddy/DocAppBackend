import sqlite3
import os

DATABASE = "./test.db"
TABLE_NAME = "sources"

def reset_table():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Drop the table if it exists
    cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
    conn.commit()

    # Create the table with the new schema
    cursor.execute(f'''
        CREATE TABLE {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            summary TEXT,
            text TEXT,  -- This column stores additional block of text
            new_column_name TEXT  -- Example of an additional column
        )
    ''')
    conn.commit()
    conn.close()

    print(f"Table '{TABLE_NAME}' dropped and recreated successfully.")

if __name__ == "__main__":
    if os.path.exists(DATABASE):
        reset_table()
    else:
        print(f"Database '{DATABASE}' does not exist.")
