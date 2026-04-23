from __future__ import annotations

from datetime import date, datetime, time, timedelta

from .models import (
    AdminUser,
    AppearanceSettings,
    Appointment,
    Barber,
    BlockedSchedule,
    BusinessSettings,
    Client,
    HaircutStyle,
    LocationSettings,
    Promotion,
    Service,
    SocialLink,
    Tenant,
    Testimonial,
    db,
)
from .utils import slugify


DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "Admin123*"
DEFAULT_CLIENT_PASSWORD = "Cliente123*"
DEFAULT_WHATSAPP = "809-984-6863"
DEFAULT_DOMAIN = "https://ronald-barbershop.onrender.com"

DEFAULT_SERVICES = [
    {
        "nombre": "Corte clasico",
        "descripcion": "Acabado limpio, simetria precisa y presencia impecable.",
        "precio": 12,
        "duracion_minutos": 40,
        "categoria": "Cortes clasicos",
        "image_url": "",
    },
    {
        "nombre": "Fade",
        "descripcion": "Degradado moderno con transicion premium y linea definida.",
        "precio": 15,
        "duracion_minutos": 45,
        "categoria": "Fades",
        "image_url": "",
    },
    {
        "nombre": "Low fade",
        "descripcion": "Fade bajo con apariencia elegante para diario o ejecutivo.",
        "precio": 16,
        "duracion_minutos": 50,
        "categoria": "Fades",
        "image_url": "",
    },
    {
        "nombre": "Mid fade",
        "descripcion": "Balance perfecto entre presencia urbana y pulcritud.",
        "precio": 16,
        "duracion_minutos": 50,
        "categoria": "Fades",
        "image_url": "",
    },
    {
        "nombre": "High fade",
        "descripcion": "Contraste marcado con look contemporaneo y fuerte.",
        "precio": 17,
        "duracion_minutos": 50,
        "categoria": "Fades",
        "image_url": "",
    },
    {
        "nombre": "Taper fade",
        "descripcion": "Taper refinado ideal para estilo limpio y versatil.",
        "precio": 15,
        "duracion_minutos": 45,
        "categoria": "Fades",
        "image_url": "",
    },
    {
        "nombre": "Barba",
        "descripcion": "Perfilado, definicion y limpieza profesional.",
        "precio": 8,
        "duracion_minutos": 30,
        "categoria": "Barba",
        "image_url": "",
    },
    {
        "nombre": "Corte + barba",
        "descripcion": "Servicio integral para una imagen premium completa.",
        "precio": 22,
        "duracion_minutos": 70,
        "categoria": "Combo",
        "image_url": "",
    },
    {
        "nombre": "Diseno",
        "descripcion": "Lineas personalizadas y detalles visuales con precision.",
        "precio": 10,
        "duracion_minutos": 25,
        "categoria": "Detalles",
        "image_url": "",
    },
    {
        "nombre": "Cejas",
        "descripcion": "Definicion sutil y armonia para completar el look.",
        "precio": 5,
        "duracion_minutos": 15,
        "categoria": "Detalles",
        "image_url": "",
    },
    {
        "nombre": "Lavado",
        "descripcion": "Preparacion o cierre del servicio con frescura y limpieza.",
        "precio": 5,
        "duracion_minutos": 15,
        "categoria": "Complementos",
        "image_url": "",
    },
    {
        "nombre": "Coloracion",
        "descripcion": "Color profesional para renovar estilo y personalidad.",
        "precio": 20,
        "duracion_minutos": 60,
        "categoria": "Color",
        "image_url": "",
    },
    {
        "nombre": "Linea",
        "descripcion": "Mantenimiento rapido de contornos y definicion.",
        "precio": 6,
        "duracion_minutos": 15,
        "categoria": "Detalles",
        "image_url": "",
    },
    {
        "nombre": "Servicio premium",
        "descripcion": "Experiencia completa con corte, barba, detalle y acabado superior.",
        "precio": 28,
        "duracion_minutos": 80,
        "categoria": "Premium",
        "image_url": "",
    },
]

DEFAULT_BARBERS = [
    {
        "nombre": "Ronald",
        "especialidad": "Fades premium y cortes ejecutivos",
        "telefono": "8095550101",
        "bio": "Especialista en precision, transiciones limpias y atencion premium.",
        "foto": "",
    },
    {
        "nombre": "Luis",
        "especialidad": "Barba, lineas y disenos",
        "telefono": "8095550202",
        "bio": "Experto en perfilado, barba y detalles creativos.",
        "foto": "",
    },
    {
        "nombre": "Carlos",
        "especialidad": "Estilo clasico y look urbano",
        "telefono": "8095550303",
        "bio": "Ideal para clientes que buscan puntualidad y un look elegante.",
        "foto": "",
    },
]

