import pymongo
import time
import os

# --- CONFIGURATION ---
DB_NAME = "imdb_project"
CLIENT = pymongo.MongoClient("mongodb://localhost:27017/")
DB = CLIENT[DB_NAME]


def ensure_indexes():
    """
    CRUCIAL : Crée des index sur mid et pid pour accélérer les $lookup.
    Sans ça, les jointures MongoDB sur des collections plates sont extrêmement lentes.
    """
    print("🔨 Création des index MongoDB pour optimisation des $lookup...")
    DB.movies.create_index("mid")
    DB.persons.create_index("pid")
    DB.principals.create_index("mid")
    DB.principals.create_index("pid")
    DB.ratings.create_index("mid")
    DB.genres.create_index("mid")
    DB.genres.create_index("genre")
    DB.directors.create_index("pid")
    DB.directors.create_index("mid")
    DB.characters.create_index("mid")
    print("✅ Index créés.")


# ==========================================
# 1. Filmographie d’un acteur
# ==========================================
def query_1_actor_filmography(actor_name):
    """
    Pipeline : Persons -> Principals -> Movies -> Ratings
    """
    pipeline = [
        # 1. Trouver l'acteur (Filtre)
        {"$match": {"primaryName": {"$regex": actor_name, "$options": "i"}}},

        # 2. Joindre avec Principals (quels films ?)
        {"$lookup": {
            "from": "principals",
            "localField": "pid",
            "foreignField": "pid",
            "as": "roles"
        }},
        {"$unwind": "$roles"},  # Aplatir le tableau

        # 3. Filtrer uniquement 'actor' ou 'actress'
        {"$match": {"roles.category": {"$in": ["actor", "actress"]}}},

        # 4. Joindre avec Movies (infos film)
        {"$lookup": {
            "from": "movies",
            "localField": "roles.mid",
            "foreignField": "mid",
            "as": "movie_info"
        }},
        {"$unwind": "$movie_info"},

        # 5. Joindre avec Ratings (note)
        {"$lookup": {
            "from": "ratings",
            "localField": "roles.mid",
            "foreignField": "mid",
            "as": "rating_info"
        }},
        # Ratings peut être vide, donc preserveNullAndEmptyArrays si on veut garder le film
        {"$unwind": {"path": "$rating_info", "preserveNullAndEmptyArrays": True}},

        # 6. Projection finale (SELECT)
        {"$project": {
            "_id": 0,
            "Title": "$movie_info.primaryTitle",
            "Year": "$movie_info.startYear",
            "Character": "$roles.job",  # Ou character name si dispo ailleurs
            "Rating": "$rating_info.averageRating"
        }},
        {"$sort": {"Year": -1}}
    ]
    return list(DB.persons.aggregate(pipeline))


# ==========================================
# 2. Top N films par genre
# ==========================================
def query_2_top_movies(genre, start_year, end_year, limit):
    """
    Pipeline : Genres -> Movies -> Ratings
    """
    pipeline = [
        # 1. Filtrer par Genre
        {"$match": {"genre": genre}},

        # 2. Joindre Movies
        {"$lookup": {
            "from": "movies",
            "localField": "mid",
            "foreignField": "mid",
            "as": "movie"
        }},
        {"$unwind": "$movie"},

        # 3. Filtrer par Année
        {"$match": {
            "movie.startYear": {"$gte": start_year, "$lte": end_year}
        }},

        # 4. Joindre Ratings
        {"$lookup": {
            "from": "ratings",
            "localField": "mid",
            "foreignField": "mid",
            "as": "rating"
        }},
        {"$unwind": "$rating"},

        # 5. Tri et Limite
        {"$sort": {"rating.averageRating": -1, "rating.numVotes": -1}},
        {"$limit": limit},

        {"$project": {
            "Title": "$movie.primaryTitle",
            "Year": "$movie.startYear",
            "Rating": "$rating.averageRating"
        }}
    ]
    return list(DB.genres.aggregate(pipeline))


# ==========================================
# 3. Acteurs multi-rôles
# ==========================================
def query_3_multi_roles():
    """
    Group by mid+pid sur la collection characters
    """
    pipeline = [
        # 1. Grouper par Film et Acteur
        {"$group": {
            "_id": {"mid": "$mid", "pid": "$pid"},
            "roles_count": {"$sum": 1},
            "char_names": {"$push": "$name"}
        }},

        # 2. HAVING count > 1
        {"$match": {"roles_count": {"$gt": 1}}},

        # 3. Joindre pour avoir les noms (Optionnel pour la perf, mais plus joli)
        {"$lookup": {
            "from": "persons",
            "localField": "_id.pid",
            "foreignField": "pid",
            "as": "actor"
        }},
        {"$unwind": "$actor"},
        {"$lookup": {
            "from": "movies",
            "localField": "_id.mid",
            "foreignField": "mid",
            "as": "movie"
        }},
        {"$unwind": "$movie"},

        {"$limit": 20},
        {"$project": {
            "Actor": "$actor.primaryName",
            "Movie": "$movie.primaryTitle",
            "Roles": "$roles_count"
        }}
    ]
    return list(DB.characters.aggregate(pipeline))


