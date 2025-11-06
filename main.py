import os

import pandas as pd
from bson import ObjectId
from dotenv import load_dotenv
from minio import Minio
from pymongo import MongoClient
from flask import Flask, render_template, request, redirect, url_for, jsonify
from initialize_project import login_user, create_initial_admin_user, verify_login
import bcrypt
from datetime import datetime
from controllers.client_management import create_client, edit_client, create_client_user_c
from controllers.user_management import create_user
from models.ClientDocumentManager import ClientDocumentManager
from models.client import Client
from models.floorplan_model import FloorPlanModel
from minio.error import S3Error
from datetime import timedelta
from zoneinfo import ZoneInfo
from models.trap_model import TrapModel

from flask import session, redirect, url_for, render_template, request

from functools import wraps
from flask import redirect, url_for, session
from routes.onlyoffice_routes import onlyoffice_bp
from routes.downloads import downloads_bp


# Charger les variables d'environnement
load_dotenv()

# Initialiser l'application Flask
app = Flask(__name__)
app.register_blueprint(onlyoffice_bp)
app.register_blueprint(downloads_bp)
app.secret_key = os.getenv("SECRET_KEY")

# Définir l'environnement (DEV pour développement, PROD pour production)
IS_DEV = os.getenv("ENV", "DEV") == "DEV"

if IS_DEV:
    mongo_host = os.getenv("DEV_MONGO_HOST")
    mongo_database = os.getenv("DEV_MONGO_DATABASE")
    mongo_uri = f"mongodb://{mongo_host}/{mongo_database}"
else:
    mongo_uri = os.getenv("PROD_MONGO_URI")
    mongo_database = os.getenv("PROD_MONGO_DATABASE")
    mongo_uri = os.getenv("PROD_MONGO_URI")

