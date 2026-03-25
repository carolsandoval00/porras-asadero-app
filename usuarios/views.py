from django.shortcuts import render
from django.contrib.auth.models import User

def consultar_usuario(request):
    usuario = None
    username = request.GET.get('username')  # tomamos el valor del input en la URL o formulario
    if username:
        try:
            usuario = User.objects.get(username=username)
        except User.DoesNotExist:
            usuario = None

    return render(request, 'usuarios/consultar_usuario.html', {'usuario': usuario})