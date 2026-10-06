from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def centroayuda(request):
    contexto = {
        'nombre': request.user.get_full_name() or request.user.username,
    }
    return render(request, 'ayuda.html')