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
import os
from dotenv import load_dotenv
import google.generativeai as genai
import time
from functools import wraps

# Cargar variables del archivo .env
load_dotenv() 

# Configuración de la clave secreta de Stripe desde .env
stripe.api_key = os.getenv('STRIPE_API_KEY')

# Configuración de Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Sistema de caché y throttling para Gemini
_chat_cache = {}
_last_request_time = {}
MIN_INTERVAL_SECONDS = 5  # Mínimo 5 segundos entre solicitudes (para cuentas nuevas de Gemini)


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


@catalog.route('/api/chat', methods=['POST', 'GET'])
def chat():
    """Endpoint para chat con Gemini AI con throttling y caché
    
    GET: /api/chat?message=tu%20mensaje
    POST: {"message": "tu mensaje"}
    """
    try:
        user_message = ""
        
        # Obtener mensaje desde JSON o parámetros
        if request.method == 'POST':
            if request.json:
                user_message = request.json.get("message", "").strip()
        else:  # GET
            user_message = request.args.get("message", "").strip()
        
        if not user_message:
            return jsonify({
                "error": "No message provided",
                "usage": {
                    "GET": "/api/chat?message=tu%20mensaje",
                    "POST": '{"message": "tu mensaje"}'
                }
            }), 400

        # Obtener ID de usuario o IP para throttling
        user_id = str(current_user.id) if current_user.is_authenticated else request.remote_addr
        
        # Verificar throttling
        current_time = time.time()
        if user_id in _last_request_time:
            time_elapsed = current_time - _last_request_time[user_id]
            if time_elapsed < MIN_INTERVAL_SECONDS:
                wait_time = MIN_INTERVAL_SECONDS - time_elapsed
                return jsonify({
                    "error": f"Por favor espera {wait_time:.1f} segundos antes de hacer otra solicitud",
                    "wait_seconds": wait_time
                }), 429
        
        # Verificar caché
        cache_key = f"{user_id}:{user_message}"
        if cache_key in _chat_cache:
            return jsonify({"message": _chat_cache[cache_key], "cached": True})

        # Usar el modelo de Gemini disponible con reintentos
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Reintentos con backoff exponencial para manejar errores 429
        max_retries = 3
        retry_delay = 1
        bot_message = None
        
        for attempt in range(max_retries):
            try:
                response = model.generate_content(user_message)
                bot_message = response.text
                break
            except Exception as retry_error:
                error_str = str(retry_error)
                if "429" in error_str or "quota" in error_str.lower():
                    if attempt < max_retries - 1:
                        print(f"Intento {attempt + 1} falló, reintentando en {retry_delay} segundos...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Backoff exponencial
                    else:
                        return jsonify({
                            "error": "Se excedió el límite de uso de la API de Gemini. Intenta más tarde.",
                            "retry_after": 60
                        }), 429
                else:
                    raise retry_error
        
        # Guardar en caché y actualizar tiempo
        _chat_cache[cache_key] = bot_message
        _last_request_time[user_id] = current_time
        
        # Limpiar caché antiguo si crece demasiado
        if len(_chat_cache) > 100:
            _chat_cache.clear()
        
        return jsonify({"message": bot_message})
    except Exception as e:
        error_str = str(e)
        print(f"Error en chat: {error_str}")
        
        # Mejorar mensaje de error para el usuario
        if "429" in error_str or "quota" in error_str.lower():
            return jsonify({
                "error": "Se excedió el límite de uso de la API de Gemini. Intenta más tarde.",
                "retry_after": 60
            }), 429
        elif "401" in error_str or "unauthorized" in error_str.lower():
            return jsonify({
                "error": "Error de autenticación con Gemini API. Verifica tu clave API."
            }), 401
        else:
            return jsonify({"error": error_str}), 500


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
        # Detectar si es JSON (API) o form data (HTML)
        if request.is_json:
            correo = request.json.get('email', '')
            password = request.json.get('password', '')
        else:
            correo = request.form.get('email', '')
            password = request.form.get('contraseña', '')
        
        existing_user = Usuarios.query.filter_by(correo=correo).first()

        if not (existing_user and existing_user.check_password(password)):
            if request.is_json:
                return jsonify({'success': False, 'error': 'Credenciales inválidas'}), 401
            return render_template('iniciosesion.html')
        
        login_user(existing_user, remember=True)
        access_token = create_access_token(identity=str(existing_user.id))
        print(f'Token JWT generado: {access_token}')
        
        # Si es JSON, devolver token
        if request.is_json:
            return jsonify({
                'success': True,
                'token': access_token,
                'user_id': existing_user.id,
                'nombre': existing_user.nombre
            }), 200
        
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


@catalog.route("/perfil")
@login_required
def perfil():
    servicio = usuario_servicios.query.filter_by(usuario_id=current_user.id).all()
    return render_template('perfil.html', servicios=servicio)


@catalog.route('/inicio', methods=['GET', 'POST'])
def inicio():
    return render_template('iniciosesion.html')


PRODUCTOS = {
    "price_1Sq8BYCsm3x3qNyuNTqUuaZY": {"nombre": "Basic", "precio": 15},
    "price_1Sq8CqCsm3x3qNyu2r4B9J7E": {"nombre": "Essential", "precio": 25},
    "price_1Sq8DRCsm3x3qNyu8nXutWZP": {"nombre": "Premium", "precio": 50},
}

@catalog.route("/crear-suscripcion/<price_id>")
@login_required
def crear_suscripcion(price_id):
    panel_id = request.args.get("panel_id")
    
    if not panel_id:
        return "Panel ID requerido", 400
    
    if price_id not in PRODUCTOS:
        return "Producto no válido", 400

    # Verificar si ya tiene una suscripción en ESTE panel específico
    suscripcion_existente = usuario_servicios.query.filter_by(
        usuario_id=current_user.id,
        servicio_id=panel_id
    ).first()
    
    if suscripcion_existente:
        # Permitir upgrade/downgrade guardando el tipo de acción
        accion = "upgrade"  # Puedes determinar esto comparando precios
        success_url = f"{request.host_url}suscripcion-exitosa/{price_id}?session_id={{CHECKOUT_SESSION_ID}}&panel_id={panel_id}&accion={accion}"
    else:
        # Nueva suscripción
        success_url = f"{request.host_url}suscripcion-exitosa/{price_id}?session_id={{CHECKOUT_SESSION_ID}}&panel_id={panel_id}&accion=nueva"

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=f"{request.host_url}",
        client_reference_id=f"{current_user.id}|{panel_id}"  # Incluir panel_id
    )

    return redirect(session.url, code=303)