# Connexion à MongoDB
client = MongoClient(mongo_uri)
db = client[mongo_database]
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limite à 16 Mo
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


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:  # Vérifie si la session contient un utilisateur
            return redirect(url_for("login"))  # Redirige vers la page de connexion
        return f(*args, **kwargs)

    return decorated_function


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Vérification des informations de connexion
        if verify_login(db, username, password):
            # Stocker les informations de l'utilisateur dans la session
            user = db.userInternet.find_one({"username": username})
            session["user_id"] = str(user["_id"])
            session["username"] = user["username"]
            session["display_name"] = user["displayname"]

            return redirect(url_for("welcome"))
        else:
            return render_template("login.html", error="Nom d'utilisateur ou mot de passe incorrect.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)  # Efface uniquement les clés d'admi
    return redirect(url_for("login"))


@app.route("/logout_client")
def logout_client():
    session.pop("client_user_id", None)  # Efface uniquement les clés de client
    session.pop("client_id", None)  # Efface toutes les données de session
    return redirect(url_for("client_login"))


@app.route("/welcome")
@login_required  # Utilisez le décorateur pour vérifier la session
def welcome():
    # Optionnel : vous pouvez afficher des informations sur l'utilisateur connecté
    # username = session.get("username", "Utilisateur")
    #
    display_name = session["username"]
    return render_template("welcome.html", message=f"Bienvenue, {display_name} ")


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


@app.route("/del_bucket")
def del_bucket():
    client = Minio(
        endpoint="https://minio.ahc-digital.com:9000",
        access_key="PierreAdmin",
        secret_key="O36paraf=Oceanweb++76",
        secure=True
    )

    bucket_name = "client-documents"

    # Supprimer tous les objets du bucket
    for obj in client.list_objects(bucket_name, recursive=True):
        client.remove_object(bucket_name, obj.object_name)

    # Supprimer le bucket
    client.remove_bucket(bucket_name)
    print(f"✅ Le bucket '{bucket_name}' a été supprimé.")


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


@app.route("/create_client", methods=["GET", "POST"])
def create_client_route():
    if request.method == "POST":
        # Appelle la fonction centralisée pour créer le client
        create_client(db, request.form, session["username"])
        return redirect(url_for("welcome", load="client_list"))

    # Passe un client vide pour la création
    empty_client = Client().to_dict()
    return render_template("create_client.html", client=empty_client, is_edit=False)


@app.route("/client_list")
def client_list():
    page = int(request.args.get('page', 1))  # Page actuelle, par défaut 1
    per_page = 50  # Nombre de clients par page
    skip = (page - 1) * per_page

    # Recherche et filtre
    search_query = request.args.get('search', '').strip()

    # Construire la requête MongoDB
    query = {}
    if search_query:
        try:
            # Si la recherche est un entier, rechercher dans `contractNumber`
            search_number = int(search_query)
            query["$or"] = [
                {"contractNumber": search_number},
                {"entity": search_number}
            ]
        except ValueError:
            # Sinon, utiliser une recherche textuelle
            query["$or"] = [
                {"companyName": {"$regex": search_query, "$options": "i"}},
                {"email": {"$regex": search_query, "$options": "i"}}
            ]

    # Total des clients pour pagination
    total_clients = db.clients.count_documents(query)

    # Récupération des clients avec pagination
    clients = list(db.clients.find(query, {
        "companyName": 1,
        "responsible": 1,
        "email": 1,
        "serviceAddress.treatmentPlaceName": 1,
        "contractNumber": 1,
        "entity": 1
    }).skip(skip).limit(per_page))

    # Calcul du nombre total de pages
    total_pages = (total_clients + per_page - 1) // per_page

    return render_template("client_list.html", clients=clients, page=page, total_pages=total_pages)


@app.route("/edit_client/<client_id>", methods=["GET", "POST"])
def edit_client_route(client_id):
    return edit_client(db, client_id, session["username"])


@app.route("/delete_client/<client_id>", methods=["POST"])
def delete_client(client_id):
    try:
        result = db.clients.delete_one({"_id": ObjectId(client_id)})
        if result.deleted_count == 1:
            return "Client supprimé", 200
        else:
            return "Client non trouvé", 404
    except Exception as e:
        return str(e), 500


@app.route("/delete_client/<client_id>", methods=["POST"])
def delete_client_route(client_id):
    return delete_client(db, client_id)


@app.route("/upload_document/<client_id>", methods=["POST"])
def upload_document(client_id):
    """
    Gère l'upload de document pour un client spécifique.
    """
    print(f"Route /upload_document appelée avec client_id: {client_id}")
    file = request.files.get("documentFile")
    document_type = request.form.get("documentType")  # Récupérer le type de document

    if not file or file.filename == "":
        print("Erreur : Aucun fichier sélectionné ou fichier vide.")
        return "Erreur : Aucun fichier sélectionné ou fichier vide.", 400

    if not document_type:
        print("Erreur : Type de document non spécifié.")
        return "Erreur : Type de document non spécifié.", 400

    client_doc_manager = ClientDocumentManager(db)
    print(f"Nom du fichier : {file.filename}")
    print(f"Type MIME : {file.content_type}")
    print(f"Type de document : {document_type}")

    # Lire les données du fichier
    file_data = file.stream.read()
    file_size = len(file_data)
    print(f"Taille des données lues : {file_size} octets")

    if file_size == 0:
        print("Erreur : Le fichier est vide.")
        return "Erreur : Le fichier est vide.", 400

    # Réinitialiser le pointeur du flux pour permettre d'autres lectures
    file.stream.seek(0)

    try:
        client_doc_manager.handle_file_upload(client_id, file, session["username"], document_type)  # Passez le type
        print(f"Fichier {file.filename} reçu pour le client {client_id}.")

        return redirect(url_for("welcome", load=f"edit_client_route={client_id}"))
    except Exception as e:
        print(f"Erreur lors de l'upload : {e}")
        return f"Erreur : {e}", 400


@app.route("/view_document/<document_id>", methods=["GET"])
def view_document(document_id):
    client_doc_manager = ClientDocumentManager(db)

    try:
        # Récupérer les métadonnées du document depuis MongoDB
        document = client_doc_manager.get_document_by_id(document_id)
        if not document:
            return "Document introuvable.", 404

        # Générer une URL signée pour l'accès temporaire
        object_name = document["fileUrl"].split(f"/{client_doc_manager.bucket_name}/")[-1]
        presigned_url = client_doc_manager.generate_presigned_url(object_name)

        # Rediriger vers l'URL signée
        return redirect(presigned_url)
    except Exception as e:
        return f"Erreur lors de l'accès au document : {e}", 500


@app.route("/upload_page/<client_id>", methods=["GET"])
def upload_page(client_id):
    """
    Affiche une page pour envoyer un fichier pour un client spécifique.
    """
    client = db.clients.find_one({"_id": ObjectId(client_id)})
    if not client:
        return "Client introuvable", 404
    return render_template("upload_file.html", client=client)


@app.route("/list_minio_files")
def list_minio_files():
    """
    Affiche la liste des fichiers présents dans le bucket MinIO avec des liens pour les voir.
    """
    try:
        # Configure le client MinIO
        minio_client = Minio(
            endpoint=os.getenv("AWS_ENDPOINT_URL").replace("http://", ""),
            access_key=os.getenv("AWS_ACCESS_KEY_ID"),
            secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            secure=False  # Désactive SSL pour un environnement local
        )

        # Nom du bucket
        bucket_name = os.getenv("AWS_BUCKET_NAME")

        # Récupère la liste des objets
        objects = minio_client.list_objects(bucket_name, recursive=True)
        file_list = []

        # Génère des URLs signées pour chaque fichier
        for obj in objects:
            presigned_url = minio_client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=obj.object_name,
                expires=timedelta(hours=1)  # URL valide pendant 1 heure
            )
            file_list.append({
                "name": obj.object_name,
                "size": obj.size,
                "url": presigned_url
            })

        return render_template("minio_file_list.html", files=file_list)

    except S3Error as e:
        return f"Erreur lors de la récupération des fichiers : {str(e)}", 500


