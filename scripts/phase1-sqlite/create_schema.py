import sqlite3
import os

# --- CONFIGURATION CHEMINS (Identique) ---
current_script_path = os.path.abspath(__file__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(current_script_path)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'imdb-tiny.db')

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


def create_schema():
    print(f"🚀 Création du schéma dans : {DB_PATH}")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
    except sqlite3.OperationalError as e:
        print(f"❌ Erreur : {e}")
        return

    # --- 1. Tables Principales ---
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS movies
                   (
                       mid
                       TEXT
                       PRIMARY
                       KEY,
                       primaryTitle
                       TEXT,
                       originalTitle
                       TEXT,
                       isAdult
                       INTEGER,
                       startYear
                       INTEGER,
                       runtimeMinutes
                       INTEGER
                   );
                   """)

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS persons
                   (
                       pid
                       TEXT
                       PRIMARY
                       KEY,
                       primaryName
                       TEXT,
                       birthYear
                       INTEGER,
                       deathYear
                       INTEGER
                   );
                   """)

    # --- 2. Tables Extensions ---
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS ratings
                   (
                       mid
                       TEXT
                       PRIMARY
                       KEY,
                       averageRating
                       REAL,
                       numVotes
                       INTEGER,
                       FOREIGN
                       KEY
                   (
                       mid
                   ) REFERENCES movies
                   (
                       mid
                   )
                       );
                   """)

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS titles
                   (
                       mid
                       TEXT,
                       ordering
                       INTEGER,
                       title
                       TEXT,
                       region
                       TEXT,
                       language
                       TEXT,
                       isOriginalTitle
                       INTEGER,
                       PRIMARY
                       KEY
                   (
                       mid,
                       ordering
                   ),
                       FOREIGN KEY
                   (
                       mid
                   ) REFERENCES movies
                   (
                       mid
                   )
                       );
                   """)

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS genres
                   (
                       mid
                       TEXT,
                       genre
                       TEXT,
                       PRIMARY
                       KEY
                   (
                       mid,
                       genre
                   ),
                       FOREIGN KEY
                   (
                       mid
                   ) REFERENCES movies
                   (
                       mid
                   )
                       );
                   """)

    # --- 3. NOUVELLES TABLES ---

    # Table PROFESSIONS (pid, jobName)
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS professions
                   (
                       pid
                       TEXT,
                       jobName
                       TEXT,
                       PRIMARY
                       KEY
                   (
                       pid,
                       jobName
                   ),
                       FOREIGN KEY
                   (
                       pid
                   ) REFERENCES persons
                   (
                       pid
                   )
                       );
                   """)

    # Table KNOWN_FOR (pid, mid) - Films pour lesquels la personne est connue
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS known_for
                   (
                       pid
                       TEXT,
                       mid
                       TEXT,
                       PRIMARY
                       KEY
                   (
                       pid,
                       mid
                   ),
                       FOREIGN KEY
                   (
                       pid
                   ) REFERENCES persons
                   (
                       pid
                   ),
                       FOREIGN KEY
                   (
                       mid
                   ) REFERENCES movies
                   (
                       mid
                   )
                       );
                   """)

    # --- 4. Tables d'Association ---
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS directors
                   (
                       mid
                       TEXT,
                       pid
                       TEXT,
                       PRIMARY
                       KEY
                   (
                       mid,
                       pid
                   ),
                       FOREIGN KEY
                   (
                       mid
                   ) REFERENCES movies
                   (
                       mid
                   ),
                       FOREIGN KEY
                   (
                       pid
                   ) REFERENCES persons
                   (
                       pid
                   )
                       );
                   """)

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS writers
                   (
                       mid
                       TEXT,
                       pid
                       TEXT,
                       PRIMARY
                       KEY
                   (
                       mid,
                       pid
                   ),
                       FOREIGN KEY
                   (
                       mid
                   ) REFERENCES movies
                   (
                       mid
                   ),
                       FOREIGN KEY
                   (
                       pid
                   ) REFERENCES persons
                   (
                       pid
                   )
                       );
                   """)

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS principals
                   (
                       mid
                       TEXT,
                       ordering
                       INTEGER,
                       pid
                       TEXT,
                       category
                       TEXT,
                       job
                       TEXT,
                       PRIMARY
                       KEY
                   (
                       mid,
                       ordering
                   ),
                       FOREIGN KEY
                   (
                       mid
                   ) REFERENCES movies
                   (
                       mid
                   ),
                       FOREIGN KEY
                   (
                       pid
                   ) REFERENCES persons
                   (
                       pid
                   )
                       );
                   """)

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS characters
                   (
                       mid
                       TEXT,
                       pid
                       TEXT,
                       name
                       TEXT,
                       FOREIGN
                       KEY
                   (
                       mid
                   ) REFERENCES movies
                   (
                       mid
                   ),
                       FOREIGN KEY
                   (
                       pid
                   ) REFERENCES persons
                   (
                       pid
                   )
                       );
                   """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chars_mid ON characters(mid);")

    # Index utiles pour les nouvelles tables
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_professions_pid ON professions(pid);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_knownfor_pid ON known_for(pid);")

    print("✅ Schéma mis à jour avec succès (inclus professions & known_for).")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_schema()