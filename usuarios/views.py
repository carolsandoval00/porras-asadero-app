from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Usuario

def inicio_usuarios(request):
    usuarios = Usuario.objects.all()
    return render(request, 'usuarios/inicio_usuarios.html', {'usuarios': usuarios})


@login_required
def actualizar_usuarios(request, id):
    # Validación de permisos (solo admin)
    if not request.user.is_superuser:
        return render(request, 'usuarios/validar_permisos.html')

    usuario = get_object_or_404(Usuario, id=id)

    if request.method == "POST":
        usuario.nombre = request.POST.get("nombre")
        usuario.email = request.POST.get("email")
        usuario.telefono = request.POST.get("telefono")
        usuario.save()
        return redirect('inicio_usuarios')

    return render(request, 'usuarios/actualizar_usuarios.html', {'usuario': usuario})