from django.shortcuts import render, redirect
from django.contrib.auth.models import User

def eliminar_usuario(request):
    # Aquí buscamos un usuario específico por ejemplo el primero en la base de datos
    # O puedes usar un usuario fijo como 'admin' si solo es de prueba
    usuario = User.objects.first()  # solo como ejemplo

    if request.method == 'POST':
        usuario.delete()
        return redirect('inicio')  # página a donde redirigir después de eliminar

    return render(request, 'usuarios/eliminar_usuario.html', {'usuario': usuario})