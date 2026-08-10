import sqlite3
import os

dbs = [
    r"G:\AI\E-zzio\runtime\memory\sqlite\cognitive_store.db",
    r"G:\AI\E-zzio\runtime\memory\database\memory.sqlite3"
]

for db_path in dbs:
    print(f"\n============================================================")
    print(f" RADIOGRAPHIE DE : {db_path.split('E-zzio')[1]}")
    print(f"============================================================")
    
    if not os.path.exists(db_path):
        print("[X] Base de données introuvable.")
        continue
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("[-] Base de données vide ou aucune table trouvée.")
            
        for table_name, table_sql in tables:
            print(f"\n--- TABLE : {table_name} ---")
            print(table_sql)
            
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f" -> Enregistrements : {count}")
            
        conn.close()
    except Exception as e:
        print(f"[!] Erreur de lecture : {e}")
