import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.http import require_POST

from .models import Usuario

# Constantes de plantillas
TEMPLATE_LOGIN = 'usuarios/login.html'
TEMPLATE_LISTA = 'usuarios/lista/lista_personal.html'
TEMPLATE_PERFIL = 'usuarios/panel_perfil.html'

# Instancias para restablecimiento de contraseña
token_generator = PasswordResetTokenGenerator()


# ==========================================
# VISTAS DE AUTENTICACIÓN Y REGISTRO
# ==========================================

def login_view(request):
    vista = request.GET.get('vista', 'login')
    if request.user.is_authenticated and vista == 'login':
        return redirect('inicio_usuarios')
    if request.method == 'POST':
        usuario_input = request.POST.get('username')
        password_input = request.POST.get('password')
        user = authenticate(request, username=usuario_input, password=password_input)
        if user is not None:
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redireccion_post_login(request)
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
            return render(request, TEMPLATE_LOGIN, {'vista': 'login'})
    context = {'vista': vista}
    return render(request, TEMPLATE_LOGIN, context)


def registro_view(request):
    """
    Registro público de usuarios: permite crear una cuenta nueva
    directamente desde la pantalla de login.
    """
    if request.user.is_authenticated:
        return redirect('inicio_usuarios')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        rol = request.POST.get('rol', 'MESERO').strip()

        ROLES_PERMITIDOS = ['MESERO', 'CAJERO']
        if rol not in ROLES_PERMITIDOS:
            rol = 'MESERO'

        errores = []
        if not first_name or not last_name or not username or not email or not password:
            errores.append('Todos los campos son obligatorios.')
        if password and password2 and password != password2:
            errores.append('Las contraseñas no coinciden.')
        if len(password) < 6:
            errores.append('La contraseña debe tener al menos 6 caracteres.')
        if username and Usuario.objects.filter(username=username).exists():
            errores.append('Ese nombre de usuario ya está en uso.')
        if email and Usuario.objects.filter(email=email).exists():
            errores.append('Ese correo electrónico ya está registrado.')

        if errores:
            for e in errores:
                messages.error(request, e)
            context = {
                'vista': 'registro',
                'form_data': request.POST,
            }
            return render(request, TEMPLATE_LOGIN, context)

        nuevo_usuario = Usuario.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email,
            rol=rol,
        )
        login(request, nuevo_usuario)
        messages.success(request, f'¡Bienvenido, {nuevo_usuario.first_name}! Tu cuenta fue creada correctamente.')
        return redireccion_post_login(request)

    context = {'vista': 'registro'}
    return render(request, TEMPLATE_LOGIN, context)


@login_required
def redireccion_post_login(request):
    if request.user.is_superuser or request.user.rol == 'ADMIN':
        return redirect('inicio_usuarios')
    return redirect('panel_perfil')


def logout_view(request):
    logout(request)
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('login')


# ==========================================
# VISTAS DE RECUPERACIÓN DE CONTRASEÑA
# ==========================================

def recuperar_password(request):
    """
    Vista GET: muestra el formulario para pedir el correo.
    Vista POST: si el correo existe, envía el enlace de recuperación.
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        usuario = Usuario.objects.filter(email__iexact=email).first()

        if usuario:
            uid = urlsafe_base64_encode(force_bytes(usuario.pk))
            token = token_generator.make_token(usuario)
            dominio = get_current_site(request).domain
            enlace = f"http://{dominio}{reverse('restablecer_password', kwargs={'uidb64': uid, 'token': token})}"

            mensaje_html = render_to_string('usuarios/correo_recuperacion.html', {
                'usuario': usuario,
                'enlace': enlace,
            })

            send_mail(
                subject="Recupera tu contraseña - Porras Asadero",
                message="",
                from_email=None,  # usa DEFAULT_FROM_EMAIL de settings.py
                recipient_list=[usuario.email],
                html_message=mensaje_html,
            )

        # Se muestra siempre el mismo mensaje para no revelar qué correos existen
        return render(request, 'usuarios/recuperar_password.html', {'vista': 'enviado', 'email': email})

    return render(request, 'usuarios/recuperar_password.html')


def restablecer_password(request, uidb64, token):
    """
    Valida el enlace (uidb64 + token) y permite establecer la nueva contraseña.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        usuario = Usuario.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        usuario = None

    validlink = usuario is not None and token_generator.check_token(usuario, token)

    if request.method == 'POST' and validlink:
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        if password != password2:
            messages.error(request, "Las contraseñas no coinciden.")
        elif len(password) < 6:
            messages.error(request, "La contraseña debe tener mínimo 6 caracteres.")
        else:
            usuario.set_password(password)
            usuario.save()
            return render(request, 'usuarios/restablecer_password.html', {
                'vista': 'exitoso',
                'validlink': True
            })

    return render(request, 'usuarios/restablecer_password.html', {
        'vista': 'reset',  # Evita renderizar la plantilla con el menú lateral
        'validlink': validlink,
        'uidb64': uidb64,
        'token': token,
    })


