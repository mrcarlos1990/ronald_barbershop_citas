from __future__ import annotations

from datetime import date, datetime, timedelta

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class TimestampMixin:
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def created_at(self):
        return self.fecha_creacion


class Tenant(db.Model, TimestampMixin):
    __tablename__ = "tenants"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    domain_url = db.Column(db.String(255))
    plan_name = db.Column(db.String(80), nullable=False, default="Trial")
    trial_ends_at = db.Column(db.DateTime)
    active = db.Column(db.Boolean, nullable=False, default=True)

    admin_users = db.relationship("AdminUser", back_populates="tenant", lazy="dynamic")
    clients = db.relationship("Client", back_populates="tenant", lazy="dynamic")
    services = db.relationship("Service", back_populates="tenant", lazy="dynamic")
    barbers = db.relationship("Barber", back_populates="tenant", lazy="dynamic")
    appointments = db.relationship("Appointment", back_populates="tenant", lazy="dynamic")
    blocked_schedules = db.relationship("BlockedSchedule", back_populates="tenant", lazy="dynamic")
    business_settings = db.relationship("BusinessSettings", back_populates="tenant", uselist=False)
    haircut_styles = db.relationship("HaircutStyle", back_populates="tenant", lazy="dynamic")
    promotions = db.relationship("Promotion", back_populates="tenant", lazy="dynamic")
    location_settings = db.relationship("LocationSettings", back_populates="tenant", uselist=False)
    appearance_settings = db.relationship("AppearanceSettings", back_populates="tenant", uselist=False)
    social_links = db.relationship("SocialLink", back_populates="tenant", lazy="dynamic")
    testimonials = db.relationship("Testimonial", back_populates="tenant", lazy="dynamic")


class AdminUser(db.Model, TimestampMixin):
    __tablename__ = "usuarios_admin"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), index=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    nombre_completo = db.Column(db.String(120), nullable=False, default="Administrador")
    password_hash = db.Column(db.String(255), nullable=False)

    tenant = db.relationship("Tenant", back_populates="admin_users")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Client(UserMixin, db.Model, TimestampMixin):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), index=True)
    nombre = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    telefono = db.Column(db.String(30), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    notas = db.Column(db.Text)

    tenant = db.relationship("Tenant", back_populates="clients")
    citas = db.relationship("Appointment", back_populates="cliente", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return bool(self.activo)

    @property
    def total_citas(self):
        return self.citas.count()

    @property
    def ultima_cita(self):
        return self.citas.order_by(Appointment.fecha.desc(), Appointment.hora.desc()).first()


class Service(db.Model, TimestampMixin):
    __tablename__ = "servicios"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), index=True)
    nombre = db.Column(db.String(120), nullable=False, index=True)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False, default=0)
    duracion_minutos = db.Column(db.Integer, nullable=False, default=30)
    image_url = db.Column(db.String(255))
    categoria = db.Column(db.String(80))
    activo = db.Column(db.Boolean, nullable=False, default=True)

    tenant = db.relationship("Tenant", back_populates="services")
    citas = db.relationship("Appointment", back_populates="servicio", lazy="dynamic")
    haircut_styles = db.relationship("HaircutStyle", back_populates="service", lazy="dynamic")


class Barber(db.Model, TimestampMixin):
    __tablename__ = "barberos"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), index=True)
    nombre = db.Column(db.String(120), nullable=False, index=True)
    especialidad = db.Column(db.String(160))
    telefono = db.Column(db.String(30))
    foto = db.Column(db.String(255))
    bio = db.Column(db.Text)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    tenant = db.relationship("Tenant", back_populates="barbers")
    citas = db.relationship("Appointment", back_populates="barbero", lazy="dynamic")
    horarios_bloqueados = db.relationship("BlockedSchedule", back_populates="barbero", lazy="dynamic")


