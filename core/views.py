from django.shortcuts import render
from pedidos.models import Categoria

def inicio(request):
    nombre = 'Fergie'
    # Consultar las categorías y realizar prefetch de sus productos asociados
    categorias_menu = Categoria.objects.all().prefetch_related('productos')
    context = { 
        'nombre' : nombre,
        'titulo' : 'inicio',
        'categorias_menu': categorias_menu,
    }
    return render(request, 'usuario/index.html', context)

def inicio_admin(request):
    nombre = 'Fergie'
    context = { 
        'nombre' : nombre,
        'titulo' : 'inicio',
    }
    return render(request, 'administrador/index.html', context) 