@app.route("/client_dashboard")
def client_dashboard():
    client_id = session.get("client_id")
    if not client_id:
        return redirect(url_for("client_login"))

    # Récupérer les informations du client
    client = db.clients.find_one({"_id": ObjectId(client_id)})
    if not client:
        return "Client introuvable.", 404

    # Récupérer les documents associés au client
    client_doc_manager = ClientDocumentManager(db)
    documents = client_doc_manager.get_documents_by_client(client_id)

    # Récupérer les plans d'étage du client
    floorplans = list(db.floorPlans.find({"clientId": client_id}))
    floorplan_model = FloorPlanModel(db)

    for plan in floorplans:
        if "imagePath" in plan and plan["imagePath"]:
            plan["imageUrl"] = floorplan_model.get_signed_url(plan["imagePath"])  # Générer URL de l’image

        # Récupérer les pièges associés à ce plan
        plan["traps"] = list(db.traps.find({"planId": plan["_id"]}))

    return render_template(
        "client_dashboard.html",
        client=client,
        documents=documents,
        floorplans=floorplans
    )


@app.route("/client_login", methods=["GET", "POST"])
def client_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Vérifier l'utilisateur dans `clientUsers`
        client_user = db.clientUsers.find_one({"username": username})
        if client_user and bcrypt.checkpw(password.encode("utf-8"), client_user["password_hash"]):
            # Mettre à jour la date et l'heure de la dernière connexion
            db.clientUsers.update_one(
                {"_id": client_user["_id"]},
                {"$set": {"lastLogin": datetime.now(ZoneInfo("Europe/Paris"))}}
            )

            # Stocker les informations dans la session
            session["client_user_id"] = str(client_user["_id"])  # Stocker l'utilisateur dans la session
            session["client_id"] = client_user["clientId"]  # Stocker le client lié

            return redirect(url_for("client_dashboard"))
        else:
            return render_template("client_login.html", error="Nom d'utilisateur ou mot de passe incorrect.")

    return render_template("client_login.html")


@app.route("/create_client_user/<client_id>", methods=["POST"])
def create_client_user(client_id):
    """
    Route pour créer un utilisateur pour un client donné.
    """
    try:
        # Passe l'utilisateur connecté comme créateur
        create_client_user_c(db, client_id, request.form, session["username"])
        return redirect(url_for("welcome", load=f"edit_client_route={client_id}"))
    except ValueError as e:
        return f"Erreur : {e}", 400


import re  # Import pour utiliser les expressions régulières
from datetime import datetime


