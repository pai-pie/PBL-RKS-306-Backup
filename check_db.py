import sqlite3
from datetime import datetime

def check_database():
    print("🔍 CHECKING DATABASE CONTENT")
    print("=" * 60)
    
    conn = sqlite3.connect('guardiantix.db')
    cursor = conn.cursor()
    
    # Cek semua tabel
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("📊 TABLES:", [table[0] for table in tables])
    
    print("\n👥 USER DATA:")
    print("-" * 60)
    
    # Cek struktur tabel user
    cursor.execute("PRAGMA table_info(user);")
    columns = cursor.fetchall()
    print("Columns:", [col[1] for col in columns])
    
    # Ambil semua data user
    cursor.execute("SELECT * FROM user;")
    users = cursor.fetchall()
    
    print(f"\nTotal users: {len(users)}")
    print("-" * 60)
    
    for user in users:
        user_id, username, email, password_hash, role, phone, join_date = user
        print(f"ID: {user_id}")
        print(f"  Username: {username}")
        print(f"  Email: {email}")
        print(f"  Role: {role}")
        print(f"  Join Date: {join_date}")
        print(f"  Password Hash: {password_hash[:50]}...")
        print("-" * 40)
    
    conn.close()

if __name__ == "__main__":
    check_database()