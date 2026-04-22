from __future__ import annotations

from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from .decorators import client_required
from .models import Appointment, Barber, HaircutStyle, Promotion, Service, Testimonial, db
from .utils import (
    active_promotions_query,
    build_available_slots,
    build_calendar_days,
    build_reusable_whatsapp_link,
    build_whatsapp_confirmation_link,
    get_appearance_settings,
    get_business_settings,
    get_current_tenant_id,
    get_location_settings,
    get_social_links,
    get_tenant,
    parse_date,
    parse_month,
    parse_time,
    select_barber_for_booking,
)


main_bp = Blueprint("main", __name__)


def _tenant_id_for_request() -> int:
    return getattr(current_user, "tenant_id", None) or get_current_tenant_id()


def _booking_context(form_data: dict | None = None):
    tenant_id = _tenant_id_for_request()
    settings = get_business_settings(tenant_id=tenant_id)
    services = Service.query.filter_by(tenant_id=tenant_id, activo=True).order_by(Service.nombre.asc()).all()
    barbers = Barber.query.filter_by(tenant_id=tenant_id, activo=True).order_by(Barber.nombre.asc()).all()
    booking_url = url_for("main.booking_form")
    return {
        "settings": settings,
        "services": services,
        "barbers": barbers,
        "form_data": form_data or {},
        "today_iso": date.today().isoformat(),
        "calendar_initial_month": date.today().strftime("%Y-%m"),
        "landing_whatsapp_link": build_reusable_whatsapp_link(settings, booking_url=request.url_root.rstrip("/") + booking_url),
    }


@main_bp.route("/")
def landing():
    tenant = get_tenant()
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
        "public_business.html",
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


@main_bp.route("/agendar", methods=["GET", "POST"])
@client_required
def booking_form():
    tenant_id = current_user.tenant_id or get_current_tenant_id()

    if request.method == "GET":
        form_data = {
            "servicio_id": request.args.get("servicio_id", ""),
            "barbero_id": request.args.get("barbero_id", ""),
            "fecha": request.args.get("fecha", ""),
            "hora": request.args.get("hora", ""),
            "nota": "",
        }
        return render_template("agendar.html", **_booking_context(form_data))

    form_data = request.form.to_dict()
    service = Service.query.filter_by(id=request.form.get("servicio_id", type=int) or 0, tenant_id=tenant_id).first()
    preferred_barber = Barber.query.filter_by(id=request.form.get("barbero_id", type=int) or 0, tenant_id=tenant_id).first()
    booking_date = parse_date(request.form.get("fecha"))
    booking_time = parse_time(request.form.get("hora"))
    note = (request.form.get("nota") or "").strip()

    errors = []
    if service is None or not service.activo:
        errors.append("Selecciona un servicio valido.")
    if booking_date is None or booking_date < date.today():
        errors.append("Selecciona una fecha valida.")
    if booking_time is None:
        errors.append("Selecciona un horario disponible.")

    assigned_barber = None
    if not errors and service and booking_date and booking_time:
        assigned_barber = select_barber_for_booking(
            booking_date,
            booking_time,
            service.duracion_minutos,
            preferred_barber_id=preferred_barber.id if preferred_barber else None,
            tenant_id=tenant_id,
        )
        if assigned_barber is None:
            errors.append("Ese horario ya no esta disponible o queda fuera del horario laboral.")

    if errors:
        for error in errors:
            flash(error, "danger")
        return render_template("agendar.html", **_booking_context(form_data))

    appointment = Appointment(
        tenant_id=tenant_id,
        cliente_id=current_user.id,
        servicio_id=service.id,
        barbero_id=assigned_barber.id,
        nombre_cliente=current_user.nombre,
        telefono=current_user.telefono,
        fecha=booking_date,
        hora=booking_time,
        duracion_minutos=service.duracion_minutos,
        estado="pendiente",
        nota=note or None,
    )
    db.session.add(appointment)
    db.session.commit()

    flash("Tu cita fue registrada correctamente.", "success")
    return redirect(url_for("main.booking_confirmation", appointment_id=appointment.id))


@main_bp.route("/confirmacion/<int:appointment_id>")
@client_required
def booking_confirmation(appointment_id: int):
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        cliente_id=current_user.id,
        tenant_id=current_user.tenant_id,
    ).first()
    if appointment is None:
        flash("La cita solicitada no existe.", "warning")
        return redirect(url_for("main.booking_form"))

    settings = get_business_settings(tenant_id=appointment.tenant_id)
    booking_url = request.url_root.rstrip("/") + url_for("main.booking_form")
    whatsapp_link = build_whatsapp_confirmation_link(settings, appointment)
    reusable_whatsapp_link = build_reusable_whatsapp_link(settings, booking_url=booking_url)

    return render_template(
        "booking_confirmed.html",
        appointment=appointment,
        whatsapp_link=whatsapp_link,
        reusable_whatsapp_link=reusable_whatsapp_link,
        booking_url=booking_url,
    )


@main_bp.route("/disponibilidad")
def availability():
    tenant_id = getattr(current_user, "tenant_id", None) or get_current_tenant_id()
    service_id = request.args.get("service_id", type=int)
    booking_date = parse_date(request.args.get("date"))
    barber_id = request.args.get("barber_id", type=int)
    exclude_appointment_id = request.args.get("exclude_appointment_id", type=int)

    service = Service.query.filter_by(id=service_id or 0, tenant_id=tenant_id).first()
    if not service or not booking_date or booking_date < date.today():
        return jsonify({"slots": []})

    slots = build_available_slots(
        booking_date,
        service.duracion_minutos,
        preferred_barber_id=barber_id,
        exclude_appointment_id=exclude_appointment_id,
        tenant_id=tenant_id,
    )
    return jsonify({"slots": slots})


@main_bp.route("/calendar-days")
def calendar_days():
    tenant_id = getattr(current_user, "tenant_id", None) or get_current_tenant_id()
    service_id = request.args.get("service_id", type=int)
    month_value = request.args.get("month") or date.today().strftime("%Y-%m")
    barber_id = request.args.get("barber_id", type=int)

    if parse_month(month_value) is None:
        return jsonify({"days": [], "requires_service": True})

    service = Service.query.filter_by(id=service_id or 0, tenant_id=tenant_id).first()
    if service is None:
        return jsonify({"days": [], "requires_service": True})

    days = build_calendar_days(
        month_value,
        service.duracion_minutos,
        preferred_barber_id=barber_id,
        tenant_id=tenant_id,
    )
    return jsonify(
        {
            "days": days[0]["days"],
            "month_label": days[0]["month_label"],
            "month_value": days[0]["month_value"],
            "first_weekday": days[0]["first_weekday"],
            "requires_service": False,
        }
    )
