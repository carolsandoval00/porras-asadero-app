from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
from .models import Usuario

# Definimos las rutas de los templates según tu estructura de carpetas
TEMPLATE_LOGIN = 'usuarios/login.html'
TEMPLATE_LISTA = 'usuarios/lista/lista_personal.html'
TEMPLATE_PERFIL = 'usuarios/panel_perfil.html'

# --- LOGIN Y FLUJO DE ACCESO ---

def login_view(request):
    vista = request.GET.get('vista', 'login')

    if request.user.is_authenticated and vista == 'login':
        return redirect('inicio_usuarios')

    if request.method == 'POST':
        if vista in ['login', 'acceder', None]:
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

    return render(request, TEMPLATE_LOGIN, {'vista': vista})

@login_required
def redireccion_post_login(request):
    if request.user.is_superuser or request.user.rol == 'ADMIN':
        return redirect('inicio_usuarios')
    return redirect('panel_perfil')

def logout_view(request):
    logout(request)
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect('login')


# --- GESTIÓN DE PERSONAL (CRUD) ---

@login_required
def inicio_usuarios(request):
    usuarios = Usuario.objects.all()
    return render(request, TEMPLATE_LOGIN, {'vista': 'inicio', 'usuarios': usuarios})

@login_required
def lista_personal(request):
    if request.user.rol != 'ADMIN' and not request.user.is_superuser:
        return redirect('validar_permisos')
    
    personal = Usuario.objects.all()
    return render(request, TEMPLATE_LISTA, {
        'vista': 'lista', 
        'personal_list': personal
    })

@login_required
def registrar_personal(request):
    if request.method == "POST":
        data = request.POST
        if Usuario.objects.filter(username=data.get('username')).exists():
            messages.error(request, 'El nombre de usuario ya existe.')
        else:
            nuevo_usuario = Usuario.objects.create_user(
                username=data.get('username'),
                password=data.get('password'),
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                email=data.get('email'),
                telefono=data.get('telefono'),
                tipo_documento=data.get('tipo_documento'),
                documento=data.get('documento'),
                rol=data.get('rol', 'MESERO'),
            )
            messages.success(request, f'Usuario {nuevo_usuario.username} creado con éxito.')
            return redirect('lista_personal')

    return render(request, TEMPLATE_LOGIN, {'vista': 'registrar'})

@login_required
def actualizar_usuarios(request, id):
    if request.user.rol != 'ADMIN' and not request.user.is_superuser and request.user.id != id:
        return redirect('validar_permisos')

    usuario_edit = get_object_or_404(Usuario, id=id)
    if request.method == "POST":
        data = request.POST
        usuario_edit.first_name = data.get('first_name')
        usuario_edit.last_name = data.get('last_name')
        usuario_edit.email = data.get('email')
        usuario_edit.telefono = data.get('telefono')
        usuario_edit.tipo_documento = data.get('tipo_documento')
        usuario_edit.documento = data.get('documento')
        
        if request.user.rol == 'ADMIN' or request.user.is_superuser:
            usuario_edit.rol = data.get('rol')
            
        usuario_edit.save()
        messages.success(request, 'Datos actualizados correctamente.')
        return redirect('lista_personal')

    return render(request, TEMPLATE_LOGIN, {'vista': 'actualizar', 'usuario': usuario_edit})

@login_required
def inicio_usuarios(request):
    usuarios = Usuario.objects.all()
    return render(request, TEMPLATE_LISTA, {'vista': 'inicio', 'usuarios': usuarios})

@login_required
def panel_perfil(request):
    return render(request, TEMPLATE_PERFIL, {'usuario': request.user})

def validar_permisos(request):
    return render(request, TEMPLATE_LOGIN, {'vista': 'sin_permisos'})

def acceder_sistema(request):
    if not Usuario.objects.filter(username="restaurante").exists():
        Usuario.objects.create_superuser(
            username="restaurante", 
            password="porras_123", 
            first_name="Administrador",
            rol='ADMIN'
        )
    return redirect('login')

@login_required
def inicio_usuarios(request):
    usuarios = Usuario.objects.all()
    return render(request, TEMPLATE_LOGIN, {'vista': 'inicio', 'usuarios': usuarios})

@login_required
def inactivar_usuario(request):
    if request.user.rol == 'ADMIN' or request.user.is_superuser:
        username = request.GET.get('username')
        if username:
            usuario = get_object_or_404(Usuario, username=username)
            usuario.is_active = False
            usuario.save()
            messages.warning(request, f"Usuario {username} inactivado.")
    return redirect('lista_personal')

class CustomPasswordResetView(PasswordResetView):
    template_name = TEMPLATE_LOGIN
    success_url = reverse_lazy('password_reset_done')
    extra_context = {'vista': 'recuperar'}