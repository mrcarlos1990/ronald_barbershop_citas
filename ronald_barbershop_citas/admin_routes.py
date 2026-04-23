from __future__ import annotations

from datetime import date, datetime
from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, logout_user
from sqlalchemy import and_, or_

from .decorators import admin_required
from .models import AdminUser, Appointment, Barber, BlockedSchedule, Client, Service, db
from .utils import (
    STATUS_LABELS,
    build_agenda_rows,
    get_business_settings,
    get_current_tenant_id,
    is_valid_email,
    is_valid_phone,
    normalize_phone,
    parse_date,
    parse_time,
    select_barber_for_booking,
)


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _is_safe_internal_path(path: str | None) -> bool:
    if not path:
        return False
    parsed = urlparse(path)
    return parsed.scheme == "" and parsed.netloc == "" and path.startswith("/")


def _load_active_form_options(tenant_id: int):
    services = Service.query.filter_by(tenant_id=tenant_id, activo=True).order_by(Service.nombre.asc()).all()
    barbers = Barber.query.filter_by(tenant_id=tenant_id, activo=True).order_by(Barber.nombre.asc()).all()
    return services, barbers


def _default_appointment_form(appointment: Appointment | None = None) -> dict:
    if appointment is None:
        return {
            "servicio_id": "",
            "barbero_id": "",
            "fecha": date.today().isoformat(),
            "hora": "",
            "nombre_cliente": "",
            "telefono": "",
            "nota": "",
            "estado": "confirmada",
        }

    return {
        "servicio_id": appointment.servicio_id,
        "barbero_id": appointment.barbero_id,
        "fecha": appointment.fecha.isoformat(),
        "hora": appointment.hora.strftime("%H:%M"),
        "nombre_cliente": appointment.nombre_cliente,
        "telefono": appointment.telefono,
        "nota": appointment.nota or "",
        "estado": appointment.estado,
    }


def _save_appointment_from_request(appointment: Appointment | None = None) -> tuple[Appointment | None, dict]:
    tenant_id = get_current_tenant_id()
    form_data = request.form.to_dict()
    service = Service.query.filter_by(id=request.form.get("servicio_id", type=int) or 0, tenant_id=tenant_id).first()
    preferred_barber = Barber.query.filter_by(id=request.form.get("barbero_id", type=int) or 0, tenant_id=tenant_id).first()
    booking_date = parse_date(request.form.get("fecha"))
    booking_time = parse_time(request.form.get("hora"))
    customer_name = (request.form.get("nombre_cliente") or "").strip()
    customer_phone = (request.form.get("telefono") or "").strip()
    note = (request.form.get("nota") or "").strip()
    status = (request.form.get("estado") or "confirmada").strip().lower()

    errors = []
    if service is None or not service.activo:
        errors.append("Selecciona un servicio valido.")
    if booking_date is None or booking_date < date.today():
        errors.append("Selecciona una fecha valida.")
    if booking_time is None:
        errors.append("Selecciona un horario disponible.")
    if not customer_name:
        errors.append("El nombre del cliente es obligatorio.")
    if not is_valid_phone(customer_phone):
        errors.append("Ingresa un telefono valido de 10 u 11 digitos.")
    if status not in STATUS_LABELS:
        errors.append("Selecciona un estado valido.")

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
            errors.append("Ese horario no esta disponible para el servicio y barbero seleccionados.")

    if errors:
        for error in errors:
            flash(error, "danger")
        return None, form_data

    normalized_phone = normalize_phone(customer_phone)
    client = Client.query.filter_by(tenant_id=tenant_id, telefono=normalized_phone).first()
    if client is None:
        client = Client(tenant_id=tenant_id, nombre=customer_name, telefono=normalized_phone, notas=note or None)
        db.session.add(client)
        db.session.flush()
    else:
        client.nombre = customer_name
        if note:
            client.notas = note

    if appointment is None:
        appointment = Appointment()
        db.session.add(appointment)

    appointment.tenant_id = tenant_id
    appointment.cliente_id = client.id
    appointment.servicio_id = service.id
    appointment.barbero_id = assigned_barber.id
    appointment.nombre_cliente = customer_name
    appointment.telefono = normalized_phone
    appointment.fecha = booking_date
    appointment.hora = booking_time
    appointment.duracion_minutos = service.duracion_minutos
    appointment.estado = status
    appointment.nota = note or None

    db.session.commit()
    return appointment, form_data


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_user_id"):
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        admin = AdminUser.query.filter(db.func.lower(AdminUser.username) == username.lower()).first()

        if admin and admin.check_password(password):
            if current_user.is_authenticated:
                logout_user()
            session.clear()
            session["admin_user_id"] = admin.id
            session["admin_tenant_id"] = admin.tenant_id
            flash("Sesion iniciada correctamente.", "success")
            next_url = request.args.get("next")
            if _is_safe_internal_path(next_url):
                return redirect(next_url)
            return redirect(url_for("admin.dashboard"))

        flash("Credenciales invalidas. Verifica usuario y contrasena.", "danger")

    return render_template("admin/login.html")


