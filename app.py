from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask import jsonify
from flask import flash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import pytz
import json
import sqlite3  #
import os

app = Flask(__name__)
app.secret_key = 'mi_clave_secreta'

# Zona horaria de Chile
chile_timezone = pytz.timezone('Chile/Continental')  # Usar esta zona horaria para Chile (Chile continental)

# Obtener la fecha y hora en la zona horaria de Chile
fecha_chile = datetime.now(chile_timezone)  # Esto te da la hora local de Chile

# Configuración de la base de datos
# Define la ruta absoluta de la base de datos
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'usuarios.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Suprimir la advertencia
db = SQLAlchemy(app)

# Configuración para la subida de archivos
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Tamaño máximo de archivo: 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Crear el directorio de subidas si no existe
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Definición del modelo de usuario
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), unique=True, nullable=False)
    rol = db.Column(db.String(50), nullable=False)
    clave = db.Column(db.String(120), nullable=False)
    foto_perfil = db.Column(db.String(120), nullable=True)  # Nueva columna para la foto de perfil

# Nuevo modelo para las selecciones
class Seleccion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    elevacion = db.Column(db.Integer, nullable=False)
    tipo = db.Column(db.String(10), nullable=False)
    seccion = db.Column(db.String(10), nullable=False)
    etapa = db.Column(db.String(50), nullable=False)  # Indicar si es enfierradura, moldaje, instalaciones, hormigón
    supervisor = db.Column(db.String(80), nullable=False)  # Quién realizó la selección
    rol_supervisor = db.Column(db.String(50), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.now(pytz.timezone('Chile/Continental')))
    foto = db.Column(db.String(120), nullable=True)  # Nueva columna para almacenar la ruta de la foto
    respuestas_cuestionario = db.Column(db.Text, nullable=True)  
    porcentaje = db.Column(db.Integer, nullable=False)  # Nueva columna para almacenar el porcentaje
    aprobado = db.Column(db.Boolean, default=False)
    reprobado = db.Column(db.Boolean, default=False)  # Nuevo campo para marcar reprobación
    razon_rechazo = db.Column(db.Text, nullable=True)  # Razón del rechazo


class CalendarEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('Usuario', backref='events')

    def __repr__(self):
        return f'<CalendarEvent {self.date}: {self.note}>'


# Crear la base de datos y las tablas
with app.app_context():
    db.create_all()

# Función para verificar si el archivo tiene una extensión permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ruta principal que redirige al login
@app.route('/')
def home():
    return redirect(url_for('login'))

# Configuración para guardar fotos
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ruta para el login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nombre = request.form['nombre']
        clave = request.form['clave']
        
        # Comprobar si el usuario existe en la base de datos
        usuario = Usuario.query.filter_by(nombre=nombre).first()
        if usuario and usuario.clave == clave:
            # Guardar la información del usuario en la sesión
            session['nombre'] = usuario.nombre
            session['rol'] = usuario.rol
            print(session['rol'])  # Depuración

            
            # Redirigir según el rol
            if usuario.rol.strip().lower() == "jefe de terreno":
                return redirect(url_for('respuestas_selecciones'))
            else:
                return redirect(url_for('profile'))  # Cambia a la ruta correspondiente para otros roles
        else:
            return 'Nombre o clave incorrectos', 400

    return render_template('login.html')




# Ruta para el registro de usuarios
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        rol = request.form['rol']
        clave = request.form['clave']
        
        if Usuario.query.filter_by(nombre=nombre).first():
            return 'El nombre de usuario ya existe', 400
        
        # Crear nuevo usuario y agregarlo a la base de datos
        nuevo_usuario = Usuario(nombre=nombre, rol=rol, clave=clave)
        db.session.add(nuevo_usuario)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')


# Decorador para restringir acceso solo a jefes de terreno
def requiere_jefe_terreno(func):
    def wrapper(*args, **kwargs):
        if session.get('rol', '').strip().lower() != 'Jefe de terreno':
            return 'Acceso no autorizado', 403
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


