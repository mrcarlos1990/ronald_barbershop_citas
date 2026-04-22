# Ronald BarberShop Citas

Aplicacion web profesional para reservas de barberia construida con Flask, SQLite, SQLAlchemy, Jinja2, HTML, CSS y JavaScript. El sistema esta pensado para clientes que llegan desde un enlace compartido por WhatsApp y para una administracion diaria clara, elegante y segura.

## Caracteristicas principales

- Landing page premium, responsive y optimizada para moviles.
- Registro y login de clientes con cuenta propia.
- Sesion de cliente separada de la sesion administrativa.
- Calendario visual moderno con disponibilidad dinamica.
- Reserva de citas solo para clientes autenticados.
- Confirmacion final con boton real de WhatsApp y mensaje prellenado.
- Panel privado de cliente para ver, cancelar y reprogramar citas.
- Login seguro de administrador con rutas protegidas.
- Dashboard admin con metricas, agenda del dia, proximas citas y clientes recientes.
- CRUD de servicios.
- CRUD de barberos.
- Gestion de citas, estados y reprogramaciones.
- Gestion de clientes con activacion o desactivacion.
- Bloqueo manual de horarios.
- Datos semilla listos para pruebas.

## Tecnologias usadas

- Python 3
- Flask
- Flask-Login
- Flask-SQLAlchemy
- SQLite
- SQLAlchemy
- Jinja2
- HTML5
- CSS3
- JavaScript
- Werkzeug Password Hashing

## Arquitectura de autenticacion

- Clientes: usan Flask-Login y acceden a su panel privado desde `/cliente/...`.
- Administradores: usan una sesion administrativa aislada desde `/admin/...`.
- Ambas sesiones no se mezclan. Al iniciar sesion como admin se cierra la sesion activa de cliente, y al iniciar sesion como cliente se limpia la sesion admin.

Esta separacion se hizo a proposito para mantener permisos y paneles claramente aislados.

## Estructura del proyecto

```text
Ronald BarberShop/
├── app.py
├── config.py
├── seed.py
├── requirements.txt
├── README.md
├── instance/
│   └── ronald_barbershop.db
├── static/
│   ├── css/
│   │   ├── style.css
│   │   └── styles.css
│   ├── js/
│   │   └── app.js
│   └── img/
│       └── logo.svg
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── landing.html
│   ├── registro_cliente.html
│   ├── login_cliente.html
│   ├── recuperar_cliente.html
│   ├── panel_cliente.html
│   ├── mis_citas.html
│   ├── agendar.html
│   ├── confirmacion.html
│   ├── login_admin.html
│   └── admin/
│       ├── base_admin.html
│       ├── dashboard.html
│       ├── appointments.html
│       ├── appointment_form.html
│       ├── services.html
│       ├── barbers.html
│       ├── clients.html
│       ├── blocked_slots.html
│       ├── settings.html
│       └── login.html
├── utils/
│   └── helpers.py
└── ronald_barbershop_citas/
    ├── __init__.py
    ├── admin_routes.py
    ├── client_routes.py
    ├── config.py
    ├── decorators.py
    ├── models.py
    ├── routes.py
    ├── seed.py
    └── utils.py
```

## Instalacion paso a paso

### 1. Crear entorno virtual

En PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

En CMD:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### 2. Instalar dependencias

```bash
python -m pip install -r requirements.txt
```

### 3. Inicializar base de datos y semillas

La aplicacion crea tablas y ejecuta semillas automaticamente al arrancar. Si quieres forzarlo manualmente:

```bash
python seed.py
```

### 4. Iniciar el proyecto

```bash
python app.py
```

La app quedara disponible en:

- Cliente y landing: `http://127.0.0.1:5000/`
- Reserva directa: `http://127.0.0.1:5000/agendar`
- Login cliente: `http://127.0.0.1:5000/cliente/login`
- Registro cliente: `http://127.0.0.1:5000/cliente/registro`
- Login admin: `http://127.0.0.1:5000/admin/login`

## Credenciales por defecto

### Administrador

- Usuario: `admin`
- Contrasena: `Admin123*`

Importante:

