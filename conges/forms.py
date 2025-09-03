from django import forms
from .models import DemandeConge, TypeConge
from datetime import date, timedelta

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
        
        # Limiter les dates de début à partir d'aujourd'hui
        self.fields['date_debut'].widget.attrs['min'] = date.today().isoformat()
    
    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        type_conge = cleaned_data.get('type_conge')
        
        if date_debut and date_fin:
            if date_fin < date_debut:
                raise forms.ValidationError("La date de fin doit être postérieure à la date de début")
            
            # Vérifier si l'employé a assez de congés
            if self.employe and type_conge and type_conge.nom == 'ANNUEL':
                jours_demandes = self.employe.calculer_jours_ouvrables(date_debut, date_fin)
                conges_restants = self.employe.conges_restants()
                
                if jours_demandes > conges_restants:
                    raise forms.ValidationError(
                        f"Vous n'avez que {conges_restants} jours de congé restants. "
                        f"Vous demandez {jours_demandes} jours."
                    )
        
        return cleaned_data

class TraitementCongeForm(forms.ModelForm):
    class Meta:
        model = DemandeConge
        fields = ['statut', 'motif_rejet']
        widgets = {
            'statut': forms.Select(attrs={'class': 'form-control'}),
            'motif_rejet': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Motif du rejet (obligatoire si rejeté)'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['statut'].choices = [
            ('APPROUVE', 'Approuver'),
            ('REJETE', 'Rejeter'),
        ]
    
    def clean(self):
        cleaned_data = super().clean()
        statut = cleaned_data.get('statut')
        motif_rejet = cleaned_data.get('motif_rejet')
        
        if statut == 'REJETE' and not motif_rejet:
            raise forms.ValidationError("Le motif de rejet est obligatoire lors d'un refus")
        
        return cleaned_data

class FiltreCongeForm(forms.Form):
    STATUT_CHOICES = [
        ('', 'Tous les statuts'),
        ('EN_ATTENTE', 'En attente'),
        ('APPROUVE', 'Approuvé'),
        ('REJETE', 'Rejeté'),
    ]
    
    date_debut = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    date_fin = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    statut = forms.ChoiceField(choices=STATUT_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    employe = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom de l\'employé'}))