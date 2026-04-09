from django.shortcuts import render

def inicio(request):
    nombre = 'Fergie'
    context = { 
        'nombre' : nombre,
        'titulo' : 'inicio',
    }
    return render(request, 'usuario/index.html', context)

def inicio_admin(request):
    nombre = 'Fergie'
    context = { 
        'nombre' : nombre,
        'titulo' : 'inicio',
    }
    return render(request, 'administrador/index.html', context) 