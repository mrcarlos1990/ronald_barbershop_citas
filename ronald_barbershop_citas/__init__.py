from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, session
from sqlalchemy import inspect, text

from .config import Config
from .models import AdminUser, db
from .seed import seed_database
from .utils import (
    STATUS_LABELS,
    build_whatsapp_target,
    format_currency,
    format_date,
    format_datetime,
    format_time,
    get_business_settings,
)


def ensure_schema() -> None:
    inspector = inspect(db.engine)
    if "barberos" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("barberos")}
    statements = []

    if "telefono" not in columns:
        statements.append("ALTER TABLE barberos ADD COLUMN telefono VARCHAR(30)")
    if "foto" not in columns:
        statements.append("ALTER TABLE barberos ADD COLUMN foto VARCHAR(255)")

    if not statements:
        return

    for statement in statements:
        db.session.execute(text(statement))
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

    from .admin_routes import admin_bp
    from .routes import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    app.jinja_env.filters["currency"] = format_currency
    app.jinja_env.filters["display_time"] = format_time
    app.jinja_env.filters["display_date"] = format_date
    app.jinja_env.filters["display_datetime"] = format_datetime

    @app.context_processor
    def inject_globals():
        admin_user = None
        admin_user_id = session.get("admin_user_id")
        if admin_user_id:
            admin_user = db.session.get(AdminUser, admin_user_id)
        settings = get_business_settings()

        return {
            "global_settings": settings,
            "current_admin": admin_user,
            "status_labels": STATUS_LABELS,
            "whatsapp_target": build_whatsapp_target(settings.telefono_whatsapp),
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
        seed_database()

    return app
