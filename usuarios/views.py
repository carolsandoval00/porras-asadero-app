from django.shortcuts import render, redirect
from django.contrib.auth.models import User

def inactivar_usuario(request):
    usuario = User.objects.first()  # puedes cambiar esto según tu lógica

    if request.method == 'POST':
        usuario.is_active = False
        usuario.save()
        return redirect('inicio')

    return render(request, 'usuarios/inactivar_usuario.html', {'usuario': usuario})