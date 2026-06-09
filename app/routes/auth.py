from flask import Blueprint, request, session, jsonify, render_template, redirect, url_for
from sqlalchemy.exc import IntegrityError
from app.services.auth_service import register as register_user, login as login_user
from app.models.user import User
from app.extensions import db

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _bad_request(msg="bad request"):
    return jsonify({"error": msg}), 400


def _wants_json():
    return request.is_json or (
        request.accept_mimetypes["application/json"] > request.accept_mimetypes["text/html"]
    )


def _auth_payload():
    if request.is_json:
        return request.get_json() or {}
    return request.form


def _auth_error(message, status, template):
    if _wants_json():
        return jsonify({"error": message}), status
    return render_template(template), status


@auth_bp.route("/register", methods=["GET", "POST"], endpoint="register")
def register_route():
    if request.method == "GET":
        return render_template("auth/register.html")

    data = _auth_payload()

    email = data.get("email")
    password = data.get("password")
    username = data.get("username")

    if not email:
        return _auth_error("email required", 400, "auth/register.html")
    if "@" not in email:
        return _auth_error("invalid email format", 400, "auth/register.html")
    if not password:
        return _auth_error("password required", 400, "auth/register.html")
    if not username:
        return _auth_error("username required", 400, "auth/register.html")

    # Check duplicates early to return a clear status code
    if User.query.filter_by(email=email).first():
        return _auth_error("email already exists", 409, "auth/register.html")
    if User.query.filter_by(username=username).first():
        return _auth_error("username already exists", 409, "auth/register.html")

    try:
        user = register_user(email=email, password=password, username=username)
    except IntegrityError:
        db.session.rollback()
        return _auth_error("duplicate or integrity error", 409, "auth/register.html")
    except Exception as e:
        db.session.rollback()
        print("REGISTER ERROR:", repr(e))
        raise

    session["user_id"] = str(user.id)
    session["user"] = {"uid": str(user.id), "username": user.username, "email": user.email}

    if _wants_json():
        return jsonify({"user_id": str(user.id)})
    return redirect("/")


@auth_bp.route("/login", methods=["GET", "POST"], endpoint="login")
def login_route():
    if request.method == "GET":
        return render_template("auth/login.html")

    data = _auth_payload()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return _auth_error("email and password required", 400, "auth/login.html")

    user = login_user(email, password)

    if not user:
        return _auth_error("invalid credentials", 401, "auth/login.html")

    session["user_id"] = str(user.id)
    session["user"] = {"uid": str(user.id), "username": user.username, "email": user.email}

    if _wants_json():
        return jsonify({"message": "login success"})
    return redirect("/")


@auth_bp.route("/logout", methods=["GET", "POST"], endpoint="logout")
def logout():
    session.clear()
    if request.method == "GET" and not _wants_json():
        return redirect(url_for("main.index"))
    return jsonify({"message": "logged out"})

@auth_bp.get("/me")
def me():
    from flask import g
    if not getattr(g, "user", None):
        return jsonify({"error": "unauthorized"}), 401

    return jsonify({
        "user_id": str(g.user.id),
        "username": g.user.username
    })


@auth_bp.get("/terms-of-service", endpoint="terms_of_service")
def terms_of_service():
    return render_template("auth/terms_of_service.html")


@auth_bp.get("/privacy-policy", endpoint="privacy_policy")
def privacy_policy():
    return render_template("auth/privacy_policy.html")


@auth_bp.route("/login-for-setup", methods=["GET", "POST"], endpoint="login_for_setup")
def login_for_setup():
    if request.method == "POST":
        return login_route()
    return render_template("auth/login_for_setup.html")


@auth_bp.route("/user-setup", methods=["GET", "POST"], endpoint="user_setup")
def user_setup():
    return render_template("auth/user_setup.html")
