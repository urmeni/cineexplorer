import sqlite3
import os

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'imdb-tiny.db')


def get_connection():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Base de données introuvable : {DB_PATH}")
    return sqlite3.connect(DB_PATH)


# ==========================================
# 1. Filmographie d’un acteur
# ==========================================
def query_1_actor_filmography(conn, actor_name: str):
    """
    Q1: Dans quels films a joué un acteur donné ?
    Retourne : (Titre, Année, Personnage, Note)
    """
    sql = """
          SELECT m.primaryTitle, \
                 m.startYear, \
                 c.name as character_name, \
                 r.averageRating
          FROM persons p
                   JOIN principals pr ON p.pid = pr.pid
                   JOIN movies m ON pr.mid = m.mid
                   LEFT JOIN characters c ON m.mid = c.mid AND p.pid = c.pid
                   LEFT JOIN ratings r ON m.mid = r.mid
          WHERE p.primaryName LIKE ?
            AND (pr.category = 'actor' OR pr.category = 'actress')
          ORDER BY m.startYear DESC; \
          """
    # On ajoute des % pour le LIKE
    return conn.execute(sql, (f'%{actor_name}%',)).fetchall()


# ==========================================
# 2. Top N films par genre et période
# ==========================================
def query_2_top_movies_by_genre(conn, genre: str, start_year: int, end_year: int, limit: int):
    """
    Q2: Les N meilleurs films d’un genre sur une période.
    Retourne : (Titre, Année, Note, Votes)
    """
    sql = """
          SELECT m.primaryTitle, \
                 m.startYear, \
                 r.averageRating, \
                 r.numVotes
          FROM movies m
                   JOIN genres g ON m.mid = g.mid
                   JOIN ratings r ON m.mid = r.mid
          WHERE g.genre = ?
            AND m.startYear BETWEEN ? AND ?
          ORDER BY r.averageRating DESC, r.numVotes DESC LIMIT ?; \
          """
    return conn.execute(sql, (genre, start_year, end_year, limit)).fetchall()


# ==========================================
# 3. Acteurs multi-rôles
# ==========================================
def query_3_multi_role_actors(conn):
    """
    Q3: Acteurs ayant joué plusieurs personnages dans un même film.
    Retourne : (Acteur, Film, Nombre de rôles)
    """
    sql = """
          SELECT p.primaryName, \
                 m.primaryTitle, \
                 COUNT(c.name) as role_count
          FROM characters c
                   JOIN persons p ON c.pid = p.pid
                   JOIN movies m ON c.mid = m.mid
          GROUP BY c.mid, c.pid
          HAVING role_count > 1
          ORDER BY role_count DESC LIMIT 20; \
          """
    return conn.execute(sql).fetchall()


# ==========================================
# 4. Collaborations (Sous-requête)
# ==========================================
def query_4_collaborations(conn, actor_name: str):
    """
    Q4: Réalisateurs ayant travaillé avec un acteur spécifique.
    Utilise une sous-requête pour trouver les films de l'acteur.
    Retourne : (Réalisateur, Nombre de films communs)
    """
    sql = """
          SELECT p_dir.primaryName as Director, \
                 COUNT(d.mid)      as movie_count
          FROM directors d
                   JOIN persons p_dir ON d.pid = p_dir.pid
          WHERE d.mid IN (
              -- Sous-requête : ID des films où joue l'acteur cible
              SELECT pr.mid
              FROM principals pr
                       JOIN persons p_act ON pr.pid = p_act.pid
              WHERE p_act.primaryName LIKE ?
                AND (pr.category = 'actor' OR pr.category = 'actress'))
          GROUP BY d.pid
          ORDER BY movie_count DESC LIMIT 10; \
          """
    return conn.execute(sql, (f'%{actor_name}%',)).fetchall()


# ==========================================
# 5. Genres populaires (GROUP BY + HAVING)
# ==========================================
def query_5_popular_genres(conn):
    """
    Q5: Genres ayant une note moyenne > 7.0 et plus de 50 films.
    Retourne : (Genre, Note Moyenne, Nombre de films)
    """
    sql = """
          SELECT g.genre, \
                 ROUND(AVG(r.averageRating), 2) as avg_rating, \
                 COUNT(m.mid)                   as movie_count
          FROM genres g
                   JOIN ratings r ON g.mid = r.mid
                   JOIN movies m ON g.mid = m.mid
          GROUP BY g.genre
          HAVING avg_rating > 7.0 \
             AND movie_count > 50
          ORDER BY avg_rating DESC; \
          """
    return conn.execute(sql).fetchall()


# ==========================================
# 6. Évolution de carrière (CTE)
# ==========================================
def query_6_career_evolution(conn, actor_name: str):
    """
    Q6: Nombre de films par décennie avec note moyenne pour un acteur.
    Utilise une CTE (Common Table Expression).
    Retourne : (Décennie, Nombre de films, Note Moyenne)
    """
    sql = """
          WITH ActorMovies AS (SELECT m.startYear, \
                                      r.averageRating \
                               FROM persons p \
                                        JOIN principals pr ON p.pid = pr.pid \
                                        JOIN movies m ON pr.mid = m.mid \
                                        LEFT JOIN ratings r ON m.mid = r.mid \
                               WHERE p.primaryName LIKE ?)
          SELECT (startYear / 10) * 10        as decade, \
                 COUNT(*)                     as films_count, \
                 ROUND(AVG(averageRating), 2) as avg_rating
          FROM ActorMovies
          WHERE startYear IS NOT NULL
          GROUP BY decade
          ORDER BY decade; \
          """
    return conn.execute(sql, (f'%{actor_name}%',)).fetchall()


