from __future__ import annotations

from datetime import date

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for

from .decorators import admin_required
from .models import (
    AppearanceSettings,
    Barber,
    HaircutStyle,
    LocationSettings,
    Promotion,
    Service,
    SocialLink,
    Testimonial,
    db,
)
from .uploads import UploadValidationError, delete_uploaded_file, save_image_upload
from .utils import (
    CURRENCY_PRESETS,
    LANGUAGE_LABELS,
    active_promotions_query,
    build_reusable_whatsapp_link,
    get_appearance_settings,
    get_business_settings,
    get_current_tenant_id,
    get_location_settings,
    get_social_links,
    get_tenant,
    is_valid_email,
    is_valid_phone,
    normalize_phone,
    parse_date,
    parse_time,
)


business_bp = Blueprint("business", __name__)
THEME_OPTIONS = ("premium_dark", "urban_gold", "street_modern", "classic_barber", "luxury_modern")
APPEARANCE_PRESETS = ("Barberia urbana", "Barberia premium", "Barberia clasica", "Barberia moderna minimalista")
BUTTON_STYLE_OPTIONS = ("pill_glow", "solid", "outline", "sharp")
CARD_STYLE_OPTIONS = ("glass", "solid_dark", "editorial", "minimal")
BORDER_STYLE_OPTIONS = ("straight", "soft", "rounded")
HEADER_STYLE_OPTIONS = ("floating", "solid", "transparent")
FOOTER_STYLE_OPTIONS = ("premium", "minimal", "editorial")


def _tenant_id() -> int:
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        abort(404)
    return tenant_id


def _color_or_default(value: str | None, default: str) -> str:
    color = (value or "").strip()
    if color and len(color) in {4, 7} and color.startswith("#"):
        return color
    return default


