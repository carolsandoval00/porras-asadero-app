from django.shortcuts import render

def inicio_usuarios(request):
    nombre = 'Fergie'
    context = { 
        'nombre' : nombre,
        'titulo' : 'Usuarios',
    }
    return render(request, 'actualizar_usuarios.html', context) 

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Usuario

def inicio_usuarios(request):
    usuarios = Usuario.objects.all()
    return render(request, 'inicio_usuarios.html', {'usuarios': usuarios})

