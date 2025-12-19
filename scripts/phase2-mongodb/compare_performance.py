import pymongo
import time

DB_NAME = "imdb_project"
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client[DB_NAME]

TARGET_MOVIE_ID = "tt0002130"  # Un film existant (Dante's Inferno)


def fetch_movie_flat():
    """Récupère un film complet via collections plates (N requêtes)"""
    # 1. Info principale
    movie = db.movies.find_one({"mid": TARGET_MOVIE_ID})
    # 2. Rating
    rating = db.ratings.find_one({"mid": TARGET_MOVIE_ID})
    # 3. Genres
    genres = list(db.genres.find({"mid": TARGET_MOVIE_ID}))
    # 4. Directors
    directors_links = list(db.directors.find({"mid": TARGET_MOVIE_ID}))
    directors = []
    for d in directors_links:
        p = db.persons.find_one({"pid": d['pid']})
        if p: directors.append(p['primaryName'])
    # 5. Cast
    cast_links = list(db.principals.find({"mid": TARGET_MOVIE_ID, "category": "actor"}))
    cast = []
    for c in cast_links:
        p = db.persons.find_one({"pid": c['pid']})
        if p: cast.append(p['primaryName'])

    return {
        "title": movie.get('primaryTitle'),
        "rating": rating.get('averageRating') if rating else None,
        "genres": [g['genre'] for g in genres],
        "directors": directors,
        "cast": cast
    }


def fetch_movie_structured():
    """Récupère un film complet via collection structurée (1 requête)"""
    return db.movies_complete.find_one({"_id": TARGET_MOVIE_ID})


def get_collection_size(coll_name):
    return db.command("collstats", coll_name)["storageSize"] / (1024 * 1024)


def run_comparison():
    print(f"\n--- COMPARATIF : Récupération Film Complet ({TARGET_MOVIE_ID}) ---")

    # TEST 1 : PLAT
    start = time.time()
    res_flat = fetch_movie_flat()
    time_flat = (time.time() - start) * 1000
    print(f"📋 Modèle PLAT (N requêtes)      : {time_flat:.4f} ms")

    # TEST 2 : STRUCTURÉ
    start = time.time()
    res_struct = fetch_movie_structured()
    time_struct = (time.time() - start) * 1000
    print(f"📦 Modèle STRUCTURÉ (1 requête)  : {time_struct:.4f} ms")

    # Gain
    gain = time_flat / time_struct
    print(f"🚀 Gain de vitesse : x{gain:.1f}")

    print("\n--- COMPARATIF : Espace Disque ---")

    # Taille Flat (Somme des collections)
    flat_cols = ["movies", "ratings", "genres", "directors", "writers", "principals", "characters", "titles"]
    size_flat = sum(get_collection_size(c) for c in flat_cols)

    # Taille Structuré
    size_struct = get_collection_size("movies_complete")

    print(f"💾 Taille Total 'Flat'      : {size_flat:.2f} Mo")
    print(f"💾 Taille 'Movies Complete' : {size_struct:.2f} Mo")
    print(f"📈 Augmentation taille    : +{((size_struct - size_flat) / size_flat) * 100:.1f}%")
    print("(Normal : redondance des données = plus d'espace, mais lecture plus rapide)")


if __name__ == "__main__":
    run_comparison()