DEFAULT_CLIENTS = [
    {
        "nombre": "Carlos Mejia",
        "username": "carlosmejia",
        "email": "carlos@ronaldbarbershop.local",
        "telefono": "8095551010",
        "notas": "Prefiere low fade con textura.",
    },
    {
        "nombre": "Andres Ventura",
        "username": "andresventura",
        "email": "andres@ronaldbarbershop.local",
        "telefono": "8295552020",
        "notas": "Solicita aviso por WhatsApp antes de la cita.",
    },
    {
        "nombre": "Miguel Santos",
        "username": "miguelsantos",
        "email": "miguel@ronaldbarbershop.local",
        "telefono": "8495553030",
        "notas": "Cliente premium frecuente.",
    },
]

DEFAULT_STYLES = [
    {
        "name": "Buzz cut",
        "description": "Minimalista, limpio y masculino. Ideal para mantenimiento simple.",
        "trending": True,
        "suggested_price": 12,
        "service_name": "Corte clasico",
    },
    {
        "name": "Crew cut",
        "description": "Corte estructurado con apariencia profesional y fresca.",
        "trending": False,
        "suggested_price": 13,
        "service_name": "Corte clasico",
    },
    {
        "name": "Fade clasico",
        "description": "Transicion premium con acabado suave y limpio.",
        "trending": True,
        "suggested_price": 15,
        "service_name": "Fade",
    },
    {
        "name": "Low fade con diseno",
        "description": "Fade bajo con lineas laterales para un look moderno.",
        "trending": True,
        "suggested_price": 18,
        "service_name": "Low fade",
    },
    {
        "name": "French crop",
        "description": "Textura al frente y perfil pulcro con mucho estilo.",
        "trending": True,
        "suggested_price": 16,
        "service_name": "Mid fade",
    },
    {
        "name": "Pompadour",
        "description": "Volumen superior con presencia fuerte y elegante.",
        "trending": False,
        "suggested_price": 19,
        "service_name": "Servicio premium",
    },
]

DEFAULT_PROMOTIONS = [
    {
        "title": "Semana del caballero",
        "description": "Descuento especial para cortes premium y combos de barba.",
        "discount_percentage": 15,
        "special_price": None,
        "start_date": date.today(),
        "end_date": date.today() + timedelta(days=15),
        "image_url": "",
        "active": True,
    },
    {
        "title": "Combo ejecutivo",
        "description": "Corte + barba con atencion prioritaria y detalle final.",
        "discount_percentage": 10,
        "special_price": 20,
        "start_date": date.today(),
        "end_date": date.today() + timedelta(days=30),
        "image_url": "",
        "active": True,
    },
]

DEFAULT_TESTIMONIALS = [
    {
        "client_name": "Daniel Rosario",
        "comment": "La experiencia se siente premium desde que reservas hasta que sales del local.",
        "rating": 5,
    },
    {
        "client_name": "Jose Miguel",
        "comment": "Puntualidad, buen ambiente y cortes modernos. Muy recomendado.",
        "rating": 5,
    },
]

DEFAULT_SOCIAL_LINKS = [
    ("Instagram", "Instagram", "https://instagram.com/ronaldbarbershop"),
    ("Facebook", "Facebook", "https://facebook.com/ronaldbarbershop"),
    ("TikTok", "TikTok", "https://tiktok.com/@ronaldbarbershop"),
]

DEFAULT_PUBLIC_TEXTS = {
    "description": "Barberia urbana premium con reservas online, WhatsApp y una experiencia visual lista para clientes modernos.",
    "hero_badge_text": "Ronald premium experience",
    "hero_title": "Ronald BarberShop",
    "hero_description": (
        "Reserva online, confirma por WhatsApp y llega directo a una experiencia "
        "de barberia urbana, precisa y profesional."
    ),
    "services_title": "Servicios premium con precios claros",
    "services_description": (
        "Cortes, fades, barba y detalles disenados para que cada cliente reserve "
        "con confianza."
    ),
    "styles_title": "Estilos de cortes que inspiran tu proximo look",
    "styles_description": (
        "Explora tendencias, precios sugeridos y looks disponibles antes de elegir "
        "tu cita."
    ),
    "promotions_title": "Promociones activas para reservar hoy",
    "promotions_description": (
        "Ofertas visibles y faciles de compartir para impulsar visitas desde WhatsApp."
    ),
    "location_title": "Encuentranos facilmente",
    "location_description": "Ubicacion, referencia y ruta lista para que llegues sin perder tiempo.",
    "testimonials_title": "Clientes que recomiendan la experiencia",
    "testimonials_description": "Prueba social para que nuevos visitantes reserven con confianza.",
    "final_cta_title": "Listo para reservar en",
    "final_cta_description": (
        "Elige servicio, fecha y hora. Nosotros nos encargamos de que tu experiencia "
        "empiece con presencia y puntualidad."
    ),
}


