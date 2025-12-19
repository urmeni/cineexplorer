import pymongo
import time
import os

# --- CONFIGURATION ---
DB_NAME = "imdb_project"
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client[DB_NAME]


def migrate_structured():
    print("🚀 Démarrage de la dénormalisation (Création de movies_complete)...")
    start_time = time.time()

    # Pipeline d'agrégation massif
    pipeline = [
        # 1. Base : Informations du film
        {"$project": {
            "_id": "$mid",  # On garde ttXXXX comme _id
            "title": "$primaryTitle",
            "year": "$startYear",
            "runtime": "$runtimeMinutes"
        }},

        # 2. Embedding : RATINGS (1-1)
        {"$lookup": {
            "from": "ratings",
            "localField": "_id",
            "foreignField": "mid",
            "as": "rating_obj"
        }},
        {"$unwind": {"path": "$rating_obj", "preserveNullAndEmptyArrays": True}},

        # 3. Embedding : GENRES (1-N) -> Liste de strings
        {"$lookup": {
            "from": "genres",
            "localField": "_id",
            "foreignField": "mid",
            "as": "genres_list"
        }},

        # 4. Embedding : DIRECTORS (N-N résolu)
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

        # 5. Embedding : WRITERS (N-N résolu)
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

        # 6. Embedding : CAST (Principals + Characters) - Le plus complexe
        {"$lookup": {
            "from": "principals",
            "let": {"mid": "$_id"},
            "pipeline": [
                {"$match": {
                    "$expr": {"$eq": ["$mid", "$$mid"]},
                    "category": {"$in": ["actor", "actress"]}
                }},
                # Récupérer le nom de l'acteur
                {"$lookup": {
                    "from": "persons",
                    "localField": "pid",
                    "foreignField": "pid",
                    "as": "p"
                }},
                {"$unwind": "$p"},
                # Récupérer le(s) nom(s) du personnage joué
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
                    "_id": 0,
                    "person_id": "$pid",
                    "name": "$p.primaryName",
                    "ordering": "$ordering",
                    # Transformation de [{name: "A"}, {name: "B"}] en ["A", "B"]
                    "characters": {"$map": {"input": "$char_docs", "as": "c", "in": "$$c.name"}}
                }},
                {"$sort": {"ordering": 1}}
            ],
            "as": "cast"
        }},

        # 7. Embedding : TITLES (International)
        {"$lookup": {
            "from": "titles",
            "let": {"mid": "$_id"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$mid", "$$mid"]}}},
                {"$project": {"_id": 0, "region": 1, "title": 1, "language": 1}}
            ],
            "as": "titles"
        }},

        # 8. Mise en forme finale (Reshape)
        {"$project": {
            "title": 1,
            "year": 1,
            "runtime": 1,
            "genres": {"$map": {"input": "$genres_list", "as": "g", "in": "$$g.genre"}},  # Aplatir genres
            "rating": {"average": "$rating_obj.averageRating", "votes": "$rating_obj.numVotes"},
            "directors": 1,
            "writers": 1,
            "cast": 1,
            "titles": 1
        }},

        # 9. Écriture dans la nouvelle collection
        {"$out": "movies_complete"}
    ]

    # Exécution
    try:
        db.movies.aggregate(pipeline)
        duration = time.time() - start_time
        count = db.movies_complete.count_documents({})
        print(f"✅ Terminé en {duration:.2f} secondes.")
        print(f"📦 Collection 'movies_complete' créée avec {count} documents.")

        # Création d'index sur la nouvelle collection pour la recherche
        print("🔨 Création des index...")
        db.movies_complete.create_index("title")
        db.movies_complete.create_index("year")
        db.movies_complete.create_index("genres")
        db.movies_complete.create_index("cast.name")  # Pour chercher par acteur

    except Exception as e:
        print(f"❌ Erreur : {e}")


if __name__ == "__main__":
    migrate_structured()