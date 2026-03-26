from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.views.generic import DetailView
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
from .forms import CustomPasswordResetForm
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import PersonalForm
from .models import Personal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Usuario

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

    return render(request, 'actualizar_usuarios.html', context) 




def inicio_usuarios(request):
    usuarios = Usuario.objects.all()
    return render(request, 'inicio_usuarios.html', {'usuarios': usuarios})


@login_required
def actualizar_usuarios(request, id):

    usuario = get_object_or_404(Usuario, pk=id)

    if request.method == "POST":
        usuario.nombre = request.POST.get("nombre")
        usuario.email = request.POST.get("email")
        usuario.telefono = request.POST.get("telefono")
        usuario.rol = request.POST.get("rol")
        usuario.save()

        return redirect('inicio_usuarios')

    return render(request, 'actualizar_usuarios.html', {'usuario': usuario})

    return render(request, 'inicio_usuarios.html', context) 
    return render(request, 'inicio_usuarios.html', context) 



def DetalleUsuarioView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'usuarios/detalle_usuario.html'
    context_object_name = 'perfil' 

class CustomPasswordResetView(PasswordResetView):
    template_name = 'usuarios/recuperar.html'
    form_class = CustomPasswordResetForm
    success_url = reverse_lazy('recuperar_enviado')


def registrar_personal(request):
    if request.method == 'POST':
        form = PersonalForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "¡Personal registrado correctamente!")
            return redirect('lista_personal')
    else:
        form = PersonalForm()
    return render(request, 'usuarios/registrar_personal.html', {'form': form})

def lista_personal(request):
    personal_list = Personal.objects.all()
    return render(request, 'usuarios/lista_personal.html', {'personal_list': personal_list})
