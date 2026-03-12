from django.shortcuts import render

def inicio_reservas(request):
    nombre = 'Fergie'
    context = { 
        'nombre' : nombre,
        'titulo' : 'Reservas',
    }
    return render(request, 'inicio_reservas.html', context) 

