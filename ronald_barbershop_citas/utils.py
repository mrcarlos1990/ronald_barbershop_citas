from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, time, timedelta
from typing import Any
from urllib.parse import quote

from sqlalchemy import or_

from .models import Appointment, Barber, BlockedSchedule, BusinessSettings


STATUS_LABELS = {
    "pendiente": "Pendiente",
    "confirmada": "Confirmada",
    "completada": "Completada",
    "cancelada": "Cancelada",
}


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_time(value: str | None) -> time | None:
    if not value:
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def parse_month(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m")
        return parsed.year, parsed.month
    except ValueError:
        return None


def format_time(value: time | None) -> str:
    if not value:
        return ""
    return value.strftime("%I:%M %p").lstrip("0")


def format_date(value: date | None) -> str:
    if not value:
        return ""
    return value.strftime("%d/%m/%Y")


def format_datetime(value: datetime | None) -> str:
    if not value:
        return ""
    return value.strftime("%d/%m/%Y %I:%M %p").lstrip("0")


def format_currency(value: float | int | None) -> str:
    amount = float(value or 0)
    return f"US${amount:,.2f}"


def normalize_phone(phone: str | None) -> str:
    return "".join(character for character in (phone or "") if character.isdigit())


def is_valid_phone(phone: str | None) -> bool:
    digits = normalize_phone(phone)
    if len(digits) == 10:
        return True
    return len(digits) == 11 and digits.startswith("1")


def build_whatsapp_target(phone: str | None) -> str:
    digits = normalize_phone(phone)
    if len(digits) == 10:
        return f"1{digits}"
    return digits


def get_business_settings() -> BusinessSettings:
    settings = BusinessSettings.query.first()
    if settings is None:
        settings = BusinessSettings()
        from .models import db

        db.session.add(settings)
        db.session.commit()
    return settings


def time_ranges_overlap(start_a: time, duration_a: int, start_b: time, duration_b: int) -> bool:
    base_day = date.today()
    start_a_dt = datetime.combine(base_day, start_a)
    end_a_dt = start_a_dt + timedelta(minutes=duration_a)
    start_b_dt = datetime.combine(base_day, start_b)
    end_b_dt = start_b_dt + timedelta(minutes=duration_b)
    return max(start_a_dt, start_b_dt) < min(end_a_dt, end_b_dt)


def build_daily_slots(settings: BusinessSettings, duration_minutes: int | None = None) -> list[time]:
    duration = duration_minutes or settings.intervalo_minutos
    start = datetime.combine(date.today(), settings.hora_apertura)
    end = datetime.combine(date.today(), settings.hora_cierre)
    interval = timedelta(minutes=settings.intervalo_minutos)

    slots: list[time] = []
    current = start
    while current + timedelta(minutes=duration) <= end:
        slots.append(current.time().replace(second=0, microsecond=0))
        current += interval
    return slots


def is_slot_inside_business_hours(target_date: date, start_time: time, duration_minutes: int) -> bool:
    settings = get_business_settings()
    allowed_slots = build_daily_slots(settings, duration_minutes)
    if start_time not in allowed_slots:
        return False

    start_dt = datetime.combine(target_date, start_time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    opening_dt = datetime.combine(target_date, settings.hora_apertura)
    closing_dt = datetime.combine(target_date, settings.hora_cierre)
    return opening_dt <= start_dt and end_dt <= closing_dt


def appointment_has_conflict(
    target_date: date,
    start_time: time,
    duration_minutes: int,
    barber_id: int,
    exclude_appointment_id: int | None = None,
) -> bool:
    appointment_query = Appointment.query.filter(
        Appointment.fecha == target_date,
        Appointment.barbero_id == barber_id,
        Appointment.estado != "cancelada",
    )

    if exclude_appointment_id:
        appointment_query = appointment_query.filter(Appointment.id != exclude_appointment_id)

    for appointment in appointment_query.all():
        if time_ranges_overlap(start_time, duration_minutes, appointment.hora, appointment.duracion_minutos):
            return True

    block_query = BlockedSchedule.query.filter(
        BlockedSchedule.fecha == target_date,
        or_(BlockedSchedule.barbero_id == barber_id, BlockedSchedule.barbero_id.is_(None)),
    )

    for block in block_query.all():
        block_duration = (
            datetime.combine(target_date, block.hora_fin) - datetime.combine(target_date, block.hora_inicio)
        ).seconds // 60
        if time_ranges_overlap(start_time, duration_minutes, block.hora_inicio, block_duration):
            return True

    return False


def get_available_barbers_for_slot(
    target_date: date,
    start_time: time,
    duration_minutes: int,
    preferred_barber_id: int | None = None,
    exclude_appointment_id: int | None = None,
) -> list[Barber]:
    if not is_slot_inside_business_hours(target_date, start_time, duration_minutes):
        return []

    if target_date < date.today():
        return []

    now = datetime.now()
    if target_date == now.date() and datetime.combine(target_date, start_time) <= now:
        return []

    query = Barber.query.filter_by(activo=True).order_by(Barber.nombre.asc())

    if preferred_barber_id:
        barber = query.filter(Barber.id == preferred_barber_id).first()
        candidates = [barber] if barber else []
    else:
        candidates = query.all()

    available: list[Barber] = []
    for barber in candidates:
        if barber is None:
            continue
        if not appointment_has_conflict(
            target_date,
            start_time,
            duration_minutes,
            barber.id,
            exclude_appointment_id=exclude_appointment_id,
        ):
            available.append(barber)
    return available


def select_barber_for_booking(
    target_date: date,
    start_time: time,
    duration_minutes: int,
    preferred_barber_id: int | None = None,
    exclude_appointment_id: int | None = None,
) -> Barber | None:
    available = get_available_barbers_for_slot(
        target_date,
        start_time,
        duration_minutes,
        preferred_barber_id=preferred_barber_id,
        exclude_appointment_id=exclude_appointment_id,
    )
    return available[0] if available else None


def build_available_slots(
    target_date: date,
    duration_minutes: int,
    preferred_barber_id: int | None = None,
    exclude_appointment_id: int | None = None,
) -> list[dict[str, Any]]:
    settings = get_business_settings()
    slots = build_daily_slots(settings, duration_minutes)
    available_slots: list[dict[str, Any]] = []

    for slot in slots:
        available_barbers = get_available_barbers_for_slot(
            target_date,
            slot,
            duration_minutes,
            preferred_barber_id=preferred_barber_id,
            exclude_appointment_id=exclude_appointment_id,
        )
        if not available_barbers:
            continue

        primary_barber = available_barbers[0]
        available_slots.append(
            {
                "value": slot.strftime("%H:%M"),
                "label": format_time(slot),
                "barber_name": primary_barber.nombre,
                "barber_id": primary_barber.id,
                "available_barbers": [barber.id for barber in available_barbers],
            }
        )

    return available_slots


def build_calendar_days(
    month_value: str,
    duration_minutes: int,
    preferred_barber_id: int | None = None,
) -> list[dict[str, Any]]:
    parsed = parse_month(month_value)
    if parsed is None:
        today = date.today()
        year, month = today.year, today.month
    else:
        year, month = parsed

    first_weekday, total_days = monthrange(year, month)
    today = date.today()
    day_rows: list[dict[str, Any]] = []

    for day_number in range(1, total_days + 1):
        current_date = date(year, month, day_number)
        is_past = current_date < today
        slots_count = 0
        if not is_past:
            slots_count = len(
                build_available_slots(
                    current_date,
                    duration_minutes,
                    preferred_barber_id=preferred_barber_id,
                )
            )

        day_rows.append(
            {
                "date": current_date.isoformat(),
                "day": day_number,
                "available": slots_count > 0,
                "disabled": is_past,
                "slots_count": slots_count,
                "is_today": current_date == today,
            }
        )

    return [
        {
            "first_weekday": first_weekday,
            "days": day_rows,
            "month_label": datetime(year, month, 1).strftime("%B %Y"),
            "month_value": f"{year:04d}-{month:02d}",
        }
    ]


def build_agenda_rows(target_date: date) -> list[dict[str, Any]]:
    settings = get_business_settings()
    appointments = (
        Appointment.query.filter_by(fecha=target_date)
        .order_by(Appointment.hora.asc(), Appointment.nombre_cliente.asc())
        .all()
    )
    blocks = (
        BlockedSchedule.query.filter_by(fecha=target_date)
        .order_by(BlockedSchedule.hora_inicio.asc())
        .all()
    )

    rows: list[dict[str, Any]] = []
    for slot in build_daily_slots(settings, settings.intervalo_minutos):
        items = []
        for appointment in appointments:
            if appointment.hora == slot:
                items.append(
                    {
                        "kind": "appointment",
                        "title": f"{appointment.nombre_cliente} - {appointment.servicio.nombre}",
                        "subtitle": f"{appointment.barbero.nombre} - {appointment.telefono}",
                        "status": appointment.estado,
                        "url": f"/admin/appointments/{appointment.id}/edit",
                    }
                )

        for block in blocks:
            if block.hora_inicio == slot:
                items.append(
                    {
                        "kind": "block",
                        "title": block.motivo,
                        "subtitle": block.barbero.nombre if block.barbero else "Bloqueo general",
                        "status": "bloqueado",
                        "url": "/admin/blocked-slots",
                    }
                )

        rows.append({"label": format_time(slot), "entries": items})

    return rows


def build_whatsapp_confirmation_link(settings: BusinessSettings, appointment: Appointment) -> str:
    business_phone = build_whatsapp_target(settings.telefono_whatsapp)
    if not business_phone:
        return ""

    message = quote(
        "\n".join(
            [
                f"Hola, soy {appointment.nombre_cliente}. Confirmo mi cita en {settings.nombre_negocio} \U0001f488",
                f"Servicio: {appointment.servicio.nombre}",
                f"Barbero: {appointment.barbero.nombre}",
                f"Fecha: {format_date(appointment.fecha)}",
                f"Hora: {format_time(appointment.hora)}",
                "Gracias.",
            ]
        )
    )
    return f"https://wa.me/{business_phone}?text={message}"


def build_reusable_whatsapp_link(settings: BusinessSettings, booking_url: str | None = None) -> str:
    business_phone = build_whatsapp_target(settings.telefono_whatsapp)
    if not business_phone:
        return ""

    lines = [
        "Hola. Bienvenido a Ronald BarberShop.",
        "Agenda tu cita aqui:",
    ]
    if booking_url:
        lines.append(booking_url)
    else:
        lines.append("https://tudominio.com/agendar")

    text = quote("\n".join(lines))
    return f"https://wa.me/{business_phone}?text={text}"