def _get_or_create_tenant() -> Tenant:
    tenant = Tenant.query.filter_by(slug="ronald-barbershop").first()
    if tenant is None:
        tenant = Tenant(
            name="Ronald BarberShop",
            slug=slugify("Ronald BarberShop"),
            domain_url=DEFAULT_DOMAIN,
            plan_name="Trial",
            trial_ends_at=datetime.utcnow() + timedelta(days=14),
            active=True,
        )
        db.session.add(tenant)
        db.session.commit()
    return tenant


def _normalize_existing_records(tenant: Tenant) -> None:
    for admin in AdminUser.query.all():
        if admin.tenant_id is None:
            admin.tenant_id = tenant.id

    for client in Client.query.all():
        if client.tenant_id is None:
            client.tenant_id = tenant.id
        if not client.username:
            client.username = f"cliente{client.id}"
        if client.email is None and client.username:
            client.email = f"{client.username}@ronaldbarbershop.local"
        if not client.password_hash:
            client.set_password(DEFAULT_CLIENT_PASSWORD)
        if client.activo is None:
            client.activo = True

    for service in Service.query.all():
        if service.tenant_id is None:
            service.tenant_id = tenant.id
        if not service.categoria:
            service.categoria = "General"

    for barber in Barber.query.all():
        if barber.tenant_id is None:
            barber.tenant_id = tenant.id

    for appointment in Appointment.query.all():
        if appointment.tenant_id is None:
            appointment.tenant_id = tenant.id

    for block in BlockedSchedule.query.all():
        if block.tenant_id is None:
            block.tenant_id = tenant.id


