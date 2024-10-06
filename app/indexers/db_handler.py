import sqlite3

# Path to the database file
DATABASE = './test.db'

# Initialize the database and create the `subtopic_entries` table if it doesn't exist
def init_db():
    """
    Initialize the database, creating the subtopic_entries table if git doesn't exist.
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subtopic_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subtopic_name TEXT UNIQUE NOT NULL,
            blob_urls TEXT  -- Store array of blob URLs as a comma-separated string
        )
    ''')
    conn.commit()
    conn.close()

def update_or_insert_subtopic(subtopic_name: str, new_blob_urls: list[str]) -> list[str]:
    """
    Update or insert subtopic with associated blob URLs into the subtopic_entries table and return all blob URLs.

    :param subtopic_name: The subtopic name.
    :param new_blob_urls: List of new blob URLs.
    :return: The complete list of blob URLs for the subtopic.
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Check if subtopic already exists
    cursor.execute('SELECT blob_urls FROM subtopic_entries WHERE subtopic_name = ?', (subtopic_name,))
    result = cursor.fetchone()

    if result:
        # Subtopic exists, append new URLs to the existing ones
        existing_blob_urls = result[0].split(",") if result[0] else []
        updated_blob_urls = list(set(existing_blob_urls + new_blob_urls))  # Avoid duplicates
        updated_blob_urls_str = ",".join(updated_blob_urls)

        cursor.execute('''
            UPDATE subtopic_entries
            SET blob_urls = ?
            WHERE subtopic_name = ?
        ''', (updated_blob_urls_str, subtopic_name))

        conn.commit()
        conn.close()
        return updated_blob_urls  # Return the complete set of blob URLs
    else:
        # Subtopic doesn't exist, create a new entry
        blob_urls_str = ",".join(new_blob_urls)
        cursor.execute('''
            INSERT INTO subtopic_entries (subtopic_name, blob_urls)
            VALUES (?, ?)
        ''', (subtopic_name, blob_urls_str))

        conn.commit()
        conn.close()
        return new_blob_urls  # Return the new blob URLs
    