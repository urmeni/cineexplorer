import sqlite3
import pymongo
import os
import time
import math

# --- CONFIGURATION ---
BATCH_SIZE = 5000  # Nombre de documents insérés à la fois
DB_NAME = "imdb_project"  # Nom de la base MongoDB

# Chemins
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SQLITE_DB_PATH = os.path.join(BASE_DIR, 'data', 'imdb.db')


def migrate_flat():
    # 1. Connexion SQLite
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"❌ Erreur : Base SQLite introuvable à {SQLITE_DB_PATH}")
        return

    print(f"🔌 Connexion à SQLite ({SQLITE_DB_PATH})...")
    conn_sql = sqlite3.connect(SQLITE_DB_PATH)
    # Permet d'accéder aux colonnes par leur nom (comme un dictionnaire)
    conn_sql.row_factory = sqlite3.Row
    cursor = conn_sql.cursor()

    # 2. Connexion MongoDB
    print(f"🔌 Connexion à MongoDB (localhost:27017 / DB: {DB_NAME})...")
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db_mongo = client[DB_NAME]

    # 3. Récupérer la liste de toutes les tables SQLite
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row['name'] for row in cursor.fetchall() if row['name'] != 'sqlite_sequence']

    print(f"\n🚀 Démarrage de la migration de {len(tables)} tables vers des collections plates...")
    start_global = time.time()

    stats = []

    for table in tables:
        print(f"\n📦 Traitement de la table : '{table}'")

        # A. Nettoyage : On vide la collection cible pour éviter les doublons
        db_mongo[table].drop()

        # B. Lecture SQLite (Comptage préalable pour la barre de progression)
        count_cursor = conn_sql.execute(f"SELECT COUNT(*) FROM {table}")
        total_rows = count_cursor.fetchone()[0]

        if total_rows == 0:
            print("   ⚠️ Table vide, ignorée.")
            continue

        # C. Migration par lots (Batch)
        cursor.execute(f"SELECT * FROM {table}")

        inserted_count = 0
        start_table = time.time()

        while True:
            # On récupère X lignes
            rows = cursor.fetchmany(BATCH_SIZE)
            if not rows:
                break

            # Conversion : SQLite Row -> Dictionnaire Python (JSON)
            documents = [dict(row) for row in rows]

            # Insertion MongoDB
            db_mongo[table].insert_many(documents)

            inserted_count += len(documents)

            # Affichage progression
            progress = (inserted_count / total_rows) * 100
            print(f"   ↳ {inserted_count}/{total_rows} ({progress:.1f}%)", end='\r')

        duration = time.time() - start_table

        # D. Vérification (Comptage MongoDB)
        mongo_count = db_mongo[table].count_documents({})

        status = "✅ OK" if mongo_count == total_rows else "❌ ÉCART"
        print(f"   {status} | SQL: {total_rows} -> Mongo: {mongo_count} en {duration:.2f}s")

        stats.append({
            "table": table,
            "sql": total_rows,
            "mongo": mongo_count,
            "status": status
        })

    conn_sql.close()
    client.close()

    # 4. Rapport final
    print("\n" + "=" * 50)
    print("BILAN MIGRATION")
    print("=" * 50)
    print(f"{'TABLE':<15} | {'SQL':<10} | {'MONGO':<10} | {'ÉTAT':<5}")
    print("-" * 50)
    for s in stats:
        print(f"{s['table']:<15} | {s['sql']:<10} | {s['mongo']:<10} | {s['status']}")
    print("=" * 50)
    print(f"✨ Migration terminée en {time.time() - start_global:.2f} secondes.")


if __name__ == "__main__":
    migrate_flat()