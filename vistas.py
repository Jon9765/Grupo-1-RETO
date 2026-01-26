from flask import Flask, request, Blueprint, render_template, jsonify, redirect, url_for,session
from datetime import date, timedelta
from mi_app import db
from mi_app.catalogo.modelos import Usuarios, Servicios, usuario_servicios, contacto
from flask_login import current_user, login_user, logout_user, login_required
from mi_app import login_manager
from flask_restful import Resource, reqparse, abort
from mi_app import api
from mi_app import jwt
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import stripe
from dotenv import load_dotenv
import os




load_dotenv()
stripe.api_key = "sk_test_51SnjHUCsm3x3qNyu2phwsxytV8lM3XPVN2yAwgGPqdhRYj29gdM0rTez4MKor4XOd0lNEoQJYzv7IdgXJsUlO0LF00r7tHFKLG"


# ============= PARSERS PARA VALIDACIÓN =============
servicio_parser = reqparse.RequestParser()
servicio_parser.add_argument('nombre', type=str, required=True, help='Nombre del servicio es requerido')
servicio_parser.add_argument('descripcion', type=str, required=False, default='')

usuario_servicio_parser = reqparse.RequestParser()
usuario_servicio_parser.add_argument('usuario_id', type=int, required=True, help='ID de usuario requerido')
usuario_servicio_parser.add_argument('servicio_id', type=int, required=True, help='ID de servicio requerido')
usuario_servicio_parser.add_argument('nombre_servicio', type=str, required=True, help='Nombre del servicio requerido')
usuario_servicio_parser.add_argument('costo', type=float, required=True, help='Costo requerido')

contacto_parser = reqparse.RequestParser()
contacto_parser.add_argument('correo', type=str, required=True, help='Correo requerido')
contacto_parser.add_argument('asunto', type=str, required=True, help='Asunto requerido')
contacto_parser.add_argument('texto', type=str, required=True, help='Mensaje requerido')

catalog = Blueprint('catalog', __name__)

@login_manager.user_loader
def load_user(id):
    return Usuarios.query.get(int(id))

# ============= VISTAS HTML (Frontend) =============
@catalog.route('/')
@catalog.route('/home')
def index():
    return render_template("index.html")

@catalog.route('/servicio', methods=['GET', 'POST'])
def servicio():
    if request.method == 'POST':
        nombre = request.form['nombre']
        precio = request.form['precio']
        id_servicio = int(request.form['servicio'])
        fecha_actual = date.today()
        renovacion = fecha_actual + timedelta(days=365)
        
        dato = usuario_servicios(current_user.id if current_user.is_authenticated else 1, 
                                id_servicio, nombre, precio, renovacion)
        db.session.add(dato)
        db.session.commit()
 
    return render_template("servicios.html")

@catalog.route('/contacto', methods=['GET', 'POST'])
def contactos():
    if request.method == 'POST':
        correo = request.form['correo']
        asunto = request.form['asunto']
        mensaje = request.form['mensaje']

        nuevo_contacto = contacto(correo, asunto, mensaje)
        db.session.add(nuevo_contacto)
        db.session.commit()
        
    return render_template("contacto.html")

@catalog.route('/json', methods=['GET'])
def recojer():
    datos = usuario_servicios.query.all()
    res = {}
    for dato in datos:
        res[dato.id] = {
            'usuario': str(dato.usuario_id),
            'servicio': str(dato.servicio_id),
            'nombre_servicio': dato.nombre_servicio,
            'coste': str(dato.costo),
            'caducidad': str(dato.renovacion)
        }
    return jsonify(res)

@catalog.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('catalog.perfil'))
    
    if request.method == 'POST':
        correo = request.form.get('email', '')
        password = request.form.get('contraseña', '')
        existing_user = Usuarios.query.filter_by(correo=correo).first()

        if not (existing_user and existing_user.check_password(password)):
            return render_template('iniciosesion.html')
        login_user(existing_user, remember=True)
        access_token = create_access_token(identity=str(existing_user.id))
        print(f'Token JWT generado: {access_token}')
        return redirect(url_for('catalog.perfil'))
    
    return render_template('iniciosesion.html')

@catalog.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('catalog.index'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '')
        correo = request.form.get('correo', '')
        password = request.form.get('password', '')
        
        if (nombre and password and correo):
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


