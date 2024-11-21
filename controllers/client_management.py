from datetime import datetime

from flask import request, render_template, redirect, url_for
from bson.objectid import ObjectId
from datetime import datetime


def create_client(db):
    if request.method == "POST":
        client_data = {
            "companyName": request.form.get("companyName"),
            "responsible": {
                "firstName": request.form.get("firstName"),
                "lastName": request.form.get("lastName"),
            },
            "email": request.form.get("email"),
            "phone": request.form.get("phone"),
            "gsm": request.form.get("gsm"),
            "vatNumber": request.form.get("vatNumber"),
            "billingAddress": {
                "address": request.form.get("billingAddress[address]"),
                "postalCode": request.form.get("billingAddress[postalCode]"),
                "city": request.form.get("billingAddress[city]"),
                "country": request.form.get("billingAddress[country]"),
            },
            "serviceAddress": {
                "address": request.form.get("serviceAddress[address]"),
                "postalCode": request.form.get("serviceAddress[postalCode]"),
                "city": request.form.get("serviceAddress[city]"),
                "country": request.form.get("serviceAddress[country]"),
            },
            "creationDate": datetime.utcnow(),
            "modificationDate": datetime.utcnow(),
            "user": {
                "createdBy": "admin",
                "modifiedBy": "admin",
            },
            "notes": request.form.get("notes"),
        }

        # Insérer les données dans la base de données MongoDB
        db.clients.insert_one(client_data)

        # Rediriger vers la liste des clients
        return redirect(url_for("welcome", load="client_list"))

    return render_template("create_client.html")




def edit_client(db, client_id):
    # Gestion du formulaire soumis
    if request.method == "POST":
        updated_data = {
            "companyName": request.form.get("companyName"),
            "responsible": {
                "firstName": request.form.get("firstName"),
                "lastName": request.form.get("lastName")
            },
            "email": request.form.get("email"),
            "phone": request.form.get("phone"),
            "gsm": request.form.get("gsm"),
            "vatNumber": request.form.get("vatNumber"),
            "billingAddress": {
                "address": request.form.get("billingAddress[address]"),
                "postalCode": request.form.get("billingAddress[postalCode]"),
                "city": request.form.get("billingAddress[city]"),
                "country": request.form.get("billingAddress[country]")
            },
            "serviceAddress": {
                "address": request.form.get("serviceAddress[address]"),
                "postalCode": request.form.get("serviceAddress[postalCode]"),
                "city": request.form.get("serviceAddress[city]"),
                "country": request.form.get("serviceAddress[country]")
            },
            "modificationDate": datetime.utcnow()
        }

        # Met à jour les données dans la base de données
        db.clients.update_one({"_id": ObjectId(client_id)}, {"$set": updated_data})
        return redirect(url_for("welcome", load="client_list"))

    # Charge les données actuelles du client
    client = db.clients.find_one({"_id": ObjectId(client_id)})
    return render_template("create_client.html", client=client, is_edit=True)