# Ruta del perfil donde se realiza el registro de selecciones
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'nombre' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.filter_by(nombre=session['nombre']).first()

    if request.method == 'POST':
        try:
            # Manejo de la subida de la foto de perfil
            foto_perfil = request.files.get('foto_perfil')
            if foto_perfil and allowed_file(foto_perfil.filename):
                filename = secure_filename(foto_perfil.filename)
                foto_perfil_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                foto_perfil.save(foto_perfil_path)
                usuario.foto_perfil = foto_perfil_path  # Actualiza la ruta de la foto de perfil
                db.session.commit()

            elevacion = int(request.form['elevacion'])
            tipo = request.form['tipo']
            seccion = request.form['seccion']
            etapa = request.form['etapa']
            foto = request.files['foto'] if 'foto' in request.files else None
            porcentaje = request.form['porcentaje']  # Obtener el porcentaje del formulario
            # Recoger respuestas del cuestionario
            respuestas_cuestionario = {
                "safetyCheck": request.form.get('respuestas[safetyCheck]'),
                "qualityCheck": request.form.get('respuestas[qualityCheck]'),
                "materialCheck": request.form.get('respuestas[materialCheck]')
            }

            # Convertir el diccionario de respuestas a una cadena JSON
            respuestas_json = json.dumps(respuestas_cuestionario)

            # Imprimir las respuestas para depuración
            print(f"Respuestas del cuestionario: {respuestas_cuestionario}")


            # Guardar la foto si se subió
            foto_path = None
            if foto and allowed_file(foto.filename):
                filename = secure_filename(foto.filename)
                foto_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                foto.save(foto_path)

            # Guardar la selección en la base de datos
            nueva_seleccion = Seleccion(usuario_id=usuario.id, elevacion=elevacion, tipo=tipo, seccion=seccion, etapa=etapa, supervisor=usuario.nombre, rol_supervisor=usuario.rol, foto=foto_path, porcentaje=porcentaje, respuestas_cuestionario=respuestas_json  # Guardamos las respuestas como una cadena JSON
)
            db.session.add(nueva_seleccion)
            db.session.commit()


          
            # Redirigir a la misma página para evitar el reenvío del formulario
            return redirect(url_for('profile'))
        except ValueError:
            return 'Valor de elevación no válido', 400
        except Exception as e:
            return f'Ocurrió un error: {e}', 400


    # Obtener todas las selecciones de todos los usuarios, ordenadas por fecha descendente
    selecciones = Seleccion.query.order_by(Seleccion.fecha.desc()).all()


    return render_template('profile.html', selecciones=selecciones, nombre=session['nombre'], rol=session['rol'], foto_perfil=usuario.foto_perfil)




# Ruta para ver el avance de todas las selecciones
@app.route('/avance')
def avance():
    # Verificar si el usuario está autenticado
    if 'nombre' not in session:
        return redirect(url_for('login'))

    # Obtener el usuario actual desde la sesión
    usuario = Usuario.query.filter_by(nombre=session['nombre']).first()

    # Obtener todas las selecciones, ordenadas por elevación de mayor a menor
    selecciones = db.session.query(Seleccion, Usuario).join(Usuario, Seleccion.usuario_id == Usuario.id).order_by(Seleccion.elevacion.desc()).all()

    # Decodificar las respuestas del cuestionario de JSON a diccionario para cada selección
    for seleccion, usuario in selecciones:
        if seleccion.respuestas_cuestionario:
            seleccion.respuestas_cuestionario = json.loads(seleccion.respuestas_cuestionario)

    # Pasar los datos a la plantilla
    return render_template('avance.html', selecciones=selecciones, nombre=usuario.nombre, rol=usuario.rol)


from datetime import datetime