@admin_bp.route("/logout")
@admin_required
def logout():
    session.clear()
    flash("La sesion fue cerrada.", "success")
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
@admin_required
def dashboard():
    tenant_id = get_current_tenant_id()
    today = date.today()
    today_appointments = Appointment.query.filter_by(tenant_id=tenant_id, fecha=today).order_by(Appointment.hora.asc()).all()
    upcoming_appointments = (
        Appointment.query.filter(
            Appointment.tenant_id == tenant_id,
            Appointment.estado != "cancelada",
            or_(
                Appointment.fecha > today,
                and_(Appointment.fecha == today, Appointment.hora >= datetime.now().time()),
            ),
        )
        .order_by(Appointment.fecha.asc(), Appointment.hora.asc())
        .limit(8)
        .all()
    )
    recent_clients = Client.query.filter_by(tenant_id=tenant_id).order_by(Client.fecha_creacion.desc()).limit(6).all()

    top_service_row = (
        db.session.query(Service.nombre, db.func.count(Appointment.id).label("total"))
        .select_from(Appointment)
        .join(Service, Service.id == Appointment.servicio_id)
        .filter(Appointment.tenant_id == tenant_id, Appointment.estado != "cancelada")
        .group_by(Service.nombre)
        .order_by(db.desc("total"))
        .first()
    )
    top_barber_row = (
        db.session.query(Barber.nombre, db.func.count(Appointment.id).label("total"))
        .select_from(Appointment)
        .join(Barber, Barber.id == Appointment.barbero_id)
        .filter(Appointment.tenant_id == tenant_id, Appointment.estado != "cancelada")
        .group_by(Barber.nombre)
        .order_by(db.desc("total"))
        .first()
    )
    busiest_hours = (
        db.session.query(Appointment.hora, db.func.count(Appointment.id).label("total"))
        .filter(Appointment.tenant_id == tenant_id, Appointment.estado != "cancelada")
        .group_by(Appointment.hora)
        .order_by(db.desc("total"), Appointment.hora.asc())
        .limit(3)
        .all()
    )
    estimated_income = (
        db.session.query(db.func.coalesce(db.func.sum(Service.precio), 0))
        .select_from(Appointment)
        .join(Service, Service.id == Appointment.servicio_id)
        .filter(Appointment.tenant_id == tenant_id, Appointment.estado.in_(("confirmada", "completada")))
        .scalar()
        or 0
    )

    stats = {
        "total": Appointment.query.filter_by(tenant_id=tenant_id).count(),
        "pendientes": Appointment.query.filter_by(tenant_id=tenant_id, estado="pendiente").count(),
        "confirmadas": Appointment.query.filter_by(tenant_id=tenant_id, estado="confirmada").count(),
        "completadas": Appointment.query.filter_by(tenant_id=tenant_id, estado="completada").count(),
        "canceladas": Appointment.query.filter_by(tenant_id=tenant_id, estado="cancelada").count(),
        "citas_hoy": Appointment.query.filter_by(tenant_id=tenant_id, fecha=today).count(),
        "clientes": Client.query.filter_by(tenant_id=tenant_id).count(),
        "nuevos_clientes_hoy": Client.query.filter(Client.tenant_id == tenant_id, db.func.date(Client.fecha_creacion) == today.isoformat()).count(),
        "ingresos_estimados": estimated_income,
    }

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        today_appointments=today_appointments,
        upcoming_appointments=upcoming_appointments,
        recent_clients=recent_clients,
        top_service=top_service_row,
        top_barber=top_barber_row,
        busiest_hours=busiest_hours,
    )


