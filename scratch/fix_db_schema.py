import sqlite3

def main():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(admin_surveys)")
    columns = c.fetchall()
    print("Columns in admin_surveys:")
    for col in columns:
        print(col)
        
    # Let's try to add the column if it's missing
    col_names = [col[1] for col in columns]
    if 'short_code' not in col_names:
        print("short_code column is missing. Adding it...")
        try:
            c.execute("ALTER TABLE admin_surveys ADD COLUMN short_code TEXT")
            conn.commit()
            print("Successfully added short_code column.")
        except Exception as e:
            print("Failed to add column:", e)
            
    conn.close()

if __name__ == "__main__":
    main()
