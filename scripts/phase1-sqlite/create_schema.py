import sqlite3
import os

# On récupère le chemin absolu du script actuel
current_script_path = os.path.abspath(__file__)

# On remonte l'arborescence pour trouver la racine 'cineexplorer'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(current_script_path)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'imdb.db')

def create_schema():
    print(f"Création de la base de données dans : {DB_PATH}")

    # Connexion (crée le fichier s'il n'existe pas)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Activation des clés étrangères (important pour SQLite)
    cursor.execute("PRAGMA foreign_keys = ON;")

    # --- 1. Tables Principales ---

    # Table MOVIES
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

    # Table PERSONS
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

    # --- 2. Tables "One-to-One" ou Extension ---

    # Table RATINGS (Liée à Movies)
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

    # --- 3. Tables de Détails (Weak Entities) ---

    # Table TITLES (Titres alternatifs)
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

    # Table GENRES (Multivaluée)
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

    # --- 4. Tables d'Association (Many-to-Many) ---

    # Table DIRECTORS
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

    # Table WRITERS
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

    # Table PRINCIPALS (Casting principal avec ordre)
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

    # Table CHARACTERS (Personnages joués)
    # Note : Le CSV characters ne semble pas avoir d'ordering unique,
    # donc la PK est composite sur (mid, pid, name) pour éviter les doublons stricts
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
    # Index optionnel pour accélérer les recherches de personnages
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chars_mid ON characters(mid);")

    print("Schéma créé avec succès.")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_schema()