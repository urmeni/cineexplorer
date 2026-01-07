import pymongo
import time
import sys


def init_replica_set():
    print("⚙Initialisation du Replica Set 'rs0'...")

    try:
        # On se connecte au nœud qui sera le primaire (27017)
        # directConnection=True est important pour configurer un nœud spécifique avant que le RS existe
        client = pymongo.MongoClient("mongodb://localhost:27017/", directConnection=True)

        # Configuration du Replica Set
        config = {
            "_id": "rs0",
            "members": [
                {"_id": 0, "host": "localhost:27017"},
                {"_id": 1, "host": "localhost:27018"},
                {"_id": 2, "host": "localhost:27019"}
            ]
        }

        # Commande admin pour initier
        client.admin.command("replSetInitiate", config)
        print("Commande 'replSetInitiate' envoyée avec succès.")

        # Attente de l'élection
        print("⏳ Attente de l'élection du Primary...")
        time.sleep(10)  # On laisse le temps au cluster de voter

        # Vérification
        status = client.admin.command("replSetGetStatus")
        print(f"\n--- État du Cluster (Set: {status['set']}) ---")
        for member in status['members']:
            state_str = "PRIMARY" if member['state'] == 1 else "SECONDARY" if member['state'] == 2 else f"STATE {member['state']}"
            print(f"   [{member['_id']}] {member['name']} : {state_str}")

    except pymongo.errors.OperationFailure as e:
        if "already initialized" in str(e):
            print("⚠️  Le Replica Set est DÉJÀ initialisé.")
            # On affiche quand même le statut
            client = pymongo.MongoClient("mongodb://localhost:27017/", directConnection=True)
            status = client.admin.command("replSetGetStatus")
            for member in status['members']:
                print(f"   [{member['_id']}] {member['name']} : État {member['stateStr']}")
        else:
            print(f"Erreur critique : {e}")


if __name__ == "__main__":
    init_replica_set()