# ============= API RESTFUL - SERVICIOS =============
class ServiciosApi(Resource):
    """
    API RESTful para gestión de servicios (catálogo de servicios disponibles)
    
    Endpoints:
    - GET /api/servicios - Lista todos los servicios disponibles
    - GET /api/servicios/<id> - Obtiene un servicio específico
    - POST /api/servicios - Crea un nuevo servicio
    - PUT /api/servicios/<id> - Actualiza un servicio
    - DELETE /api/servicios/<id> - Elimina un servicio
    """
    @jwt_required()
    def get(self, id=None):
        try:
            # GET /api/servicios - Listar todos
            if id is None:
                servicios = Servicios.query.all()
                if not servicios:
                    return {
                        'success': False,
                        'message': 'No hay servicios disponibles',
                        'data': []
                    }, 404

                res = []
                for s in servicios:
                    res.append({
                        'id': s.id,
                        'nombre': s.nombre,
                        'descripcion': s.descripcion
                    })
                
                return {
                    'success': True,
                    'count': len(res),
                    'data': res
                }, 200

            # GET /api/servicios/<id> - Obtener servicio específico
            servicio = Servicios.query.get(id)
            if not servicio:
                return {
                    'success': False,
                    'message': f'Servicio con id {id} no encontrado'
                }, 404

            return {
                'success': True,
                'data': {
                    'id': servicio.id,
                    'nombre': servicio.nombre,
                    'descripcion': servicio.descripcion
                }
            }, 200

        except Exception as e:
            return {
                'success': False,
                'error': 'Error interno del servidor',
                'message': str(e)
            }, 500
    @jwt_required()
    def post(self):
        """Crear un nuevo servicio"""
        try:
            args = servicio_parser.parse_args()

            # Verificar si ya existe
            existing = Servicios.query.filter_by(nombre=args['nombre']).first()
            if existing:
                return {
                    'success': False,
                    'message': f'El servicio "{args["nombre"]}" ya existe'
                }, 409

            servicio = Servicios(args['nombre'], args['descripcion'])
            db.session.add(servicio)
            db.session.commit()

            return {
                'success': True,
                'message': 'Servicio creado exitosamente',
                'data': {
                    'id': servicio.id,
                    'nombre': servicio.nombre,
                    'descripcion': servicio.descripcion
                }
            }, 201

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': 'Error al crear el servicio',
                'message': str(e)
            }, 500
    @jwt_required()
    def put(self, id):
        """Actualizar un servicio"""
        try:
            args = servicio_parser.parse_args()

            servicio = Servicios.query.get(id)
            if not servicio:
                return {
                    'success': False,
                    'message': f'Servicio con id {id} no encontrado'
                }, 404

            servicio.nombre = args['nombre']
            servicio.descripcion = args['descripcion']
            db.session.commit()

            return {
                'success': True,
                'message': 'Servicio actualizado exitosamente',
                'data': {
                    'id': servicio.id,
                    'nombre': servicio.nombre,
                    'descripcion': servicio.descripcion
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': 'Error al actualizar el servicio',
                'message': str(e)
            }, 500
    @jwt_required()
    def delete(self, id):
        """Eliminar un servicio"""
        try:
            servicio = Servicios.query.get(id)
            if not servicio:
                return {
                    'success': False,
                    'message': f'Servicio con id {id} no encontrado'
                }, 404

            # Verificar si tiene suscripciones activas
            suscripciones = usuario_servicios.query.filter_by(servicio_id=id).count()
            if suscripciones > 0:
                return {
                    'success': False,
                    'message': f'No se puede eliminar. Hay {suscripciones} usuarios suscritos a este servicio'
                }, 409

            nombre = servicio.nombre
            db.session.delete(servicio)
            db.session.commit()

            return {
                'success': True,
                'message': f'Servicio "{nombre}" eliminado exitosamente'
            }, 200

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': 'Error al eliminar el servicio',
                'message': str(e)
            }, 500