# ==========================================
# VISTAS DE ADMINISTRACIÓN DE USUARIOS Y PERFIL
# ==========================================

@login_required
def inicio_usuarios(request):
    usuarios = Usuario.objects.all()
    context = {
        'vista': 'inicio',
        'usuarios': usuarios,
    }
    return render(request, TEMPLATE_LOGIN, context)


@login_required
def lista_personal(request):
    if request.user.rol != 'ADMIN' and not request.user.is_superuser:
        return redirect('validar_permisos')

    personal = Usuario.objects.all()

    personal_json = json.dumps([
        {
            'id': u.id,
            'nom': u.first_name,
            'ape': u.last_name,
            'email': u.email,
            'user': u.username,
            'rol': u.rol,
            'e': 'activo' if u.is_active else 'inactivo',
            'tel': getattr(u, 'telefono', '') or '',
            'doc': getattr(u, 'documento', '') or '',
            'tdoc': getattr(u, 'tipo_documento', '') or '',
            'dir': getattr(u, 'direccion', '') or '',
            'foto': u.foto.url if u.foto else '',
            'notas': '',
            'perms': [],
            'acc': '-',
            'cr': u.date_joined.isoformat() if hasattr(u, 'date_joined') else '',
        }
        for u in personal
    ])

    context = {
        'vista': 'lista',
        'personal_list': personal,
        'personal_list_json': personal_json,
    }
    return render(request, TEMPLATE_LISTA, context)


@login_required
@require_POST
def crear_usuario(request):
    if request.user.rol != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    try:
        data = json.loads(request.body)
        if not data.get('nom') or not data.get('ape') or not data.get('email') \
                or not data.get('user') or not data.get('rol'):
            return JsonResponse({'ok': False, 'error': 'Faltan campos obligatorios'}, status=400)
        if Usuario.objects.filter(username=data['user']).exists():
            return JsonResponse({'ok': False, 'error': 'Ese nombre de usuario ya existe'}, status=400)
        ROL_MAP = {
            'Administrador': 'ADMIN',
            'Mesero': 'MESERO',
            'Cajero': 'CAJERO',
            'Cocina': 'COCINA',
        }
        nuevo = Usuario.objects.create_user(
            username=data['user'],
            password=data.get('pw', 'cambiar123'),
            first_name=data['nom'],
            last_name=data['ape'],
            email=data['email'],
            telefono=data.get('tel', ''),
            tipo_documento=data.get('tdoc', ''),
            documento=data.get('doc', ''),
            rol=ROL_MAP.get(data['rol'], 'MESERO'),
            is_active=data.get('e', 'activo') == 'activo',
        )
        if hasattr(nuevo, 'direccion'):
            nuevo.direccion = data.get('dir', '')
            nuevo.save()
        return JsonResponse({'ok': True, 'id': nuevo.pk})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def editar_usuario_json(request, id):
    if request.user.rol != 'ADMIN' and not request.user.is_superuser and request.user.id != id:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    try:
        data = json.loads(request.body)
        usuario = get_object_or_404(Usuario, pk=id)
        ROL_MAP = {
            'Administrador': 'ADMIN',
            'Mesero': 'MESERO',
            'Cajero': 'CAJERO',
            'Cocina': 'COCINA',
        }
        usuario.first_name = data.get('nom', usuario.first_name)
        usuario.last_name = data.get('ape', usuario.last_name)
        usuario.email = data.get('email', usuario.email)
        usuario.telefono = data.get('tel', '')
        usuario.tipo_documento = data.get('tdoc', '')
        usuario.documento = data.get('doc', '')
        usuario.is_active = data.get('e', 'activo') == 'activo'
        if request.user.rol == 'ADMIN' or request.user.is_superuser:
            usuario.rol = ROL_MAP.get(data.get('rol', ''), usuario.rol)
        if hasattr(usuario, 'direccion'):
            usuario.direccion = data.get('dir', '')
        usuario.save()
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


