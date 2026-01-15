from flask  import request, Blueprint, render_template, jsonify,redirect, url_for
from datetime import date, timedelta
from mi_app import db
from mi_app.catalogo.modelos import Usuarios, Servicios, usuario_servicios, contacto
from flask_login import  current_user, login_user, logout_user, login_required
from mi_app import login_manager

catalog = Blueprint('catalog',__name__)

@login_manager.user_loader
def load_user(id):
    return Usuarios.query.get(int(id))
#Nada mas inicar la app se ejecuta el archivo index.html
@catalog.route('/')
@catalog.route('/home')
def index():
    return render_template("index.html")

#Crea la ruta de servicios.html y le da la capacidad de usar el metodo post
@catalog.route('/servicio',methods=[ 'GET','POST'])
def servicio():
    if request.method=='POST':
        #Recoje los datos que el formulario envia
        nombre = request.form['nombre']
        precio = request.form['precio']
        id_servicio = int(request.form['servicio'])
        fecha_actual = date.today()
        renovacion = fecha_actual + timedelta(days=365)
        
        #Introduce los datos anteriormente recojidos en el objeto dato crea el insert query 
        dato = usuario_servicios(1,id_servicio,nombre,precio,renovacion)
        #Crea un insert query en el 
        db.session.add(dato)
        db.session.commit()
 
    return render_template("servicios.html")

#Desde el formulario de Contacto.html se envia modo post a flask y se encarga de mandar lso datos a las base de datos
@catalog.route('/contacto', methods=[ 'GET','POST'])
def contactos():
    if request.method == 'POST':
        correo = request.form['correo']
        asunto = request.form['asunto']
        mensaje = request.form['mensaje']

        contactos=contacto(correo,asunto,mensaje)
        db.session.add(contactos)
        db.session.commit()
        
        '''
        password = "pana"
        hash_object = hashlib.sha256(password.encode('utf-8'))
        hashed_password = hash_object.hexdigest()
        usuario1=Usuarios('manu','miabuela67@hotmail.com',hashed_password)
        db.session.add(usuario1)
        db.session.commit()
        '''
    return render_template("contacto.html")

#Recoge los datos desde la base de datos y los recoje en un json y los muestra en la ruta json
@catalog.route('/json',methods=['GET'])
def recojer():
        datos = usuario_servicios.query.all()
        res = {}
        for dato in datos:
             res[dato.id] = {
            'usuario': str(dato.usuario_id),
            'servicio': str(dato.servicio_id),
            'nombre_servicio': dato.nombre_servicio,
            'coste':str(dato.costo),
            'caducidad':dato.renovacion
        }
        return jsonify(res)

@catalog.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('catalog.perfil'))
    correo = request.form['correo']
    password = request.form['password']
    existing_user = Usuarios.query.filter_by(correo=correo).first()

    if not (existing_user and existing_user.check_password(password)):
        return render_template('iniciosesion.html')
    login_user(existing_user, remember=True)
    return redirect(url_for('catalog.perfil'))

@catalog.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('catalog.index'))
    nombre = request.form['nombre']
    correo = request.form['correo']
    password = request.form['password']
    print(nombre, correo, password)
    if (nombre and password):
        existing_user = Usuarios.query.filter_by(correo=correo).first()
        if existing_user:
            return render_template('iniciosesion.html')
        user = Usuarios(nombre, correo, password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('catalog.login'))
    return render_template('iniciosesion.html')

@catalog.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('catalog.index'))

@catalog.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    return render_template('perfil.html')

@catalog.route('/inicio', methods=['GET', 'POST'])
def inicio():
    return render_template('iniciosesion.html')