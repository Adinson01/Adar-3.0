from flask import Flask, render_template

app = Flask(__name__)

# Aquí es donde rediriges temporalmente
@app.route('/')
def login():
    # Asegúrate de que esta ruta cargue la página de login
    return render_template('login.html')

@app.route('/login')
def login():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)



