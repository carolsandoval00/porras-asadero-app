from django.shortcuts import render

def inicio(request):
    nombre = 'Fergie'
    context = { 
        'nombre' : nombre,
        'titulo' : 'inicio',
    }
    return render(request, 'index.html', context) 