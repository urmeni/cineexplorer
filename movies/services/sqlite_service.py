import sqlite3
from django.conf import settings


def get_sqlite_stats():
    """
    Récupère des stats simples depuis SQLite pour tester la connexion.
    """
    db_path = settings.DATABASES['default']['NAME']

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Exemple : Compter les films et les personnes
        count_movies = cursor.execute("SELECT count(*) FROM movies").fetchone()[0]
        count_persons = cursor.execute("SELECT count(*) FROM persons").fetchone()[0]

        conn.close()

        return {
            "status": "✅ Connecté",
            "movies_count": count_movies,
            "persons_count": count_persons,
            "path": str(db_path)
        }
    except Exception as e:
        return {"status": f"❌ Erreur : {e}"}