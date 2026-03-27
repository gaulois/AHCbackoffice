from functools import wraps

import bcrypt
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Blueprint, render_template, request, redirect, url_for, session, current_app

from initialize_project import verify_login

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = current_app.config["MONGO_DB"]

        if verify_login(db, username, password):
            user = db.userInternet.find_one({"username": username})
            session["user_id"] = str(user["_id"])
            session["username"] = user["username"]
            session["display_name"] = user["displayname"]
            return redirect(url_for("welcome"))
        else:
            return render_template("login.html", error="Nom d'utilisateur ou mot de passe incorrect.")
    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("auth.login"))


@auth_bp.route("/logout_client")
def logout_client():
    session.pop("client_user_id", None)
    session.pop("client_id", None)
    return redirect(url_for("auth.client_login"))


@auth_bp.route("/client_login", methods=["GET", "POST"])
def client_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = current_app.config["MONGO_DB"]

        client_user = db.clientUsers.find_one({"username": username})
        if client_user and bcrypt.checkpw(password.encode("utf-8"), client_user["password_hash"]):
            db.clientUsers.update_one(
                {"_id": client_user["_id"]},
                {"$set": {"lastLogin": datetime.now(ZoneInfo("Europe/Paris"))}}
            )
            session["client_user_id"] = str(client_user["_id"])
            session["client_id"] = client_user["clientId"]
            return redirect(url_for("client_dashboard"))
        else:
            return render_template("client_login.html", error="Nom d'utilisateur ou mot de passe incorrect.")
    return render_template("client_login.html")