# ==========================================
# 4. Collaborations (Brad Pitt)
# ==========================================
def query_4_collaborations(actor_name):
    """
    Stratégie complexe en NoSQL plat :
    1. Trouver PID acteur
    2. Trouver MIDs acteur (principals)
    3. Trouver Directors de ces MIDs
    4. Grouper
    """
    # Étape 1 : Récupérer le PID de l'acteur (Recherche simple)
    actor = DB.persons.find_one({"primaryName": {"$regex": actor_name, "$options": "i"}})
    if not actor: return []
    actor_pid = actor['pid']

    pipeline = [
        # 1. Partir des films où Brad Pitt a joué
        {"$match": {"pid": actor_pid, "category": {"$in": ["actor", "actress"]}}},

        # 2. Joindre Directors sur le même film (Self-Join like)
        {"$lookup": {
            "from": "directors",
            "localField": "mid",
            "foreignField": "mid",
            "as": "dir_link"
        }},
        {"$unwind": "$dir_link"},

        # 3. Grouper par Director PID
        {"$group": {
            "_id": "$dir_link.pid",
            "count": {"$sum": 1}
        }},

        # 4. Récupérer le nom du réalisateur
        {"$lookup": {
            "from": "persons",
            "localField": "_id",
            "foreignField": "pid",
            "as": "director_info"
        }},
        {"$unwind": "$director_info"},

        {"$sort": {"count": -1}},
        {"$limit": 10},
        {"$project": {
            "Director": "$director_info.primaryName",
            "Collaborations": "$count"
        }}
    ]
    return list(DB.principals.aggregate(pipeline))


# ==========================================
# 5. Genres populaires
# ==========================================
def query_5_popular_genres():
    pipeline = [
        # 1. Joindre Ratings
        {"$lookup": {
            "from": "ratings",
            "localField": "mid",
            "foreignField": "mid",
            "as": "rate"
        }},
        {"$unwind": "$rate"},

        # 2. Grouper par Genre
        {"$group": {
            "_id": "$genre",
            "avg_rating": {"$avg": "$rate.averageRating"},
            "num_movies": {"$sum": 1}
        }},

        # 3. Filtrer (HAVING)
        {"$match": {
            "avg_rating": {"$gt": 7.0},
            "num_movies": {"$gt": 50}
        }},

        {"$sort": {"avg_rating": -1}}
    ]
    return list(DB.genres.aggregate(pipeline))


# ==========================================
# 6. Évolution de carrière (CTE like)
# ==========================================
def query_6_career_evolution(actor_name):
    pipeline = [
        {"$match": {"primaryName": {"$regex": actor_name, "$options": "i"}}},
        {"$lookup": {
            "from": "principals",
            "localField": "pid",
            "foreignField": "pid",
            "as": "roles"
        }},
        {"$unwind": "$roles"},
        {"$lookup": {
            "from": "movies",
            "localField": "roles.mid",
            "foreignField": "mid",
            "as": "movie"
        }},
        {"$unwind": "$movie"},
        {"$lookup": {
            "from": "ratings",
            "localField": "roles.mid",
            "foreignField": "mid",
            "as": "rate"
        }},
        {"$unwind": "$rate"},

        # Calcul de la décennie
        {"$project": {
            "year": "$movie.startYear",
            "rating": "$rate.averageRating",
            "decade": {
                "$subtract": ["$movie.startYear", {"$mod": ["$movie.startYear", 10]}]
            }
        }},

        {"$group": {
            "_id": "$decade",
            "count": {"$sum": 1},
            "avg_rating": {"$avg": "$rating"}
        }},
        {"$sort": {"_id": 1}}
    ]
    return list(DB.persons.aggregate(pipeline))


