from __future__ import annotations

from datetime import date, datetime
from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import and_, or_

from .decorators import client_required
from .models import Appointment, Barber, Client, Service, db
from .utils import (
    build_reusable_whatsapp_link,
    build_whatsapp_confirmation_link,
    client_can_manage_appointment,
    get_current_tenant_id,
    get_business_settings,
    is_valid_email,
    is_valid_phone,
    normalize_phone,
    parse_date,
    parse_time,
    select_barber_for_booking,
)


client_bp = Blueprint("client", __name__, url_prefix="/cliente")


def _is_safe_internal_path(path: str | None) -> bool:
    if not path:
        return False
    parsed = urlparse(path)
    return parsed.scheme == "" and parsed.netloc == "" and path.startswith("/")


def _booking_context(form_data: dict | None = None, appointment: Appointment | None = None):
    tenant_id = getattr(current_user, "tenant_id", None) or get_current_tenant_id()
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
        "calendar_initial_month": (
            appointment.fecha.strftime("%Y-%m")
            if appointment
            else (form_data.get("fecha", "")[:7] if form_data and form_data.get("fecha") else date.today().strftime("%Y-%m"))
        ),
        "landing_whatsapp_link": build_reusable_whatsapp_link(
            settings,
            booking_url=request.url_root.rstrip("/") + booking_url,
        ),
        "appointment": appointment,
        "form_action": request.path,
        "submit_label": "Guardar reprogramacion" if appointment else "Confirmar cita",
    }


def _find_client_by_identifier(identifier: str) -> Client | None:
    clean_identifier = (identifier or "").strip()
    if not clean_identifier:
        return None

    tenant_id = get_current_tenant_id()
    return Client.query.filter(
        Client.tenant_id == tenant_id,
        or_(
            db.func.lower(Client.username) == clean_identifier.lower(),
            db.func.lower(Client.email) == clean_identifier.lower(),
        )
    ).first()


def _validate_client_identity_fields(
    username: str,
    email: str,
    phone: str,
    current_client_id: int | None = None,
) -> list[str]:
    tenant_id = get_current_tenant_id()
    errors = []

    if not username:
        errors.append("El username es obligatorio.")
    else:
        existing_username = Client.query.filter(
            Client.tenant_id == tenant_id,
            db.func.lower(Client.username) == username.lower(),
            Client.id != (current_client_id or 0),
        ).first()
        if existing_username:
            errors.append("Ese username ya esta en uso.")

    if email:
        if not is_valid_email(email):
            errors.append("Ingresa un correo valido.")
        else:
            existing_email = Client.query.filter(
                Client.tenant_id == tenant_id,
                db.func.lower(Client.email) == email.lower(),
                Client.id != (current_client_id or 0),
            ).first()
            if existing_email:
                errors.append("Ese correo ya esta registrado.")

    if not is_valid_phone(phone):
        errors.append("Ingresa un telefono valido de 10 u 11 digitos.")
    else:
        normalized_phone = normalize_phone(phone)
        existing_phone = Client.query.filter(
            Client.tenant_id == tenant_id,
            Client.telefono == normalized_phone,
            Client.id != (current_client_id or 0),
        ).first()
        if existing_phone:
            errors.append("Ese telefono ya esta vinculado a otra cuenta.")

    return errors


def _save_client_appointment(appointment: Appointment | None = None) -> tuple[Appointment | None, dict]:
    tenant_id = current_user.tenant_id or get_current_tenant_id()
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
            exclude_appointment_id=appointment.id if appointment else None,
            tenant_id=tenant_id,
        )
        if assigned_barber is None:
            errors.append("Ese horario ya no esta disponible o queda fuera del horario laboral.")

    if errors:
        for error in errors:
            flash(error, "danger")
        return None, form_data

    if appointment is None:
        appointment = Appointment(tenant_id=tenant_id, cliente_id=current_user.id)
        db.session.add(appointment)

    appointment.tenant_id = tenant_id
    appointment.cliente_id = current_user.id
    appointment.servicio_id = service.id
    appointment.barbero_id = assigned_barber.id
    appointment.nombre_cliente = current_user.nombre
    appointment.telefono = current_user.telefono
    appointment.fecha = booking_date
    appointment.hora = booking_time
    appointment.duracion_minutos = service.duracion_minutos
    appointment.estado = "pendiente" if appointment.id is None else appointment.estado
    appointment.nota = note or None
    db.session.commit()
    return appointment, form_data


