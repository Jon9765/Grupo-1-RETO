from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_restful import Api
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import stripe
import os
app = Flask(__name__)
#85.50.79.98 ip publica
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")


api = Api(app)
CORS(app)
CORS(app, origins=["http://localhost:8080"], supports_credentials=True)
app.secret_key = 'key_dwes_daw2'
app.config['JWT_SECRET_KEY'] = 'key_dwes_jwt'
#app.config['JWT_TOKEN_LOCATION'] = 'cookies'
jwt = JWTManager(app)
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://grupo1:grupo1root@pgsql03.dinaserver.com/trambot_db'
db = SQLAlchemy(app)
from  mi_app.catalogo.vistas import catalog
app.register_blueprint(catalog)
with app.app_context():
    db.create_all()