@login_required
def eliminar_usuario(request, id):
    if request.user.rol != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403) \
            if request.headers.get('Content-Type') == 'application/json' \
            else redirect('validar_permisos')
    usuario = get_object_or_404(Usuario, id=id)
    if request.method == 'POST':
        if usuario.id == request.user.id:
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({'ok': False, 'error': 'No puedes eliminar tu propia cuenta'}, status=400)
            messages.error(request, 'No puedes eliminar tu propia cuenta.')
            return redirect('lista_personal')
        nombre = f'{usuario.first_name} {usuario.last_name}'
        usuario.delete()
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({'ok': True})
        messages.success(request, f'Usuario {nombre} eliminado correctamente.')
        return redirect('lista_personal')
    return redirect('lista_personal')


@login_required
def inactivar_usuario(request):
    if request.user.rol == 'ADMIN' or request.user.is_superuser:
        username = request.GET.get('username')
        if username:
            usuario = get_object_or_404(Usuario, username=username)
            usuario.is_active = False
            usuario.save()
            messages.warning(request, f'Usuario {username} inactivado.')
    return redirect('lista_personal')


@login_required
def panel_perfil(request):
    context = {'usuario': request.user}
    return render(request, TEMPLATE_PERFIL, context)


def validar_permisos(request):
    context = {'vista': 'sin_permisos'}
    return render(request, TEMPLATE_LOGIN, context)


def acceder_sistema(request):
    if not Usuario.objects.filter(username='restaurante').exists():
        Usuario.objects.create_superuser(
            username='restaurante',
            password='porras_123',
            first_name='Administrador',
            rol='ADMIN',
        )
    return redirect('login')


@login_required
def actualizar_usuario(request, pk):
    if request.user.id != pk and request.user.rol != 'ADMIN' and not request.user.is_superuser:
        return redirect('validar_permisos')
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        usuario.first_name = request.POST.get('first_name', usuario.first_name)
        usuario.last_name = request.POST.get('last_name', usuario.last_name)
        usuario.email = request.POST.get('email', usuario.email)
        usuario.telefono = request.POST.get('telefono', '')
        usuario.tipo_documento = request.POST.get('tipo_documento', '')
        usuario.documento = request.POST.get('documento', '')
        if request.user.rol == 'ADMIN' or request.user.is_superuser:
            usuario.rol = request.POST.get('rol', usuario.rol)
        usuario.save()
        messages.success(request, 'Datos actualizados correctamente.')
        return redirect('panel_perfil')
    context = {
        'vista': 'actualizar',
        'usuario': usuario,
    }
    return render(request, TEMPLATE_LOGIN, context)


@login_required
@require_POST
def actualizar_foto(request, pk):
    if request.user.id != pk and request.user.rol != 'ADMIN' and not request.user.is_superuser:
        return redirect('validar_permisos')
    usuario = get_object_or_404(Usuario, pk=pk)
    if 'foto' in request.FILES:
        usuario.foto = request.FILES['foto']
        usuario.save()
        messages.success(request, 'Foto de perfil actualizada.')
    else:
        messages.warning(request, 'No se recibió ninguna imagen.')
    return redirect('panel_perfil')