from __future__ import annotations

from datetime import datetime, timedelta

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class TimestampMixin:
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def created_at(self):
        return self.fecha_creacion


class AdminUser(db.Model, TimestampMixin):
    __tablename__ = "usuarios_admin"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    nombre_completo = db.Column(db.String(120), nullable=False, default="Administrador")
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Client(db.Model, TimestampMixin):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    telefono = db.Column(db.String(30), unique=True, nullable=False)
    notas = db.Column(db.Text)

    citas = db.relationship("Appointment", back_populates="cliente", lazy="dynamic")

    @property
    def total_citas(self):
        return self.citas.count()

    @property
    def ultima_cita(self):
        return self.citas.order_by(Appointment.fecha.desc(), Appointment.hora.desc()).first()


class Service(db.Model, TimestampMixin):
    __tablename__ = "servicios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False, default=0)
    duracion_minutos = db.Column(db.Integer, nullable=False, default=30)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    citas = db.relationship("Appointment", back_populates="servicio", lazy="dynamic")


class Barber(db.Model, TimestampMixin):
    __tablename__ = "barberos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), unique=True, nullable=False)
    especialidad = db.Column(db.String(160))
    telefono = db.Column(db.String(30))
    foto = db.Column(db.String(255))
    bio = db.Column(db.Text)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    citas = db.relationship("Appointment", back_populates="barbero", lazy="dynamic")
    horarios_bloqueados = db.relationship("BlockedSchedule", back_populates="barbero", lazy="dynamic")


class BusinessSettings(db.Model):
    __tablename__ = "configuracion_negocio"

    id = db.Column(db.Integer, primary_key=True)
    nombre_negocio = db.Column(db.String(120), nullable=False, default="Ronald BarberShop")
    eslogan = db.Column(
        db.String(180),
        nullable=False,
        default="Precision, estilo y presencia en cada corte.",
    )
    telefono_whatsapp = db.Column(db.String(30), nullable=False, default="809-984-6863")
    direccion = db.Column(db.String(200), default="Santo Domingo, Republica Dominicana")
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


class Appointment(db.Model, TimestampMixin):
    __tablename__ = "citas"
    __table_args__ = (
        db.UniqueConstraint("barbero_id", "fecha", "hora", name="uq_cita_inicio_barbero"),
    )

    VALID_STATES = ("pendiente", "confirmada", "completada", "cancelada")

    id = db.Column(db.Integer, primary_key=True)
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
    barbero_id = db.Column(db.Integer, db.ForeignKey("barberos.id"), nullable=True)
    fecha = db.Column(db.Date, nullable=False, index=True)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    motivo = db.Column(db.String(180), nullable=False, default="Horario no disponible")

    barbero = db.relationship("Barber", back_populates="horarios_bloqueados")
