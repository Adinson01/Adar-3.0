from app import db  # Asegúrate de que esto apunte a tu archivo app.py

# Crear la base de datos
with db.app.app_context():  # Cambiamos esto para asegurar el contexto de la aplicación
    db.create_all()
    print("Base de datos creada con éxito.")
