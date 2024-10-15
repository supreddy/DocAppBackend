import sqlite3

# Database file
DATABASE = "./test.db"

# Function to update the 'type' column to 'link' for specific records
def update_type_to_link():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        # Example: Update the type column to 'link' for all records where the title contains "http"
        cursor.execute('''
            UPDATE sources 
            SET type = 'link' 
            WHERE title LIKE '%http%' OR summary LIKE '%http%'
        ''')
        
        # Commit the changes
        conn.commit()

        print(f"Records updated successfully. Total rows affected: {cursor.rowcount}")
    
    except sqlite3.Error as e:
        print(f"Error updating 'type' column: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    update_type_to_link()