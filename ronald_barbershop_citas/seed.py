from __future__ import annotations

from datetime import date, time, timedelta

from .models import AdminUser, Appointment, Barber, BlockedSchedule, BusinessSettings, Client, Service, db


DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "Admin123*"
DEFAULT_WHATSAPP = "809-984-6863"

DEFAULT_SERVICES = [
    {
        "nombre": "Corte de cabello",
        "descripcion": "Corte premium con acabado limpio y estilo actual.",
        "precio": 12,
        "duracion_minutos": 45,
    },
    {
        "nombre": "Barba",
        "descripcion": "Perfilado, recorte y definicion profesional.",
        "precio": 8,
        "duracion_minutos": 30,
    },
    {
        "nombre": "Corte + barba",
        "descripcion": "Servicio completo para una imagen impecable.",
        "precio": 18,
        "duracion_minutos": 60,
    },
    {
        "nombre": "Cerquillo",
        "descripcion": "Mantenimiento rapido para conservar tu look.",
        "precio": 6,
        "duracion_minutos": 20,
    },
    {
        "nombre": "Diseno",
        "descripcion": "Lineas y detalles creativos con precision.",
        "precio": 10,
        "duracion_minutos": 30,
    },
    {
        "nombre": "Lavado",
        "descripcion": "Lavado y preparacion capilar antes o despues del corte.",
        "precio": 5,
        "duracion_minutos": 15,
    },
    {
        "nombre": "Servicio premium",
        "descripcion": "Experiencia premium completa con corte, barba y detalle final.",
        "precio": 25,
        "duracion_minutos": 75,
    },
]

DEFAULT_BARBERS = [
    {
        "nombre": "Ronald",
        "especialidad": "Fade premium y cortes ejecutivos",
        "telefono": "8095550101",
        "bio": "Especialista en precision, fades modernos y acabado premium.",
        "foto": "",
    },
    {
        "nombre": "Luis",
        "especialidad": "Barba y diseno",
        "telefono": "8095550202",
        "bio": "Experto en perfilado, diseno y combinaciones corte mas barba.",
        "foto": "",
    },
    {
        "nombre": "Carlos",
        "especialidad": "Estilo clasico y atencion rapida",
        "telefono": "8095550303",
        "bio": "Ideal para clientes que buscan puntualidad y look elegante.",
        "foto": "",
    },
]


def seed_database() -> None:
    settings = BusinessSettings.query.first()
    if settings is None:
        settings = BusinessSettings(
            nombre_negocio="Ronald BarberShop",
            eslogan="Precision, estilo y presencia en cada corte.",
            telefono_whatsapp=DEFAULT_WHATSAPP,
            direccion="Santo Domingo, Republica Dominicana",
            intervalo_minutos=30,
        )
        db.session.add(settings)
    else:
        if not settings.telefono_whatsapp or settings.telefono_whatsapp == "18095551234":
            settings.telefono_whatsapp = DEFAULT_WHATSAPP

    admin = AdminUser.query.filter_by(username=DEFAULT_ADMIN_USERNAME).first()
    if admin is None:
        admin = AdminUser(username=DEFAULT_ADMIN_USERNAME, nombre_completo="Administrador Ronald")
        admin.set_password(DEFAULT_ADMIN_PASSWORD)
        db.session.add(admin)
    elif admin.check_password("Admin12345"):
        admin.set_password(DEFAULT_ADMIN_PASSWORD)

    for service_data in DEFAULT_SERVICES:
        service = Service.query.filter_by(nombre=service_data["nombre"]).first()
        if service is None:
            service = Service(**service_data, activo=True)
            db.session.add(service)

    for barber_data in DEFAULT_BARBERS:
        barber = Barber.query.filter_by(nombre=barber_data["nombre"]).first()
        if barber is None:
            barber = Barber(**barber_data, activo=True)
            db.session.add(barber)
        else:
            barber.telefono = barber.telefono or barber_data["telefono"]
            barber.bio = barber.bio or barber_data["bio"]
            barber.especialidad = barber.especialidad or barber_data["especialidad"]

    db.session.commit()

    if Client.query.count() == 0 and Appointment.query.count() == 0:
        clients = [
            Client(nombre="Carlos Mejia", telefono="8095551010", notas="Prefiere degradado bajo."),
            Client(nombre="Andres Ventura", telefono="8295552020"),
            Client(nombre="Miguel Santos", telefono="8495553030"),
        ]
        db.session.add_all(clients)
        db.session.flush()

        services = {service.nombre: service for service in Service.query.all()}
        barbers = {barber.nombre: barber for barber in Barber.query.all()}
        today = date.today()
        tomorrow = today + timedelta(days=1)

        db.session.add_all(
            [
                Appointment(
                    cliente_id=clients[0].id,
                    servicio_id=services["Corte de cabello"].id,
                    barbero_id=barbers["Ronald"].id,
                    nombre_cliente=clients[0].nombre,
                    telefono=clients[0].telefono,
                    fecha=today,
                    hora=time(15, 0),
                    duracion_minutos=services["Corte de cabello"].duracion_minutos,
                    estado="confirmada",
                    nota="Cliente frecuente.",
                ),
                Appointment(
                    cliente_id=clients[1].id,
                    servicio_id=services["Barba"].id,
                    barbero_id=barbers["Luis"].id,
                    nombre_cliente=clients[1].nombre,
                    telefono=clients[1].telefono,
                    fecha=today,
                    hora=time(16, 0),
                    duracion_minutos=services["Barba"].duracion_minutos,
                    estado="pendiente",
                ),
                Appointment(
                    cliente_id=clients[2].id,
                    servicio_id=services["Servicio premium"].id,
                    barbero_id=barbers["Carlos"].id,
                    nombre_cliente=clients[2].nombre,
                    telefono=clients[2].telefono,
                    fecha=tomorrow,
                    hora=time(11, 0),
                    duracion_minutos=services["Servicio premium"].duracion_minutos,
                    estado="pendiente",
                    nota="Solicita un look ejecutivo con barba definida.",
                ),
            ]
        )

    if BlockedSchedule.query.count() == 0:
        tomorrow = date.today() + timedelta(days=1)
        db.session.add(
            BlockedSchedule(
                fecha=tomorrow,
                hora_inicio=time(13, 0),
                hora_fin=time(14, 0),
                motivo="Pausa de almuerzo",
            )
        )

    db.session.commit()
