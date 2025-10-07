import os
import sqlite3

print("🔄 RESETTING DATABASE...")

# Hapus semua file database yang mungkin
db_files = [
    'guardiantix.db',
    'instance/guardiantix.db',
    '../guardiantix.db'
]

for db_file in db_files:
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"🗑️ Deleted: {db_file}")

# Buat database baru
print("📁 Creating new database...")
conn = sqlite3.connect('guardiantix.db')
cursor = conn.cursor()

# Buat tabel
cursor.execute('''
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(80) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    phone VARCHAR(20),
    join_date DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

conn.commit()
conn.close()

print("✅ Database reset complete!")
print("📁 Current directory:", os.getcwd())
print("📁 Files in directory:", [f for f in os.listdir('.') if f.endswith('.db')])