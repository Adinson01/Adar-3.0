from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Inicializa SQLAlchemy
db = SQLAlchemy()

# Definición del modelo de usuario
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), unique=True, nullable=False)
    rol = db.Column(db.String(50), nullable=False)
    clave = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f'<Usuario {self.nombre}>'

# Nuevo modelo para las selecciones
class Seleccion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    elevacion = db.Column(db.Integer, nullable=False)
    tipo = db.Column(db.String(10), nullable=False)
    seccion = db.Column(db.String(10), nullable=False)
    etapa = db.Column(db.String(50), nullable=False)  # Indicar si es enfierradura, moldaje, instalaciones, hormigón
    supervisor = db.Column(db.String(80), nullable=False)  # Quién realizó la selección
    fecha = db.Column(db.DateTime, default=datetime.utcnow)  # Fecha automática

    usuario = db.relationship('Usuario', backref='selecciones')  # Relación inversa para acceder a las selecciones del usuario

    def __repr__(self):
        return f'<Seleccion {self.tipo} {self.seccion} en {self.elevacion}>'

class Notificacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    mensaje = db.Column(db.String(200), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship('Usuario', backref='notificaciones')  # Relación inversa para acceder a las notificaciones del usuario

    def __repr__(self):
        return f'<Notificacion {self.mensaje}>'
