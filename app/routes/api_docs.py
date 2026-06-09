from flask import Blueprint, current_app, jsonify, redirect, render_template, url_for

api_docs_bp = Blueprint("api_docs", __name__, url_prefix="/api-docs")


@api_docs_bp.get("", endpoint="index")
def index():
    return render_template("api_docs/index.html")


@api_docs_bp.get("/test", endpoint="test_interface")
def test_interface():
    return render_template("api_docs/test.html")


@api_docs_bp.get("/daily-checkin", endpoint="daily_checkin_apis")
def daily_checkin_apis():
    return render_template("api_docs/daily_checkin_apis.html")


@api_docs_bp.get("/exchange-shop", endpoint="exchange_shop_apis")
def exchange_shop_apis():
    return render_template("api_docs/exchange_shop_apis.html")


@api_docs_bp.get("/logout", endpoint="logout")
def logout():
    return redirect(url_for("main.index"))


@api_docs_bp.get("/api/endpoints")
def endpoints():
    data = []
    for rule in current_app.url_map.iter_rules():
        methods = sorted(rule.methods - {"HEAD", "OPTIONS"})
        data.append({
            "endpoint": rule.endpoint,
            "rule": rule.rule,
            "methods": methods,
            "blueprint": rule.endpoint.split(".", 1)[0] if "." in rule.endpoint else "app",
            "description": "",
            "requires_auth": False,
            "is_api": rule.rule.startswith("/api/") or "/api/" in rule.rule,
        })
    return jsonify({"total": len(data), "endpoints": data})