@client_bp.route("/registro", methods=["GET", "POST"])
def register():
    tenant_id = get_current_tenant_id()
    if current_user.is_authenticated:
        return redirect(url_for("client.dashboard"))

    form_data = {
        "nombre": "",
        "username": "",
        "email": "",
        "telefono": "",
    }

    if request.method == "POST":
        form_data = request.form.to_dict()
        name = (request.form.get("nombre") or "").strip()
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        phone = (request.form.get("telefono") or "").strip()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        errors = []
        if not name:
            errors.append("El nombre completo es obligatorio.")
        errors.extend(_validate_client_identity_fields(username, email, phone))
        if len(password) < 8:
            errors.append("La contrasena debe tener al menos 8 caracteres.")
        if password != confirm_password:
            errors.append("Las contrasenas no coinciden.")

        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            client = Client(
                tenant_id=tenant_id,
                nombre=name,
                username=username,
                email=email or None,
                telefono=normalize_phone(phone),
                activo=True,
            )
            client.set_password(password)
            db.session.add(client)
            db.session.commit()
            session.pop("admin_user_id", None)
            login_user(client)
            flash("Tu cuenta fue creada correctamente.", "success")
            next_url = request.args.get("next")
            if _is_safe_internal_path(next_url):
                return redirect(next_url)
            return redirect(url_for("client.dashboard"))

    return render_template("registro_cliente.html", form_data=form_data)


@client_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("client.dashboard"))

    form_data = {"identifier": ""}
    if request.method == "POST":
        form_data = request.form.to_dict()
        identifier = (request.form.get("identifier") or "").strip()
        password = request.form.get("password") or ""
        client = _find_client_by_identifier(identifier)

        if client and client.activo and client.check_password(password):
            session.pop("admin_user_id", None)
            login_user(client)
            flash("Sesion iniciada correctamente.", "success")
            next_url = request.args.get("next")
            if _is_safe_internal_path(next_url):
                return redirect(next_url)
            return redirect(url_for("client.dashboard"))

        flash("Credenciales invalidas o cuenta inactiva.", "danger")

    return render_template("login_cliente.html", form_data=form_data)


@client_bp.route("/logout")
@client_required
def logout():
    logout_user()
    flash("Sesion de cliente cerrada correctamente.", "success")
    return redirect(url_for("main.landing"))