# Ruta para ver el avance de todas las selecciones
@app.route('/avancejefe')
def avancejefe():
    # Verificar si el usuario está autenticado
    if 'nombre' not in session:
        return redirect(url_for('login'))

    # Obtener el usuario actual desde la sesión
    usuario = Usuario.query.filter_by(nombre=session['nombre']).first()

    # Obtener todas las selecciones, ordenadas por elevación de mayor a menor
    selecciones = db.session.query(Seleccion, Usuario).join(Usuario, Seleccion.usuario_id == Usuario.id).order_by(Seleccion.elevacion.desc()).all()

    # Decodificar las respuestas del cuestionario de JSON a diccionario para cada selección
    for seleccion, usuario in selecciones:
        if seleccion.respuestas_cuestionario:
            seleccion.respuestas_cuestionario = json.loads(seleccion.respuestas_cuestionario)

    # Pasar los datos a la plantilla
    return render_template('avancejefe.html', selecciones=selecciones, nombre=usuario.nombre, rol=usuario.rol)


from datetime import datetime

@app.route('/avance_calculado', methods=['GET'])
def avance_calculado():
    if 'nombre' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.filter_by(nombre=session['nombre']).first()
    rol = usuario.rol

    selecciones = Seleccion.query.filter_by(usuario_id=usuario.id).order_by(Seleccion.fecha.desc()).all()

    agrupadas = {}
    for seleccion in selecciones:
        key = (seleccion.elevacion, seleccion.tipo)
        if key not in agrupadas:
            agrupadas[key] = {
                'elevacion': seleccion.elevacion, 
                'tipo': seleccion.tipo, 
                'secciones': [], 
                'porcentaje': 0, 
                'fecha_inicio': seleccion.fecha, 
                'fecha_termino': seleccion.fecha
            }
        agrupadas[key]['porcentaje'] += seleccion.porcentaje
        agrupadas[key]['secciones'].append(seleccion.seccion)
        if seleccion.fecha > agrupadas[key]['fecha_termino']:
            agrupadas[key]['fecha_termino'] = seleccion.fecha
        if seleccion.fecha < agrupadas[key]['fecha_inicio']:
            agrupadas[key]['fecha_inicio'] = seleccion.fecha

    for seleccion in agrupadas.values():
        seleccion['diferencia_dias'] = (seleccion['fecha_termino'] - seleccion['fecha_inicio']).days + 1

    total_porcentaje = sum(s['porcentaje'] for s in agrupadas.values())
    avance_completo = round((total_porcentaje / 1000) * 100, 2)

    selecciones_agrupadas = list(agrupadas.values())

    return render_template(
        'avance_calculado.html',
        selecciones=selecciones_agrupadas,
        usuario=usuario,
        rol=rol,
        avance_completo=avance_completo
    )


@app.route('/jefeavancecalculado', methods=['GET'])
def jefeavancecalculado():
    if 'nombre' not in session:
        return redirect(url_for('login'))

    # Recupera al usuario actual para mostrarlo en la plantilla
    usuario = Usuario.query.filter_by(nombre=session['nombre']).first()

    # Recupera TODAS las selecciones, sin filtrar por usuario
    selecciones = Seleccion.query.order_by(Seleccion.fecha.desc()).all()

    # Agrupa las selecciones por elevación y tipo
    agrupadas = {}
    for seleccion in selecciones:
        key = (seleccion.elevacion, seleccion.tipo)
        if key not in agrupadas:
            agrupadas[key] = {
                'elevacion': seleccion.elevacion,
                'tipo': seleccion.tipo,
                'secciones': [],
                'porcentaje': 0,
                'fecha_inicio': seleccion.fecha,
                'fecha_termino': seleccion.fecha,
                'rol_supervisor': seleccion.rol_supervisor  # Asegúrate de incluir este campo
            }
        agrupadas[key]['porcentaje'] += seleccion.porcentaje
        agrupadas[key]['secciones'].append(seleccion.seccion)
        if seleccion.fecha > agrupadas[key]['fecha_termino']:
            agrupadas[key]['fecha_termino'] = seleccion.fecha
        if seleccion.fecha < agrupadas[key]['fecha_inicio']:
            agrupadas[key]['fecha_inicio'] = seleccion.fecha

    # Calcula la diferencia de días para cada agrupación
    for seleccion in agrupadas.values():
        seleccion['diferencia_dias'] = (seleccion['fecha_termino'] - seleccion['fecha_inicio']).days + 1

    # Calcula el porcentaje de avance total
    total_porcentaje = sum(s['porcentaje'] for s in agrupadas.values())
    avance_completo = round((total_porcentaje / 4000) * 100, 2)

    # Agrupa por rol de supervisor para calcular el avance por rol
    agrupadas_por_rol = {}
    for seleccion in selecciones:
        rol = seleccion.rol_supervisor
        if rol not in agrupadas_por_rol:
            agrupadas_por_rol[rol] = {
                'rol': rol,
                'porcentaje': 0
            }
        agrupadas_por_rol[rol]['porcentaje'] += seleccion.porcentaje

    # Calcula el porcentaje de avance para cada rol
    for rol, datos in agrupadas_por_rol.items():
        datos['porcentaje'] = round((datos['porcentaje'] / 1000) * 100, 2)

    selecciones_agrupadas = list(agrupadas.values())

    # Verifica el rol del usuario
    rol = usuario.rol if hasattr(usuario, 'rol') else 'Desconocido'

    return render_template(
        'jefeavancecalculado.html',
        selecciones=selecciones_agrupadas,
        usuario=usuario,
        rol=usuario.rol, 
        avance_completo=avance_completo,
        agrupadas_por_rol=agrupadas_por_rol  # Pasa los datos del avance por rol a la plantilla
    )



