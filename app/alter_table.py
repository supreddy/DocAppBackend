import sqlite3

# Database file
DATABASE = "./test.db"

def alter_table_add_type_column():
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # SQL statement to alter the table by adding a 'type' column with a default value of an empty string
        alter_table_query = "ALTER TABLE sources ADD COLUMN type TEXT DEFAULT '';"
        
        # Execute the SQL statement
        cursor.execute(alter_table_query)

        # Commit the transaction
        conn.commit()

        print("Column 'type' added successfully with default blank value.")
    
    except sqlite3.OperationalError as e:
        # Catch the case when the column already exists or any other operational error occurs
        print(f"Error: {e}")
    
    finally:
        # Close the database connection
        conn.close()

# Run the function to alter the table
if __name__ == "__main__":
    alter_table_add_type_column()
