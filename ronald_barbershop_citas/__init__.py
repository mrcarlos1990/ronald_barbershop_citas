from datetime import datetime
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_login import LoginManager, current_user
from sqlalchemy import inspect, text

from .config import Config
from .models import AdminUser, Client, db
from .uploads import build_media_url
from .seed import seed_database
from .utils import (
    LANGUAGE_LABELS,
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
    get_language_code,
    get_location_settings,
    get_social_links,
    get_tenant,
    translate,
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

    if "business_settings" in table_names:
        business_columns = {column["name"] for column in inspector.get_columns("business_settings")}
        if "description" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN description TEXT")
        if "secondary_logo_url" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN secondary_logo_url VARCHAR(255)")
        if "cover_url" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN cover_url VARCHAR(255)")
        if "featured_image_url" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN featured_image_url VARCHAR(255)")
        if "login_image_url" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN login_image_url VARCHAR(255)")
        if "background_image_url" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN background_image_url VARCHAR(255)")
        if "logo_path" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN logo_path VARCHAR(255)")
        if "secondary_logo_path" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN secondary_logo_path VARCHAR(255)")
        if "banner_path" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN banner_path VARCHAR(255)")
        if "cover_path" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN cover_path VARCHAR(255)")
        if "featured_image_path" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN featured_image_path VARCHAR(255)")
        if "login_image_path" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN login_image_path VARCHAR(255)")
        if "background_image_path" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN background_image_path VARCHAR(255)")
        if "accent_color" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN accent_color VARCHAR(20) DEFAULT '#0ea5e9'")
        if "button_color" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN button_color VARCHAR(20) DEFAULT '#d2b271'")
        if "highlight_color" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN highlight_color VARCHAR(20) DEFAULT '#f6c36d'")
        if "visual_theme" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN visual_theme VARCHAR(80) DEFAULT 'urban_gold'")
        if "default_language" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN default_language VARCHAR(10) DEFAULT 'es'")
        if "currency_code" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN currency_code VARCHAR(10) DEFAULT 'USD'")
        if "currency_symbol" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN currency_symbol VARCHAR(10) DEFAULT '$'")
        if "hero_badge_text" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN hero_badge_text VARCHAR(180)")
        if "hero_title" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN hero_title VARCHAR(220)")
        if "hero_description" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN hero_description TEXT")
        if "services_title" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN services_title VARCHAR(220)")
        if "services_description" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN services_description TEXT")
        if "styles_title" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN styles_title VARCHAR(220)")
        if "styles_description" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN styles_description TEXT")
        if "promotions_title" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN promotions_title VARCHAR(220)")
        if "promotions_description" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN promotions_description TEXT")
        if "location_title" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN location_title VARCHAR(220)")
        if "location_description" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN location_description TEXT")
        if "testimonials_title" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN testimonials_title VARCHAR(220)")
        if "testimonials_description" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN testimonials_description TEXT")
        if "final_cta_title" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN final_cta_title VARCHAR(220)")
        if "final_cta_description" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN final_cta_description TEXT")
        if "show_language_selector" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN show_language_selector BOOLEAN DEFAULT 1")
        if "show_banner" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN show_banner BOOLEAN DEFAULT 1")
        if "show_how_to_get" not in business_columns:
            statements.append("ALTER TABLE business_settings ADD COLUMN show_how_to_get BOOLEAN DEFAULT 1")

    if "appearance_settings" in table_names:
        appearance_columns = {column["name"] for column in inspector.get_columns("appearance_settings")}
        if "theme_name" not in appearance_columns:
            statements.append("ALTER TABLE appearance_settings ADD COLUMN theme_name VARCHAR(80) DEFAULT 'Barberia urbana'")
        if "button_style" not in appearance_columns:
            statements.append("ALTER TABLE appearance_settings ADD COLUMN button_style VARCHAR(80) DEFAULT 'pill_glow'")
        if "card_style" not in appearance_columns:
            statements.append("ALTER TABLE appearance_settings ADD COLUMN card_style VARCHAR(80) DEFAULT 'glass'")
        if "border_style" not in appearance_columns:
            statements.append("ALTER TABLE appearance_settings ADD COLUMN border_style VARCHAR(80) DEFAULT 'rounded'")
        if "header_style" not in appearance_columns:
            statements.append("ALTER TABLE appearance_settings ADD COLUMN header_style VARCHAR(80) DEFAULT 'floating'")
        if "footer_style" not in appearance_columns:
            statements.append("ALTER TABLE appearance_settings ADD COLUMN footer_style VARCHAR(80) DEFAULT 'premium'")
        if "enable_animations" not in appearance_columns:
            statements.append("ALTER TABLE appearance_settings ADD COLUMN enable_animations BOOLEAN DEFAULT 1")
        if "urban_mode" not in appearance_columns:
            statements.append("ALTER TABLE appearance_settings ADD COLUMN urban_mode BOOLEAN DEFAULT 1")
        if "dark_mode" not in appearance_columns:
            statements.append("ALTER TABLE appearance_settings ADD COLUMN dark_mode BOOLEAN DEFAULT 1")

    if "haircut_styles" in table_names:
        styles_columns = {column["name"] for column in inspector.get_columns("haircut_styles")}
        if "image_path" not in styles_columns:
            statements.append("ALTER TABLE haircut_styles ADD COLUMN image_path VARCHAR(255)")

    if "promotions" in table_names:
        promotion_columns = {column["name"] for column in inspector.get_columns("promotions")}
        if "image_path" not in promotion_columns:
            statements.append("ALTER TABLE promotions ADD COLUMN image_path VARCHAR(255)")
        if "special_price" not in promotion_columns:
            statements.append("ALTER TABLE promotions ADD COLUMN special_price FLOAT")

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
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

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
    app.jinja_env.globals["media_url"] = build_media_url

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
            "current_language": get_language_code(tenant_id=tenant_id),
            "available_languages": LANGUAGE_LABELS,
            "t": translate,
        }

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("500.html"), 500

    @app.errorhandler(413)
    def file_too_large(error):
        flash("La imagen supera el tamano permitido. Usa archivos de hasta 5 MB.", "danger")
        return redirect(request.referrer or url_for("business.settings"))

    with app.app_context():
        db.create_all()
        ensure_schema()
        db.create_all()
        seed_database()

    return app
