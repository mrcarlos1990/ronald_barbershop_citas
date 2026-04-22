from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, session
from flask_login import LoginManager, current_user
from sqlalchemy import inspect, text

from .config import Config
from .models import AdminUser, Client, db
from .seed import seed_database
from .utils import (
    STATUS_LABELS,
    build_whatsapp_target,
    format_currency,
    format_date,
    format_datetime,
    format_time,
    get_admin_from_session,
    get_appearance_settings,
    get_business_settings,
    get_current_tenant_id,
    get_location_settings,
    get_social_links,
    get_tenant,
)


login_manager = LoginManager()
login_manager.login_view = "client.login"
login_manager.login_message = "Debes iniciar sesion como cliente para continuar."
login_manager.login_message_category = "warning"


def ensure_schema() -> None:
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()
    statements: list[str] = []

    if "usuarios_admin" in table_names:
        admin_columns = {column["name"] for column in inspector.get_columns("usuarios_admin")}
        if "tenant_id" not in admin_columns:
            statements.append("ALTER TABLE usuarios_admin ADD COLUMN tenant_id INTEGER")

    if "clientes" in table_names:
        client_columns = {column["name"] for column in inspector.get_columns("clientes")}
        if "username" not in client_columns:
            statements.append("ALTER TABLE clientes ADD COLUMN username VARCHAR(80)")
        if "email" not in client_columns:
            statements.append("ALTER TABLE clientes ADD COLUMN email VARCHAR(120)")
        if "password_hash" not in client_columns:
            statements.append("ALTER TABLE clientes ADD COLUMN password_hash VARCHAR(255)")
        if "activo" not in client_columns:
            statements.append("ALTER TABLE clientes ADD COLUMN activo BOOLEAN DEFAULT 1")
        if "tenant_id" not in client_columns:
            statements.append("ALTER TABLE clientes ADD COLUMN tenant_id INTEGER")

    if "servicios" in table_names:
        service_columns = {column["name"] for column in inspector.get_columns("servicios")}
        if "tenant_id" not in service_columns:
            statements.append("ALTER TABLE servicios ADD COLUMN tenant_id INTEGER")
        if "image_url" not in service_columns:
            statements.append("ALTER TABLE servicios ADD COLUMN image_url VARCHAR(255)")
        if "categoria" not in service_columns:
            statements.append("ALTER TABLE servicios ADD COLUMN categoria VARCHAR(80)")

    if "barberos" in table_names:
        barber_columns = {column["name"] for column in inspector.get_columns("barberos")}
        if "telefono" not in barber_columns:
            statements.append("ALTER TABLE barberos ADD COLUMN telefono VARCHAR(30)")
        if "foto" not in barber_columns:
            statements.append("ALTER TABLE barberos ADD COLUMN foto VARCHAR(255)")
        if "tenant_id" not in barber_columns:
            statements.append("ALTER TABLE barberos ADD COLUMN tenant_id INTEGER")

    if "citas" in table_names:
        appointment_columns = {column["name"] for column in inspector.get_columns("citas")}
        if "tenant_id" not in appointment_columns:
            statements.append("ALTER TABLE citas ADD COLUMN tenant_id INTEGER")

    if "horarios_bloqueados" in table_names:
        blocked_columns = {column["name"] for column in inspector.get_columns("horarios_bloqueados")}
        if "tenant_id" not in blocked_columns:
            statements.append("ALTER TABLE horarios_bloqueados ADD COLUMN tenant_id INTEGER")

    for statement in statements:
        db.session.execute(text(statement))
    if statements:
        db.session.commit()


def create_app(config_class=Config) -> Flask:
    app = Flask(
        __name__,
        instance_path=str(config_class.INSTANCE_DIR),
        template_folder=str(config_class.TEMPLATES_DIR),
        static_folder=str(config_class.STATIC_DIR),
    )
    app.config.from_object(config_class)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from .admin_routes import admin_bp
    from .business_routes import business_bp
    from .client_routes import client_bp
    from .routes import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(business_bp)

    app.jinja_env.filters["currency"] = format_currency
    app.jinja_env.filters["display_time"] = format_time
    app.jinja_env.filters["display_date"] = format_date
    app.jinja_env.filters["display_datetime"] = format_datetime

    @login_manager.user_loader
    def load_client_user(user_id: str):
        if not user_id or not str(user_id).isdigit():
            return None
        return db.session.get(Client, int(user_id))

    @app.context_processor
    def inject_globals():
        admin_user = get_admin_from_session()
        tenant_slug = request.view_args.get("tenant_slug") if request.view_args else None
        active_tenant = (
            get_tenant(tenant_slug=tenant_slug, create_default=False)
            if tenant_slug
            else get_tenant(
                tenant_id=session.get("admin_tenant_id") or getattr(current_user, "tenant_id", None) or get_current_tenant_id(),
            )
        )
        tenant_id = active_tenant.id if active_tenant else None
        settings = get_business_settings(tenant_id=tenant_id)
        client_user = current_user if getattr(current_user, "is_authenticated", False) else None

        return {
            "global_settings": settings,
            "current_admin": admin_user,
            "current_client": client_user,
            "current_tenant": active_tenant,
            "current_location": get_location_settings(tenant_id=tenant_id),
            "current_appearance": get_appearance_settings(tenant_id=tenant_id),
            "current_social_links": get_social_links(tenant_id=tenant_id),
            "status_labels": STATUS_LABELS,
            "whatsapp_target": build_whatsapp_target(settings.whatsapp),
            "current_year": datetime.now().year,
        }

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("500.html"), 500

    with app.app_context():
        db.create_all()
        ensure_schema()
        db.create_all()
        seed_database()

    return app
