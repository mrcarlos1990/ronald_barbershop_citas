from functools import wraps

from flask import flash, redirect, request, session, url_for
from flask_login import current_user, login_required, logout_user


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_user_id"):
            flash("Inicia sesion para acceder al panel administrativo.", "warning")
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def client_required(view):
    @login_required
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not getattr(current_user, "activo", False):
            logout_user()
            flash("Tu cuenta de cliente no esta activa. Contacta a la barberia.", "warning")
            return redirect(url_for("client.login"))
        return view(*args, **kwargs)

    return wrapped_view
