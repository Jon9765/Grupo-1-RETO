from flask  import request, Blueprint, render_template
from mi_app import db
from mi_app.catalogo.modelos import Usuarios, Servicios, usuario_servicios, contacto

catalog = Blueprint('catalog',__name__)

@catalog.route('/')
@catalog.route('/home')
def index():
    return render_template("index.html")
@catalog.route('/servicio')
def servicio():
    return render_template("servicios.html")

@catalog.route('/contacto', methods=[ 'GET','POST'])
def contactos():
    if request.method == 'POST':
        correo=request.form['correo']
        asunto=request.form['asunto']
        mensaje= request.form['mensaje']

        contactos=contacto(correo,asunto,mensaje)
        db.session.add(contactos)
        db.session.commit()

    return render_template("contacto.html")

