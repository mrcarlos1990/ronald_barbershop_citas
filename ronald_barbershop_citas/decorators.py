from functools import wraps

from flask import flash, redirect, request, session, url_for


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_user_id"):
            flash("Inicia sesión para acceder al panel administrativo.", "warning")
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view