- Cambia esta contrasena en cuanto pongas el sistema en uso real.

### Clientes de prueba

Todos los clientes semilla usan la misma contrasena:

- Contrasena: `Cliente123*`

Usuarios cargados:

- `carlosmejia`
- `andresventura`
- `miguelsantos`

Tambien puedes iniciar sesion con sus correos:

- `carlos@ronaldbarbershop.local`
- `andres@ronaldbarbershop.local`
- `miguel@ronaldbarbershop.local`

## Flujo del cliente

1. El cliente crea su cuenta o inicia sesion.
2. Entra a `/agendar`.
3. Selecciona servicio y barbero.
4. El calendario visual muestra los dias con disponibilidad real.
5. El sistema carga solo horarios validos segun servicio, barbero, duracion, horario laboral y bloqueos.
6. Confirma la cita.
7. Se muestra el resumen final y el boton real de WhatsApp con mensaje prellenado.

## Panel del cliente

Desde el panel privado el cliente puede:

- Ver sus proximas citas.
- Ver historial.
- Reprogramar si la cita aun no ha iniciado.
- Cancelar si la cita aun no ha iniciado.
- Actualizar nombre, username, correo, telefono y observaciones.
- Abrir WhatsApp hacia la barberia.

## Recuperacion de contrasena del cliente

Existe una recuperacion local simple en:

- `/cliente/recuperar-password`

Flujo actual:

- Se valida username o correo.
- Se valida el telefono asociado a la cuenta.
- Se permite definir una nueva contrasena.

Esta implementacion deja la estructura lista para evolucionar luego a correo o SMS.

## Panel administrativo

El administrador puede:

- Ver metricas de citas y clientes.
- Revisar la agenda del dia.
- Crear citas manualmente.
- Editar, reprogramar, cancelar o eliminar citas.
- Gestionar servicios.
- Gestionar barberos.
- Gestionar clientes.
- Bloquear horarios.
- Ajustar configuracion general del negocio.

## WhatsApp configurable

El numero actual de WhatsApp configurado por defecto es:

- `809-984-6863`

Puedes cambiarlo desde cualquiera de estas dos vias:

### Opcion 1. Panel admin

- Inicia sesion en `/admin/login`
- Ve a `Configuracion`
- Edita el campo `Telefono WhatsApp`

### Opcion 2. Semilla y configuracion inicial

Archivo:

- `ronald_barbershop_citas/seed.py`

Variable:

- `DEFAULT_WHATSAPP`

## Horario laboral configurable

Se puede ajustar desde el panel admin en `Configuracion`:

- Hora de apertura
- Hora de cierre
- Intervalo de agenda

La disponibilidad del calendario respeta:

- horario laboral
- citas existentes
- duracion del servicio
- bloqueos manuales
- disponibilidad del barbero

## Reglas de negocio implementadas

- No permite reservas en fechas pasadas.
- No permite doble reserva con el mismo barbero al mismo tiempo.
- Evita conflictos por solapamiento de duracion.
- No muestra horarios bloqueados.
- No muestra horarios fuera del horario laboral.
- Solo clientes autenticados pueden reservar.
- Cada cliente solo puede ver sus propias citas.
- El admin puede gestionar todo desde rutas separadas.

## Base de datos

Tablas principales:

- `usuarios_admin`
- `clientes`
- `servicios`
- `barberos`
- `citas`
- `horarios_bloqueados`
- `configuracion_negocio`

Archivo SQLite actual:

- `instance/ronald_barbershop.db`

## Comandos utiles

Reinstalar dependencias:

```bash
python -m pip install -r requirements.txt
```

Ejecutar semillas manualmente:

```bash
python seed.py
```

Iniciar servidor local:

```bash
python app.py
```

## Produccion

El proyecto esta listo para correr localmente y tiene estructura preparada para produccion. Para desplegar:

- cambia `SECRET_KEY`
- desactiva `debug=True`
- usa Gunicorn o un servidor WSGI equivalente
- configura un proxy como Nginx o Caddy
- reemplaza credenciales por defecto

## Firma

Desarrollado por:

- `Ing. Amauri Feliz`