@client_bp.route("/recuperar-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("client.dashboard"))

    form_data = {"identifier": "", "telefono": ""}
    if request.method == "POST":
        form_data = request.form.to_dict()
        identifier = (request.form.get("identifier") or "").strip()
        phone = (request.form.get("telefono") or "").strip()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        client = _find_client_by_identifier(identifier)
        errors = []

        if client is None:
            errors.append("No existe una cuenta con ese usuario o correo.")
        elif client.telefono != normalize_phone(phone):
            errors.append("El telefono no coincide con la cuenta registrada.")

        if len(password) < 8:
            errors.append("La nueva contrasena debe tener al menos 8 caracteres.")
        if password != confirm_password:
            errors.append("Las contrasenas no coinciden.")

        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            client.set_password(password)
            db.session.commit()
            flash("Contrasena actualizada. Ya puedes iniciar sesion.", "success")
            return redirect(url_for("client.login"))

    return render_template("recuperar_cliente.html", form_data=form_data)


@client_bp.route("/panel", methods=["GET", "POST"])
@client_required
def dashboard():
    if request.method == "POST":
        action = request.form.get("action") or "profile"
        if action == "profile":
            name = (request.form.get("nombre") or "").strip()
            username = (request.form.get("username") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            phone = (request.form.get("telefono") or "").strip()
            notes = (request.form.get("notas") or "").strip()

            errors = []
            if not name:
                errors.append("El nombre completo es obligatorio.")
            errors.extend(_validate_client_identity_fields(username, email, phone, current_user.id))

            if errors:
                for error in errors:
                    flash(error, "danger")
            else:
                current_user.nombre = name
                current_user.username = username
                current_user.email = email or None
                current_user.telefono = normalize_phone(phone)
                current_user.notas = notes or None
                db.session.commit()
                flash("Tu perfil fue actualizado.", "success")
                return redirect(url_for("client.dashboard"))

    today = date.today()
    now_time = datetime.now().time()
    upcoming_appointments = (
        Appointment.query.filter(
            Appointment.cliente_id == current_user.id,
            Appointment.tenant_id == current_user.tenant_id,
            or_(
                Appointment.fecha > today,
                and_(Appointment.fecha == today, Appointment.hora >= now_time),
            ),
        )
        .order_by(Appointment.fecha.asc(), Appointment.hora.asc())
        .all()
    )
    history_appointments = (
        Appointment.query.filter(
            Appointment.cliente_id == current_user.id,
            Appointment.tenant_id == current_user.tenant_id,
            or_(
                Appointment.fecha < today,
                and_(Appointment.fecha == today, Appointment.hora < now_time),
            ),
        )
        .order_by(Appointment.fecha.desc(), Appointment.hora.desc())
        .limit(8)
        .all()
    )
    settings = get_business_settings(tenant_id=current_user.tenant_id)
    contact_link = build_reusable_whatsapp_link(settings, booking_url=request.url_root.rstrip("/") + url_for("main.booking_form"))

    return render_template(
        "panel_cliente.html",
        upcoming_appointments=upcoming_appointments,
        history_appointments=history_appointments,
        contact_link=contact_link,
        client_can_manage_appointment=client_can_manage_appointment,
    )


@client_bp.route("/citas")
@client_required
def appointments():
    settings = get_business_settings(tenant_id=current_user.tenant_id)
    contact_link = build_reusable_whatsapp_link(settings, booking_url=request.url_root.rstrip("/") + url_for("main.booking_form"))
    all_appointments = (
        Appointment.query.filter_by(cliente_id=current_user.id, tenant_id=current_user.tenant_id)
        .order_by(Appointment.fecha.desc(), Appointment.hora.desc())
        .all()
    )
    return render_template(
        "mis_citas.html",
        appointments=all_appointments,
        contact_link=contact_link,
        client_can_manage_appointment=client_can_manage_appointment,
    )


@client_bp.route("/citas/<int:appointment_id>/cancelar", methods=["POST"])
@client_required
def cancel_appointment(appointment_id: int):
    appointment = Appointment.query.filter_by(id=appointment_id, cliente_id=current_user.id, tenant_id=current_user.tenant_id).first()
    if appointment is None:
        flash("No puedes acceder a esa cita.", "danger")
        return redirect(url_for("client.appointments"))

    if not client_can_manage_appointment(appointment):
        flash("Esa cita ya no puede cancelarse.", "warning")
        return redirect(url_for("client.appointments"))

    appointment.estado = "cancelada"
    db.session.commit()
    flash("La cita fue cancelada correctamente.", "success")
    return redirect(url_for("client.appointments"))


@client_bp.route("/citas/<int:appointment_id>/reprogramar", methods=["GET", "POST"])
@client_required
def reschedule_appointment(appointment_id: int):
    appointment = Appointment.query.filter_by(id=appointment_id, cliente_id=current_user.id, tenant_id=current_user.tenant_id).first()
    if appointment is None:
        flash("No puedes acceder a esa cita.", "danger")
        return redirect(url_for("client.appointments"))

    if not client_can_manage_appointment(appointment):
        flash("Esa cita ya no puede reprogramarse.", "warning")
        return redirect(url_for("client.appointments"))

    form_data = {
        "servicio_id": appointment.servicio_id,
        "barbero_id": appointment.barbero_id,
        "fecha": appointment.fecha.isoformat(),
        "hora": appointment.hora.strftime("%H:%M"),
        "nota": appointment.nota or "",
    }

    if request.method == "POST":
        updated_appointment, form_data = _save_client_appointment(appointment=appointment)
        if updated_appointment is not None:
            flash("Tu cita fue reprogramada correctamente.", "success")
            return redirect(url_for("main.booking_confirmation", appointment_id=updated_appointment.id))

    return render_template("agendar.html", **_booking_context(form_data=form_data, appointment=appointment), exclude_appointment_id=appointment.id)
