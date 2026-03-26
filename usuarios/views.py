from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User

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