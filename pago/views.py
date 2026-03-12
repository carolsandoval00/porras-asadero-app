from django.shortcuts import render

def inicio_pago(request):
    nombre = 'Fergie'
    context = { 
        'nombre' : nombre,
        'titulo' : 'Pago',
    }
    return render(request, 'inicio_pago.html', context) 