class BusinessSettings(db.Model, TimestampMixin):
    __tablename__ = "business_settings"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    business_name = db.Column(db.String(120), nullable=False, default="Ronald BarberShop")
    slogan = db.Column(db.String(180), nullable=False, default="Precision, estilo y presencia en cada corte.")
    phone = db.Column(db.String(30))
    whatsapp = db.Column(db.String(30), nullable=False, default="809-984-6863")
    email = db.Column(db.String(120))
    address = db.Column(db.String(200), default="Santo Domingo, Republica Dominicana")
    location_reference = db.Column(db.String(200))
    city = db.Column(db.String(120), default="Santo Domingo")
    province_state = db.Column(db.String(120), default="Distrito Nacional")
    country = db.Column(db.String(120), default="Republica Dominicana")
    google_maps_url = db.Column(db.String(255))
    logo_url = db.Column(db.String(255))
    banner_url = db.Column(db.String(255))
    logo_path = db.Column(db.String(255))
    banner_path = db.Column(db.String(255))
    featured_image_path = db.Column(db.String(255))
    primary_color = db.Column(db.String(20), nullable=False, default="#d2b271")
    secondary_color = db.Column(db.String(20), nullable=False, default="#7f1f1f")
    visual_theme = db.Column(db.String(80), nullable=False, default="urban_gold")
    default_language = db.Column(db.String(10), nullable=False, default="es")
    currency_code = db.Column(db.String(10), nullable=False, default="USD")
    currency_symbol = db.Column(db.String(10), nullable=False, default="$")
    working_days = db.Column(db.String(120), default="Lunes a Sabado")
    hora_apertura = db.Column(
        db.Time,
        nullable=False,
        default=lambda: datetime.strptime("09:00", "%H:%M").time(),
    )
    hora_cierre = db.Column(
        db.Time,
        nullable=False,
        default=lambda: datetime.strptime("19:00", "%H:%M").time(),
    )
    intervalo_minutos = db.Column(db.Integer, nullable=False, default=30)
    mensaje_bienvenida = db.Column(
        db.String(220),
        nullable=False,
        default="Hola. Bienvenido a Ronald BarberShop. Agenda tu cita en menos de un minuto.",
    )
    hero_badge_text = db.Column(db.String(180))
    hero_title = db.Column(db.String(220))
    hero_description = db.Column(db.Text)
    services_title = db.Column(db.String(220))
    services_description = db.Column(db.Text)
    styles_title = db.Column(db.String(220))
    styles_description = db.Column(db.Text)
    promotions_title = db.Column(db.String(220))
    promotions_description = db.Column(db.Text)
    location_title = db.Column(db.String(220))
    location_description = db.Column(db.Text)
    testimonials_title = db.Column(db.String(220))
    testimonials_description = db.Column(db.Text)
    final_cta_title = db.Column(db.String(220))
    final_cta_description = db.Column(db.Text)
    show_map = db.Column(db.Boolean, nullable=False, default=True)
    show_gallery_styles = db.Column(db.Boolean, nullable=False, default=True)
    show_promotions = db.Column(db.Boolean, nullable=False, default=True)
    show_testimonials = db.Column(db.Boolean, nullable=False, default=True)
    show_language_selector = db.Column(db.Boolean, nullable=False, default=True)

    tenant = db.relationship("Tenant", back_populates="business_settings")

    @property
    def nombre_negocio(self):
        return self.business_name

    @nombre_negocio.setter
    def nombre_negocio(self, value):
        self.business_name = value

    @property
    def eslogan(self):
        return self.slogan

    @eslogan.setter
    def eslogan(self, value):
        self.slogan = value

    @property
    def telefono_whatsapp(self):
        return self.whatsapp

    @telefono_whatsapp.setter
    def telefono_whatsapp(self, value):
        self.whatsapp = value

    @property
    def direccion(self):
        return self.address

    @direccion.setter
    def direccion(self, value):
        self.address = value

    @property
    def logo_src(self):
        return self.logo_path or self.logo_url

    @property
    def banner_src(self):
        return self.banner_path or self.banner_url

    @property
    def featured_image_src(self):
        return self.featured_image_path


class AppearanceSettings(db.Model, TimestampMixin):
    __tablename__ = "appearance_settings"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    featured_image_url = db.Column(db.String(255))
    visual_style = db.Column(db.String(80), nullable=False, default="urban_gold")
    show_services = db.Column(db.Boolean, nullable=False, default=True)
    show_barbers = db.Column(db.Boolean, nullable=False, default=True)
    show_gallery_styles = db.Column(db.Boolean, nullable=False, default=True)
    show_promotions = db.Column(db.Boolean, nullable=False, default=True)
    show_testimonials = db.Column(db.Boolean, nullable=False, default=True)

    tenant = db.relationship("Tenant", back_populates="appearance_settings")