@app.route('/rendimiento', methods=['GET', 'POST'])
def rendimiento():
    if 'nombre' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.filter_by(nombre=session['nombre']).first()
    rol = usuario.rol

    selecciones = Seleccion.query.filter_by(usuario_id=usuario.id).order_by(Seleccion.fecha.desc()).all()

    agrupadas = {}
    for seleccion in selecciones:
        key = (seleccion.elevacion, seleccion.tipo)
        if key not in agrupadas:
            agrupadas[key] = {
                'elevacion': seleccion.elevacion, 
                'tipo': seleccion.tipo, 
                'secciones': [], 
                'porcentaje': 0, 
                'fecha_inicio': seleccion.fecha, 
                'fecha_termino': seleccion.fecha,
                'trabajadores': [],  # Lista para almacenar los trabajadores
                'factores': []       # Lista para almacenar los factores
            }
        agrupadas[key]['porcentaje'] += seleccion.porcentaje
        agrupadas[key]['secciones'].append(seleccion.seccion)
        if seleccion.fecha > agrupadas[key]['fecha_termino']:
            agrupadas[key]['fecha_termino'] = seleccion.fecha
        if seleccion.fecha < agrupadas[key]['fecha_inicio']:
            agrupadas[key]['fecha_inicio'] = seleccion.fecha

    for seleccion in agrupadas.values():
        seleccion['diferencia_dias'] = (seleccion['fecha_termino'] - seleccion['fecha_inicio']).days + 1

    # Si es un POST, capturamos los datos ingresados en la tabla
    if request.method == 'POST':
        for seleccion in selecciones:
            trabajadores = request.form.get(f'trabajadores_{seleccion.id}')
            factor = request.form.get(f'factor_{seleccion.id}')
            if trabajadores:
                # Almacenamos el número de trabajadores, puedes guardarlo en la base de datos si lo deseas
                seleccion.trabajadores = int(trabajadores)
            if factor:
                # Almacenamos el factor, puedes guardarlo en la base de datos si lo deseas
                seleccion.factor = float(factor)
        
        # Guardamos los cambios si es necesario
        db.session.commit()

    selecciones_agrupadas = list(agrupadas.values())

    return render_template(
        'rendimiento.html',
        selecciones=selecciones_agrupadas,
        usuario=usuario,
        rol=rol
    )


@app.route('/Jefe_terreno')
def jefe_terreno():
    # Verificar que el usuario tiene sesión activa y el rol correcto
    if 'nombre' in session and session.get('rol') == "Jefe de terreno":
        return render_template('respuestas_selecciones.html')
    else:
        return redirect(url_for('login'))  # Redirigir al login si no está autorizado


