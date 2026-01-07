from pymongo import MongoClient
import sys

def test_mongo_connection():
    print("Tentative de connexion à MongoDB...")
    try:
        client = MongoClient('mongodb://localhost:27017/')
        client.admin.command('ping')
        print("Connexion RÉUSSIE à MongoDB !")
        print(f"   Version : {client.server_info()['version']}")
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    test_mongo_connection()