import pymongo
import time
import sys
from pymongo.errors import AutoReconnect, ConnectionFailure, ServerSelectionTimeoutError

# URL de connexion au Replica Set (on liste tous les membres potentiels)
MONGO_URI = "mongodb://localhost:27017,localhost:27018,localhost:27019/?replicaSet=rs0"


def get_topology(client):
    """Récupère l'état actuel du cluster"""
    try:
        status = client.admin.command("replSetGetStatus")
        topology = {}
        for member in status['members']:
            state = "PRIMARY" if member['state'] == 1 else "SECONDARY" if member[
                                                                              'state'] == 2 else f"STATE {member['state']}"
            topology[member['name']] = state
        return topology
    except Exception as e:
        return None


def wait_for_primary(client):
    """Boucle jusqu'à ce qu'un primaire soit élu"""
    print("⏳ Recherche du nouveau Primary...")
    start = time.time()
    while True:
        try:
            # ismaster permet de savoir qui est le chef
            status = client.admin.command("isMaster")
            if status.get("ismaster"):
                end = time.time()
                print(f"✅ NOUVEAU PRIMARY DÉTECTÉ : {status.get('primary')}")
                print(f"⏱️ Temps de bascule (Failover) : {end - start:.2f} secondes")
                return status.get('primary')
        except (AutoReconnect, ConnectionFailure):
            # C'est normal d'avoir des erreurs pendant l'élection
            time.sleep(0.5)
        except Exception as e:
            print(f"Erreur : {e}")
            time.sleep(1)


def run_failover_test():
    print("=" * 60)
    print("TEST DE TOLÉRANCE AUX PANNES (FAILOVER)")
    print("=" * 60)

    # Connexion robuste
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["imdb_project"]
    collection = db["failover_test"]

    # --- ÉTAPE 1 : ÉTAT INITIAL ---
    print("\n--- 1. ÉTAT INITIAL ---")
    topo = get_topology(client)
    primary_host = None
    if topo:
        for host, state in topo.items():
            print(f"   [{host}] : {state}")
            if state == "PRIMARY": primary_host = host
    else:
        print("❌ Impossible de récupérer la topologie.")
        return

    # --- ÉTAPE 2 : ÉCRITURE ---
    print("\n--- 2. TEST D'ÉCRITURE ---")
    try:
        doc = {"test": "failover", "timestamp": time.time()}
        res = collection.insert_one(doc)
        print(f"✅ Document inséré sur le PRIMARY ({primary_host}) avec ID: {res.inserted_id}")
        print("   La réplication vers les Secondaries est automatique.")
    except Exception as e:
        print(f"❌ Erreur d'écriture : {e}")

    # --- ÉTAPE 3 : PANNE ---
    print("\n" + "!" * 60)
    print(f"👉 ACTION REQUISE : Va dans le terminal du PRIMARY ({primary_host})")
    print("👉 Fais 'Ctrl+C' pour l'arrêter maintenant !")
    print("!" * 60)

    input("⌨️  Une fois le serveur arrêté, appuie sur [ENTRÉE] ici pour lancer le chrono...")

    # --- ÉTAPE 4 : NOUVEAU PRIMARY ---
    print("\n--- 4. ÉLECTION DU NOUVEAU PRIMARY ---")
    new_primary = wait_for_primary(client)

    if new_primary == primary_host:
        print("⚠️  Bizarre, le Primary semble être le même. Es-tu sûr de l'avoir coupé ?")
    else:
        print(f"🎉 L'ancien Primary ({primary_host}) est mort, vive le nouveau ({new_primary}) !")

    # --- ÉTAPE 5 : LECTURE ---
    print("\n--- 5. VÉRIFICATION DES DONNÉES ---")
    try:
        # On essaie de relire le document inséré avant la panne
        count = collection.count_documents({"test": "failover"})
        if count > 0:
            print(f"✅ DONNÉES PRÉSERVÉES ! {count} document(s) retrouvé(s).")
            print("   Cela prouve que la donnée a eu le temps d'être répliquée avant le crash.")
        else:
            print("❌ Données perdues (n'ont pas eu le temps d'être répliquées).")
    except Exception as e:
        print(f"❌ Erreur de lecture : {e}")

    # --- ÉTAPE 6 : RECONNEXION ---
    print("\n" + "!" * 60)
    print(f"👉 ACTION REQUISE : Relance le nœud que tu as arrêté ({primary_host})")
    print(f"   Commande rappel : mongod --replSet rs0 --port <PORT> --dbpath ...")
    print("!" * 60)
    input("⌨️  Appuie sur [ENTRÉE] une fois le nœud relancé...")

    print("⏳ Attente de la synchronisation (Resync)...")
    time.sleep(5)
    topo = get_topology(client)
    print("Nouvel état du cluster :")
    for host, state in topo.items():
        print(f"   [{host}] : {state}")

    # --- ÉTAPE 7 : DOUBLE PANNE ---
    print("\n--- 7. SCÉNARIO CATASTROPHE (DOUBLE PANNE) ---")
    print("Pour qu'un Replica Set fonctionne en écriture, il faut une MAJORITÉ (Quorum).")
    print("Avec 3 nœuds, majorité = 2.")
    print("Si 2 nœuds tombent, il en reste 1. 1 < 2. Donc le dernier devient READ-ONLY.")

    print("\n👉 ACTION : Tue un DEUXIÈME nœud (n'importe lequel sauf le dernier survivant).")
    input("⌨️  Appuie sur [ENTRÉE] une fois fait...")

    print("Tentative d'écriture (devrait échouer ou timeout)...")
    try:
        collection.insert_one({"test": "crash_test"}, write_concern=pymongo.WriteConcern(w=1, wtimeout=3000))
        print("❌ Écriture réussie (Inattendu avec 1 seul nœud actif sur 3 !)")
    except Exception as e:
        print(f"✅ Écriture bloquée comme prévu : {e}")
        print("   Le cluster est passé en mode LECTURE SEULE (Secondary) pour protéger les données.")

    print("\n🏁 Test terminé.")


if __name__ == "__main__":
    run_failover_test()