@app.route('/respuestas_selecciones', methods=['GET', 'POST'])
def respuestas_selecciones():
    # Verificar si el usuario está autenticado
    if 'nombre' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.filter_by(nombre=session['nombre']).first()

    # Verificar si el usuario existe en la base de datos
    if not usuario:
        flash('Usuario no encontrado. Por favor, inicia sesión de nuevo.', 'error')
        return redirect(url_for('login'))

    # Procesar notas del calendario si el método es POST
    if request.method == 'POST':
        date_str = request.form.get('date')  # Recibir fecha como cadena
        note = request.form.get('note')  # Recibir la nota


        if date_str and note:
            try:
                # Convertir la cadena de fecha a un objeto datetime.date
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

                # Crear un nuevo evento de calendario
                event = CalendarEvent(
                    user_id=usuario.id, 
                    date=date_obj, 
                    note=note, 
                    created_at=datetime.now()
                )

                # Guardar el evento en la base de datos
                db.session.add(event)
                db.session.commit()

                # Respuesta en caso de éxito
                return {'success': True, 'message': 'Nota agregada correctamente'}

            except ValueError:
                return {'success': False, 'message': 'Formato de fecha inválido. Use el formato AAAA-MM-DD'}
            except Exception as e:
                db.session.rollback()
                return {'success': False, 'message': f'Ocurrió un error al agregar la nota: {str(e)}'}

    if request.method == 'GET':
        date_str = request.args.get('date')
        if date_str:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            events = CalendarEvent.query.filter_by(date=date_obj, user_id=usuario.id).all()
            notes = [{"note": event.note} for event in events]
            return jsonify({'notes': notes})




    # Obtener los eventos del calendario del usuario actual
    calendar_events = CalendarEvent.query.filter_by(user_id=usuario.id).all()

    selecciones_pendientes = Seleccion.query.filter(
        Seleccion.aprobado.is_(False), 
        Seleccion.reprobado.is_(False)
    ).order_by(Seleccion.fecha.desc()).all()

    for seleccion in selecciones_pendientes:
        if seleccion.respuestas_cuestionario:
            seleccion.respuestas_cuestionario = json.loads(seleccion.respuestas_cuestionario)


    return render_template(
        'respuestas_selecciones.html',
        selecciones=selecciones_pendientes,
        usuario=usuario,
        rol=usuario.rol,
        calendar_events=calendar_events
    )

@app.route('/reprobar_protocolo/<int:id>', methods=['POST'])
def reprobar_protocolo(id):
    # Obtener la razón de rechazo desde el cuerpo de la solicitud JSON
    data = request.get_json()
    razon_rechazo = data.get('reason')
    
    # Buscar la selección en la base de datos
    seleccion = Seleccion.query.get(id)
    
    if not seleccion:
        return jsonify({'success': False, 'error': 'Selección no encontrada'}), 404

    # Actualizar el estado de la selección y la razón de rechazo
    seleccion.reprobado = True
    seleccion.aprobado = False
    seleccion.razon_rechazo = razon

    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Protocolo reprobado con éxito.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/subir_foto', methods=['POST'])
def subir_foto():
    if 'nombre' not in session:
        return jsonify({'success': False, 'error': 'Usuario no autenticado'}), 401
    
    usuario = Usuario.query.filter_by(nombre=session['nombre']).first()
    if not usuario:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

    # Validar archivo
    if 'foto_perfil' not in request.files:
        return jsonify({'success': False, 'error': 'No se encontró el archivo'}), 400

    file = request.files['foto_perfil']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400

    # Guardar el archivo
    if file:
        filename = f"{usuario.id}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Actualizar el usuario con el nombre del archivo
        usuario.foto_perfil = filename
        db.session.commit()

        return jsonify({'success': True, 'filename': filename})