@catalog.route("/suscripcion-exitosa/<price_id>")
@login_required
def suscripcion_exitosa(price_id):
    session_id = request.args.get("session_id")
    panel_id = request.args.get("panel_id")
    accion = request.args.get("accion", "nueva")
    
    if not session_id or not panel_id:
        return "Falta session_id o panel_id", 400

    session_obj = stripe.checkout.Session.retrieve(session_id)
    if session_obj.payment_status != "paid":
        return "Pago no completado", 400

    # Extraer usuario_id del client_reference_id
    usuario_id = session_obj.client_reference_id.split('|')[0]
    producto = PRODUCTOS[price_id]

    # Buscar suscripción existente en este panel
    suscripcion_existente = usuario_servicios.query.filter_by(
        usuario_id=usuario_id,
        servicio_id=panel_id
    ).first()

    if suscripcion_existente:
        # Actualizar el plan existente (upgrade/downgrade)
        suscripcion_existente.nombre_servicio = producto['nombre']
        suscripcion_existente.costo = producto['precio']
        mensaje = f"Plan mejorado a {producto['nombre']} correctamente"
    else:
        # Crear nueva suscripción para este panel
        nueva_suscripcion = usuario_servicios(
            usuario_id=usuario_id,
            servicio_id=panel_id,
            nombre_servicio=producto['nombre'],
            costo=producto['precio'],
            renovacion="anual"
        )
        db.session.add(nueva_suscripcion)
        mensaje = f"Suscripción {producto['nombre']} activada correctamente"
    
    db.session.commit()

    return mensaje


# Ruta adicional para ver todas las suscripciones del usuario
@catalog.route("/mis-suscripciones")
@login_required
def mis_suscripciones():
    suscripciones = usuario_servicios.query.filter_by(
        usuario_id=current_user.id
    ).all()
    
    # Aquí puedes renderizar una plantilla con todas las suscripciones
    # agrupadas por panel
    return render_template('mis_suscripciones.html', suscripciones=suscripciones)


# Ruta para cancelar una suscripción específica
@catalog.route("/cancelar-suscripcion/<int:servicio_id>")
@login_required
def cancelar_suscripcion(servicio_id):
    suscripcion = usuario_servicios.query.filter_by(
        usuario_id=current_user.id,
        servicio_id=servicio_id
    ).first()
    
    if not suscripcion:
        return "Suscripción no encontrada", 404
    
    # Aquí deberías también cancelar en Stripe si es necesario
    db.session.delete(suscripcion)
    db.session.commit()
    
    return redirect(url_for('catalog.mis_suscripciones'))



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