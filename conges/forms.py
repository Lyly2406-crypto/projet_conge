from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from .models import ( User, Direction, Service, Departement, TypeConge, DemandeConge, NotificationConge)


class CustomUserCreationForm(UserCreationForm):
    """Formulaire de création d'utilisateur avec champs personnalisés"""
    
    # FIELDS personnalisés avec labels explicites
    email = forms.EmailField(
        label="Adresse e-mail professionnelle",
        help_text="Cette adresse sera utilisée pour les notifications"
    )
    
    first_name = forms.CharField(
        label="Prénom",
        max_length=30,
        help_text="Votre prénom"
    )
    
    last_name = forms.CharField(
        label="Nom de famille",
        max_length=30,
        help_text="Votre nom de famille"
    )
    
    date_embauche = forms.DateField(
        label="Date d'embauche",
        required=False,
        help_text="Date d'entrée dans l'entreprise"
    )
    
    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name', 'password1', 'password2',
            'role', 'direction', 'service', 'departement',
            'manager', 'jours_conges_annuels', 'date_embauche'
        )
        
        # LABELS pour tous les champs du modèle
        labels = {
            'username': 'Nom d\'utilisateur',
            'role': 'Rôle dans l\'organisation',
            'direction': 'Direction de rattachement',
            'service': 'Service de rattachement',
            'departement': 'Département de rattachement',
            'manager': 'Manager direct',
            'jours_conges_annuels': 'Jours de congés annuels alloués',
        }
        
        # WIDGETS avec styles et attributs
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom d\'utilisateur unique'
            }),
            'date_embauche': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'role': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'direction': forms.Select(attrs={
                'class': 'form-control',
                'data-placeholder': 'Choisir une direction'
            }),
            'service': forms.Select(attrs={
                'class': 'form-control',
                'data-placeholder': 'Choisir un service'
            }),
            'departement': forms.Select(attrs={
                'class': 'form-control',
                'data-placeholder': 'Choisir un département'
            }),
            'manager': forms.Select(attrs={
                'class': 'form-control',
                'data-placeholder': 'Choisir un manager'
            }),
            'jours_conges_annuels': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '15',
                'max': '30',
                'value': '21'
            }),
        }
        
        # HELP TEXTS
        help_texts = {
            'username': 'Utilisé pour se connecter. Lettres, chiffres et @/./+/-/_ seulement.',
            'role': 'Définit les permissions dans l\'application',
            'jours_conges_annuels': 'Nombre de jours de congés payés par an (généralement 21)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personnaliser les WIDGETS des champs de mot de passe
        self.fields['password1'].widget = forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe sécurisé'
        })
        self.fields['password2'].widget = forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmer le mot de passe'
        })
        
        # Personnaliser les LABELS des mots de passe
        self.fields['password1'].label = "Mot de passe"
        self.fields['password2'].label = "Confirmation du mot de passe"
        
        # Filtrer les managers potentiels
        self.fields['manager'].queryset = User.objects.filter(
            role__in=[User.Role.MANAGER, User.Role.CHEF_DEPT, 
                     User.Role.CHEF_SERVICE, User.Role.DIRECTEUR]
        )
        
        # Rendre certains champs obligatoires
        self.fields['email'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True


class DirectionForm(forms.ModelForm):
    """Formulaire pour créer/modifier une direction"""
    
    # FIELD personnalisé avec validation
    code = forms.CharField(
        label="Code de la direction",
        max_length=10,
        help_text="Code unique (ex: TECH, RH, FIN)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: TECH',
            'style': 'text-transform: uppercase;'
        })
    )
    
    class Meta:
        model = Direction
        fields = ['nom', 'code', 'description', 'directeur']
        
        # LABELS explicites
        labels = {
            'nom': 'Nom de la direction',
            'description': 'Description des activités',
            'directeur': 'Directeur responsable',
        }
        
        # WIDGETS avec styles
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Technologies et Systèmes d\'Information'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Décrivez les missions et responsabilités de cette direction...'
            }),
            'directeur': forms.Select(attrs={
                'class': 'form-control',
                'data-placeholder': 'Sélectionner un directeur'
            }),
        }
        
        # HELP TEXTS
        help_texts = {
            'nom': 'Nom complet et officiel de la direction',
            'description': 'Optionnel : décrivez le rôle et les missions',
            'directeur': 'Personne responsable de cette direction',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Seuls les directeurs peuvent être assignés
        self.fields['directeur'].queryset = User.objects.filter(role=User.Role.DIRECTEUR)


class ServiceForm(forms.ModelForm):
    """Formulaire pour créer/modifier un service"""
    
    class Meta:
        model = Service
        fields = ['nom', 'code', 'direction', 'chef_service', 'description']
        
        # LABELS
        labels = {
            'nom': 'Nom du service',
            'code': 'Code du service',
            'direction': 'Direction de rattachement',
            'chef_service': 'Chef de service',
            'description': 'Description du service',
        }
        
        # WIDGETS
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Développement Informatique'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: DEV',
                'maxlength': '10',
                'style': 'text-transform: uppercase;'
            }),
            'direction': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'chef_service': forms.Select(attrs={
                'class': 'form-control',
                'data-placeholder': 'Sélectionner un chef de service'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Missions et responsabilités de ce service...'
            }),
        }
        
        # HELP TEXTS
        help_texts = {
            'code': 'Code court unique au sein de la direction',
            'direction': 'Direction à laquelle appartient ce service',
            'chef_service': 'Responsable de ce service',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['chef_service'].queryset = User.objects.filter(role=User.Role.CHEF_SERVICE)


class DepartementForm(forms.ModelForm):
    """Formulaire pour créer/modifier un département"""
    
    class Meta:
        model = Departement
        fields = ['nom', 'code', 'service', 'chef_departement', 'description']
        
        # LABELS
        labels = {
            'nom': 'Nom du département',
            'code': 'Code du département', 
            'service': 'Service de rattachement',
            'chef_departement': 'Chef de département',
            'description': 'Description du département',
        }
        
        # WIDGETS
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Support Technique'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: SUP',
                'maxlength': '10',
                'style': 'text-transform: uppercase;'
            }),
            'service': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'chef_departement': forms.Select(attrs={
                'class': 'form-control',
                'data-placeholder': 'Sélectionner un chef de département'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Activités spécifiques de ce département...'
            }),
        }
        
        # HELP TEXTS
        help_texts = {
            'code': 'Code court unique au sein du service',
            'service': 'Service auquel appartient ce département',
            'chef_departement': 'Responsable de ce département',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['chef_departement'].queryset = User.objects.filter(role=User.Role.CHEF_DEPT)


class TypeCongeForm(forms.ModelForm):
    """Formulaire pour créer/modifier un type de congé"""
    
    # FIELD personnalisé pour la durée
    duree_max_jours = forms.IntegerField(
        label="Durée maximale (en jours)",
        required=False,
        min_value=1,
        max_value=365,
        help_text="Laisser vide si pas de limite"
    )
    
    class Meta:
        model = TypeConge
        fields = [
            'nom', 'description', 'necessite_justificatif',
            'duree_max_jours', 'approbateur_requis', 
            'delai_prevenance_jours', 'actif'
        ]
        
        # LABELS
        labels = {
            'nom': 'Type de congé',
            'description': 'Description détaillée',
            'necessite_justificatif': 'Justificatif obligatoire',
            'approbateur_requis': 'Qui peut approuver',
            'delai_prevenance_jours': 'Délai de préavis (jours)',
            'actif': 'Type de congé actif',
        }
        
        # WIDGETS
        widgets = {
            'nom': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Décrivez ce type de congé et ses conditions...'
            }),
            'necessite_justificatif': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'approbateur_requis': forms.Select(attrs={
                'class': 'form-control'
            }),
            'delai_prevenance_jours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '30',
                'value': '7'
            }),
            'actif': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
        # HELP TEXTS
        help_texts = {
            'necessite_justificatif': 'Cochez si un document justificatif est requis',
            'delai_prevenance_jours': 'Nombre de jours minimum avant la date de début',
            'actif': 'Décochez pour désactiver temporairement ce type',
        }


