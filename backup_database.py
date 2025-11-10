# backup_database.py
from database import Database
import os

def backup_database():
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    
    print("🔧 Creating database backup...")
    
    # Get all table data
    tables = ['users', 'events', 'tickets', 'payments', 'orders']
    
    with open('db_konser_backup.sql', 'w', encoding='utf-8') as f:
        f.write('-- GuardianTix Database Backup\n')
        f.write('SET FOREIGN_KEY_CHECKS=0;\n\n')
        
        for table in tables:
            print(f"📦 Backing up {table}...")
            
            # Get table structure
            cursor.execute(f"SHOW CREATE TABLE {table}")
            create_table = cursor.fetchone()
            if create_table:
                f.write(f'{create_table["Create Table"]};\n\n')
            
            # Get table data
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            if rows:
                columns = list(rows[0].keys())
                f.write(f'INSERT INTO {table} ({", ".join(columns)}) VALUES\n')
                
                for i, row in enumerate(rows):
                    values = []
                    for col in columns:
                        val = row[col]
                        if val is None:
                            values.append('NULL')
                        elif isinstance(val, str):
                            # Escape single quotes
                            escaped_val = str(val).replace("'", "''")
                            values.append(f"'{escaped_val}'")
                        else:
                            values.append(str(val))
                    
                    f.write(f'({", ".join(values)})')
                    f.write(',\n' if i < len(rows)-1 else ';\n\n')
        
        f.write('SET FOREIGN_KEY_CHECKS=1;\n')
        f.write('-- Backup completed\n')
    
    conn.close()
    print('✅ Backup completed: db_konser_backup.sql')

if __name__ == '__main__':
    backup_database()