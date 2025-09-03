from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils import timezone
from datetime import date

from .models import User, DemandeConge, TypeConge, NotificationConge


# -------------------------------
# Formulaire pour créer un utilisateur
# -------------------------------
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'department', 'jours_conges_annuels')


# -------------------------------
# Formulaire pour modifier un utilisateur
# -------------------------------
class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'department', 'jours_conges_annuels')


# -------------------------------
# Formulaire pour créer une demande de congé
# -------------------------------
class DemandeCongeForm(forms.ModelForm):
    class Meta:
        model = DemandeConge
        fields = ['type_conge', 'date_debut', 'date_fin', 'motif_demande', 'justificatif']
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'motif_demande': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'type_conge': forms.Select(attrs={'class': 'form-control'}),
            'justificatif': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.employe = kwargs.pop('employe', None)
        super().__init__(*args, **kwargs)
        # Bloquer les dates avant aujourd'hui
        self.fields['date_debut'].widget.attrs['min'] = date.today().isoformat()

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        type_conge = cleaned_data.get('type_conge')

        if date_debut and date_fin and date_fin < date_debut:
            raise forms.ValidationError("La date de fin doit être postérieure à la date de début")

        # Vérifier le solde de congés si c'est un congé annuel
        if self.employe and type_conge and type_conge.nom == TypeConge.TypeCongeChoices.ANNUEL:
            jours_demandes = self.employe.calculer_jours_ouvrables(date_debut, date_fin)
            conges_restants = self.employe.conges_restants()
            if jours_demandes > conges_restants:
                raise forms.ValidationError(
                    f"Vous n'avez que {conges_restants} jours de congé restants. "
                    f"Vous demandez {jours_demandes} jours."
                )

        return cleaned_data


# -------------------------------
# Formulaire pour traiter une demande (par un manager ou RH)
# -------------------------------
class TraitementCongeForm(forms.ModelForm):
    class Meta:
        model = DemandeConge
        fields = ['statut', 'motif_rejet']
        widgets = {
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'motif_rejet': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Motif du rejet (obligatoire si rejeté)'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Restreindre aux choix pertinents
        self.fields['statut'].choices = [
            (DemandeConge.StatutChoices.APPROUVE, "Approuver"),
            (DemandeConge.StatutChoices.REJETE, "Rejeter"),
        ]

    def clean(self):
        cleaned_data = super().clean()
        statut = cleaned_data.get('statut')
        motif_rejet = cleaned_data.get('motif_rejet')
        if statut == DemandeConge.StatutChoices.REJETE and not motif_rejet:
            raise forms.ValidationError("Le motif de rejet est obligatoire lors d'un refus")
        return cleaned_data


# -------------------------------
# Formulaire pour filtrer les demandes
# -------------------------------
class FiltreCongeForm(forms.Form):
    STATUT_CHOICES = [
        ('', 'Tous les statuts'),
        (DemandeConge.StatutChoices.EN_ATTENTE, 'En attente'),
        (DemandeConge.StatutChoices.APPROUVE, 'Approuvé'),
        (DemandeConge.StatutChoices.REJETE, 'Rejeté'),
    ]

    date_debut = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    date_fin = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    statut = forms.ChoiceField(choices=STATUT_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    employe = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Nom de l'employé"}))


# -------------------------------
# Formulaire pour notifications
# -------------------------------
class NotificationCongeForm(forms.ModelForm):
    class Meta:
        model = NotificationConge
        fields = ['demande', 'employe', 'message', 'lu']

    def marquer_comme_lu(self):
        self.instance.lu = True
        self.instance.date_lecture = timezone.now()
        self.instance.save()
