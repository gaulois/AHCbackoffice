from models.client import Client
from bson.objectid import ObjectId
from flask import request, render_template, redirect, url_for


def create_client(db):
    if request.method == "POST":
        # Crée un client à partir des données du formulaire
        client = Client.from_form(request.form)
        client.save(db)  # Sauvegarde dans MongoDB
        return redirect(url_for("welcome", load="client_list"))

    return render_template("create_client.html")


def edit_client(db, client_id):
    if request.method == "POST":
        # Charge le client existant pour conserver ses métadonnées
        existing_client = db.clients.find_one({"_id": ObjectId(client_id)})
        client = Client.from_form(request.form, existing_client)
        client.save(db)  # Sauvegarde les modifications
        return redirect(url_for("welcome", load="client_list"))

    # Charge les données actuelles du client pour pré-remplir le formulaire
    client_data = db.clients.find_one({"_id": ObjectId(client_id)})
    return render_template("create_client.html", client=client_data, is_edit=True)

def delete_client(db, client_id):
    client = Client(client_id=ObjectId(client_id))
    if client.delete(db):
        return jsonify({"message": "Client supprimé avec succès"}), 200
    return jsonify({"error": "Client non trouvé"}), 404