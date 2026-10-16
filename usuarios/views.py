import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout, get_user_model, update_session_auth_hash
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

from .forms import PersonalForm, RegistroForm, _validar_nombre
from .models import Usuario

# Constantes de plantillas
TEMPLATE_LOGIN = 'usuarios/login.html'
TEMPLATE_LISTA = 'usuarios/lista/lista_personal.html'
TEMPLATE_PERFIL = 'usuarios/panel_perfil.html'

# Instancias para restablecimiento de contraseña
token_generator = PasswordResetTokenGenerator()

# ==========================================
# MAPEOS ENTRE EL FRONTEND (JS) Y EL MODELO
# ==========================================
# El JS usa nombres "bonitos"; el modelo guarda códigos.
ROL_MAP = {
    'Administrador': 'ADMIN',
    'Mesero': 'MESERO',
    'Cajero': 'CAJERO',
    'Cocina': 'COCINERA',   # el modelo usa COCINERA, no COCINA
}
ROL_INV = {v: k for k, v in ROL_MAP.items()}

TDOC_MAP = {
    'Cédula de Ciudadanía': 'CC',
    'Cédula de Extranjería': 'CE',
    'Tarjeta de Identidad': 'TI',
    'Pasaporte': 'PP',
}
TDOC_INV = {v: k for k, v in TDOC_MAP.items()}


def _es_admin(user):
    return user.is_superuser or user.rol == 'ADMIN'


def _datos_form_desde_json(data, base=None):
    """
    Convierte el JSON del frontend en los campos que espera PersonalForm.
    `base` es el usuario existente (al editar) para usar sus valores como respaldo.
    """
    return {
        'first_name': (data.get('nom') or '').strip(),
        'last_name': (data.get('ape') or '').strip(),
        'username': (data.get('user') or (base.username if base else '')).strip(),
        'email': (data.get('email') or '').strip(),
        'telefono': (data.get('tel') or '').strip(),
        'rol': ROL_MAP.get(data.get('rol'), base.rol if base else ''),
        'tipo_documento': TDOC_MAP.get(data.get('tdoc'), 'CC'),
        'documento': (data.get('doc') or '').strip(),
        'is_active': data.get('e', 'activo') == 'activo',
    }


def _errores_a_texto(form):
    return '; '.join(
        f'{campo}: {", ".join(errores)}' for campo, errores in form.errors.items()
    )


def _usuario_a_dict(u):
    """Formato que espera el JavaScript de la plantilla (personal_list_json)."""
    return {
        'id': u.id,
        'nom': u.first_name,
        'ape': u.last_name,
        'email': u.email,
        'user': u.username,
        'rol': ROL_INV.get(u.rol, u.rol),
        'e': 'activo' if u.is_active else 'inactivo',
        'tel': getattr(u, 'telefono', '') or '',
        'doc': getattr(u, 'documento', '') or '',
        'tdoc': TDOC_INV.get(getattr(u, 'tipo_documento', ''), ''),
        'dir': getattr(u, 'direccion', '') or '',
        'foto': u.foto.url if u.foto else '',
        'notas': '',
        'perms': [],
        'acc': u.last_login.strftime('%d/%m/%Y %H:%M') if u.last_login else '—',
        'cr': u.date_joined.isoformat() if hasattr(u, 'date_joined') else '',
    }


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

        if '@' in usuario_input:
            usuario_obj = Usuario.objects.filter(email__iexact=usuario_input).first()
            if usuario_obj:
                usuario_input = usuario_obj.username

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
        form = RegistroForm(request.POST)
        rol = request.POST.get('rol', 'MESERO').strip()

        ROLES_PERMITIDOS = ['MESERO', 'CAJERO', 'COCINERA']
        if rol not in ROLES_PERMITIDOS:
            rol = 'MESERO'

        if form.is_valid():
            nuevo_usuario = Usuario.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                rol=rol,
            )
            login(request, nuevo_usuario)
            messages.success(
                request,
                f'¡Bienvenido, {nuevo_usuario.first_name}! Tu cuenta fue creada correctamente.'
            )
            return redireccion_post_login(request)

        for field, errores in form.errors.items():
            for error in errores:
                messages.error(request, f'{error}')

        context = {
            'vista': 'registro',
            'form': form,
            'form_data': request.POST,
        }
        return render(request, TEMPLATE_LOGIN, context)

    context = {'vista': 'registro', 'form': RegistroForm()}
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
    if request.user.rol == 'COCINERA' and not request.user.is_superuser:
        return redirect('pedidos:orden_lista')
    usuarios = Usuario.objects.all()
    context = {
        'vista': 'inicio',
        'usuarios': usuarios,
    }
    return render(request, TEMPLATE_LOGIN, context)