@app.route('/upload_excel', methods=['GET', 'POST'])
def upload_excel():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            return "Erreur : Aucun fichier sélectionné.", 400

        # Lire le fichier Excel
        try:
            df = pd.read_excel(file)
        except Exception as e:
            return f"Erreur lors de la lecture du fichier Excel : {e}", 400

        # Traitement des données
        for _, row in df.iterrows():
            try:
                # Extraction du nombre de mois (contractDuration)
                contract_duration_raw = row.get("Nb de mois du contrat", "")
                contract_duration = 0  # Valeur par défaut si extraction échoue

                if isinstance(contract_duration_raw, str):
                    match = re.search(r'\d+', contract_duration_raw)
                    if match:
                        contract_duration = int(match.group())

                # Conversion de la date de début de contrat (contractStartDate)
                contract_start_date_raw = row.get("Date début du contrat", "")
                contract_start_date = ""
                if isinstance(contract_start_date_raw, datetime):  # Si c'est un objet datetime
                    contract_start_date = contract_start_date_raw.strftime("%Y-%m-%d")
                elif isinstance(contract_start_date_raw, str):
                    try:
                        parsed_date = datetime.strptime(contract_start_date_raw, "%d/%m/%Y")
                        contract_start_date = parsed_date.strftime("%Y-%m-%d")
                    except ValueError:
                        contract_start_date = ""

                # Mappez les colonnes Excel aux champs de la base de données
                client_data = {
                    "companyName": row.get("Company name", "") or "",
                    "responsible": {
                        "firstName": row.get("First Name", "") or "",
                        "lastName": row.get("Last Name", "") or "",
                    },
                    "email": row.get("Email", "") or "",
                    "phone": row.get("Phone", "") or "",
                    "gsm": row.get("GSM", "") or "",
                    "vatNumber": row.get("TVA", "") or "",
                    "billingAddress": {
                        "address": row.get("adresses siège social", "") or "",
                        "postalCode": row.get("cp siège social", "") or "",
                        "city": row.get("ville siège social", "") or "",
                        "country": "",
                    },
                    "serviceAddress": {
                        "address": row.get("adresse lieu de traitement", "") or "",
                        "postalCode": row.get("ggg ", "") or "",
                        "city": row.get("ville lieu de traitement", "") or "",
                        "country": "",
                        "treatmentPlaceName": row.get("nom lieux de traitement") or "",
                    },
                    "notes": row.get("NOTES", "") or "",
                    "contractType": row.get("type de contrat", "") or "",
                    "contractNumber": row.get("N° Contrat", "") or "",
                    "entity": row.get("Entité ", "") or "",
                    "infoScanCtr": row.get("INFO SCAN CTR", "") or "",
                    "contractStartDate": contract_start_date,
                    "contractDuration": contract_duration,
                    "accountingEmails": row.get("mails comptabilité", "").split(",") if row.get(
                        "mails comptabilité") else [],
                    "nbPrestations": int(row.get("Nb de Prestions", 0)) if not pd.isna(
                        row.get("Nb de Prestions")) else 0,
                    "planningInfo": row.get("INFOS POUR PLANNINGS", "") or "",
                    "emailBeforeService": row.get("MAIL CLIENT AVANT PRESTATION", "") == "on",
                    "user": {
                        "createdBy": "admin",  # Remplacer par l'utilisateur connecté si nécessaire
                        "modifiedBy": "admin",
                    },
                    "creationDate": datetime.now(ZoneInfo("Europe/Paris")),
                    "modificationDate": datetime.now(ZoneInfo("Europe/Paris")),
                }

                # Insertion dans MongoDB
                db.clients.insert_one(client_data)
            except Exception as e:
                print(f"Erreur lors du traitement de la ligne {row.to_dict()} : {e}")

        return redirect(url_for("welcome", load="client_list"))

    return render_template('upload_excel.html')


@app.route("/add_intervention/<client_id>", methods=["POST"])
def add_intervention(client_id):
    """
    Ajoute une intervention pour un client spécifique.
    """
    try:
        # Récupérer les données du formulaire
        new_date = request.form.get("newInterventionDate")
        description = request.form.get("description", "").strip()

        # Vérifier que la date est fournie
        if not new_date:
            return "Erreur : La date d'intervention est obligatoire.", 400

        # Convertir la date en format datetime
        intervention_date = datetime.strptime(new_date, "%Y-%m-%d")

        # Préparer les données pour l'insertion
        intervention = {
            "clientId": client_id,
            "date": intervention_date,
            "description": description
        }

        # Insérer dans la collection `interventions`
        db.interventions.insert_one(intervention)

        # Rediriger vers l'onglet Dates d'Intervention du client
        return redirect(url_for("welcome", load=f"edit_client_route={client_id}#dates"))

    except Exception as e:
        print(f"Erreur lors de l'ajout de l'intervention : {e}")
        return f"Erreur : {e}", 500


