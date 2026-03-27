from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from bson import ObjectId
from controllers.client_management import create_client, edit_client
from models.client import Client

clients_bp = Blueprint('clients', __name__)


@clients_bp.route("/create_client", methods=["GET", "POST"])
def create_client_route():
    db = current_app.config['MONGO_DB']
    if request.method == "POST":
        # Appelle la fonction centralisée pour créer le client
        create_client(db, request.form, session["username"])
        return redirect(url_for("welcome", load="client_list"))

    # Passe un client vide pour la création
    empty_client = Client().to_dict()
    return render_template("create_client.html", client=empty_client, is_edit=False)


@clients_bp.route("/client_list")
def client_list():
    db = current_app.config['MONGO_DB']
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


@clients_bp.route("/edit_client/<client_id>", methods=["GET", "POST"])
def edit_client_route(client_id):
    db = current_app.config['MONGO_DB']
    return edit_client(db, client_id, session["username"])


@clients_bp.route("/delete_client/<client_id>", methods=["POST"])
def delete_client(client_id):
    db = current_app.config['MONGO_DB']
    try:
        result = db.clients.delete_one({"_id": ObjectId(client_id)})
        if result.deleted_count == 1:
            return "Client supprimé", 200
        else:
            return "Client non trouvé", 404
    except Exception as e:
        return str(e), 500


@clients_bp.route("/delete_client/<client_id>", methods=["POST"])
def delete_client_route(client_id):
    return delete_client(db, client_id)