# ============= API RESTFUL - SUSCRIPCIONES (usuario_servicios) =============
class SuscripcionesApi(Resource):
    """
    API RESTful para gestión de suscripciones de usuarios a servicios
    
    Endpoints:
    - GET /api/suscripciones - Lista todas las suscripciones
    - GET /api/suscripciones/<id> - Obtiene una suscripción específica
    - POST /api/suscripciones - Crea una nueva suscripción
    - PUT /api/suscripciones/<id> - Actualiza una suscripción
    - DELETE /api/suscripciones/<id> - Elimina una suscripción
    """
    @jwt_required()
    def get(self, id=None):
        try:
            # GET /api/suscripciones - Listar todas
            if id is None:
                suscripciones = usuario_servicios.query.all()
                if not suscripciones:
                    return {
                        'success': False,
                        'message': 'No hay suscripciones',
                        'data': []
                    }, 404

                res = []
                for s in suscripciones:
                    res.append({
                        'id': s.id,
                        'usuario_id': s.usuario_id,
                        'usuario_nombre': s.usuario.nombre if s.usuario else None,
                        'servicio_id': s.servicio_id,
                        'servicio_nombre': s.servicio.nombre if s.servicio else None,
                        'nombre_servicio': s.nombre_servicio,
                        'costo': float(s.costo),
                        'renovacion': str(s.renovacion)
                    })
                
                return {
                    'success': True,
                    'count': len(res),
                    'data': res
                }, 200

            # GET /api/suscripciones/<id> - Obtener suscripción específica
            suscripcion = usuario_servicios.query.get(id)
            if not suscripcion:
                return {
                    'success': False,
                    'message': f'Suscripción con id {id} no encontrada'
                }, 404

            return {
                'success': True,
                'data': {
                    'id': suscripcion.id,
                    'usuario_id': suscripcion.usuario_id,
                    'usuario_nombre': suscripcion.usuario.nombre if suscripcion.usuario else None,
                    'servicio_id': suscripcion.servicio_id,
                    'servicio_nombre': suscripcion.servicio.nombre if suscripcion.servicio else None,
                    'nombre_servicio': suscripcion.nombre_servicio,
                    'costo': float(suscripcion.costo),
                    'renovacion': str(suscripcion.renovacion)
                }
            }, 200

        except Exception as e:
            return {
                'success': False,
                'error': 'Error interno del servidor',
                'message': str(e)
            }, 500
    @jwt_required()
    def post(self):
        """Crear una nueva suscripción"""
        try:
            args = usuario_servicio_parser.parse_args()

            # Verificar que el usuario existe
            usuario = Usuarios.query.get(args['usuario_id'])
            if not usuario:
                return {
                    'success': False,
                    'message': f'Usuario con id {args["usuario_id"]} no encontrado'
                }, 404

            # Verificar que el servicio existe
            servicio = Servicios.query.get(args['servicio_id'])
            if not servicio:
                return {
                    'success': False,
                    'message': f'Servicio con id {args["servicio_id"]} no encontrado'
                }, 404

            # Calcular fecha de renovación (1 año desde hoy)
            fecha_actual = date.today()
            renovacion = fecha_actual + timedelta(days=365)

            nueva_suscripcion = usuario_servicios(
                args['usuario_id'],
                args['servicio_id'],
                args['nombre_servicio'],
                args['costo'],
                renovacion
            )

            db.session.add(nueva_suscripcion)
            db.session.commit()

            return {
                'success': True,
                'message': 'Suscripción creada exitosamente',
                'data': {
                    'id': nueva_suscripcion.id,
                    'usuario_id': nueva_suscripcion.usuario_id,
                    'servicio_id': nueva_suscripcion.servicio_id,
                    'nombre_servicio': nueva_suscripcion.nombre_servicio,
                    'costo': float(nueva_suscripcion.costo),
                    'renovacion': str(nueva_suscripcion.renovacion)
                }
            }, 201

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': 'Error al crear la suscripción',
                'message': str(e)
            }, 500
    @jwt_required()
    def put(self, id):
        """Actualizar una suscripción"""
        try:
            suscripcion = usuario_servicios.query.get(id)
            if not suscripcion:
                return {
                    'success': False,
                    'message': f'Suscripción con id {id} no encontrada'
                }, 404

            # Parser parcial para actualización
            parser = reqparse.RequestParser()
            parser.add_argument('nombre_servicio', type=str, required=False)
            parser.add_argument('costo', type=float, required=False)
            args = parser.parse_args()

            # Actualizar solo los campos proporcionados
            if args['nombre_servicio']:
                suscripcion.nombre_servicio = args['nombre_servicio']
            if args['costo']:
                suscripcion.costo = args['costo']

            db.session.commit()

            return {
                'success': True,
                'message': 'Suscripción actualizada exitosamente',
                'data': {
                    'id': suscripcion.id,
                    'nombre_servicio': suscripcion.nombre_servicio,
                    'costo': float(suscripcion.costo),
                    'renovacion': str(suscripcion.renovacion)
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': 'Error al actualizar la suscripción',
                'message': str(e)
            }, 500
    @jwt_required()
    def delete(self, id):
        """Eliminar una suscripción"""
        try:
            suscripcion = usuario_servicios.query.get(id)
            if not suscripcion:
                return {
                    'success': False,
                    'message': f'Suscripción con id {id} no encontrada'
                }, 404

            nombre = suscripcion.nombre_servicio
            db.session.delete(suscripcion)
            db.session.commit()

            return {
                'success': True,
                'message': f'Suscripción "{nombre}" eliminada exitosamente'
            }, 200

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': 'Error al eliminar la suscripción',
                'message': str(e)
            }, 500


