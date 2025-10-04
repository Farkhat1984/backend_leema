import sqlite3

conn = sqlite3.connect('fashion_platform.db')
cursor = conn.cursor()

# Check existing transaction types
cursor.execute('SELECT DISTINCT type FROM transactions')
print("Existing transaction types:")
for row in cursor.fetchall():
    print(f"  - {row[0]}")

# Check existing transaction statuses
cursor.execute('SELECT DISTINCT status FROM transactions')
print("\nExisting transaction statuses:")
for row in cursor.fetchall():
    print(f"  - {row[0]}")

# Check table schema
cursor.execute('PRAGMA table_info(transactions)')
cols = cursor.fetchall()
print(f"\nTransaction table has {len(cols)} columns:")
for row in cols:
    print(f"  {row[1]}: {row[2]}")

# Check for description column specifically
has_description = any(col[1] == 'description' for col in cols)
print(f"\nHas 'description' column: {has_description}")

conn.close()