@admin_bp.route("/services", methods=["GET", "POST"])
@admin_required
def services():
    tenant_id = get_current_tenant_id()
    service_to_edit = None

    if request.method == "POST":
        service_id = request.form.get("service_id", type=int)
        name = (request.form.get("nombre") or "").strip()
        description = (request.form.get("descripcion") or "").strip()
        duration_minutes = request.form.get("duracion_minutos", type=int) or 0
        price = request.form.get("precio", type=float)
        category = (request.form.get("categoria") or "").strip()
        image_url = (request.form.get("image_url") or "").strip()
        active = request.form.get("activo") == "on"
        existing_service = Service.query.filter(
            Service.tenant_id == tenant_id,
            db.func.lower(Service.nombre) == name.lower(),
            Service.id != (service_id or 0),
        ).first()

        if not name or duration_minutes <= 0:
            flash("Nombre y duracion son obligatorios.", "danger")
        elif price is None or price < 0:
            flash("Ingresa un precio valido.", "danger")
        elif existing_service:
            flash("Ya existe un servicio con ese nombre.", "danger")
        else:
            if service_id:
                service = Service.query.filter_by(id=service_id, tenant_id=tenant_id).first()
                if service is None:
                    flash("El servicio no existe.", "danger")
                    return redirect(url_for("admin.services"))
            else:
                service = Service(tenant_id=tenant_id)
                db.session.add(service)

            service.nombre = name
            service.descripcion = description or None
            service.duracion_minutos = duration_minutes
            service.precio = price
            service.categoria = category or None
            service.image_url = image_url or None
            service.activo = active
            db.session.commit()
            flash("Servicio guardado correctamente.", "success")
            return redirect(url_for("admin.services"))

    edit_id = request.args.get("edit", type=int)
    if edit_id:
        service_to_edit = Service.query.filter_by(id=edit_id, tenant_id=tenant_id).first()

    service_list = Service.query.filter_by(tenant_id=tenant_id).order_by(Service.activo.desc(), Service.nombre.asc()).all()
    return render_template("admin/services.html", service_list=service_list, service_to_edit=service_to_edit)


@admin_bp.route("/services/<int:service_id>/delete", methods=["POST"])
@admin_required
def delete_service(service_id: int):
    service = Service.query.filter_by(id=service_id, tenant_id=get_current_tenant_id()).first()
    if service is None:
        flash("El servicio no existe.", "warning")
    elif service.citas.count() > 0:
        flash("No puedes eliminar un servicio con citas registradas. Puedes desactivarlo.", "danger")
    else:
        db.session.delete(service)
        db.session.commit()
        flash("Servicio eliminado correctamente.", "success")
    return redirect(url_for("admin.services"))


