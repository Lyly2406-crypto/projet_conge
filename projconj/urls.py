"""
URL configuration for gestion_conge project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from conges import views


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('nouvelle-demande/', views.nouvelle_demande, name='nouvelle_demande'),
    path('mes-demandes/', views.mes_demandes, name='mes_demandes'),
    path('gestion-demandes/', views.gestion_demandes, name='gestion_demandes'),
    path('traiter-demande/<int:demande_id>/', views.traiter_demande, name='traiter_demande'),
    path('calculer-jours/', views.calculer_jours_ajax, name='calculer_jours_ajax'),
]
    

