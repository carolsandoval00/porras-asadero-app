from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.views.generic import DetailView
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin

def inactivar_usuario(request):
    usuario = User.objects.first()  # puedes cambiar esto según tu lógica

    if request.method == 'POST':
        usuario.is_active = False
        usuario.save()
        return redirect('inicio')

    return render(request, 'usuarios/inactivar_usuario.html', {'usuario': usuario})
def inicio_usuarios(request):
    nombre = 'Fergie'
    context = { 
        'nombre' : nombre,
        'titulo' : 'Usuarios',
    }
    return render(request, 'inicio_usuarios.html', context) 
    return render(request, 'inicio_usuarios.html', context) 



def DetalleUsuarioView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'usuarios/detalle_usuario.html'
    context_object_name = 'perfil' 