@business_bp.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def settings():
    tenant_id = _tenant_id()
    settings_record = get_business_settings(tenant_id=tenant_id)
    appearance_record = get_appearance_settings(tenant_id=tenant_id)
    location_record = get_location_settings(tenant_id=tenant_id)
    social_map = {link.platform.lower(): link for link in SocialLink.query.filter_by(tenant_id=tenant_id).all()}

    if request.method == "POST":
        business_name = (request.form.get("business_name") or "").strip()
        slogan = (request.form.get("slogan") or "").strip()
        description = (request.form.get("description") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        whatsapp = (request.form.get("whatsapp") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        address = (request.form.get("address") or "").strip()
        reference = (request.form.get("location_reference") or "").strip()
        city = (request.form.get("city") or "").strip()
        province_state = (request.form.get("province_state") or "").strip()
        country = (request.form.get("country") or "").strip()
        google_maps_url = (request.form.get("google_maps_url") or "").strip()
        working_days = (request.form.get("working_days") or "").strip()
        default_language = (request.form.get("default_language") or "es").strip().lower()
        currency_code = (request.form.get("currency_code") or "USD").strip().upper()
        currency_symbol = (request.form.get("currency_symbol") or "").strip()
        opening_time = parse_time(request.form.get("hora_apertura"))
        closing_time = parse_time(request.form.get("hora_cierre"))
        interval = request.form.get("intervalo_minutos", type=int) or 30
        primary_color = _color_or_default(request.form.get("primary_color"), "#d2b271")
        secondary_color = _color_or_default(request.form.get("secondary_color"), "#7f1f1f")
        accent_color = _color_or_default(request.form.get("accent_color"), "#0ea5e9")
        button_color = _color_or_default(request.form.get("button_color"), "#d2b271")
        highlight_color = _color_or_default(request.form.get("highlight_color"), "#f6c36d")
        welcome_message = (request.form.get("mensaje_bienvenida") or "").strip()
        visual_theme = (request.form.get("visual_theme") or "urban_gold").strip()
        hero_badge_text = (request.form.get("hero_badge_text") or "").strip()
        hero_title = (request.form.get("hero_title") or "").strip()
        hero_description = (request.form.get("hero_description") or "").strip()
        services_title = (request.form.get("services_title") or "").strip()
        services_description = (request.form.get("services_description") or "").strip()
        styles_title = (request.form.get("styles_title") or "").strip()
        styles_description = (request.form.get("styles_description") or "").strip()
        promotions_title = (request.form.get("promotions_title") or "").strip()
        promotions_description = (request.form.get("promotions_description") or "").strip()
        location_title = (request.form.get("location_title") or "").strip()
        location_description = (request.form.get("location_description") or "").strip()
        testimonials_title = (request.form.get("testimonials_title") or "").strip()
        testimonials_description = (request.form.get("testimonials_description") or "").strip()
        final_cta_title = (request.form.get("final_cta_title") or "").strip()
        final_cta_description = (request.form.get("final_cta_description") or "").strip()

        errors = []
        if not business_name:
            errors.append("El nombre del negocio es obligatorio.")
        if not slogan:
            errors.append("El slogan es obligatorio.")
        if phone and not is_valid_phone(phone):
            errors.append("Ingresa un telefono valido.")
        if not is_valid_phone(whatsapp):
            errors.append("Ingresa un WhatsApp valido.")
        if email and not is_valid_email(email):
            errors.append("Ingresa un correo valido.")
        if not opening_time or not closing_time or opening_time >= closing_time:
            errors.append("Define un horario de apertura y cierre valido.")
        if interval not in {15, 20, 30, 45, 60}:
            errors.append("El intervalo debe ser 15, 20, 30, 45 o 60 minutos.")
        if visual_theme not in THEME_OPTIONS:
            errors.append("Selecciona un tema visual valido.")
        if default_language not in LANGUAGE_LABELS:
            errors.append("Selecciona un idioma por defecto valido.")
        if currency_code not in CURRENCY_PRESETS:
            errors.append("Selecciona una moneda valida.")
        if not currency_symbol:
            currency_symbol = CURRENCY_PRESETS.get(currency_code, CURRENCY_PRESETS["USD"])["symbol"]

        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            try:
                logo_path = save_image_upload(
                    request.files.get("logo_file"),
                    tenant_id=tenant_id,
                    category="branding",
                    current_path=settings_record.logo_path,
                )
                secondary_logo_path = save_image_upload(
                    request.files.get("secondary_logo_file"),
                    tenant_id=tenant_id,
                    category="branding",
                    current_path=settings_record.secondary_logo_path,
                )
                banner_path = save_image_upload(
                    request.files.get("banner_file"),
                    tenant_id=tenant_id,
                    category="branding",
                    current_path=settings_record.banner_path,
                )
                cover_path = save_image_upload(
                    request.files.get("cover_file"),
                    tenant_id=tenant_id,
                    category="branding",
                    current_path=settings_record.cover_path,
                )
                featured_image_path = save_image_upload(
                    request.files.get("featured_image_file"),
                    tenant_id=tenant_id,
                    category="branding",
                    current_path=settings_record.featured_image_path,
                )
                login_image_path = save_image_upload(
                    request.files.get("login_image_file"),
                    tenant_id=tenant_id,
                    category="branding",
                    current_path=settings_record.login_image_path,
                )
                background_image_path = save_image_upload(
                    request.files.get("background_image_file"),
                    tenant_id=tenant_id,
                    category="branding",
                    current_path=settings_record.background_image_path,
                )
            except UploadValidationError as error:
                flash(str(error), "danger")
                return redirect(url_for("business.settings"))

            settings_record.business_name = business_name
            settings_record.slogan = slogan
            settings_record.description = description or None
            settings_record.phone = normalize_phone(phone) if phone else None
            settings_record.whatsapp = normalize_phone(whatsapp)
            settings_record.email = email or None
            settings_record.address = address
            settings_record.location_reference = reference or None
            settings_record.city = city or None
            settings_record.province_state = province_state or None
            settings_record.country = country or None
            settings_record.google_maps_url = google_maps_url or None
            if "logo_url" in request.form:
                settings_record.logo_url = (request.form.get("logo_url") or "").strip() or None
            if "secondary_logo_url" in request.form:
                settings_record.secondary_logo_url = (request.form.get("secondary_logo_url") or "").strip() or None
            if "banner_url" in request.form:
                settings_record.banner_url = (request.form.get("banner_url") or "").strip() or None
            if "cover_url" in request.form:
                settings_record.cover_url = (request.form.get("cover_url") or "").strip() or None
            if "featured_image_url" in request.form:
                settings_record.featured_image_url = (request.form.get("featured_image_url") or "").strip() or None
            if "login_image_url" in request.form:
                settings_record.login_image_url = (request.form.get("login_image_url") or "").strip() or None
            if "background_image_url" in request.form:
                settings_record.background_image_url = (request.form.get("background_image_url") or "").strip() or None
            settings_record.logo_path = logo_path
            settings_record.secondary_logo_path = secondary_logo_path
            settings_record.banner_path = banner_path
            settings_record.cover_path = cover_path
            settings_record.featured_image_path = featured_image_path
            settings_record.login_image_path = login_image_path
            settings_record.background_image_path = background_image_path
            settings_record.primary_color = primary_color
            settings_record.secondary_color = secondary_color
            settings_record.accent_color = accent_color
            settings_record.button_color = button_color
            settings_record.highlight_color = highlight_color
            settings_record.visual_theme = visual_theme
            settings_record.default_language = default_language
            settings_record.currency_code = currency_code
            settings_record.currency_symbol = currency_symbol
            settings_record.working_days = working_days or "Lunes a Sabado"
            settings_record.hora_apertura = opening_time
            settings_record.hora_cierre = closing_time
            settings_record.intervalo_minutos = interval
            settings_record.mensaje_bienvenida = welcome_message or settings_record.mensaje_bienvenida
            settings_record.hero_badge_text = hero_badge_text or None
            settings_record.hero_title = hero_title or None
            settings_record.hero_description = hero_description or None
            settings_record.services_title = services_title or None
            settings_record.services_description = services_description or None
            settings_record.styles_title = styles_title or None
            settings_record.styles_description = styles_description or None
            settings_record.promotions_title = promotions_title or None
            settings_record.promotions_description = promotions_description or None
            settings_record.location_title = location_title or None
            settings_record.location_description = location_description or None
            settings_record.testimonials_title = testimonials_title or None
            settings_record.testimonials_description = testimonials_description or None
            settings_record.final_cta_title = final_cta_title or None
            settings_record.final_cta_description = final_cta_description or None
            settings_record.show_map = request.form.get("show_map") == "on"
            settings_record.show_gallery_styles = request.form.get("show_gallery_styles") == "on"
            settings_record.show_promotions = request.form.get("show_promotions") == "on"
            settings_record.show_testimonials = request.form.get("show_testimonials") == "on"
            settings_record.show_banner = request.form.get("show_banner") == "on"
            settings_record.show_how_to_get = request.form.get("show_how_to_get") == "on"
            settings_record.show_language_selector = request.form.get("show_language_selector") == "on"

            appearance_record.featured_image_url = settings_record.featured_image_url
            appearance_record.visual_style = visual_theme
            appearance_record.theme_name = request.form.get("theme_name") or appearance_record.theme_name
            appearance_record.show_services = request.form.get("show_services") == "on"
            appearance_record.show_barbers = request.form.get("show_barbers") == "on"
            appearance_record.show_gallery_styles = settings_record.show_gallery_styles
            appearance_record.show_promotions = settings_record.show_promotions
            appearance_record.show_testimonials = settings_record.show_testimonials

            location_record.address = address
            location_record.reference = reference or None
            location_record.google_maps_url = google_maps_url or None
            location_record.show_map = settings_record.show_map

            for platform in ("instagram", "facebook", "tiktok"):
                url_value = (request.form.get(f"{platform}_url") or "").strip()
                existing = social_map.get(platform)
                if url_value:
                    if existing is None:
                        existing = SocialLink(
                            tenant_id=tenant_id,
                            platform=platform.capitalize(),
                            label=platform.capitalize(),
                            url=url_value,
                            active=True,
                        )
                        db.session.add(existing)
                    else:
                        existing.url = url_value
                        existing.active = True
                elif existing is not None:
                    existing.active = False

            db.session.commit()
            flash("Ajustes del negocio actualizados correctamente.", "success")
            return redirect(url_for("business.settings"))

    return render_template(
        "admin/settings.html",
        settings_record=settings_record,
        appearance_record=appearance_record,
        location_record=location_record,
        social_map=social_map,
        theme_options=THEME_OPTIONS,
        language_options=LANGUAGE_LABELS,
        currency_options=CURRENCY_PRESETS,
    )


@business_bp.route("/admin/appearance", methods=["GET", "POST"])
@admin_required
def appearance():
    tenant_id = _tenant_id()
    settings_record = get_business_settings(tenant_id=tenant_id)
    appearance_record = get_appearance_settings(tenant_id=tenant_id)

    if request.method == "POST":
        visual_theme = (request.form.get("visual_theme") or "urban_gold").strip()
        theme_name = (request.form.get("theme_name") or "Barberia urbana").strip()
        button_style = (request.form.get("button_style") or "pill_glow").strip()
        card_style = (request.form.get("card_style") or "glass").strip()
        border_style = (request.form.get("border_style") or "rounded").strip()
        header_style = (request.form.get("header_style") or "floating").strip()
        footer_style = (request.form.get("footer_style") or "premium").strip()

        errors = []
        if visual_theme not in THEME_OPTIONS:
            errors.append("Selecciona un tema visual valido.")
        if theme_name not in APPEARANCE_PRESETS:
            errors.append("Selecciona una identidad visual valida.")
        if button_style not in BUTTON_STYLE_OPTIONS:
            errors.append("Selecciona un estilo de botones valido.")
        if card_style not in CARD_STYLE_OPTIONS:
            errors.append("Selecciona un estilo de tarjetas valido.")
        if border_style not in BORDER_STYLE_OPTIONS:
            errors.append("Selecciona una forma de bordes valida.")
        if header_style not in HEADER_STYLE_OPTIONS:
            errors.append("Selecciona un estilo de header valido.")
        if footer_style not in FOOTER_STYLE_OPTIONS:
            errors.append("Selecciona un estilo de footer valido.")

        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            try:
                featured_image_path = save_image_upload(
                    request.files.get("featured_image_file"),
                    tenant_id=tenant_id,
                    category="branding",
                    current_path=settings_record.featured_image_path,
                )
                background_image_path = save_image_upload(
                    request.files.get("background_image_file"),
                    tenant_id=tenant_id,
                    category="branding",
                    current_path=settings_record.background_image_path,
                )
            except UploadValidationError as error:
                flash(str(error), "danger")
                return redirect(url_for("business.appearance"))

            settings_record.visual_theme = visual_theme
            settings_record.primary_color = _color_or_default(request.form.get("primary_color"), settings_record.primary_color)
            settings_record.secondary_color = _color_or_default(request.form.get("secondary_color"), settings_record.secondary_color)
            settings_record.accent_color = _color_or_default(request.form.get("accent_color"), settings_record.accent_color)
            settings_record.button_color = _color_or_default(request.form.get("button_color"), settings_record.button_color)
            settings_record.highlight_color = _color_or_default(request.form.get("highlight_color"), settings_record.highlight_color)
            settings_record.featured_image_path = featured_image_path
            settings_record.background_image_path = background_image_path

            if "featured_image_url" in request.form:
                settings_record.featured_image_url = (request.form.get("featured_image_url") or "").strip() or None
            if "background_image_url" in request.form:
                settings_record.background_image_url = (request.form.get("background_image_url") or "").strip() or None

            appearance_record.visual_style = visual_theme
            appearance_record.theme_name = theme_name
            appearance_record.button_style = button_style
            appearance_record.card_style = card_style
            appearance_record.border_style = border_style
            appearance_record.header_style = header_style
            appearance_record.footer_style = footer_style
            appearance_record.enable_animations = request.form.get("enable_animations") == "on"
            appearance_record.urban_mode = request.form.get("urban_mode") == "on"
            appearance_record.dark_mode = request.form.get("dark_mode") == "on"
            appearance_record.show_services = request.form.get("show_services") == "on"
            appearance_record.show_barbers = request.form.get("show_barbers") == "on"
            appearance_record.show_gallery_styles = request.form.get("show_gallery_styles") == "on"
            appearance_record.show_promotions = request.form.get("show_promotions") == "on"
            appearance_record.show_testimonials = request.form.get("show_testimonials") == "on"
            appearance_record.featured_image_url = settings_record.featured_image_url

            settings_record.show_gallery_styles = appearance_record.show_gallery_styles
            settings_record.show_promotions = appearance_record.show_promotions
            settings_record.show_testimonials = appearance_record.show_testimonials

            db.session.commit()
            flash("Apariencia actualizada correctamente.", "success")
            return redirect(url_for("business.appearance"))

    return render_template(
        "admin/appearance.html",
        settings_record=settings_record,
        appearance_record=appearance_record,
        theme_options=THEME_OPTIONS,
        appearance_presets=APPEARANCE_PRESETS,
        button_style_options=BUTTON_STYLE_OPTIONS,
        card_style_options=CARD_STYLE_OPTIONS,
        border_style_options=BORDER_STYLE_OPTIONS,
        header_style_options=HEADER_STYLE_OPTIONS,
        footer_style_options=FOOTER_STYLE_OPTIONS,
    )


@business_bp.route("/admin/location", methods=["GET", "POST"])
@admin_required
def location():
    tenant_id = _tenant_id()
    location_record = get_location_settings(tenant_id=tenant_id)
    settings_record = get_business_settings(tenant_id=tenant_id)

    if request.method == "POST":
        address = (request.form.get("address") or "").strip()
        reference = (request.form.get("reference") or "").strip()
        latitude = (request.form.get("latitude") or "").strip()
        longitude = (request.form.get("longitude") or "").strip()
        google_maps_url = (request.form.get("google_maps_url") or "").strip()

        if not address:
            flash("La direccion es obligatoria.", "danger")
        else:
            location_record.address = address
            location_record.reference = reference or None
            location_record.latitude = latitude or None
            location_record.longitude = longitude or None
            location_record.google_maps_url = google_maps_url or None
            location_record.show_map = request.form.get("show_map") == "on"
            settings_record.address = address
            settings_record.location_reference = reference or None
            settings_record.google_maps_url = google_maps_url or None
            settings_record.show_map = location_record.show_map
            db.session.commit()
            flash("Ubicacion actualizada correctamente.", "success")
            return redirect(url_for("business.location"))

    return render_template("admin/location.html", location_record=location_record, settings_record=settings_record)


@business_bp.route("/admin/styles", methods=["GET", "POST"])
@admin_required
def styles():
    tenant_id = _tenant_id()
    services = Service.query.filter_by(tenant_id=tenant_id).order_by(Service.nombre.asc()).all()

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        description = (request.form.get("description") or "").strip()
        trending = request.form.get("trending") == "on"
        suggested_price = request.form.get("suggested_price", type=float)
        service_id = request.form.get("service_id", type=int)
        active = request.form.get("active") == "on"
        service = Service.query.filter_by(id=service_id or 0, tenant_id=tenant_id).first() if service_id else None

        if not name:
            flash("El nombre del estilo es obligatorio.", "danger")
        elif service_id and service is None:
            flash("Selecciona un servicio valido para este tenant.", "danger")
        else:
            try:
                image_path = save_image_upload(
                    request.files.get("image_file"),
                    tenant_id=tenant_id,
                    category="styles",
                )
            except UploadValidationError as error:
                flash(str(error), "danger")
                return redirect(url_for("business.styles"))

            style = HaircutStyle(
                tenant_id=tenant_id,
                service_id=service.id if service else None,
                name=name,
                description=description or None,
                image_url=(request.form.get("image_url") or "").strip() or None,
                image_path=image_path,
                trending=trending,
                suggested_price=suggested_price,
                active=active,
            )
            db.session.add(style)
            db.session.commit()
            flash("Estilo de corte creado correctamente.", "success")
            return redirect(url_for("business.styles"))

    style_list = (
        HaircutStyle.query.filter_by(tenant_id=tenant_id)
        .order_by(HaircutStyle.trending.desc(), HaircutStyle.fecha_creacion.desc())
        .all()
    )
    return render_template("admin/styles.html", style_list=style_list, services=services)


@business_bp.route("/admin/styles/<int:style_id>", methods=["POST", "PUT", "DELETE"])
@admin_required
def style_detail(style_id: int):
    tenant_id = _tenant_id()
    style = HaircutStyle.query.filter_by(id=style_id, tenant_id=tenant_id).first()
    if style is None:
        abort(404)

    method = request.method
    intent = (request.form.get("_intent") or "").lower()
    if method == "POST" and intent == "delete":
        method = "DELETE"
    elif method == "POST":
        method = "PUT"

    if method == "DELETE":
        delete_uploaded_file(style.image_path)
        db.session.delete(style)
        db.session.commit()
        if request.method == "POST":
            flash("Estilo eliminado correctamente.", "success")
            return redirect(url_for("business.styles"))
        return jsonify({"ok": True})

    payload = request.get_json(silent=True) if request.method == "PUT" else request.form
    name = (payload.get("name") or "").strip()
    description = (payload.get("description") or "").strip()
    service_id = int(payload.get("service_id") or 0) or None
    service = Service.query.filter_by(id=service_id or 0, tenant_id=tenant_id).first() if service_id else None
    suggested_price = None
    if payload.get("suggested_price"):
        try:
            suggested_price = float(payload.get("suggested_price"))
        except (TypeError, ValueError):
            suggested_price = None

    if not name:
        if request.method == "POST":
            flash("El nombre del estilo es obligatorio.", "danger")
            return redirect(url_for("business.styles"))
        return jsonify({"ok": False, "message": "El nombre es obligatorio."}), 400
    if service_id and service is None:
        if request.method == "POST":
            flash("Selecciona un servicio valido para este tenant.", "danger")
            return redirect(url_for("business.styles"))
        return jsonify({"ok": False, "message": "Servicio invalido."}), 400

    image_path = style.image_path
    if request.method == "POST":
        try:
            image_path = save_image_upload(
                request.files.get("image_file"),
                tenant_id=tenant_id,
                category="styles",
                current_path=style.image_path,
            )
        except UploadValidationError as error:
            flash(str(error), "danger")
            return redirect(url_for("business.styles"))

    style.name = name
    style.description = description or None
    if "image_url" in payload:
        style.image_url = (payload.get("image_url") or "").strip() or None
    style.image_path = image_path
    style.service_id = service.id if service else None
    style.trending = payload.get("trending") in {"on", True, "true", "1"}
    style.active = payload.get("active") in {"on", True, "true", "1"}
    style.suggested_price = suggested_price
    db.session.commit()

    if request.method == "POST":
        flash("Estilo actualizado correctamente.", "success")
        return redirect(url_for("business.styles"))
    return jsonify({"ok": True})


@business_bp.route("/admin/promotions", methods=["GET", "POST"])
@admin_required
def promotions():
    tenant_id = _tenant_id()

    if request.method == "POST":
        action = (request.form.get("_action") or "create").lower()
        promotion_id = request.form.get("promotion_id", type=int)

        if action == "delete" and promotion_id:
            promotion = Promotion.query.filter_by(id=promotion_id, tenant_id=tenant_id).first()
            if promotion is not None:
                delete_uploaded_file(promotion.image_path)
                db.session.delete(promotion)
                db.session.commit()
                flash("Promocion eliminada correctamente.", "success")
            return redirect(url_for("business.promotions"))

        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        discount_percentage = request.form.get("discount_percentage", type=float)
        special_price = request.form.get("special_price", type=float)
        start_date = parse_date(request.form.get("start_date"))
        end_date = parse_date(request.form.get("end_date"))
        active = request.form.get("active") == "on"

        errors = []
        if not title:
            errors.append("El titulo de la promocion es obligatorio.")
        if discount_percentage is None or discount_percentage < 0:
            errors.append("Ingresa un porcentaje de descuento valido.")
        if not start_date or not end_date or end_date < start_date:
            errors.append("Define un rango de fechas valido.")

        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            try:
                image_path = save_image_upload(
                    request.files.get("image_file"),
                    tenant_id=tenant_id,
                    category="promotions",
                )
            except UploadValidationError as error:
                flash(str(error), "danger")
                return redirect(url_for("business.promotions"))

            promotion = Promotion(
                tenant_id=tenant_id,
                title=title,
                description=description or None,
                discount_percentage=discount_percentage,
                special_price=special_price,
                start_date=start_date,
                end_date=end_date,
                image_url=(request.form.get("image_url") or "").strip() or None,
                image_path=image_path,
                active=active,
            )
            db.session.add(promotion)
            db.session.commit()
            flash("Promocion creada correctamente.", "success")
            return redirect(url_for("business.promotions"))

    promotion_list = (
        Promotion.query.filter_by(tenant_id=tenant_id)
        .order_by(Promotion.start_date.desc(), Promotion.fecha_creacion.desc())
        .all()
    )
    return render_template("admin/promotions.html", promotion_list=promotion_list, today=date.today())


@business_bp.route("/admin/subscription")
@admin_required
def subscription():
    tenant = get_tenant(tenant_id=_tenant_id())
    return render_template("admin/subscription.html", tenant=tenant)


@business_bp.route("/<tenant_slug>")
def public_business(tenant_slug: str):
    if tenant_slug.lower() in {"admin", "cliente"}:
        abort(404)

    tenant = get_tenant(tenant_slug=tenant_slug, create_default=False)
    if tenant is None or not tenant.active:
        abort(404)

    settings = get_business_settings(tenant_id=tenant.id)
    appearance = get_appearance_settings(tenant_id=tenant.id)
    location = get_location_settings(tenant_id=tenant.id)
    services = Service.query.filter_by(tenant_id=tenant.id, activo=True).order_by(Service.nombre.asc()).all()
    barbers = Barber.query.filter_by(tenant_id=tenant.id, activo=True).order_by(Barber.nombre.asc()).all()
    styles = (
        HaircutStyle.query.filter_by(tenant_id=tenant.id, active=True)
        .order_by(HaircutStyle.trending.desc(), HaircutStyle.fecha_creacion.desc())
        .all()
    )
    promotions = active_promotions_query(tenant_id=tenant.id).order_by(Promotion.end_date.asc()).all()
    testimonials = Testimonial.query.filter_by(tenant_id=tenant.id, visible=True).order_by(Testimonial.fecha_creacion.desc()).all()
    social_links = get_social_links(tenant_id=tenant.id)
    booking_url = request.url_root.rstrip("/") + url_for("main.booking_form")
    whatsapp_link = build_reusable_whatsapp_link(settings, booking_url=booking_url)

    return render_template(
        "public/landing.html",
        tenant=tenant,
        settings=settings,
        appearance=appearance,
        location=location,
        services=services,
        barbers=barbers,
        styles=styles,
        promotions=promotions,
        testimonials=testimonials,
        social_links=social_links,
        booking_url=booking_url,
        whatsapp_link=whatsapp_link,
    )
