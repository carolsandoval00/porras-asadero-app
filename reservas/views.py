from django.shortcuts import render, redirect
from .models import Mesa

def actualizar_mesa(request):

    try:
        mesa = Mesa.objects.all()[0] 
    except IndexError:
        return render(request, 'reservas/sin_mesas.html') 

    if request.method == 'POST':
        mesa.capacidad = request.POST.get('capacidad')
        mesa.ubicacion = request.POST.get('ubicacion')
        mesa.estado = request.POST.get('estado')
        mesa.save()
        

    return render(request, 'reservas/actualizar_mesa.html', {'mesa': mesa})