@app.route("/add_floorplan/<client_id>", methods=["POST"])
def add_floorplan(client_id):
    """
    Route pour ajouter un nouveau plan d'étage.
    """
    file = request.files.get("image")
    name = request.form.get("name")
    description = request.form.get("description")

    if not file or file.filename.strip() == "":
        return "Erreur : Aucun fichier sélectionné ou nom de fichier invalide.", 400

    if not name:
        return "Erreur : Le nom du plan est requis.", 400

    # Crée une instance de FloorPlanModel
    floorplan_model = FloorPlanModel(db)

    try:
        # Ajouter le plan d'étage et gérer l'upload en même temps
        floorplan_model.add_floorplan(
            client_id=client_id,
            file=file,
            name=name,
            description=description,
            uploaded_by=session["username"]
        )
    except Exception as e:
        return f"Erreur : {e}", 500

    # Rediriger vers la page du client
    return redirect(url_for("welcome", load=f"edit_client_route={client_id}"))


@app.route("/add_trap/<plan_id>", methods=["POST"])
def add_trap(plan_id):
    """
    Route pour ajouter un nouveau piège à un plan d'étage.
    """
    trap_model = TrapModel(db)
    trap_data = {
        "type": request.form.get("type"),
        "label": request.form.get("label"),
        "location": request.form.get("location"),
        "coordinates": {
            "x": request.form.get("x"),
            "y": request.form.get("y")
        },
        "barcode": request.form.get("barcode")
    }

    try:
        # Ajouter le piège
        trap_model.add_trap(plan_id, trap_data)

        # Récupérer le `client_id` associé au `plan_id`
        plan = db.floorPlans.find_one({"_id": ObjectId(plan_id)})
        if not plan:
            return "Plan d'étage introuvable", 404
        client_id = plan["clientId"]

        # Rediriger vers la page d'édition du client
        return redirect(url_for("welcome", load=f"edit_client_route={client_id}"))
    except Exception as e:
        return f"Erreur : {e}", 500


@app.route("/edit_plan/<plan_id>", methods=["GET"])
def edit_plan(plan_id):
    floorplan_model = FloorPlanModel(db)
    trap_model = TrapModel(db)

    plan = floorplan_model.get_floorplan(plan_id)
    traps = trap_model.get_traps_by_plan(plan_id)

    return render_template("edit_plan.html", plan=plan, traps=traps)


@app.route("/manage_traps/<plan_id>")
@login_required
def manage_traps(plan_id):
    """
    Affiche la page pour gérer les pièges sur un plan d'étage.
    """
    try:
        object_id = ObjectId(plan_id)  # Convertir en ObjectId
    except Exception:
        return "ID de plan invalide", 400

    # Récupérer le plan et les pièges
    plan = db.floorPlans.find_one({"_id": object_id})
    if not plan:
        return "Plan d'étage introuvable", 404

    traps = list(db.traps.find({"planId": object_id}))
    for trap in traps:
        if "coordinates" in trap:
            trap["coordinates"] = {
                "x": int(trap["coordinates"]["x"]) if trap["coordinates"]["x"] else 0,
                "y": int(trap["coordinates"]["y"]) if trap["coordinates"]["y"] else 0
            }

    # Générer une URL signée pour le plan (si `imagePath` est bien défini)
    floorplan_model = FloorPlanModel(db)
    if "imagePath" in plan and plan["imagePath"]:
        plan["imageUrl"] = floorplan_model.get_signed_url(plan["imagePath"])
    else:
        plan["imageUrl"] = None

    print("Image URL:", plan.get("imageUrl"))  # Vérifier si une URL est générée

    return render_template("manage_traps.html", plan=plan, traps=traps)


@app.route("/save_trap_position", methods=["POST"])
@login_required
def save_trap_position():
    """
    Enregistre les coordonnées d'un piège sur un plan d'étage.
    """
    data = request.get_json()
    trap_id = data.get("trap_id")
    x = data.get("x")
    y = data.get("y")

    if not trap_id or x is None or y is None:
        return jsonify({"success": False, "error": "Données incomplètes"}), 400

    try:
        db.traps.update_one(
            {"_id": ObjectId(trap_id)},
            {"$set": {"coordinates": {"x": x, "y": y}}}
        )
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
