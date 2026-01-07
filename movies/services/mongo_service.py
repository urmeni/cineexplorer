from pymongo import MongoClient, DESCENDING, ASCENDING
from django.conf import settings
import re

_client = None


def get_db():
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URI)
    return _client[settings.MONGO_DB_NAME]


# --- UTILITAIRE DE CORRECTION ---
def _map_id(doc):
    """
    Crée un alias 'id' = '_id' pour que les templates Django
    puissent lire l'identifiant (Django interdit les variables commençant par _)
    """
    if doc and '_id' in doc:
        doc['id'] = doc['_id']
    return doc


def _map_cursor(cursor):
    """Applique la correction sur une liste de résultats"""
    return [_map_id(doc) for doc in list(cursor)]


# --- PAGE D'ACCUEIL ---
def get_home_stats():
    db = get_db()
    return {
        "movies": db.movies_complete.estimated_document_count(),
        "persons": db.persons.estimated_document_count(),
        "genres": len(db.movies_complete.distinct("genres"))
    }


def get_top_rated_movies(limit=6):
    db = get_db()
    cursor = db.movies_complete.find(
        {"rating.votes": {"$gt": 10000}},
        {"title": 1, "year": 1, "rating": 1, "genres": 1, "poster": 1}
    ).sort("rating.average", DESCENDING).limit(limit)
    return _map_cursor(cursor)  # <--- Correction appliquée ici


def get_recent_movies(limit=6):
    db = get_db()
    cursor = db.movies_complete.find({},
                                     {"title": 1, "year": 1, "rating": 1, "genres": 1}
                                     ).sort("year", DESCENDING).limit(limit)
    return _map_cursor(cursor)  # <--- Et ici


# --- LISTE ET FILTRES ---
def search_movies(page=1, per_page=20, filters=None, sort_by="year_desc"):
    db = get_db()
    query = {}

    # Construction de la requête (Filtres)
    if filters:
        if filters.get("genre"):
            query["genres"] = filters["genre"]
        if filters.get("year_min") or filters.get("year_max"):
            query["year"] = {}
            if filters.get("year_min"): query["year"]["$gte"] = int(filters["year_min"])
            if filters.get("year_max"): query["year"]["$lte"] = int(filters["year_max"])
        if filters.get("rating_min"):
            query["rating.average"] = {"$gte": float(filters["rating_min"])}
        if filters.get("search_text"):
            query["title"] = {"$regex": filters["search_text"], "$options": "i"}

    # Gestion du Tri
    sort_criteria = [("year", DESCENDING)]
    if sort_by == "year_asc":
        sort_criteria = [("year", ASCENDING)]
    elif sort_by == "rating_desc":
        sort_criteria = [("rating.average", DESCENDING)]
    elif sort_by == "title_asc":
        sort_criteria = [("title", ASCENDING)]

    skip = (page - 1) * per_page

    cursor = db.movies_complete.find(query).sort(sort_criteria).skip(skip).limit(per_page)
    total = db.movies_complete.count_documents(query)

    # On renvoie la liste corrigée + le total
    return _map_cursor(cursor), total


def get_all_genres():
    db = get_db()
    return sorted(db.movies_complete.distinct("genres"))


# --- DÉTAIL FILM ---
def get_movie_detail(movie_id):
    db = get_db()
    doc = db.movies_complete.find_one({"_id": movie_id})
    return _map_id(doc)  # <--- Correction pour un seul document


def get_similar_movies(movie):
    if not movie or not movie.get('genres'): return []
    db = get_db()
    cursor = db.movies_complete.find(
        {
            "genres": {"$in": movie['genres']},
            "_id": {"$ne": movie['_id']}
        },
        {"title": 1, "year": 1, "rating": 1}
    ).sort("rating.average", DESCENDING).limit(4)
    return _map_cursor(cursor)


# --- RECHERCHE GLOBALE ---
def global_search(query_text):
    db = get_db()
    regex = {"$regex": query_text, "$options": "i"}

    movies = _map_cursor(db.movies_complete.find({"title": regex}).limit(10))
    persons = _map_cursor(db.persons.find({"primaryName": regex}).limit(10))

    return {"movies": movies, "persons": persons}


# --- STATISTIQUES AVANCÉES (Pour les graphiques) ---
def get_stats_genres():
    """Top 10 genres les plus représentés"""
    db = get_db()
    pipeline = [
        {"$unwind": "$genres"}, # Aplatir le tableau genres
        {"$group": {"_id": "$genres", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    return list(db.movies_complete.aggregate(pipeline))

def get_stats_decades():
    """Distribution des films par décennie"""
    db = get_db()
    pipeline = [
        {"$match": {"year": {"$ne": None}}}, # Exclure les sans année
        {"$project": {
            "decade": {"$subtract": ["$year", {"$mod": ["$year", 10]}]}
        }},
        {"$group": {"_id": "$decade", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    return list(db.movies_complete.aggregate(pipeline))

def get_stats_ratings():
    """Distribution des notes (arrondies à l'entier)"""
    db = get_db()
    pipeline = [
        {"$match": {"rating.average": {"$ne": None}}},
        {"$project": {
            "rounded_rating": {"$floor": "$rating.average"}
        }},
        {"$group": {"_id": "$rounded_rating", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    return list(db.movies_complete.aggregate(pipeline))