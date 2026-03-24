from django.shortcuts import render

def inicio_usuarios(request):
    nombre = 'Fergie'
    context = { 
        'nombre' : nombre,
        'titulo' : 'Usuarios',
    }
<<<<<<< Updated upstream
    return render(request, 'inicio_usuarios.html', context) 
=======
    return render(request, 'inicio_usuarios.html', context) 

from django.views.generic import DetailView
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin

def DetalleUsuarioView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'usuarios/detalle_usuario.html'
    context_object_name = 'perfil' 
>>>>>>> Stashed changes
