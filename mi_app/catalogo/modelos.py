from mi_app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
#Creación de la tabla Usuarios
class Usuarios(db.Model, UserMixin):
    __tablename__ = 'usuarios'    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255))
    correo = db.Column(db.String(255), unique=True)
    pwdhash = db.Column(db.String(255))

    def __init__(self, nombre, correo, contraseña):
        self.nombre = nombre
        self.correo = correo
        self.pwdhash = generate_password_hash(contraseña)
        
    def check_password(self, contraseña):
        return check_password_hash(self.pwdhash, contraseña)
    def __repr__(self):
        return f'<Usuarios {self.id}>'

#Creación de la tabla Servicios
class Servicios(db.Model):
    __tablename__ = 'servicios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    descripcion = db.Column(db.String(500))

     #iniciador de clase
    def __init__(self, nombre,descripcion):
        self.nombre = nombre
        self.descripcion = descripcion

    def __repr__(self):
        return f'<Category {self.id}>'

#Creación de la tabla que relaciona Usuarios y Servicios(usuario_servicio)
class usuario_servicios(db.Model):
    __tablename__ = 'usuario_servicios'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    servicio_id = db.Column(db.Integer, db.ForeignKey('servicios.id'))
    nombre_servicio = db.Column(db.String(100))
    costo = db.Column(db.Float)
    renovacion = db.Column(db.String(50))

    usuario = db.relationship('Usuarios', backref=db.backref('usuario_servicios', lazy='dynamic'))
    servicio = db.relationship('Servicios', backref=db.backref('usuario_servicios', lazy='dynamic'))

    #iniciador de clase
    def __init__(self, usuario_id, servicio_id,nombre_servicio,costo,renovacion):
        self.usuario_id = usuario_id
        self.servicio_id = servicio_id
        self.nombre_servicio = nombre_servicio
        self.costo = costo
        self.renovacion = renovacion

    def __repr__(self):
        return f'<usuario_servicios {self.id}>'
    
#Creación de la tabla Contacto
class contacto(db.Model):
    __tablename__ = "contacto"
    id = db.Column(db.Integer, primary_key=True)
    correo = db.Column(db.String(100))
    asunto = db.Column(db.String(100))
    texto = db.Column(db.String(500))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    usuario_mensaje = db.relationship('Usuarios', backref=db.backref('contacto', lazy='dynamic'))
    
     #iniciador de clase
    def __init__(self, correo, asunto, texto):
        self.correo = correo
        self.asunto = asunto
        self.texto = texto

    def __repr__(self):
        return f'<usuario_servicios {self.id}>'