import bcrypt
from pymongo.errors import DuplicateKeyError
from flask import session

def create_initial_admin_user(db):
    """Crée un utilisateur admin si la collection userInternet n'existe pas."""
    # Vérifie si la collection 'userInternet' existe déjà
    if "userInternet" not in db.list_collection_names():
        print("La collection 'userInternet' n'existe pas. Création du premier utilisateur admin.")

        username = input("Entrez le nom d'utilisateur admin : ")
        password = input("Entrez le mot de passe admin : ")

        # Hachage du mot de passe
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Création de l'utilisateur admin
        admin_user = {
            "username": username,
            "userid": "admin",
            "displayname": "Administrator",
            "password_hash": password_hash,
            "role": "admin"
        }

        try:
            db.userInternet.insert_one(admin_user)
            print("Utilisateur admin créé avec succès.")
        except DuplicateKeyError:
            print("Un utilisateur admin existe déjà.")
    else:
        print("La collection 'userInternet' existe déjà.")


def login_user(db):
    """Gère la connexion de l'utilisateur."""
    username = input("Nom d'utilisateur : ")
    password = input("Mot de passe : ")

    # Recherche de l'utilisateur
    user = db.userInternet.find_one({"username": username})

    if user and bcrypt.checkpw(password.encode('utf-8'), user["password_hash"]):
        print(f"Bienvenue, {user['displayname']} !")
    else:
        print("Nom d'utilisateur ou mot de passe incorrect.")


def verify_login(db, username, password):
    """Vérifie les informations de connexion de l'utilisateur et met à jour la session."""
    user = db.userInternet.find_one({"username": username})
    if user and bcrypt.checkpw(password.encode("utf-8"), user["password_hash"]):
        # Stocker les informations utilisateur dans la session
        session["user_id"] = str(user["_id"])
        session["username"] = user["username"]
        session["display_name"] = user.get("displayname", "Utilisateur")
        return True
    return False
