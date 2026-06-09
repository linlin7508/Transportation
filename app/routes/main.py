from flask import Blueprint, render_template, request, redirect, session, url_for

main_bp = Blueprint("main", __name__)


def _firebase_config():
    return {
        "apiKey": "",
        "authDomain": "",
        "projectId": "",
        "storageBucket": "",
        "messagingSenderId": "",
        "appId": "",
    }


def _ensure_session_user():
    if "user" not in session:
        session["user"] = {
            "uid": session.get("user_id", ""),
            "username": "訪客訓練師",
            "email": "",
        }


@main_bp.get("/", endpoint="index")
def index():
    # Render the main homepage template if present
    return render_template("main/home.html")


@main_bp.get("/home", endpoint="home")
def home():
    return render_template("main/home.html")


@main_bp.get("/profile", endpoint="profile")
def profile():
    _ensure_session_user()
    return render_template("main/profile.html", firebase_config=_firebase_config())


@main_bp.route("/profile/edit", methods=["GET", "POST"], endpoint="edit_profile")
def edit_profile():
    _ensure_session_user()
    user_data = {
        "username": session["user"].get("username", "訪客訓練師"),
        "avatar": "",
        "avatar_id": "",
    }

    if request.method == "POST":
        username = request.form.get("username")
        if username:
            session["user"]["username"] = username
            session.modified = True
        return redirect(url_for("main.profile"))

    return render_template("main/edit_profile.html", user_data=user_data)
