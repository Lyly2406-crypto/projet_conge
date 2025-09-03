from django.shortcuts import render

# Create your views here.
from django.shortcuts import render

def creer_demande(request):
    # Ici tu peux mettre la logique pour créer une demande de congé
    return render(request, 'conges/creer_demande.html')