@login_required
def lista_personal(request):
    if not _es_admin(request.user):
        return redirect('validar_permisos')

    personal = Usuario.objects.all().order_by('id')
    personal_json = json.dumps([_usuario_a_dict(u) for u in personal])

    context = {
        'vista': 'lista',
        'personal_list': personal,
        'personal_list_json': personal_json,
    }
    return render(request, TEMPLATE_LISTA, context)


@login_required
@require_POST
def crear_usuario(request):
    if not _es_admin(request.user):
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    form = PersonalForm(_datos_form_desde_json(data))
    if not form.is_valid():
        return JsonResponse({'ok': False, 'error': _errores_a_texto(form)}, status=400)

    # Acepta 'password' (nuevo) o 'pw' (anterior); ya no se usa contraseña por defecto
    password = data.get('password') or data.get('pw') or ''
    if len(password) < 6:
        return JsonResponse(
            {'ok': False, 'error': 'password: La contraseña debe tener al menos 6 caracteres.'},
            status=400
        )

    try:
        nuevo = form.save(commit=False)
        nuevo.set_password(password)
        nuevo.save()
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)

    return JsonResponse({'ok': True, 'id': nuevo.pk})


@login_required
@require_POST
def editar_usuario_json(request, id):
    es_admin = _es_admin(request.user)
    if not es_admin and request.user.id != id:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    usuario = get_object_or_404(Usuario, pk=id)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    datos = _datos_form_desde_json(data, base=usuario)

    # Un usuario que no es admin y se edita a sí mismo no puede cambiar
    # su propio rol, usuario ni estado.
    if not es_admin:
        datos['rol'] = usuario.rol
        datos['username'] = usuario.username
        datos['is_active'] = usuario.is_active

    form = PersonalForm(datos, instance=usuario)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'error': _errores_a_texto(form)}, status=400)

    nuevo_pw = data.get('password') or ''
    if nuevo_pw and len(nuevo_pw) < 6:
        return JsonResponse(
            {'ok': False, 'error': 'password: La contraseña debe tener al menos 6 caracteres.'},
            status=400
        )

    try:
        usuario = form.save(commit=False)
        if nuevo_pw:
            usuario.set_password(nuevo_pw)
        usuario.save()
        # Si el usuario cambió su propia contraseña, mantener la sesión abierta
        if nuevo_pw and usuario.pk == request.user.pk:
            update_session_auth_hash(request, usuario)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)

    return JsonResponse({'ok': True, 'id': usuario.pk})


@login_required
def eliminar_usuario(request, id):
    if not _es_admin(request.user):
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
    if _es_admin(request.user):
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
    if request.user.id != pk and not _es_admin(request.user):
        return redirect('validar_permisos')
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        usuario.first_name = request.POST.get('first_name', usuario.first_name)
        usuario.last_name = request.POST.get('last_name', usuario.last_name)
        usuario.email = request.POST.get('email', usuario.email)
        usuario.telefono = request.POST.get('telefono', '') or None
        usuario.tipo_documento = request.POST.get('tipo_documento', usuario.tipo_documento)
        usuario.documento = request.POST.get('documento', '') or None
        if _es_admin(request.user):
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
    if request.user.id != pk and not _es_admin(request.user):
        return redirect('validar_permisos')
    usuario = get_object_or_404(Usuario, pk=pk)
    if 'foto' in request.FILES:
        usuario.foto = request.FILES['foto']
        usuario.save()
        messages.success(request, 'Foto de perfil actualizada.')
    else:
        messages.warning(request, 'No se recibió ninguna imagen.')
    return redirect('panel_perfil')