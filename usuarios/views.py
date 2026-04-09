from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy

# 1. Inicio
@login_required
def inicio_usuarios(request):
    usuarios = User.objects.all()
    return render(request, 'usuarios/inicio_usuarios.html', {'usuarios': usuarios})


# 2. Detalle usuario
class DetalleUsuarioView(DetailView):
    model = User
    template_name = 'usuarios/detalle_usuario.html'
    context_object_name = 'usuario'


# 3. Reset contraseña
class CustomPasswordResetView(PasswordResetView):
    template_name = 'usuarios/password_reset.html'
    email_template_name = 'usuarios/password_reset_email.html'
    success_url = reverse_lazy('recuperar_enviado')


# 4. Inactivar usuario
@login_required
def inactivar_usuario(request):
    username = request.GET.get('username')
    if username:
        usuario = get_object_or_404(User, username=username)
        usuario.is_active = False
        usuario.save()
        messages.success(request, f"Usuario {username} inactivado.")
    return redirect('inicio_usuarios')


# 5. Registrar personal (pendiente lógica)
@login_required
def registrar_personal(request):
    if request.method == "POST":
        # lógica de creación aquí
        pass
    return render(request, 'usuarios/registrar_personal.html')


# 6. Lista personal
@login_required
def lista_personal(request):
    personal = User.objects.filter(is_staff=True)
    return render(request, 'usuarios/lista_personal.html', {'personal': personal})


# 7. Consultar usuario
def consultar_usuario(request):
    usuario = None
    username = request.GET.get('username')

    if username:
        try:
            usuario = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, "Usuario no encontrado")

    return render(request, 'usuarios/consultar_usuario.html', {'usuario': usuario})


# 8. Login
def acceder_sistema(request):

    # crear usuario por defecto si no existe
    if not User.objects.filter(username="restaurante").exists():
        User.objects.create_user(username="restaurante", password="porras_123")

    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)

        if user:
            login(request, user)
            return redirect('redireccion')
        else:
            messages.error(request, "Credenciales inválidas")

    return render(request, 'usuarios/acceder_sistema.html')


# 9. Actualizar usuarios
@login_required
def actualizar_usuarios(request, id):
    usuario = get_object_or_404(User, id=id)

    if request.method == "POST":
        usuario.first_name = request.POST.get('nombre')
        usuario.save()
        return redirect('inicio_usuarios')

    return render(request, 'usuarios/actualizar_usuarios.html', {'usuario': usuario})


# 10. Permisos
def validar_permisos(request):
    return render(request, 'usuarios/validar_permisos.html')


# 11. Redirección post login
@login_required
def redireccion_post_login(request):
    return redirect('inicio_usuarios') if request.user.is_staff else redirect('consultar_usuario')