@admin_bp.route("/barbers", methods=["GET", "POST"])
@admin_required
def barbers():
    tenant_id = get_current_tenant_id()
    barber_to_edit = None

    if request.method == "POST":
        barber_id = request.form.get("barber_id", type=int)
        name = (request.form.get("nombre") or "").strip()
        specialty = (request.form.get("especialidad") or "").strip()
        phone = (request.form.get("telefono") or "").strip()
        photo = (request.form.get("foto") or "").strip()
        bio = (request.form.get("bio") or "").strip()
        active = request.form.get("activo") == "on"
        existing_barber = Barber.query.filter(
            Barber.tenant_id == tenant_id,
            db.func.lower(Barber.nombre) == name.lower(),
            Barber.id != (barber_id or 0),
        ).first()

        if not name:
            flash("El nombre del barbero es obligatorio.", "danger")
        elif phone and not is_valid_phone(phone):
            flash("El telefono del barbero debe tener 10 u 11 digitos.", "danger")
        elif existing_barber:
            flash("Ya existe un barbero con ese nombre.", "danger")
        else:
            if barber_id:
                barber = Barber.query.filter_by(id=barber_id, tenant_id=tenant_id).first()
                if barber is None:
                    flash("El barbero no existe.", "danger")
                    return redirect(url_for("admin.barbers"))
            else:
                barber = Barber(tenant_id=tenant_id)
                db.session.add(barber)

            barber.nombre = name
            barber.especialidad = specialty or None
            barber.telefono = normalize_phone(phone) if phone else None
            barber.foto = photo or None
            barber.bio = bio or None
            barber.activo = active
            db.session.commit()
            flash("Barbero guardado correctamente.", "success")
            return redirect(url_for("admin.barbers"))

    edit_id = request.args.get("edit", type=int)
    if edit_id:
        barber_to_edit = Barber.query.filter_by(id=edit_id, tenant_id=tenant_id).first()

    barber_list = Barber.query.filter_by(tenant_id=tenant_id).order_by(Barber.activo.desc(), Barber.nombre.asc()).all()
    return render_template("admin/barbers.html", barber_list=barber_list, barber_to_edit=barber_to_edit)


@admin_bp.route("/barbers/<int:barber_id>/delete", methods=["POST"])
@admin_required
def delete_barber(barber_id: int):
    barber = Barber.query.filter_by(id=barber_id, tenant_id=get_current_tenant_id()).first()
    if barber is None:
        flash("El barbero no existe.", "warning")
    elif barber.citas.count() > 0 or barber.horarios_bloqueados.count() > 0:
        flash("No puedes eliminar un barbero con historial. Puedes desactivarlo.", "danger")
    else:
        db.session.delete(barber)
        db.session.commit()
        flash("Barbero eliminado correctamente.", "success")
    return redirect(url_for("admin.barbers"))


@admin_bp.route("/appointments")
@admin_required
def appointments():
    tenant_id = get_current_tenant_id()
    selected_date = parse_date(request.args.get("date")) or date.today()
    selected_status = (request.args.get("status") or "").strip()
    selected_barber_id = request.args.get("barber_id", type=int)
    barbers = Barber.query.filter_by(tenant_id=tenant_id).order_by(Barber.nombre.asc()).all()

    appointment_query = Appointment.query.filter_by(tenant_id=tenant_id, fecha=selected_date)
    if selected_status:
        appointment_query = appointment_query.filter_by(estado=selected_status)
    if selected_barber_id:
        appointment_query = appointment_query.filter_by(barbero_id=selected_barber_id)

    day_appointments = appointment_query.order_by(Appointment.hora.asc()).all()

    upcoming_query = Appointment.query.filter(Appointment.tenant_id == tenant_id, Appointment.fecha >= date.today()).order_by(
        Appointment.fecha.asc(),
        Appointment.hora.asc(),
    )
    if selected_status:
        upcoming_query = upcoming_query.filter_by(estado=selected_status)
    if selected_barber_id:
        upcoming_query = upcoming_query.filter_by(barbero_id=selected_barber_id)

    upcoming_appointments = upcoming_query.limit(20).all()
    agenda_rows = build_agenda_rows(selected_date, tenant_id=tenant_id)

    return render_template(
        "admin/appointments.html",
        selected_date=selected_date,
        selected_status=selected_status,
        selected_barber_id=selected_barber_id,
        day_appointments=day_appointments,
        upcoming_appointments=upcoming_appointments,
        agenda_rows=agenda_rows,
        barbers=barbers,
    )


