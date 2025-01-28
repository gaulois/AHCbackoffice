from models.client import Client
from bson.objectid import ObjectId
from flask import request, render_template, redirect, url_for, jsonify
from models.ClientDocumentManager import ClientDocumentManager
from bson.objectid import ObjectId
from datetime import datetime
import bcrypt


def create_client(db, form_data, username):
    """
    Gère la création d'un client.
    :param username:
    :param db: Instance MongoDB.
    :param form_data: Données soumises via le formulaire.
    :return: Dictionnaire du client créé.
    """
    # Crée un nouveau client
    client = Client.from_form(form_data)
    client.user["createdBy"] = username
    client.user["modifiedBy"] = username
    client.save(db)

    return client.to_dict()

def edit_client(db, client_id, username):
    if request.method == "POST":
        # Charger le client existant pour conserver ses métadonnées
        existing_client = db.clients.find_one({"_id": ObjectId(client_id)})
        client = Client.from_form(request.form, existing_client)
        client.user["modifiedBy"] = username
        client.save(db)  # Sauvegarde les modifications
        return redirect(url_for("welcome", load="client_list"))

    # Charger les données actuelles du client
    client_data = db.clients.find_one({"_id": ObjectId(client_id)})
    if not client_data:
        return "Client introuvable", 404

    # Charger les interventions associées
    interventions = list(db.interventions.find({"clientId": client_id}))

    # Charger les documents et les utilisateurs associés
    client_doc_manager = ClientDocumentManager(db)
    documents = client_doc_manager.get_documents_by_client(client_id)
    client_users = list(db.clientUsers.find({"clientId": str(client_id)}))

    # Charger les plans d'étage associés
    floorplans = list(db.floorPlans.find({"clientId": client_id}))

    # Passer les données au template
    return render_template(
        "create_client.html",
        client=client_data,
        documents=documents,
        client_users=client_users,
        interventions=interventions,
        floorplans=floorplans,  # Ajouter les plans d'étage au contexte
        is_edit=True
    )


def delete_client(db, client_id):
    client = Client(client_id=ObjectId(client_id))
    if client.delete(db):
        return jsonify({"message": "Client supprimé avec succès"}), 200
    return jsonify({"error": "Client non trouvé"}), 404

def create_client_user_c(db, client_id, form_data, created_by):
    """
    Crée un utilisateur pour un client donné.
    """
    username = form_data.get("username")
    password = form_data.get("password")
    print(f"create_client_user avec client_id: {client_id}")

    if not username or not password:
        raise ValueError("Nom d'utilisateur ou mot de passe manquant.")

    # Vérifie que le client existe
    client = db.clients.find_one({"_id": ObjectId(client_id)})
    if not client:
        raise ValueError("Client introuvable.")

    # Vérifie que le nom d'utilisateur est unique
    existing_user = db.clientUsers.find_one({"username": username})
    if existing_user:
        raise ValueError("Nom d'utilisateur déjà utilisé.")

    # Hash du mot de passe
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Création de l'utilisateur avec le champ createdBy
    user_data = {
        "clientId": client_id,
        "username": username,
        "password_hash": password_hash,
        "displayName": client["companyName"],
        "createdBy": created_by,  # Ajout du créateur
        "createdDate": datetime.utcnow(),
        "lastLogin": None,
    }

    db.clientUsers.insert_one(user_data)
    print(f"Utilisateur {username} créé avec succès pour le client {client_id}.")
