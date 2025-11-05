from flask import Flask
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://jon:root@localhost/Trambot_db'
db = SQLAlchemy(app)
from  mi_app.catalogo.vistas import catalog
app.register_blueprint(catalog)
with app.app_context():
    db.create_all()