@admin_bp.route("/appointments/new", methods=["GET", "POST"])
@admin_required
def new_appointment():
    tenant_id = get_current_tenant_id()
    services, barbers = _load_active_form_options(tenant_id)
    form_data = _default_appointment_form()

    if request.method == "POST":
        appointment, form_data = _save_appointment_from_request()
        if appointment is not None:
            flash("Cita creada correctamente.", "success")
            return redirect(url_for("admin.appointments", date=appointment.fecha.isoformat()))

    return render_template(
        "admin/appointment_form.html",
        appointment=None,
        services=services,
        barbers=barbers,
        form_data=form_data,
        today_iso=date.today().isoformat(),
        calendar_initial_month=date.today().strftime("%Y-%m"),
    )


@admin_bp.route("/appointments/<int:appointment_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_appointment(appointment_id: int):
    tenant_id = get_current_tenant_id()
    appointment = Appointment.query.filter_by(id=appointment_id, tenant_id=tenant_id).first()
    if appointment is None:
        flash("La cita no existe.", "warning")
        return redirect(url_for("admin.appointments"))

    services, barbers = _load_active_form_options(tenant_id)
    form_data = _default_appointment_form(appointment)

    if request.method == "POST":
        updated_appointment, form_data = _save_appointment_from_request(appointment=appointment)
        if updated_appointment is not None:
            flash("Cita actualizada correctamente.", "success")
            return redirect(url_for("admin.appointments", date=updated_appointment.fecha.isoformat()))

    return render_template(
        "admin/appointment_form.html",
        appointment=appointment,
        services=services,
        barbers=barbers,
        form_data=form_data,
        today_iso=date.today().isoformat(),
        calendar_initial_month=appointment.fecha.strftime("%Y-%m"),
    )


@admin_bp.route("/appointments/<int:appointment_id>/status", methods=["POST"])
@admin_required
def update_appointment_status(appointment_id: int):
    appointment = Appointment.query.filter_by(id=appointment_id, tenant_id=get_current_tenant_id()).first()
    new_status = (request.form.get("estado") or "").strip().lower()

    if appointment and new_status in STATUS_LABELS:
        appointment.estado = new_status
        db.session.commit()
        flash("Estado actualizado correctamente.", "success")
    else:
        flash("No fue posible actualizar el estado.", "danger")

    target_date = appointment.fecha.isoformat() if appointment else date.today().isoformat()
    return redirect(url_for("admin.appointments", date=target_date))


@admin_bp.route("/appointments/<int:appointment_id>/delete", methods=["POST"])
@admin_required
def delete_appointment(appointment_id: int):
    appointment = Appointment.query.filter_by(id=appointment_id, tenant_id=get_current_tenant_id()).first()
    if appointment is None:
        flash("La cita no existe.", "warning")
        return redirect(url_for("admin.appointments"))

    target_date = appointment.fecha.isoformat()
    db.session.delete(appointment)
    db.session.commit()
    flash("Cita eliminada correctamente.", "success")
    return redirect(url_for("admin.appointments", date=target_date))


@admin_bp.route("/blocked-slots", methods=["GET", "POST"])
@admin_required
def blocked_slots():
    tenant_id = get_current_tenant_id()
    if request.method == "POST":
        booking_date = parse_date(request.form.get("fecha"))
        start_time = parse_time(request.form.get("hora_inicio"))
        end_time = parse_time(request.form.get("hora_fin"))
        reason = (request.form.get("motivo") or "").strip() or "Bloqueo manual"
        barber_id = request.form.get("barbero_id", type=int)

        if not booking_date or not start_time or not end_time or end_time <= start_time:
            flash("Completa un rango de horario valido.", "danger")
        elif booking_date < date.today():
            flash("No puedes bloquear fechas pasadas.", "danger")
        else:
            block = BlockedSchedule(
                tenant_id=tenant_id,
                fecha=booking_date,
                hora_inicio=start_time,
                hora_fin=end_time,
                motivo=reason,
                barbero_id=barber_id or None,
            )
            db.session.add(block)
            db.session.commit()
            flash("Horario bloqueado correctamente.", "success")
            return redirect(url_for("admin.blocked_slots"))

    barbers = Barber.query.filter_by(tenant_id=tenant_id, activo=True).order_by(Barber.nombre.asc()).all()
    blocked_list = BlockedSchedule.query.filter_by(tenant_id=tenant_id).order_by(BlockedSchedule.fecha.desc(), BlockedSchedule.hora_inicio.desc()).all()
    return render_template("admin/blocked_slots.html", barbers=barbers, blocked_list=blocked_list)


@admin_bp.route("/blocked-slots/<int:block_id>/delete", methods=["POST"])
@admin_required
def delete_blocked_slot(block_id: int):
    block = BlockedSchedule.query.filter_by(id=block_id, tenant_id=get_current_tenant_id()).first()
    if block:
        db.session.delete(block)
        db.session.commit()
        flash("Bloqueo eliminado.", "success")
    else:
        flash("El bloqueo no existe.", "warning")
    return redirect(url_for("admin.blocked_slots"))


@admin_bp.route("/clients", methods=["GET", "POST"])
@admin_required
def clients():
    tenant_id = get_current_tenant_id()
    client_to_edit = None
    search = (request.args.get("q") or "").strip()

    if request.method == "POST":
        client_id = request.form.get("client_id", type=int)
        client = Client.query.filter_by(id=client_id or 0, tenant_id=tenant_id).first()
        if client is None:
            flash("El cliente no existe.", "danger")
            return redirect(url_for("admin.clients"))

        name = (request.form.get("nombre") or "").strip()
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        phone = (request.form.get("telefono") or "").strip()
        notes = (request.form.get("notas") or "").strip()
        active = request.form.get("activo") == "on"

        errors = []
        if not name:
            errors.append("El nombre del cliente es obligatorio.")
        if not username:
            errors.append("El username es obligatorio.")
        elif Client.query.filter(Client.tenant_id == tenant_id, db.func.lower(Client.username) == username.lower(), Client.id != client.id).first():
            errors.append("Ese username ya esta en uso.")
        if email:
            if not is_valid_email(email):
                errors.append("Ingresa un correo valido.")
            elif Client.query.filter(Client.tenant_id == tenant_id, db.func.lower(Client.email) == email.lower(), Client.id != client.id).first():
                errors.append("Ese correo ya esta registrado.")
        if not is_valid_phone(phone):
            errors.append("Ingresa un telefono valido.")
        elif Client.query.filter(Client.tenant_id == tenant_id, Client.telefono == normalize_phone(phone), Client.id != client.id).first():
            errors.append("Ese telefono ya pertenece a otro cliente.")

        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            client.nombre = name
            client.username = username
            client.email = email or None
            client.telefono = normalize_phone(phone)
            client.notas = notes or None
            client.activo = active
            db.session.commit()
            flash("Cliente actualizado correctamente.", "success")
            return redirect(url_for("admin.clients"))

    edit_id = request.args.get("edit", type=int)
    if edit_id:
        client_to_edit = Client.query.filter_by(id=edit_id, tenant_id=tenant_id).first()

    client_query = Client.query.filter_by(tenant_id=tenant_id).order_by(Client.fecha_creacion.desc())

    if search:
        like_term = f"%{search}%"
        client_query = client_query.filter(
            or_(
                Client.nombre.ilike(like_term),
                Client.username.ilike(like_term),
                Client.email.ilike(like_term),
                Client.telefono.ilike(like_term),
            )
        )

    client_list = client_query.all()
    return render_template(
        "admin/clients.html",
        client_list=client_list,
        search=search,
        client_to_edit=client_to_edit,
    )


def _render_business_settings():
    from .business_routes import settings as business_settings_view

    return business_settings_view()


@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    return _render_business_settings()


@admin_bp.route("/settings-legacy", methods=["GET", "POST"])
@admin_required
def settings_legacy():
    return _render_business_settings()
