import sqlite3
import pathlib

db_path = pathlib.Path(r"G:\AI\E-zzio\data\workspace_index.db")

if not db_path.exists():
    print(f"❌ Base de données introuvable : {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Récupération de l'ensemble des tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [r[0] for r in cursor.fetchall()]

keywords = ["h3stiana", "tatouage", "rock", "métal", "metal"]
matches_found = 0

print(f"🔍 Inspection de {db_path.name} ({len(tables)} tables trouvées)...\n")

for table in tables:
    try:
        cursor.execute(f"SELECT * FROM \"{table}\"")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        for row in rows:
            row_str = " ".join([str(val) for val in row if val is not None])
            if any(kw in row_str.lower() for kw in keywords):
                matches_found += 1
                print(f"============================================================")
                print(f"📌 TABLE : {table}")
                print(f"============================================================")
                for col_name, val in zip(columns, row):
                    if val and any(kw in str(val).lower() for kw in keywords):
                        print(f"  👉 [{col_name}] :\n{val}\n")
    except Exception as e:
        continue

conn.close()

if matches_found == 0:
    print("⚠️ Aucun enregistrement textuel explicite n'a pu être extrait avec ces mots-clés.")
