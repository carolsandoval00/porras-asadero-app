from django.shortcuts import render
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User

def consultar_usuario(request):
    usuario = None
    username = request.GET.get('username')  
    if username:
        try:
            usuario = User.objects.get(username=username)
        except User.DoesNotExist:
            usuario = None

    return render(request, 'usuarios/consultar_usuario.html', {'usuario': usuario})


def acceder_sistema(request):
    if not User.objects.filter(username="restaurante").exists():
        User.objects.create_user(username="restaurante", password="porras_123")

    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = User.objects.filter(username=username).first()
        if user and user.check_password(password):
            login(request, user)
            return redirect('inicio') 
        else:
            messages.error(request, "Usuario o contraseña incorrectos")

    return render(request, 'usuarios/acceder_sistema.html')