# ============= API RESTFUL - CONTACTO =============
class ContactoApi(Resource):
    """
    API RESTful para mensajes de contacto
    
    Endpoints:
    - GET /api/contacto - Lista todos los mensajes
    - GET /api/contacto/<id> - Obtiene un mensaje específico
    - POST /api/contacto - Crea un nuevo mensaje
    - DELETE /api/contacto/<id> - Elimina un mensaje
    """
    @jwt_required()
    def get(self, id=None):
        try:
            if id is None:
                mensajes = contacto.query.all()
                if not mensajes:
                    return {
                        'success': False,
                        'message': 'No hay mensajes de contacto',
                        'data': []
                    }, 404

                res = []
                for m in mensajes:
                    res.append({
                        'id': m.id,
                        'correo': m.correo,
                        'asunto': m.asunto,
                        'texto': m.texto
                    })
                
                return {
                    'success': True,
                    'count': len(res),
                    'data': res
                }, 200

            mensaje = contacto.query.get(id)
            if not mensaje:
                return {
                    'success': False,
                    'message': f'Mensaje con id {id} no encontrado'
                }, 404

            return {
                'success': True,
                'data': {
                    'id': mensaje.id,
                    'correo': mensaje.correo,
                    'asunto': mensaje.asunto,
                    'texto': mensaje.texto
                }
            }, 200

        except Exception as e:
            return {
                'success': False,
                'error': 'Error interno del servidor',
                'message': str(e)
            }, 500
    @jwt_required()
    def post(self):
        """Crear un nuevo mensaje de contacto"""
        try:
            args = contacto_parser.parse_args()

            nuevo_mensaje = contacto(
                args['correo'],
                args['asunto'],
                args['texto']
            )

            db.session.add(nuevo_mensaje)
            db.session.commit()

            return {
                'success': True,
                'message': 'Mensaje enviado exitosamente',
                'data': {
                    'id': nuevo_mensaje.id,
                    'correo': nuevo_mensaje.correo,
                    'asunto': nuevo_mensaje.asunto
                }
            }, 201

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': 'Error al enviar el mensaje',
                'message': str(e)
            }, 500
    @jwt_required()
    def delete(self, id):
        """Eliminar un mensaje de contacto"""
        try:
            mensaje = contacto.query.get(id)
            if not mensaje:
                return {
                    'success': False,
                    'message': f'Mensaje con id {id} no encontrado'
                }, 404

            db.session.delete(mensaje)
            db.session.commit()

            return {
                'success': True,
                'message': 'Mensaje eliminado exitosamente'
            }, 200

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': 'Error al eliminar el mensaje',
                'message': str(e)
            }, 500


