from mi_app import app
#Se encarga de iniciar la aplicación
if __name__ == '__main__':
    app.env='environment'
    app.run(debug=True)