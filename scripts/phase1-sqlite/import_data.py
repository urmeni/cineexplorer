import pandas as pd
import sqlite3
import os
import time

# --- CONFIGURATION DES CHEMINS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
CSV_DIR = os.path.join(DATA_DIR, 'csv/imdb-small/')
DB_PATH = os.path.join(DATA_DIR, 'imdb.db')

# --- CONFIGURATION DE L'IMPORT ---
IMPORT_CONFIG = [
    {
        'csv': 'movies.csv',
        'table': 'movies',
        'cols': ["('mid',)", "('primaryTitle',)", "('originalTitle',)", "('isAdult',)", "('startYear',)",
                 "('runtimeMinutes',)"]
    },
    {
        'csv': 'persons.csv',
        'table': 'persons',
        'cols': ["('pid',)", "('primaryName',)", "('birthYear',)", "('deathYear',)"]
    },
    {
        'csv': 'ratings.csv',
        'table': 'ratings',
        'cols': ["('mid',)", "('averageRating',)", "('numVotes',)"]
    },
    {
        'csv': 'genres.csv',
        'table': 'genres',
        'cols': ["('mid',)", "('genre',)"]
    },
    {
        'csv': 'titles.csv',
        'table': 'titles',
        'cols': ["('mid',)", "('ordering',)", "('title',)", "('region',)", "('language',)", "('isOriginalTitle',)"]
    },
    {
        'csv': 'directors.csv',
        'table': 'directors',
        'cols': ["('mid',)", "('pid',)"]
    },
    {
        'csv': 'writers.csv',
        'table': 'writers',
        'cols': ["('mid',)", "('pid',)"]
    },
    {
        'csv': 'principals.csv',
        'table': 'principals',
        'cols': ["('mid',)", "('ordering',)", "('pid',)", "('category',)", "('job',)"]
    },
    {
        'csv': 'characters.csv',
        'table': 'characters',
        'cols': ["('mid',)", "('pid',)", "('name',)"]
    }
]


def clean_col_name(col_name):
    """
    Transforme "('mid',)" en "mid"
    """
    return col_name.replace("('", "").replace("',)", "").replace("'", "")


def import_data():
    if not os.path.exists(DB_PATH):
        print(f" Erreur : La base {DB_PATH} n'existe pas.")
        return

    conn = sqlite3.connect(DB_PATH)

    # Optimisation import
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("PRAGMA journal_mode = MEMORY")
    conn.execute("PRAGMA foreign_keys = OFF")

    start_global = time.time()
    print(f" Démarrage de l'import dans {DB_PATH}...")

    for item in IMPORT_CONFIG:
        csv_file = item['csv']
        table_name = item['table']
        dirty_columns = item['cols']  # Les noms bizarres du CSV

        # On prépare le dictionnaire de renommage : "('mid',)" -> "mid"
        rename_map = {col: clean_col_name(col) for col in dirty_columns}

        csv_path = os.path.join(CSV_DIR, csv_file)

        if not os.path.exists(csv_path):
            print(f"⚠ Fichier introuvable : {csv_file}")
            continue

        print(f"\n📥 Import de {table_name}...")

        chunksize = 10000
        total_rows = 0

        try:
            # Lecture avec les noms de colonnes "sales"
            for chunk in pd.read_csv(csv_path, usecols=dirty_columns, chunksize=chunksize, low_memory=False):
                # NETTOYAGE DES NOMS DE COLONNES
                chunk.rename(columns=rename_map, inplace=True)

                # Insertion
                chunk.to_sql(table_name, conn, if_exists='append', index=False, method='multi')
                total_rows += len(chunk)
                print(f"   -> {total_rows} lignes...", end='\r')

            print(f"{table_name} : {total_rows} importées.")

        except Exception as e:
            print(f"\n Erreur sur {table_name}: {e}")
            # Debug : Affiche les colonnes trouvées par Pandas si erreur
            try:
                test_df = pd.read_csv(csv_path, nrows=1)
                print(f"   Colonnes détectées dans le CSV : {list(test_df.columns)}")
            except:
                pass

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()

    print(f"\n Terminé en {time.time() - start_global:.2f} s.")


if __name__ == "__main__":
    import_data()