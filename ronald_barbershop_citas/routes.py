from __future__ import annotations

from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from .models import Appointment, Barber, Client, Service, db
from .utils import (
    build_available_slots,
    build_calendar_days,
    build_reusable_whatsapp_link,
    build_whatsapp_confirmation_link,
    get_business_settings,
    is_valid_phone,
    normalize_phone,
    parse_date,
    parse_month,
    parse_time,
    select_barber_for_booking,
)


main_bp = Blueprint("main", __name__)


def _booking_context(form_data: dict | None = None):
    settings = get_business_settings()
    services = Service.query.filter_by(activo=True).order_by(Service.nombre.asc()).all()
    barbers = Barber.query.filter_by(activo=True).order_by(Barber.nombre.asc()).all()
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
    settings = get_business_settings()
    services = Service.query.filter_by(activo=True).order_by(Service.id.asc()).all()
    barbers = Barber.query.filter_by(activo=True).order_by(Barber.id.asc()).all()
    booking_url = request.url_root.rstrip("/") + url_for("main.booking_form")
    whatsapp_link = build_reusable_whatsapp_link(settings, booking_url=booking_url)
    return render_template(
        "landing.html",
        settings=settings,
        services=services,
        barbers=barbers,
        booking_url=booking_url,
        whatsapp_link=whatsapp_link,
    )


@main_bp.route("/agendar", methods=["GET", "POST"])
def booking_form():
    if request.method == "GET":
        form_data = {
            "servicio_id": request.args.get("servicio_id", ""),
            "barbero_id": request.args.get("barbero_id", ""),
            "fecha": request.args.get("fecha", ""),
            "hora": request.args.get("hora", ""),
            "nombre_cliente": "",
            "telefono": "",
            "nota": "",
        }
        return render_template("booking.html", **_booking_context(form_data))

    form_data = request.form.to_dict()
    service = db.session.get(Service, request.form.get("servicio_id", type=int) or 0)
    preferred_barber = db.session.get(Barber, request.form.get("barbero_id", type=int) or 0)
    booking_date = parse_date(request.form.get("fecha"))
    booking_time = parse_time(request.form.get("hora"))
    customer_name = (request.form.get("nombre_cliente") or "").strip()
    customer_phone = (request.form.get("telefono") or "").strip()
    note = (request.form.get("nota") or "").strip()

    errors = []
    if service is None or not service.activo:
        errors.append("Selecciona un servicio valido.")
    if booking_date is None or booking_date < date.today():
        errors.append("Selecciona una fecha valida.")
    if booking_time is None:
        errors.append("Selecciona un horario disponible.")
    if not customer_name:
        errors.append("Ingresa tu nombre.")
    if not is_valid_phone(customer_phone):
        errors.append("Ingresa un telefono valido de 10 u 11 digitos.")

    assigned_barber = None
    if not errors and service and booking_date and booking_time:
        assigned_barber = select_barber_for_booking(
            booking_date,
            booking_time,
            service.duracion_minutos,
            preferred_barber_id=preferred_barber.id if preferred_barber else None,
        )
        if assigned_barber is None:
            errors.append("Ese horario ya no esta disponible o queda fuera del horario laboral.")

    if errors:
        for error in errors:
            flash(error, "danger")
        return render_template("booking.html", **_booking_context(form_data))

    normalized_phone = normalize_phone(customer_phone)
    client = Client.query.filter_by(telefono=normalized_phone).first()
    if client is None:
        client = Client(nombre=customer_name, telefono=normalized_phone, notas=note or None)
        db.session.add(client)
        db.session.flush()
    else:
        client.nombre = customer_name
        if note:
            client.notas = note

    appointment = Appointment(
        cliente_id=client.id,
        servicio_id=service.id,
        barbero_id=assigned_barber.id,
        nombre_cliente=customer_name,
        telefono=normalized_phone,
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
def booking_confirmation(appointment_id: int):
    appointment = db.session.get(Appointment, appointment_id)
    if appointment is None:
        flash("La cita solicitada no existe.", "warning")
        return redirect(url_for("main.booking_form"))

    settings = get_business_settings()
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
    service_id = request.args.get("service_id", type=int)
    booking_date = parse_date(request.args.get("date"))
    barber_id = request.args.get("barber_id", type=int)
    exclude_appointment_id = request.args.get("exclude_appointment_id", type=int)

    service = db.session.get(Service, service_id or 0)
    if not service or not booking_date or booking_date < date.today():
        return jsonify({"slots": []})

    slots = build_available_slots(
        booking_date,
        service.duracion_minutos,
        preferred_barber_id=barber_id,
        exclude_appointment_id=exclude_appointment_id,
    )
    return jsonify({"slots": slots})


@main_bp.route("/calendar-days")
def calendar_days():
    service_id = request.args.get("service_id", type=int)
    month_value = request.args.get("month") or date.today().strftime("%Y-%m")
    barber_id = request.args.get("barber_id", type=int)

    if parse_month(month_value) is None:
        return jsonify({"days": [], "requires_service": True})

    service = db.session.get(Service, service_id or 0)
    if service is None:
        return jsonify({"days": [], "requires_service": True})

    days = build_calendar_days(
        month_value,
        service.duracion_minutos,
        preferred_barber_id=barber_id,
    )
    return jsonify({"days": days[0]["days"], "month_label": days[0]["month_label"], "month_value": days[0]["month_value"], "first_weekday": days[0]["first_weekday"], "requires_service": False})