# ==========================================
# 7. Classement par genre (Window Function)
# ==========================================
def query_7_genre_rankings(conn):
    """
    Q7: Les 3 meilleurs films de chaque genre.
    Utilise RANK() OVER.
    Retourne : (Genre, Rang, Titre, Note)
    """
    sql = """
          WITH RankedMovies AS (SELECT g.genre, \
                                       m.primaryTitle, \
                                       r.averageRating, \
                                       RANK() OVER (
                PARTITION BY g.genre 
                ORDER BY r.averageRating DESC, r.numVotes DESC
            ) as rank \
                                FROM genres g \
                                         JOIN movies m ON g.mid = m.mid \
                                         JOIN ratings r ON m.mid = r.mid \
                                WHERE r.numVotes > 1000 -- Filtre pour éviter les films inconnus à 10/10
          )
          SELECT genre, rank, primaryTitle, averageRating
          FROM RankedMovies
          WHERE rank <= 3; \
          """
    return conn.execute(sql).fetchall()


# ==========================================
# 8. Carrière propulsée
# ==========================================
def query_8_breakout_career(conn):
    """
    Q8: Personnes ayant travaillé sur des petits films (<10k votes)
    ET des gros films (>200k votes).
    Note: J'ai baissé le seuil "petit" à 10k pour trouver plus de résultats dans le dataset small.
    Retourne : (Nom, Plus petit nb votes, Plus gros nb votes)
    """
    sql = """
          SELECT p.primaryName, \
                 MIN(r.numVotes) as min_votes, \
                 MAX(r.numVotes) as max_votes
          FROM persons p
                   JOIN principals pr ON p.pid = pr.pid
                   JOIN ratings r ON pr.mid = r.mid
          GROUP BY p.pid
          HAVING min_votes < 10000 \
             AND max_votes > 200000
          ORDER BY max_votes DESC LIMIT 10; \
          """
    return conn.execute(sql).fetchall()


# ==========================================
# 9. Requête Libre (Complexe)
# ==========================================
def query_9_complex_custom(conn):
    """
    Q9: "Les Acteurs Versatiles et Bankables"
    Trouve les acteurs qui ont joué dans au moins 3 genres DIFFÉRENTS
    dans des films bien notés (> 7.5), triés par nombre de genres uniques.
    Jointures : persons -> principals -> movies -> genres -> ratings
    """
    sql = """
          SELECT p.primaryName, \
                 COUNT(DISTINCT g.genre)        as unique_genres, \
                 ROUND(AVG(r.averageRating), 2) as personal_avg_rating, \
                 GROUP_CONCAT(DISTINCT g.genre) as genres_list
          FROM persons p
                   JOIN principals pr ON p.pid = pr.pid
                   JOIN movies m ON pr.mid = m.mid
                   JOIN genres g ON m.mid = g.mid
                   JOIN ratings r ON m.mid = r.mid
          WHERE r.averageRating > 7.5
            AND pr.category IN ('actor', 'actress')
          GROUP BY p.pid
          HAVING unique_genres >= 3
          ORDER BY unique_genres DESC, personal_avg_rating DESC LIMIT 10; \
          """
    return conn.execute(sql).fetchall()


# --- TEST DES REQUÊTES ---
if __name__ == "__main__":
    try:
        conn = get_connection()
        print(" Connexion réussie.\n")

        print("--- Q1: Filmographie de 'DiCaprio' ---")
        for row in query_1_actor_filmography(conn, "DiCaprio"):
            print(row)

        print("\n--- Q2: Top 3 Films 'Drama' (1990-2000) ---")
        for row in query_2_top_movies_by_genre(conn, "Drama", 1990, 2000, 3):
            print(row)

        print("\n--- Q3: Acteurs Multi-rôles (Exemple) ---")
        for row in query_3_multi_role_actors(conn):
            print(row)

        print("\n--- Q4: Collaborations avec 'Brad Pitt' ---")
        for row in query_4_collaborations(conn, "Brad Pitt"):
            print(row)

        print("\n--- Q5: Genres Populaires ---")
        for row in query_5_popular_genres(conn):
            print(row)

        print("\n--- Q6: Évolution Carrière 'Clint Eastwood' ---")
        for row in query_6_career_evolution(conn, "Clint Eastwood"):
            print(row)

        print("\n--- Q7: Top 3 par Genre (Rank) ---")
        # On limite l'affichage car ça renvoie 3 lignes par genre
        results = query_7_genre_rankings(conn)
        for row in results[:15]:
            print(row)
        print("...")

        print("\n--- Q8: Carrières Propulsées ---")
        for row in query_8_breakout_career(conn):
            print(row)

        print("\n--- Q9: Acteurs Versatiles (Requête Libre) ---")
        for row in query_9_complex_custom(conn):
            print(row)

        conn.close()

    except Exception as e:
        print(f"Erreur : {e}")