class LocationSettings(db.Model, TimestampMixin):
    __tablename__ = "location_settings"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    address = db.Column(db.String(200))
    reference = db.Column(db.String(220))
    latitude = db.Column(db.String(50))
    longitude = db.Column(db.String(50))
    google_maps_url = db.Column(db.String(255))
    show_map = db.Column(db.Boolean, nullable=False, default=True)

    tenant = db.relationship("Tenant", back_populates="location_settings")

    @property
    def embed_url(self) -> str | None:
        if self.latitude and self.longitude:
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}&output=embed"
        if self.address:
            return f"https://www.google.com/maps?q={self.address.replace(' ', '+')}&output=embed"
        return None


class SocialLink(db.Model, TimestampMixin):
    __tablename__ = "social_links"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False, index=True)
    platform = db.Column(db.String(60), nullable=False)
    label = db.Column(db.String(80))
    url = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

    tenant = db.relationship("Tenant", back_populates="social_links")


class HaircutStyle(db.Model, TimestampMixin):
    __tablename__ = "haircut_styles"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("servicios.id"))
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    image_path = db.Column(db.String(255))
    trending = db.Column(db.Boolean, nullable=False, default=False)
    suggested_price = db.Column(db.Float)
    active = db.Column(db.Boolean, nullable=False, default=True)

    tenant = db.relationship("Tenant", back_populates="haircut_styles")
    service = db.relationship("Service", back_populates="haircut_styles")

    @property
    def image_src(self):
        return self.image_path or self.image_url


class Promotion(db.Model, TimestampMixin):
    __tablename__ = "promotions"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False, index=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text)
    discount_percentage = db.Column(db.Float, nullable=False, default=0)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    image_url = db.Column(db.String(255))
    image_path = db.Column(db.String(255))
    active = db.Column(db.Boolean, nullable=False, default=True)

    tenant = db.relationship("Tenant", back_populates="promotions")

    @property
    def is_current(self) -> bool:
        today = date.today()
        return self.active and self.start_date <= today <= self.end_date

    @property
    def image_src(self):
        return self.image_path or self.image_url


class Testimonial(db.Model, TimestampMixin):
    __tablename__ = "testimonials"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False, index=True)
    client_name = db.Column(db.String(120), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=5)
    photo_url = db.Column(db.String(255))
    visible = db.Column(db.Boolean, nullable=False, default=True)

    tenant = db.relationship("Tenant", back_populates="testimonials")


class Appointment(db.Model, TimestampMixin):
    __tablename__ = "citas"
    __table_args__ = (
        db.UniqueConstraint("barbero_id", "fecha", "hora", name="uq_cita_inicio_barbero"),
    )

    VALID_STATES = ("pendiente", "confirmada", "completada", "cancelada")

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), index=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    servicio_id = db.Column(db.Integer, db.ForeignKey("servicios.id"), nullable=False)
    barbero_id = db.Column(db.Integer, db.ForeignKey("barberos.id"), nullable=False)
    nombre_cliente = db.Column(db.String(120), nullable=False)
    telefono = db.Column(db.String(30), nullable=False)
    fecha = db.Column(db.Date, nullable=False, index=True)
    hora = db.Column(db.Time, nullable=False)
    duracion_minutos = db.Column(db.Integer, nullable=False, default=30)
    estado = db.Column(db.String(30), nullable=False, default="pendiente", index=True)
    nota = db.Column(db.Text)

    tenant = db.relationship("Tenant", back_populates="appointments")
    cliente = db.relationship("Client", back_populates="citas")
    servicio = db.relationship("Service", back_populates="citas")
    barbero = db.relationship("Barber", back_populates="citas")

    @property
    def hora_fin(self):
        inicio = datetime.combine(self.fecha, self.hora)
        return (inicio + timedelta(minutes=self.duracion_minutos)).time()


class BlockedSchedule(db.Model, TimestampMixin):
    __tablename__ = "horarios_bloqueados"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), index=True)
    barbero_id = db.Column(db.Integer, db.ForeignKey("barberos.id"), nullable=True)
    fecha = db.Column(db.Date, nullable=False, index=True)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    motivo = db.Column(db.String(180), nullable=False, default="Horario no disponible")

    tenant = db.relationship("Tenant", back_populates="blocked_schedules")
    barbero = db.relationship("Barber", back_populates="horarios_bloqueados")
