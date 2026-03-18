from django.shortcuts import render

def inicio_usuarios(request):
    nombre = 'Fergie'
    context = { 
        'nombre' : nombre,
        'titulo' : 'Usuarios',
    }
    return render(request, 'inicio_usuarios.html', context) 

from django.shortcuts import render, redirect
from .forms import PersonalForm

def registrar_personal(request):
    if request.method == 'POST':
        form = PersonalForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_personal')  # puedes cambiar esto
    else:
        form = PersonalForm()

    return render(request, 'registrar_personal.html', {'form': form})