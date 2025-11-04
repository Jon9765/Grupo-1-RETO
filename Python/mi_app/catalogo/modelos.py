from mi_app import db

class Usuarios(db.Model):
    __tablename__ = 'usuarios'    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255))
    correo = db.Column(db.String(255), unique=True)
    contraseña = db.Column(db.String(255))

    def __init__(self, nombre, correo, contraseña):
        self.nombre = nombre
        self.correo = correo
        self.contraseña = contraseña
    def __repr__(self):
        return f'<Usuarios {self.id}>'


class Servicios(db.Model):
    __tablename__ = 'servicios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    descripcion = db.Column(db.String(500))

    def __init__(self, nombre,descripcion):
        self.nombre = nombre
        self.descripcion = descripcion

    def __repr__(self):
        return f'<Category {self.id}>'


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

    def __init__(self, usuario_id, servicio_id):
        self.usuario_id = usuario_id
        self.servicio_id = servicio_id

    def __repr__(self):
        return f'<usuario_servicios {self.id}>'
