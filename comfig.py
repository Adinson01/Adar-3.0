import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una_clave_secreta_por_defecto'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///site.db'  # Cambia por la URL de tu base de datos
    SQLALCHEMY_TRACK_MODIFICATIONS = False
