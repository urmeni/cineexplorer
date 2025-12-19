import pymongo
import time
import os

# --- CONFIGURATION ---
DB_NAME = "imdb_project"
BATCH_SIZE = 1000  # On traite 1000 films à la fois pour ne pas saturer la RAM

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client[DB_NAME]


def get_movie_batch(skip, limit):
    """
    Récupère une liste de 'mid' (ex: tt002130) pour le batch actuel.
    """
    cursor = db.movies.find({}, {"mid": 1, "_id": 0}).skip(skip).limit(limit)
    return [doc['mid'] for doc in cursor]


def migrate_structured():
    print(f"🚀 Démarrage de la dénormalisation optimisée (Batch size: {BATCH_SIZE})...")
    start_global = time.time()

    # 1. Nettoyage et préparation
    db.movies_complete.drop()  # On repart de zéro
    total_movies = db.movies.count_documents({})
    print(f"📦 Total films à traiter : {total_movies}")

    processed_count = 0

    while processed_count < total_movies:
        # A. Récupérer les IDs du lot actuel
        batch_mids = get_movie_batch(processed_count, BATCH_SIZE)
        if not batch_mids:
            break

        # B. Pipeline restreint aux IDs du batch (c'est ça qui accélère tout !)
        pipeline = [
            # --- FILTRE INITIAL (Le secret de la performance) ---
            {"$match": {"mid": {"$in": batch_mids}}},

            # 1. Base : Informations du film
            {"$project": {
                "_id": "$mid",  # On force ttXXXX comme clé primaire _id
                "title": "$primaryTitle",
                "year": "$startYear",
                "runtime": "$runtimeMinutes"
            }},

            # 2. Embedding : RATINGS
            {"$lookup": {
                "from": "ratings",
                "localField": "_id",
                "foreignField": "mid",
                "as": "rating_obj"
            }},
            {"$unwind": {"path": "$rating_obj", "preserveNullAndEmptyArrays": True}},

            # 3. Embedding : GENRES
            {"$lookup": {
                "from": "genres",
                "localField": "_id",
                "foreignField": "mid",
                "as": "genres_list"
            }},

            # 4. Embedding : DIRECTORS
            {"$lookup": {
                "from": "directors",
                "let": {"mid": "$_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$mid", "$$mid"]}}},
                    {"$lookup": {
                        "from": "persons",
                        "localField": "pid",
                        "foreignField": "pid",
                        "as": "p"
                    }},
                    {"$unwind": "$p"},
                    {"$project": {"_id": 0, "person_id": "$pid", "name": "$p.primaryName"}}
                ],
                "as": "directors"
            }},

            # 5. Embedding : WRITERS
            {"$lookup": {
                "from": "writers",
                "let": {"mid": "$_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$mid", "$$mid"]}}},
                    {"$lookup": {
                        "from": "persons",
                        "localField": "pid",
                        "foreignField": "pid",
                        "as": "p"
                    }},
                    {"$unwind": "$p"},
                    {"$project": {"_id": 0, "person_id": "$pid", "name": "$p.primaryName"}}
                ],
                "as": "writers"
            }},

            # 6. Embedding : CAST (Le plus lourd)
            {"$lookup": {
                "from": "principals",
                "let": {"mid": "$_id"},
                "pipeline": [
                    {"$match": {
                        "$expr": {"$eq": ["$mid", "$$mid"]},
                        "category": {"$in": ["actor", "actress"]}
                    }},
                    {"$lookup": {
                        "from": "persons",
                        "localField": "pid",
                        "foreignField": "pid",
                        "as": "p"
                    }},
                    {"$unwind": "$p"},
                    {"$lookup": {
                        "from": "characters",
                        "let": {"mid": "$mid", "pid": "$pid"},
                        "pipeline": [
                            {"$match": {"$expr": {"$and": [
                                {"$eq": ["$mid", "$$mid"]},
                                {"$eq": ["$pid", "$$pid"]}
                            ]}}},
                            {"$project": {"name": 1, "_id": 0}}
                        ],
                        "as": "char_docs"
                    }},
                    {"$project": {
                        "_id": 0, "person_id": "$pid", "name": "$p.primaryName",
                        "ordering": "$ordering",
                        "characters": {"$map": {"input": "$char_docs", "as": "c", "in": "$$c.name"}}
                    }},
                    {"$sort": {"ordering": 1}}
                ],
                "as": "cast"
            }},

            # 7. Embedding : TITLES
            {"$lookup": {
                "from": "titles",
                "let": {"mid": "$_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$mid", "$$mid"]}}},
                    {"$project": {"_id": 0, "region": 1, "title": 1, "language": 1}}
                ],
                "as": "titles"
            }},

            # 8. Mise en forme finale
            {"$project": {
                "title": 1, "year": 1, "runtime": 1,
                "genres": {"$map": {"input": "$genres_list", "as": "g", "in": "$$g.genre"}},
                "rating": {"average": "$rating_obj.averageRating", "votes": "$rating_obj.numVotes"},
                "directors": 1, "writers": 1, "cast": 1, "titles": 1
            }}
            # Note: Pas de $out ici car on insère par morceaux
        ]

        # C. Exécution du batch
        try:
            results = list(db.movies.aggregate(pipeline))
            if results:
                db.movies_complete.insert_many(results)

            processed_count += len(batch_mids)

            # Progression
            percent = (processed_count / total_movies) * 100
            print(f"   ↳ Traité : {processed_count}/{total_movies} ({percent:.1f}%)", end='\r')

        except Exception as e:
            print(f"\n❌ Erreur sur le batch : {e}")
            break

    total_time = time.time() - start_global
    print(f"\n\n✅ Terminé en {total_time:.2f} secondes.")

    # Création d'index
    print("🔨 Création des index finaux...")
    db.movies_complete.create_index("title")
    db.movies_complete.create_index("year")
    db.movies_complete.create_index("genres")
    db.movies_complete.create_index("cast.name")


if __name__ == "__main__":
    migrate_structured()