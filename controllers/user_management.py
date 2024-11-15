import bcrypt
from flask import render_template, request, redirect, url_for, flash

def create_user(db):
    if request.method == "POST":
        # Récupère les données du formulaire
        username = request.form["username"]
        displayname = request.form["displayname"]
        password = request.form["password"]
        role = request.form["role"]

        # Vérifie si le nom d'utilisateur existe déjà
        existing_user = db.userInternet.find_one({"username": username})
        if existing_user:
            # Affiche un message d'erreur si le nom d'utilisateur est déjà pris
            flash("Le nom d'utilisateur est déjà utilisé. Veuillez en choisir un autre.", "error")
            return render_template("create_user.html")  # Renvoie le formulaire avec le message d'erreur

        # Hachage du mot de passe
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        # Crée un dictionnaire pour l'utilisateur
        new_user = {
            "username": username,
            "displayname": displayname,
            "password_hash": password_hash,
            "role": role
        }

        # Insère l'utilisateur dans la collection MongoDB
        db.userInternet.insert_one(new_user)
        return redirect(url_for("user_list"))

    return render_template("create_user.html")
