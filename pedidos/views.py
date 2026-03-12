from django.shortcuts import render

def inicio_pedidos(request):
    nombre = 'Fergie'
    context = { 
        'nombre' : nombre,
        'titulo' : 'Pedidos',
    }
    return render(request, 'inicio_pedidos.html', context) 
