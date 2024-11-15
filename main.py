import os
from dotenv import load_dotenv
from pymongo import MongoClient
from flask import Flask, render_template, request, redirect, url_for
from initialize_project import login_user, create_initial_admin_user, verify_login
import bcrypt
from controllers.user_management import create_user

# Charger les variables d'environnement
load_dotenv()

# Initialiser l'application Flask
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Définir l'environnement (DEV pour développement, PROD pour production)
IS_DEV = os.getenv("ENV", "DEV") == "DEV"

# Configuration des paramètres MongoDB
if IS_DEV:
    mongo_host = os.getenv("DEV_MONGO_HOST")
    mongo_database = os.getenv("DEV_MONGO_DATABASE")
    mongo_uri = f"mongodb://{mongo_host}/{mongo_database}"
else:
    mongo_username = os.getenv("MONGO_USERNAME")
    mongo_password = os.getenv("MONGO_PASSWORD")
    mongo_host = os.getenv("PROD_MONGO_HOST")
    mongo_database = os.getenv("PROD_MONGO_DATABASE")
    mongo_uri = f"mongodb://{mongo_username}:{mongo_password}@{mongo_host}/{mongo_database}"

# Connexion à MongoDB
client = MongoClient(mongo_uri)
db = client[mongo_database]

# Vérification de l'existence de la collection et création d'un admin si nécessaire
if "userInternet" not in db.list_collection_names():
    create_initial_admin_user(db)


@app.route("/")
def home():
    # Vérifier si la collection userInternet existe
    if "userInternet" in db.list_collection_names():
        # Rediriger vers la page de login si la collection existe
        return redirect(url_for('login'))
    else:
        # Demander la création de l'admin si la collection n'existe pas
        return "Veuillez initialiser l'administrateur dans MongoDB."


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Vérification des informations de connexion
        if verify_login(db, username, password):
            return redirect(url_for("welcome"))
        else:
            return render_template("login.html", error="Nom d'utilisateur ou mot de passe incorrect.")
    return render_template("login.html")


@app.route("/welcome")
def welcome():
    return render_template("welcome.html", message="Bienvenue !")


@app.route("/create_user", methods=["GET", "POST"])
def create_user_route():
    if request.method == "POST":
        # Récupère les données du formulaire
        username = request.form.get("username")
        displayname = request.form.get("displayname")
        role = request.form.get("role")
        password = request.form.get("password")

        # Hachage du mot de passe
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        # Vérifie si l'utilisateur existe déjà
        if db.userInternet.find_one({"username": username}):
            return "Utilisateur existe déjà", 400

        # Crée un nouvel utilisateur
        new_user = {
            "username": username,
            "displayname": displayname,
            "role": role,
            "password_hash": password_hash
        }
        db.userInternet.insert_one(new_user)

        # Redirige vers welcome avec user_list chargé
        return redirect(url_for("welcome", load="user_list"))

    # Si méthode GET, affiche le formulaire
    return render_template("create_user.html")



@app.route("/user_list")
def user_list():
    # Récupère tous les utilisateurs sans le mot de passe
    users = db.userInternet.find({}, {"username": 1, "displayname": 1, "role": 1, "_id": 0})
    return render_template("user_list.html", users=users)


@app.route("/edit_user/<username>", methods=["GET", "POST"])
def edit_user(username):
    user = db.userInternet.find_one({"username": username})

    if not user:
        return "Utilisateur non trouvé", 404

    if request.method == "POST":
        displayname = request.form.get("displayname")
        role = request.form.get("role")

        # Mettre à jour les informations de l'utilisateur
        db.userInternet.update_one(
            {"username": username},
            {"$set": {"displayname": displayname, "role": role}}
        )

        return redirect(url_for("welcome", load="user_list"))

    return render_template("edit_user.html", user=user)


@app.route("/delete_user/<username>", methods=["POST"])
def delete_user(username):
    user = db.userInternet.find_one({"username": username})
    if not user:
        return "Utilisateur non trouvé", 404

    db.userInternet.delete_one({"username": username})
    return "Utilisateur supprimé", 200


@app.route("/create_client")
def create_client():
    return "Créer un client - à implémenter"


@app.route("/client_list")
def client_list():
    # Logic to display the client list
    return "Liste des clients - à implémenter"


if __name__ == "__main__":
    app.run(debug=True)
