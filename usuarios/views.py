from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Usuario


def inicio_usuarios(request):
    usuarios = Usuario.objects.all()
    return render(request, 'usuarios/inicio_usuarios.html', {'usuarios': usuarios})


@login_required
def actualizar_usuarios(request, id):
    if not request.user.is_superuser:
        return redirect('validar_permisos')

    usuario = get_object_or_404(Usuario, pk=id)

    if request.method == "POST":
        usuario.nombre = request.POST.get("nombre")
        usuario.correo = request.POST.get("correo")
        usuario.telefono = request.POST.get("telefono")
        usuario.save()
        return redirect('inicio_usuarios')

    return render(request, 'usuarios/inicio_usuarios.html', {'usuario': usuario})


def validar_permisos(request):
    return render(request, 'usuarios/validar_permisos.html')