# ==========================================
# 7. Classement par genre (Window Function)
# ==========================================
def query_7_genre_rankings():
    """
    Nécessite MongoDB 5.0+ pour $setWindowFields
    """
    pipeline = [
        # Note: Pour optimiser, on pourrait filtrer sur les films > 1000 votes avant
        {"$lookup": {
            "from": "ratings",
            "localField": "mid",
            "foreignField": "mid",
            "as": "rate"
        }},
        {"$unwind": "$rate"},
        {"$match": {"rate.numVotes": {"$gt": 1000}}},

        {"$lookup": {
            "from": "movies",
            "localField": "mid",
            "foreignField": "mid",
            "as": "movie"
        }},
        {"$unwind": "$movie"},

        # Window Function equivalent
        {"$setWindowFields": {
            "partitionBy": "$genre",
            "sortBy": {"rate.averageRating": -1},
            "output": {
                "rank": {
                    "$rank": {}
                }
            }
        }},

        {"$match": {"rank": {"$lte": 3}}},
        {"$project": {
            "_id": 0, "genre": 1, "rank": 1,
            "title": "$movie.primaryTitle",
            "rating": "$rate.averageRating"
        }}
    ]
    # Attention: cette requête est très lourde sur toute la base
    # On ajoute un $limit au début pour tester ou on s'attend à ce que ce soit long
    return list(DB.genres.aggregate(pipeline))


# ==========================================
# 8. Carrière propulsée
# ==========================================
def query_8_breakout():
    pipeline = [
        {"$lookup": {
            "from": "ratings",
            "localField": "mid",
            "foreignField": "mid",
            "as": "rate"
        }},
        {"$unwind": "$rate"},

        {"$group": {
            "_id": "$pid",
            "min_votes": {"$min": "$rate.numVotes"},
            "max_votes": {"$max": "$rate.numVotes"}
        }},

        {"$match": {
            "min_votes": {"$lt": 10000},
            "max_votes": {"$gt": 200000}
        }},

        {"$lookup": {
            "from": "persons",
            "localField": "_id",
            "foreignField": "pid",
            "as": "person"
        }},
        {"$unwind": "$person"},
        {"$limit": 10},
        {"$project": {"Name": "$person.primaryName", "Min": "$min_votes", "Max": "$max_votes"}}
    ]
    return list(DB.principals.aggregate(pipeline))


# ==========================================
# 9. Requête complexe
# ==========================================
def query_9_complex():
    """
    Acteurs versatiles (3 genres distincts, note > 7.5)
    """
    pipeline = [
        # 1. Joindre Ratings & Filtrer
        {"$lookup": {
            "from": "ratings",
            "localField": "mid",
            "foreignField": "mid",
            "as": "rate"
        }},
        {"$unwind": "$rate"},
        {"$match": {"rate.averageRating": {"$gt": 7.5}}},

        # 2. Joindre Genres
        {"$lookup": {
            "from": "genres",
            "localField": "mid",
            "foreignField": "mid",
            "as": "gen"
        }},
        {"$unwind": "$gen"},

        # 3. Filtrer acteurs
        {"$match": {"category": {"$in": ["actor", "actress"]}}},

        # 4. Group by PID
        {"$group": {
            "_id": "$pid",
            "unique_genres": {"$addToSet": "$gen.genre"}  # addToSet = DISTINCT
        }},

        # 5. Compter genres
        {"$project": {
            "nb_genres": {"$size": "$unique_genres"},
            "genres": "$unique_genres"
        }},

        {"$match": {"nb_genres": {"$gte": 3}}},

        {"$lookup": {
            "from": "persons",
            "localField": "_id",
            "foreignField": "pid",
            "as": "p"
        }},
        {"$unwind": "$p"},
        {"$sort": {"nb_genres": -1}},
        {"$limit": 10}
    ]
    return list(DB.principals.aggregate(pipeline))


# --- BENCHMARK ---
def run_benchmark():
    ensure_indexes()

    tests = [
        ("Q1 - Filmographie", lambda: query_1_actor_filmography("DiCaprio")),
        ("Q2 - Top Films", lambda: query_2_top_movies("Drama", 1990, 2000, 10)),
        ("Q3 - Multi-rôles", query_3_multi_roles),
        ("Q4 - Collaborations", lambda: query_4_collaborations("Brad Pitt")),
        ("Q5 - Genres Pop.", query_5_popular_genres),
        ("Q6 - Évolution", lambda: query_6_career_evolution("Clint Eastwood")),
        ("Q7 - Classement", query_7_genre_rankings),
        ("Q8 - Propulsé", query_8_breakout),
        ("Q9 - Complexe", query_9_complex)
    ]

    print("\n" + "=" * 60)
    print(f"{'REQUÊTE':<25} | {'TEMPS MONGO (ms)':<15}")
    print("=" * 60)

    for name, func in tests:
        start = time.time()
        try:
            results = func()
            duration = (time.time() - start) * 1000
            print(f"{name:<25} | {duration:15.2f} ms (Res: {len(results)})")
        except Exception as e:
            print(f"{name:<25} | ERREUR: {e}")


if __name__ == "__main__":
    run_benchmark()