class DemandeCongeForm(forms.ModelForm):
    """Formulaire de demande de congé par les employés"""
    
    # FIELDS personnalisés avec validation
    motif_demande = forms.CharField(
        label="Motif de la demande",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Expliquez brièvement le motif de votre demande de congé...',
            'maxlength': '500'
        }),
        max_length=500,
        help_text="Maximum 500 caractères"
    )
    
    instructions_remplacement = forms.CharField(
        label="Instructions pour le remplaçant",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Tâches à effectuer, contacts importants, dossiers prioritaires...'
        }),
        help_text="Optionnel : informations utiles pour votre remplaçant"
    )
    
    class Meta:
        model = DemandeConge
        fields = [
            'type_conge', 'date_debut', 'date_fin', 'motif_demande',
            'justificatif', 'priorite', 'remplacant', 'instructions_remplacement'
        ]
        
        # LABELS
        labels = {
            'type_conge': 'Type de congé demandé',
            'date_debut': 'Date de début',
            'date_fin': 'Date de fin (incluse)',
            'justificatif': 'Document justificatif',
            'priorite': 'Niveau de priorité',
            'remplacant': 'Remplaçant désigné',
        }
        
        # WIDGETS
        widgets = {
            'type_conge': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'date_debut': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'min': date.today().strftime('%Y-%m-%d'),
                'required': True
            }),
            'date_fin': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'min': date.today().strftime('%Y-%m-%d'),
                'required': True
            }),
            'justificatif': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx'
            }),
            'priorite': forms.Select(attrs={
                'class': 'form-control'
            }),
            'remplacant': forms.Select(attrs={
                'class': 'form-control',
                'data-placeholder': 'Choisir un collègue'
            }),
        }
        
        # HELP TEXTS
        help_texts = {
            'date_debut': 'Premier jour d\'absence',
            'date_fin': 'Dernier jour d\'absence (vous reprenez le lendemain)',
            'justificatif': 'Requis pour certains types de congés (PDF, images, Word)',
            'priorite': 'Urgente uniquement pour les cas exceptionnels',
            'remplacant': 'Collègue qui assurera vos tâches pendant votre absence',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Filtrer les types de congé actifs
            self.fields['type_conge'].queryset = TypeConge.objects.filter(actif=True)
            
            # Filtrer les remplaçants potentiels
            if self.user.departement:
                collegues = User.objects.filter(
                    departement=self.user.departement,
                    is_active=True
                ).exclude(id=self.user.id)
            elif self.user.service:
                collegues = User.objects.filter(
                    service=self.user.service,
                    is_active=True
                ).exclude(id=self.user.id)
            else:
                collegues = User.objects.filter(is_active=True).exclude(id=self.user.id)
            
            self.fields['remplacant'].queryset = collegues

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        type_conge = cleaned_data.get('type_conge')
        justificatif = cleaned_data.get('justificatif')
        priorite = cleaned_data.get('priorite')

        # Validation des dates
        if date_debut and date_fin:
            if date_fin < date_debut:
                raise ValidationError("La date de fin doit être postérieure à la date de début")
            
            # Vérification du délai de préavis
            if type_conge and priorite != DemandeConge.Priorite.URGENTE:
                delai_requis = timedelta(days=type_conge.delai_prevenance_jours)
                if date_debut - date.today() < delai_requis:
                    raise ValidationError(
                        f"Un préavis de {type_conge.delai_prevenance_jours} jours est requis "
                        f"pour ce type de congé (sauf urgence)"
                    )

        # Validation du justificatif
        if type_conge and type_conge.necessite_justificatif and not justificatif:
            raise ValidationError("Un justificatif est requis pour ce type de congé")

        # Validation du solde pour congés annuels
        if (self.user and type_conge and 
            type_conge.nom == TypeConge.Type.ANNUEL and 
            date_debut and date_fin):
            
            jours_demandes = self.user.calculer_jours_ouvrables(date_debut, date_fin)
            solde_restant = self.user.conges_restants()
            
            if jours_demandes > solde_restant:
                raise ValidationError(
                    f"Vous demandez {jours_demandes} jours mais il vous reste "
                    f"seulement {solde_restant} jours de congé"
                )

        return cleaned_data


class TraitementDemandeForm(forms.ModelForm):
    """Formulaire pour approuver/rejeter une demande de congé"""
    
    # FIELDS personnalisés
    motif_rejet = forms.CharField(
        label="Motif du rejet",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Expliquez les raisons du rejet de cette demande...'
        }),
        help_text="Obligatoire en cas de rejet"
    )
    
    commentaire_approbateur = forms.CharField(
        label="Commentaire de l'approbateur",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Commentaire optionnel sur cette demande...'
        }),
        help_text="Commentaire visible par l'employé"
    )
    
    class Meta:
        model = DemandeConge
        fields = ['statut', 'motif_rejet', 'commentaire_approbateur']
        
        # LABELS
        labels = {
            'statut': 'Décision',
        }
        
        # WIDGETS
        widgets = {
            'statut': forms.RadioSelect(attrs={
                'class': 'form-check-input'
            }),
        }
        
        # HELP TEXTS
        help_texts = {
            'statut': 'Approuver ou rejeter cette demande',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limiter les choix de statut
        self.fields['statut'].choices = [
            (DemandeConge.Statut.APPROUVE, 'Approuver'),
            (DemandeConge.Statut.REJETE, 'Rejeter'),
        ]

    def clean(self):
        cleaned_data = super().clean()
        statut = cleaned_data.get('statut')
        motif_rejet = cleaned_data.get('motif_rejet')

        if statut == DemandeConge.Statut.REJETE and not motif_rejet:
            raise ValidationError("Le motif de rejet est obligatoire")

        return cleaned_data


class FiltreDemandesForm(forms.Form):
    """Formulaire de filtrage des demandes de congé"""
    
    # FIELDS avec choix dynamiques
    employe = forms.ModelChoiceField(
        label="Employé",
        queryset=User.objects.filter(is_active=True),
        required=False,
        empty_label="Tous les employés",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'data-placeholder': 'Filtrer par employé'
        })
    )
    
    statut = forms.ChoiceField(
        label="Statut de la demande",
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    type_conge = forms.ChoiceField(
        label="Type de congé",
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    date_debut = forms.DateField(
        label="À partir du",
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        help_text="Filtrer les demandes à partir de cette date"
    )
    
    date_fin = forms.DateField(
        label="Jusqu'au",
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        help_text="Filtrer les demandes jusqu'à cette date"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Définir les choix dynamiquement
        STATUT_CHOICES = [('', 'Tous les statuts')] + list(DemandeConge.Statut.choices)
        TYPE_CHOICES = [('', 'Tous les types')] + [
            (tc.nom, tc.get_nom_display()) for tc in TypeConge.objects.filter(actif=True)
        ]
        
        self.fields['statut'].choices = STATUT_CHOICES
        self.fields['type_conge'].choices = TYPE_CHOICES
        
        if user:
            # Filtrer les employés selon les permissions
            if user.is_admin() or user.is_rh():
                pass  # Voient tous les employés
            elif user.is_directeur():
                self.fields['employe'].queryset = User.objects.filter(
                    direction=user.direction, is_active=True
                )
            elif user.is_chef_service():
                self.fields['employe'].queryset = User.objects.filter(
                    service=user.service, is_active=True
                )
            elif user.is_chef_departement():
                self.fields['employe'].queryset = User.objects.filter(
                    departement=user.departement, is_active=True
                )
            elif user.is_manager():
                self.fields['employe'].queryset = user.equipe.filter(is_active=True)
            else:
                self.fields['employe'].queryset = User.objects.filter(id=user.id)


class ProfilUtilisateurForm(forms.ModelForm):
    """Formulaire de modification du profil utilisateur"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email',
            'notifications_email', 'notifications_app'
        ]
        
        # LABELS
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom de famille',
            'email': 'Adresse e-mail',
            'notifications_email': 'Recevoir les notifications par e-mail',
            'notifications_app': 'Recevoir les notifications dans l\'application',
        }
        
        # WIDGETS
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre prénom'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre nom de famille'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'votre.email@entreprise.com'
            }),
            'notifications_email': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notifications_app': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
        # HELP TEXTS
        help_texts = {
            'email': 'Utilisée pour les notifications importantes',
            'notifications_email': 'Recevez un e-mail pour chaque notification',
            'notifications_app': 'Voir les notifications dans l\'interface web',
        }

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Cette adresse e-mail est déjà utilisée")
        return email


class StatistiquesForm(forms.Form):
    """Formulaire pour générer des statistiques"""
    
    # FIELD avec choix prédéfinis
    PERIODE_CHOICES = [
        ('mois', 'Ce mois'),
        ('trimestre', 'Ce trimestre'),
        ('annee', 'Cette année'),
        ('personnalise', 'Période personnalisée'),
    ]
    
    periode = forms.ChoiceField(
        label="Période d'analyse",
        choices=PERIODE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        help_text="Choisissez la période pour les statistiques"
    )
    
    date_debut = forms.DateField(
        label="Date de début (période personnalisée)",
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    date_fin = forms.DateField(
        label="Date de fin (période personnalisée)",
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    direction = forms.ModelChoiceField(
        label="Direction à analyser",
        queryset=Direction.objects.all(),
        required=False,
        empty_label="Toutes les directions",
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        help_text="Laisser vide pour analyser toute l'entreprise"
    )

    def clean(self):
        cleaned_data = super().clean()
        periode = cleaned_data.get('periode')
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')

        if periode == 'personnalise':
            if not date_debut or not date_fin:
                raise ValidationError(
                    "Les dates de début et fin sont obligatoires pour une période personnalisée"
                )
            if date_fin < date_debut:
                raise ValidationError("La date de fin doit être postérieure à la date de début")

        return cleaned_data