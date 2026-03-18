from django.shortcuts import render

def inicio_usuarios(request):
    nombre = 'Fergie'
    context = { 
        'nombre' : nombre,
        'titulo' : 'Usuarios',
    }
    return render(request, 'actualizar_usuarios.html', context) 

from django.shortcuts import render, get_object_or_404, redirect
from .models import Usuario

def inicio_usuarios(request):
    usuarios = Usuario.objects.all()
    return render(request, 'inicio_usuarios.html', {'usuarios': usuarios})


def actualizar_usuarios(request, id):
    usuario = get_object_or_404(Usuario, id=id)

    if request.method == "POST":
        usuario.nombre = request.POST.get("nombre")
        usuario.email = request.POST.get("email")
        usuario.telefono = request.POST.get("telefono")
        usuario.save()
        return redirect('inicio_usuarios')

    return render(request, 'actualizar_usuarios.html', {'usuario': usuario})