@app.route('/guardar_cambios', methods=['POST'])
def guardar_cambios():
    if 'nombre' not in session:
        return redirect(url_for('login'))

    # Iterar sobre las selecciones enviadas
    for seleccion in Seleccion.query.all():
        estado_nuevo = request.form.get(f"estado_{seleccion.id}")
        razon_rechazo = request.form.get(f"razon_rechazo_{seleccion.id}")  # Capturar razón de rechazo

        # Validar si el estado realmente ha cambiado
        if estado_nuevo == "aprobado" and not seleccion.aprobado:
            seleccion.aprobado = True
            seleccion.reprobado = False
        elif estado_nuevo == "reprobado" and not seleccion.reprobado:
            seleccion.aprobado = False
            seleccion.reprobado = True
        elif estado_nuevo == "pendiente" and (seleccion.aprobado or seleccion.reprobado):
            seleccion.aprobado = False
            seleccion.reprobado = False
            seleccion.razon_rechazo = razon_rechazo  # Guardar la razón de rechazo solo si es necesario

        # Solo guardar si hubo algún cambio
        db.session.add(seleccion)

    # Confirmar cambios
    db.session.commit()

    return redirect(url_for('respuestas_selecciones'))


@app.route('/obtener_estado_protocolo/<int:protocolo_id>', methods=['GET'])
def obtener_estado_protocolo(protocolo_id):
    # Busca el protocolo en la base de datos
    protocolo = Protocolo.query.get(protocolo_id)
    if protocolo:
        estado = "Aprobado" if protocolo.aprobado else "Reprobado" if protocolo.reprobado else "Pendiente"
        return jsonify(success=True, estado=estado)
    return jsonify(success=False, error="Protocolo no encontrado"), 404


@app.route('/nuevo_ruta', methods=['GET'])
def nuevo_ruta():
    if 'nombre' not in session:
        return redirect(url_for('login'))

    # Obtener el usuario desde la sesión
    usuario = Usuario.query.filter_by(nombre=session['nombre']).first()

    if not usuario:
        return redirect(url_for('login'))

    # Filtrar selecciones por el nombre del usuario
    selecciones = Seleccion.query.filter_by(supervisor=usuario.nombre).all()

    # Decodificar las respuestas del cuestionario de JSON a diccionario
    for seleccion in selecciones:
        if seleccion.respuestas_cuestionario:
            seleccion.respuestas_cuestionario = json.loads(seleccion.respuestas_cuestionario)

    return render_template('nuevo_html.html', selecciones=selecciones, usuario=usuario, rol=usuario.rol)

@app.route('/nuevojefe', methods=['GET'])
def nuevojefe():
    if 'nombre' not in session:
        return redirect(url_for('login'))

    # Obtener el usuario desde la sesión
    usuario = Usuario.query.filter_by(nombre=session['nombre']).first()

    if not usuario:
        return redirect(url_for('login'))

    # Filtrar selecciones por el nombre del usuario
    selecciones = Seleccion.query.all()

    # Decodificar las respuestas del cuestionario de JSON a diccionario
    for seleccion in selecciones:
        if seleccion.respuestas_cuestionario:
            seleccion.respuestas_cuestionario = json.loads(seleccion.respuestas_cuestionario)

    return render_template('nuevojefe.html', selecciones=selecciones, usuario=usuario, rol=usuario.rol)


@app.route('/aprobar_protocolo/<int:id>', methods=['POST'])
def aprobar_protocolo(id):
    if 'nombre' not in session:
        return redirect(url_for('login'))
    
    usuario = Usuario.query.filter_by(nombre=session['nombre']).first()
    
    if usuario.rol != 'Jefe de terreno':
        return jsonify({"error": "No tienes permisos para aprobar."}), 403

    seleccion = Seleccion.query.get(id)
    if seleccion:
        seleccion.aprobado = True  # Marcar como aprobado
        db.session.commit()  # Guardar los cambios en la base de datos
        return jsonify({"success": "Protocolo aprobado."})
    else:
        return jsonify({"error": "Selección no encontrada."}), 404

# Configurar el directorio para guardar las fotos
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Función para verificar si el archivo tiene una extensión permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('nombre', None)
    session.pop('rol', None)
    return redirect(url_for('login'))



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)



