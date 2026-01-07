import pymongo
import time
import sys

# --- CONFIGURATION ---
DB_NAME = "imdb_project"
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client[DB_NAME]


def get_valid_movie_id():
    """
    Cherche un ID de film qui existe VRAIMENT dans la base
    pour éviter les erreurs 'NoneType'.
    """
    # On prend un film au hasard dans la collection complète
    sample = db.movies_complete.find_one()

    if not sample:
        print("ERREUR : La collection 'movies_complete' est vide !")
        print("   Avez-vous bien lancé migrate_structured.py ?")
        sys.exit(1)

    return sample['_id']


def fetch_movie_flat(target_id):
    """Récupère un film complet via collections plates (N requêtes)"""
    # 1. Info principale
    movie = db.movies.find_one({"mid": target_id})
    if not movie: return None  # Sécurité

    # 2. Rating
    rating = db.ratings.find_one({"mid": target_id})
    # 3. Genres
    genres = list(db.genres.find({"mid": target_id}))
    # 4. Directors
    directors_links = list(db.directors.find({"mid": target_id}))
    directors = []
    for d in directors_links:
        p = db.persons.find_one({"pid": d['pid']})
        if p: directors.append(p['primaryName'])
    # 5. Cast
    cast_links = list(db.principals.find({"mid": target_id, "category": "actor"}))
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


def fetch_movie_structured(target_id):
    """Récupère un film complet via collection structurée (1 requête)"""
    return db.movies_complete.find_one({"_id": target_id})


def get_collection_size(coll_name):
    stats = db.command("collstats", coll_name)
    return stats["storageSize"] / (1024 * 1024)


def run_comparison():
    # 1. Récupération dynamique d'un ID valide
    try:
        target_id = get_valid_movie_id()
    except Exception as e:
        print(f"Erreur connexion : {e}")
        return

    print(f"\n--- COMPARATIF SUR LE FILM : {target_id} ---")

    # TEST 1 : PLAT
    start = time.time()
    res_flat = fetch_movie_flat(target_id)
    time_flat = (time.time() - start) * 1000
    print(f"📋 Modèle PLAT (N requêtes)      : {time_flat:.4f} ms")

    # TEST 2 : STRUCTURÉ
    start = time.time()
    res_struct = fetch_movie_structured(target_id)
    time_struct = (time.time() - start) * 1000
    print(f"📦 Modèle STRUCTURÉ (1 requête)  : {time_struct:.4f} ms")

    # Gain
    if time_struct > 0:
        gain = time_flat / time_struct
        print(f"🚀 Gain de vitesse : x{gain:.1f}")
    else:
        print("🚀 Gain : Infini (temps structuré trop court pour être mesuré)")

    print("\n--- COMPARATIF : Espace Disque ---")

    # Taille Flat (Somme des collections)
    flat_cols = ["movies", "ratings", "genres", "directors", "writers", "principals", "characters", "titles"]
    size_flat = sum(get_collection_size(c) for c in flat_cols)

    # Taille Structuré
    size_struct = get_collection_size("movies_complete")

    print(f"Taille Total 'Flat'      : {size_flat:.2f} Mo")
    print(f"Taille 'Movies Complete' : {size_struct:.2f} Mo")

    if size_flat > 0:
        augmentation = ((size_struct - size_flat) / size_flat) * 100
        print(f"📈 Augmentation taille    : +{augmentation:.1f}%")


if __name__ == "__main__":
    run_comparison()