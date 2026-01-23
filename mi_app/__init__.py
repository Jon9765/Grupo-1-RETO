from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_restful import Api
#from flask_cors import CORS
#Crea una instancia y hace la conexion con la base de datos
app = Flask(__name__)
#CORS(app, origins=["http://localhost:5173"])
api = Api(app)
app.secret_key = 'key_dwes_daw2'
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://grupo1:grupo1root@pgsql03.dinaserver.com/trambot_db'
db = SQLAlchemy(app)
from  mi_app.catalogo.vistas import catalog
app.register_blueprint(catalog)
with app.app_context():
    db.create_all()