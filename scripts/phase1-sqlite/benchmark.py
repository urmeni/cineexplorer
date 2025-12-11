import sqlite3
import time
import os
import queries  # Importe tes fonctions définies précédemment

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'imdb.db')


def get_db_size():
    """Retourne la taille de la base en Mo"""
    if os.path.exists(DB_PATH):
        return os.path.getsize(DB_PATH) / (1024 * 1024)
    return 0


def drop_indexes(conn):
    """Nettoie les index pour le test 'Sans Index'"""
    indexes = [
        "idx_persons_name", "idx_movies_year", "idx_genres_genre",
        "idx_principals_pid", "idx_principals_mid", "idx_ratings_avg",
        "idx_chars_mid"  # Celui qu'on avait mis dans create_schema
    ]
    for idx in indexes:
        conn.execute(f"DROP INDEX IF EXISTS {idx}")
    conn.commit()


def create_indexes(conn):
    """Crée les index stratégiques"""
    print("\n🔨 Création des index en cours...")
    start = time.time()

    # 1. Index sur les noms (Recherche textuelle - Q1, Q4, Q6, Q8)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_persons_name ON persons(primaryName)")

    # 2. Index sur les Clés Étrangères (Optimisation des JOINTURES - Toutes requêtes)
    # Note : SQLite indexe automatiquement les PK, mais pas forcément les FK dans les tables de liaison
    conn.execute("CREATE INDEX IF NOT EXISTS idx_principals_pid ON principals(pid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_principals_mid ON principals(mid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_directors_pid ON directors(pid)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_genres_mid ON genres(mid)")

    # 3. Index sur les filtres fréquents (WHERE / ORDER BY - Q2, Q5, Q7)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_genres_genre ON genres(genre)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_movies_year ON movies(startYear)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ratings_avg ON ratings(averageRating)")

    conn.commit()
    print(f" Index créés en {time.time() - start:.2f} s.")


def run_benchmark():
    conn = sqlite3.connect(DB_PATH)

    # Liste des tests (Nom, Fonction, Arguments)
    tests = [
        ("Q1 - Filmographie", queries.query_1_actor_filmography, ["Leonardo DiCaprio"]),
        ("Q2 - Top Films", queries.query_2_top_movies_by_genre, ["Drama", 1990, 2000, 10]),
        ("Q3 - Multi-rôles", queries.query_3_multi_role_actors, []),
        ("Q4 - Collaborations", queries.query_4_collaborations, ["Brad Pitt"]),
        ("Q5 - Genres Pop.", queries.query_5_popular_genres, []),
        ("Q6 - Évolution", queries.query_6_career_evolution, ["Clint Eastwood"]),
        ("Q7 - Classement", queries.query_7_genre_rankings, []),
        ("Q8 - Propulsé", queries.query_8_breakout_career, []),
        ("Q9 - Complexe", queries.query_9_complex_custom, [])
    ]

    results = {}

    print(f" Taille DB avant index : {get_db_size():.2f} Mo")

    # --- PHASE 1 : SANS INDEX ---
    print("\n⏱  Mesure des temps SANS index...")
    drop_indexes(conn)  # On s'assure d'être à nu

    for name, func, args in tests:
        start = time.time()
        func(conn, *args)
        duration = (time.time() - start) * 1000  # en ms
        results[name] = {"no_index": duration}
        print(f"   - {name}: {duration:.0f} ms")

    # --- PHASE 2 : AVEC INDEX ---
    create_indexes(conn)
    print(f" Taille DB après index : {get_db_size():.2f} Mo")

    print("\n⏱️  Mesure des temps AVEC index...")
    for name, func, args in tests:
        start = time.time()
        func(conn, *args)
        duration = (time.time() - start) * 1000  # en ms
        results[name]["with_index"] = duration
        print(f"   - {name}: {duration:.0f} ms")

    conn.close()

    # --- AFFICHAGE DU TABLEAU FINAL ---
    print("\n" + "=" * 85)
    print(f"{'REQUÊTE':<25} | {'SANS INDEX (ms)':<15} | {'AVEC INDEX (ms)':<15} | {'GAIN (%)':<10}")
    print("=" * 85)

    for name, data in results.items():
        t1 = data["no_index"]
        t2 = data["with_index"]
        gain = ((t1 - t2) / t1) * 100 if t1 > 0 else 0

        print(f"{name:<25} | {t1:15.2f} | {t2:15.2f} | {gain:9.1f}%")
    print("=" * 85)


if __name__ == "__main__":
    run_benchmark()