from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

from .models import User, DemandeConge, NotificationConge
from .forms import ( DemandeCongeForm,TraitementCongeForm,FiltreCongeForm, NotificationCongeForm)


# -------------------------------
# Vérifications des rôles
# -------------------------------
def est_manager_ou_rh(user):
    return user.is_authenticated and (user.is_manager() or user.is_rh() or user.is_admin())


# -------------------------------
# Tableau de bord
# -------------------------------
@login_required
def dashboard(request):
    demandes = DemandeConge.objects.filter(employe=request.user)
    notifications = NotificationConge.objects.filter(employe=request.user, lu=False)
    return render(request, "conges/dashboard.html", {
        "demandes": demandes,
        "notifications": notifications,
    })


# -------------------------------
# Créer une demande de congé
# -------------------------------
@login_required
def creer_demande_conge(request):
    if request.method == "POST":
        form = DemandeCongeForm(request.POST, request.FILES, employe=request.user)
        if form.is_valid():
            demande = form.save(commit=False)
            demande.employe = request.user
            demande.save()
            messages.success(request, "Votre demande de congé a été soumise avec succès.")
            return redirect("dashboard")
    else:
        form = DemandeCongeForm(employe=request.user)

    return render(request, "conges/creer_demande.html", {"form": form})


# -------------------------------
# Liste des demandes (RH / Manager)
# -------------------------------
@login_required
@user_passes_test(est_manager_ou_rh)
def liste_demandes(request):
    demandes = DemandeConge.objects.all()
    form_filtre = FiltreCongeForm(request.GET or None)

    if form_filtre.is_valid():
        if form_filtre.cleaned_data.get("date_debut"):
            demandes = demandes.filter(date_debut__gte=form_filtre.cleaned_data["date_debut"])
        if form_filtre.cleaned_data.get("date_fin"):
            demandes = demandes.filter(date_fin__lte=form_filtre.cleaned_data["date_fin"])
        if form_filtre.cleaned_data.get("statut"):
            demandes = demandes.filter(statut=form_filtre.cleaned_data["statut"])
        if form_filtre.cleaned_data.get("employe"):
            demandes = demandes.filter(
                employe__username__icontains=form_filtre.cleaned_data["employe"]
            )

    return render(request, "conges/liste_demandes.html", {
        "demandes": demandes,
        "form_filtre": form_filtre
    })


# -------------------------------
# Traiter une demande de congé
# -------------------------------
@login_required
@user_passes_test(est_manager_ou_rh)
def traiter_demande(request, demande_id):
    demande = get_object_or_404(DemandeConge, id=demande_id)

    if request.method == "POST":
        form = TraitementCongeForm(request.POST, instance=demande)
        if form.is_valid():
            demande = form.save(commit=False)
            demande.manager = request.user
            demande.date_traitement = timezone.now()
            demande.save()

            # Créer notification
            message = f"Votre demande de congé a été {demande.get_statut_display()}."
            if demande.statut == DemandeConge.Statut.REJETE:
                message += f" Motif: {demande.motif_rejet}"

            NotificationConge.objects.create(
                demande=demande,
                employe=demande.employe,
                message=message
            )

            messages.success(request, "La demande a été traitée avec succès.")
            return redirect("liste_demandes")
    else:
        form = TraitementCongeForm(instance=demande)

    return render(request, "conges/traiter_demande.html", {"form": form, "demande": demande})


# -------------------------------
# Voir et marquer les notifications
# -------------------------------
@login_required
def notifications(request):
    notifications = NotificationConge.objects.filter(employe=request.user)
    return render(request, "conges/notifications.html", {"notifications": notifications})


@login_required
def marquer_notification_lue(request, notification_id):
    notif = get_object_or_404(NotificationConge, id=notification_id, employe=request.user)
    notif.marquer_comme_lu()
    return redirect("notifications")

