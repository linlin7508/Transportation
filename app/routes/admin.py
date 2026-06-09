from flask import Blueprint, redirect, render_template, url_for

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("", endpoint="admin_index")
def admin_index():
    return render_template("admin/index.html")


@admin_bp.get("/data-management", endpoint="data_management")
def data_management():
    return render_template(
        "admin/data_management.html",
        expire_hours=24,
        routes_data=[],
        stops_data=[],
        buses_data=[],
    )


@admin_bp.post("/refresh-data", endpoint="refresh_data")
def refresh_data():
    return redirect(url_for("admin.data_management"))