# ============= API RESTFUL - USUARIOS =============
class UsuariosApi(Resource):
    """
    API RESTful para usuarios (solo lectura por seguridad)
    
    Endpoints:
    - GET /api/usuarios - Lista todos los usuarios
    - GET /api/usuarios/<id> - Obtiene un usuario específico
    """
    @jwt_required()
    def get(self, id=None):
        try:
            if id is None:
                usuarios = Usuarios.query.all()
                if not usuarios:
                    return {
                        'success': False,
                        'message': 'No hay usuarios',
                        'data': []
                    }, 404

                res = []
                for u in usuarios:
                    res.append({
                        'id': u.id,
                        'nombre': u.nombre,
                        'correo': u.correo
                    })
                
                return {
                    'success': True,
                    'count': len(res),
                    'data': res
                }, 200

            usuario = Usuarios.query.get(id)
            if not usuario:
                return {
                    'success': False,
                    'message': f'Usuario con id {id} no encontrado'
                }, 404

            # Obtener suscripciones del usuario
            suscripciones = usuario_servicios.query.filter_by(usuario_id=id).all()
            suscripciones_data = []
            for s in suscripciones:
                suscripciones_data.append({
                    'id': s.id,
                    'servicio': s.nombre_servicio,
                    'costo': float(s.costo),
                    'renovacion': str(s.renovacion)
                })

            return {
                'success': True,
                'data': {
                    'id': usuario.id,
                    'nombre': usuario.nombre,
                    'correo': usuario.correo,
                    'suscripciones': suscripciones_data
                }
            }, 200

        except Exception as e:
            return {
                'success': False,
                'error': 'Error interno del servidor',
                'message': str(e)
            }, 500
        

    @catalog.route("/crear-suscripcion/<plan>")
    def crear_suscripcion(plan):
        precios = {
            "basic": "price_basic_annual",
            "essential": "price_essential_annual",
            "premium": "price_premium_annual"
        }

        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{
                "price": precios[plan],
                "quantity": 1
            }],
            success_url=url_for(
                "pago_exitoso",
                plan=plan,
                _external=True
            ) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://tuweb.com/cancelado"
        )

        return redirect(session.url)
    
    @catalog.route("/pago-exitoso/<plan>")
    def pago_exitoso(plan):
        session_id = request.args.get("session_id")
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status != "paid":
            return "Pago no completado", 400

        precios = {
            "basic": 15,
            "essential": 25,
            "premium": 50
        }

        usuario_id = session.client_reference_id

        # 1️⃣ Verificar si el usuario ya tiene una suscripción activa
        suscripcion_existente = usuario_servicios.query.filter_by(usuario_id=usuario_id).order_by(usuario_servicios.id.desc()).first()

        if suscripcion_existente:
            # No puede volver a comprar la misma suscripción
            if suscripcion_existente.nombre_servicio.lower() == plan.lower():
                return "Ya tienes esta suscripción activa", 400
            # Si es un upgrade
            upgrade_map = {"basic": 1, "essential": 2, "premium": 3}
            if upgrade_map[plan.lower()] <= upgrade_map[suscripcion_existente.nombre_servicio.lower()]:
                return "No puedes bajar de plan", 400
            # Opcional: marcar como inactiva la suscripción anterior
            # suscripcion_existente.activa = False
            # db.session.commit()

        # 2️⃣ Crear un servicio único para este usuario
        nuevo_servicio = Servicios(
            nombre=f"{plan.capitalize()} - Usuario {usuario_id}",
            descripcion=f"Suscripción anual {plan.capitalize()} {precios[plan]}€"
        )
        db.session.add(nuevo_servicio)
        db.session.commit()

        # 3️⃣ Guardar en usuario_servicios conectando el servicio único
        nueva_suscripcion = usuario_servicios(
            usuario_id=usuario_id,
            servicio_id=nuevo_servicio.id,
            nombre_servicio=plan.capitalize(),
            costo=precios[plan],
            renovacion="anual"
        )

        db.session.add(nueva_suscripcion)
        db.session.commit()

        return f"Suscripción {plan.capitalize()} activada correctamente"


# ============= REGISTRO DE RECURSOS API =============
# Servicios (catálogo)
api.add_resource(ServiciosApi,
                 '/api/servicios',
                 '/api/servicios/<int:id>')

# Suscripciones (usuario_servicios)
api.add_resource(SuscripcionesApi,
                 '/api/suscripciones',
                 '/api/suscripciones/<int:id>')

# Contacto
api.add_resource(ContactoApi,
                 '/api/contacto',
                 '/api/contacto/<int:id>')

# Usuarios
api.add_resource(UsuariosApi,
                 '/api/usuarios',
                 '/api/usuarios/<int:id>')