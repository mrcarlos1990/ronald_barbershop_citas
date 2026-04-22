# ronald_barbershop_citas

Sistema web de reservas para **Ronald BarberShop** construido con Flask, SQLite, SQLAlchemy, HTML, CSS y JavaScript.

La aplicacion esta pensada para clientes que llegan desde un enlace compartido por WhatsApp y para una administracion interna que necesita controlar citas, servicios, barberos, horarios bloqueados y clientes desde un panel premium.

## Caracteristicas principales

- Landing page moderna con enfoque comercial.
- Flujo de reserva optimizado para movil.
- Calendario visual real con cambio de mes.
- Horarios disponibles dinamicos por servicio, barbero y bloqueos.
- Prevencion de dobles reservas y conflictos por duracion.
- Confirmacion final con boton real de WhatsApp y mensaje prellenado.
- Login admin con hash de contrasena, sesiones y proteccion de rutas.
- Dashboard con metricas, citas del dia, proximas citas y clientes recientes.
- CRUD de servicios.
- CRUD de barberos.
- Gestion de citas con filtros, creacion manual, edicion, reprogramacion, cambio de estado y eliminacion.
- Lista de clientes con historial resumido.
- Bloqueo manual de horarios.
- Datos semilla listos para prueba.

## Stack tecnico

- Python 3
- Flask
- Flask-SQLAlchemy
- SQLite
- SQLAlchemy
- Jinja2
- HTML5
- CSS3
- JavaScript
- Flask session
- Werkzeug

## Estructura del proyecto

```text
ronald_barbershop_citas/
├── app.py
├── config.py
├── models.py
├── seed.py
├── requirements.txt
├── README.md
├── instance/
│   └── ronald_barbershop.db
├── ronald_barbershop_citas/
│   ├── __init__.py
│   ├── admin_routes.py
│   ├── config.py
│   ├── decorators.py
│   ├── models.py
│   ├── routes.py
│   ├── seed.py
│   └── utils.py
├── static/
│   ├── css/
│   │   └── styles.css
│   ├── img/
│   │   └── logo.svg
│   └── js/
│       └── app.js
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── agendar.html
│   ├── confirmacion.html
│   ├── login.html
│   ├── landing.html
│   ├── booking.html
│   ├── booking_confirmed.html
│   ├── admin_dashboard.html
│   ├── admin_citas.html
│   ├── admin_servicios.html
│   ├── admin_barberos.html
│   ├── admin_clientes.html
│   ├── admin_horarios.html
│   └── admin/
└── utils/
    ├── __init__.py
    └── helpers.py
```

## Requisitos previos

- Python 3.10 o superior

## Instalacion paso a paso

1. Crear el entorno virtual:

```bash
python -m venv .venv
```

2. Activar el entorno virtual en Windows:

```bash
.venv\Scripts\activate
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Inicializacion de base de datos

La base SQLite se crea automaticamente al iniciar la aplicacion.

Ruta actual:

```text
instance/ronald_barbershop.db
```

Si quieres forzar la carga de datos semilla manualmente:

```bash
python seed.py
```

## Ejecutar el proyecto

```bash
python app.py
```

Luego abre:

```text
http://127.0.0.1:5000/
```

## Acceso al panel admin

- URL: `http://127.0.0.1:5000/admin/login`
- Usuario: `admin`
- Contrasena por defecto: `Admin123*`

Importante:
- Cambia esta contrasena despues de la primera puesta en marcha si el proyecto va a usarse fuera de entorno local.

## Datos semilla incluidos

La siembra crea o completa:

- Configuracion base del negocio
- Usuario admin por defecto
- Servicios:
  - Corte de cabello
  - Barba
  - Corte + barba
  - Cerquillo
  - Diseno
  - Lavado
  - Servicio premium
- 3 barberos de ejemplo
- Clientes de prueba
- Citas iniciales
- Un bloqueo horario de muestra

## Funcionalidades de negocio implementadas

- No permite reservas en fechas pasadas.
- No permite reservar fuera del horario laboral.
- No permite conflictos entre citas del mismo barbero.
- Respeta la duracion real de cada servicio.
- Oculta horarios bloqueados.
- Valida telefono, nombre, servicio, fecha y hora.
- Permite trabajar con estados:
  - pendiente
  - confirmada
  - completada
  - cancelada

## Flujo del cliente

1. El cliente abre el enlace de reservas.
2. Selecciona servicio y, opcionalmente, barbero.
3. El calendario visual muestra dias con disponibilidad.
4. Se cargan los horarios disponibles para ese dia.
5. Ingresa nombre, telefono y nota opcional.
6. Confirma la cita.
7. Ve el resumen final y puede abrir WhatsApp con un mensaje real prellenado.

## Como cambiar el numero de WhatsApp

Tienes dos formas:

1. Desde el panel admin:
- `Admin > Configuracion`

2. Desde el codigo semilla / valor por defecto:
- `ronald_barbershop_citas/models.py`
- `ronald_barbershop_citas/seed.py`

Numero configurado actualmente:

```text
809-984-6863
```

El enlace real se transforma automaticamente a formato `wa.me`.

## Como modificar horarios laborales

Desde:

- `Admin > Configuracion`

Puedes ajustar:

- hora de apertura
- hora de cierre
- intervalo de agenda

## Notas de arquitectura

- El proyecto usa app factory.
- Se incluye una pequena rutina de compatibilidad para agregar columnas nuevas en SQLite si la base ya existia.
- Las contrasenas admin se almacenan con hash usando Werkzeug.
- Las vistas usan Jinja2.
- La experiencia visual esta optimizada para movil.

## Comandos utiles

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Sembrar datos:

```bash
python seed.py
```

Ejecutar la app:

```bash
python app.py
```

## Estado del proyecto

Listo para correr localmente, probar reservas y gestionar la operacion desde el panel administrativo.
