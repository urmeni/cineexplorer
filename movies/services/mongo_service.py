from pymongo import MongoClient
from django.conf import settings

_client = None


def get_mongo_client():
    """Singleton pour la connexion MongoDB (Replica Set)"""
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URI)
    return _client


def get_mongo_stats():
    """
    Récupère des stats depuis MongoDB et identifie le nœud Primaire.
    """
    try:
        client = get_mongo_client()
        db = client[settings.MONGO_DB_NAME]

        # Test de lecture
        count = db.movies_complete.count_documents({})

        # Info sur la connexion (Qui est le Primary ?)
        is_primary = client.is_primary
        nodes = client.nodes

        return {
            "status": "✅ Connecté (Replica Set)",
            "movies_count": count,
            "nodes": list(nodes),
            "is_socket_primary": is_primary  # True si connecté au master
        }
    except Exception as e:
        return {"status": f"❌ Erreur : {e}"}