def seed_database() -> None:
    tenant = _get_or_create_tenant()
    _normalize_existing_records(tenant)
    db.session.commit()

    settings = BusinessSettings.query.filter_by(tenant_id=tenant.id).first()
    if settings is None:
        settings = BusinessSettings(
            tenant_id=tenant.id,
            business_name="Ronald BarberShop",
            slogan="Precision, estilo y presencia en cada corte.",
            phone=DEFAULT_WHATSAPP,
            whatsapp=DEFAULT_WHATSAPP,
            email="info@ronaldbarbershop.com",
            address="Av. Principal, Santo Domingo, Republica Dominicana",
            location_reference="Frente a la plaza comercial del sector",
            city="Santo Domingo",
            province_state="Distrito Nacional",
            country="Republica Dominicana",
            google_maps_url="https://maps.google.com/?q=Ronald+BarberShop+Santo+Domingo",
            logo_url="",
            logo_path="img/ronald-logo.png",
            banner_url="",
            primary_color="#d2b271",
            secondary_color="#7f1f1f",
            accent_color="#0ea5e9",
            button_color="#d2b271",
            highlight_color="#f6c36d",
            visual_theme="urban_gold",
            default_language="es",
            currency_code="USD",
            currency_symbol="US$",
            working_days="Lunes a Sabado",
            show_language_selector=True,
            show_map=True,
            show_gallery_styles=True,
            show_promotions=True,
            show_testimonials=True,
            show_banner=True,
            show_how_to_get=True,
            **DEFAULT_PUBLIC_TEXTS,
        )
        db.session.add(settings)
    else:
        settings.business_name = settings.business_name or "Ronald BarberShop"
        if not settings.logo_path and not settings.logo_url:
            settings.logo_path = "img/ronald-logo.png"
        settings.whatsapp = settings.whatsapp or DEFAULT_WHATSAPP
        settings.phone = settings.phone or DEFAULT_WHATSAPP
        settings.google_maps_url = settings.google_maps_url or "https://maps.google.com/?q=Ronald+BarberShop+Santo+Domingo"
        settings.primary_color = settings.primary_color or "#d2b271"
        settings.secondary_color = settings.secondary_color or "#7f1f1f"
        settings.accent_color = settings.accent_color or "#0ea5e9"
        settings.button_color = settings.button_color or settings.primary_color or "#d2b271"
        settings.highlight_color = settings.highlight_color or "#f6c36d"
        settings.visual_theme = settings.visual_theme or "urban_gold"
        settings.default_language = settings.default_language or "es"
        settings.currency_code = settings.currency_code or "USD"
        settings.currency_symbol = settings.currency_symbol or "US$"
        settings.show_language_selector = True if settings.show_language_selector is None else settings.show_language_selector
        settings.show_map = True if settings.show_map is None else settings.show_map
        settings.show_gallery_styles = True if settings.show_gallery_styles is None else settings.show_gallery_styles
        settings.show_promotions = True if settings.show_promotions is None else settings.show_promotions
        settings.show_testimonials = True if settings.show_testimonials is None else settings.show_testimonials
        settings.show_banner = True if settings.show_banner is None else settings.show_banner
        settings.show_how_to_get = True if settings.show_how_to_get is None else settings.show_how_to_get
        for field, value in DEFAULT_PUBLIC_TEXTS.items():
            if not getattr(settings, field, None):
                setattr(settings, field, value)

    location = LocationSettings.query.filter_by(tenant_id=tenant.id).first()
    if location is None:
        location = LocationSettings(
            tenant_id=tenant.id,
            address=settings.address,
            reference=settings.location_reference,
            latitude="18.4861",
            longitude="-69.9312",
            google_maps_url=settings.google_maps_url,
            show_map=True,
        )
        db.session.add(location)

    appearance = AppearanceSettings.query.filter_by(tenant_id=tenant.id).first()
    if appearance is None:
        appearance = AppearanceSettings(
            tenant_id=tenant.id,
            featured_image_url="",
            visual_style="urban_gold",
            theme_name="Barberia urbana",
            button_style="pill_glow",
            card_style="glass",
            border_style="rounded",
            header_style="floating",
            footer_style="premium",
            enable_animations=True,
            urban_mode=True,
            dark_mode=True,
            show_services=True,
            show_barbers=True,
            show_gallery_styles=True,
            show_promotions=True,
            show_testimonials=True,
        )
        db.session.add(appearance)
    else:
        appearance.visual_style = appearance.visual_style or "urban_gold"
        appearance.theme_name = appearance.theme_name or "Barberia urbana"
        appearance.button_style = appearance.button_style or "pill_glow"
        appearance.card_style = appearance.card_style or "glass"
        appearance.border_style = appearance.border_style or "rounded"
        appearance.header_style = appearance.header_style or "floating"
        appearance.footer_style = appearance.footer_style or "premium"
        appearance.enable_animations = True if appearance.enable_animations is None else appearance.enable_animations
        appearance.urban_mode = True if appearance.urban_mode is None else appearance.urban_mode
        appearance.dark_mode = True if appearance.dark_mode is None else appearance.dark_mode

    admin = AdminUser.query.filter_by(username=DEFAULT_ADMIN_USERNAME).first()
    if admin is None:
        admin = AdminUser(
            tenant_id=tenant.id,
            username=DEFAULT_ADMIN_USERNAME,
            nombre_completo="Administrador Ronald",
        )
        admin.set_password(DEFAULT_ADMIN_PASSWORD)
        db.session.add(admin)
    else:
        admin.tenant_id = admin.tenant_id or tenant.id
        if admin.check_password("Admin12345"):
            admin.set_password(DEFAULT_ADMIN_PASSWORD)

    for service_data in DEFAULT_SERVICES:
        service = Service.query.filter_by(tenant_id=tenant.id, nombre=service_data["nombre"]).first()
        if service is None:
            service = Service(tenant_id=tenant.id, activo=True, **service_data)
            db.session.add(service)
        else:
            service.descripcion = service.descripcion or service_data["descripcion"]
            service.precio = service.precio or service_data["precio"]
            service.duracion_minutos = service.duracion_minutos or service_data["duracion_minutos"]
            service.categoria = service.categoria or service_data["categoria"]
            service.image_url = service.image_url or service_data["image_url"]

    for barber_data in DEFAULT_BARBERS:
        barber = Barber.query.filter_by(tenant_id=tenant.id, nombre=barber_data["nombre"]).first()
        if barber is None:
            barber = Barber(tenant_id=tenant.id, activo=True, **barber_data)
            db.session.add(barber)
        else:
            barber.telefono = barber.telefono or barber_data["telefono"]
            barber.bio = barber.bio or barber_data["bio"]
            barber.especialidad = barber.especialidad or barber_data["especialidad"]

    for client_data in DEFAULT_CLIENTS:
        client = Client.query.filter_by(telefono=client_data["telefono"]).first()
        if client is None:
            client = Client(
                tenant_id=tenant.id,
                nombre=client_data["nombre"],
                username=client_data["username"],
                email=client_data["email"],
                telefono=client_data["telefono"],
                notas=client_data["notas"] or None,
                activo=True,
            )
            client.set_password(DEFAULT_CLIENT_PASSWORD)
            db.session.add(client)
        else:
            client.tenant_id = client.tenant_id or tenant.id
            client.nombre = client.nombre or client_data["nombre"]
            client.username = client.username or client_data["username"]
            client.email = client.email or client_data["email"]
            client.notas = client.notas or client_data["notas"] or None
            client.activo = True if client.activo is None else client.activo
            if not client.password_hash:
                client.set_password(DEFAULT_CLIENT_PASSWORD)

    db.session.commit()

    for platform, label, url in DEFAULT_SOCIAL_LINKS:
        social = SocialLink.query.filter_by(tenant_id=tenant.id, platform=platform).first()
        if social is None:
            db.session.add(
                SocialLink(
                    tenant_id=tenant.id,
                    platform=platform,
                    label=label,
                    url=url,
                    active=True,
                )
            )

    for testimonial_data in DEFAULT_TESTIMONIALS:
        testimonial = Testimonial.query.filter_by(
            tenant_id=tenant.id,
            client_name=testimonial_data["client_name"],
        ).first()
        if testimonial is None:
            db.session.add(
                Testimonial(
                    tenant_id=tenant.id,
                    visible=True,
                    **testimonial_data,
                )
            )

    services = {service.nombre: service for service in Service.query.filter_by(tenant_id=tenant.id).all()}
    for style_data in DEFAULT_STYLES:
        style = HaircutStyle.query.filter_by(tenant_id=tenant.id, name=style_data["name"]).first()
        if style is None:
            service = services.get(style_data["service_name"])
            db.session.add(
                HaircutStyle(
                    tenant_id=tenant.id,
                    service_id=service.id if service else None,
                    name=style_data["name"],
                    description=style_data["description"],
                    image_url="",
                    trending=style_data["trending"],
                    suggested_price=style_data["suggested_price"],
                    active=True,
                )
            )

    for promotion_data in DEFAULT_PROMOTIONS:
        promotion = Promotion.query.filter_by(tenant_id=tenant.id, title=promotion_data["title"]).first()
        if promotion is None:
            db.session.add(Promotion(tenant_id=tenant.id, **promotion_data))

    db.session.commit()

    if Appointment.query.filter_by(tenant_id=tenant.id).count() == 0:
        clients = {client.telefono: client for client in Client.query.filter_by(tenant_id=tenant.id).all()}
        barbers = {barber.nombre: barber for barber in Barber.query.filter_by(tenant_id=tenant.id).all()}
        today = date.today()
        tomorrow = today + timedelta(days=1)

        db.session.add_all(
            [
                Appointment(
                    tenant_id=tenant.id,
                    cliente_id=clients["8095551010"].id,
                    servicio_id=services["Fade"].id,
                    barbero_id=barbers["Ronald"].id,
                    nombre_cliente=clients["8095551010"].nombre,
                    telefono=clients["8095551010"].telefono,
                    fecha=today,
                    hora=time(15, 0),
                    duracion_minutos=services["Fade"].duracion_minutos,
                    estado="confirmada",
                    nota="Cliente frecuente.",
                ),
                Appointment(
                    tenant_id=tenant.id,
                    cliente_id=clients["8295552020"].id,
                    servicio_id=services["Barba"].id,
                    barbero_id=barbers["Luis"].id,
                    nombre_cliente=clients["8295552020"].nombre,
                    telefono=clients["8295552020"].telefono,
                    fecha=today,
                    hora=time(16, 0),
                    duracion_minutos=services["Barba"].duracion_minutos,
                    estado="pendiente",
                ),
                Appointment(
                    tenant_id=tenant.id,
                    cliente_id=clients["8495553030"].id,
                    servicio_id=services["Servicio premium"].id,
                    barbero_id=barbers["Carlos"].id,
                    nombre_cliente=clients["8495553030"].nombre,
                    telefono=clients["8495553030"].telefono,
                    fecha=tomorrow,
                    hora=time(11, 0),
                    duracion_minutos=services["Servicio premium"].duracion_minutos,
                    estado="pendiente",
                    nota="Solicita un look ejecutivo con barba definida.",
                ),
            ]
        )

    if BlockedSchedule.query.filter_by(tenant_id=tenant.id).count() == 0:
        tomorrow = date.today() + timedelta(days=1)
        db.session.add(
            BlockedSchedule(
                tenant_id=tenant.id,
                fecha=tomorrow,
                hora_inicio=time(13, 0),
                hora_fin=time(14, 0),
                motivo="Pausa de almuerzo",
            )
        )

    db.session.commit()
