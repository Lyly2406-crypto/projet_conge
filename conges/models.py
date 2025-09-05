from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import date, timedelta
import holidays
from django.utils import timezone


class Direction(models.Model):
    """Représente une direction de l'entreprise"""
    nom = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    directeur = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, 
                                 related_name='direction_dirigee')
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nom
    
    class Meta:
        verbose_name = "Direction"
        verbose_name_plural = "Directions"


class Service(models.Model):
    """Représente un service au sein d'une direction"""
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    direction = models.ForeignKey(Direction, on_delete=models.CASCADE, related_name='services')
    chef_service = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='service_dirige')
    description = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nom} - {self.direction.nom}"
    
    class Meta:
        verbose_name = "Service"
        verbose_name_plural = "Services"
        unique_together = ['nom', 'direction']


class Departement(models.Model):
    """Représente un département au sein d'un service"""
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='departements')
    chef_departement = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='departement_dirige')
    description = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nom} - {self.service.nom}"
    
    class Meta:
        verbose_name = "Département"
        verbose_name_plural = "Départements"
        unique_together = ['nom', 'service']


class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYE = "EMP", "Employé"
        MANAGER = "MAN", "Manager"
        CHEF_DEPT = "CHF_DEPT", "Chef de Département"
        CHEF_SERVICE = "CHF_SERV", "Chef de Service"
        DIRECTEUR = "DIR", "Directeur"
        SECRETAIRE = "SEC", "Secrétaire"
        RH = "RH", "Ressources Humaines"
        ADMIN = "ADM", "Administrateur"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.EMPLOYE)
    
    # Structure organisationnelle
    direction = models.ForeignKey(Direction, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='employes')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='employes')
    departement = models.ForeignKey(Departement, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='employes')
    
    # Manager hiérarchique direct
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='equipe')
    
    # Informations sur les congés
    jours_conges_annuels = models.PositiveSmallIntegerField(default=21)
    date_embauche = models.DateField(null=True, blank=True)
    
    # Préférences de notification
    notifications_email = models.BooleanField(default=True)
    notifications_app = models.BooleanField(default=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='conges_users',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='conges_users_permissions',
        blank=True
    )

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

    # Méthodes de vérification des rôles
    def is_employe(self):
        return self.role == self.Role.EMPLOYE

    def is_manager(self):
        return self.role == self.Role.MANAGER

    def is_chef_departement(self):
        return self.role == self.Role.CHEF_DEPT

    def is_chef_service(self):
        return self.role == self.Role.CHEF_SERV

    def is_directeur(self):
        return self.role == self.Role.DIRECTEUR

    def is_secretaire(self):
        return self.role == self.Role.SECRETAIRE

    def is_rh(self):
        return self.role == self.Role.RH

    def is_admin(self):
        return self.role == self.Role.ADMIN

    def can_approve_leave(self):
        """Détermine si l'utilisateur peut approuver des demandes de congé"""
        return self.role in [self.Role.MANAGER, self.Role.CHEF_DEPT, 
                           self.Role.CHEF_SERV, self.Role.DIRECTEUR, 
                           self.Role.RH, self.Role.ADMIN]

    def can_manage_special_leave(self):
        """Détermine si l'utilisateur peut gérer les congés spéciaux (maladie, maternité)"""
        return self.role in [self.Role.SECRETAIRE, self.Role.RH, self.Role.ADMIN]

    def get_hierarchical_level(self):
        """Retourne le niveau hiérarchique de l'utilisateur"""
        hierarchy = {
            self.Role.EMPLOYE: 1,
            self.Role.MANAGER: 2,
            self.Role.CHEF_DEPT: 3,
            self.Role.CHEF_SERV: 4,
            self.Role.DIRECTEUR: 5,
            self.Role.SECRETAIRE: 3,
            self.Role.RH: 4,
            self.Role.ADMIN: 6
        }
        return hierarchy.get(self.role, 1)

    def get_subordinates(self):
        """Retourne tous les subordonnés de cet utilisateur"""
        subordinates = []
        
        if self.is_directeur():
            # Un directeur voit tous les employés de sa direction
            subordinates = User.objects.filter(direction=self.direction).exclude(id=self.id)
        elif self.is_chef_service():
            # Un chef de service voit tous les employés de son service
            subordinates = User.objects.filter(service=self.service).exclude(id=self.id)
        elif self.is_chef_departement():
            # Un chef de département voit tous les employés de son département
            subordinates = User.objects.filter(departement=self.departement).exclude(id=self.id)
        elif self.is_manager():
            # Un manager voit son équipe directe
            subordinates = self.equipe.all()
        
        return subordinates

    def conges_consommes_annee(self, annee=None):
        if annee is None:
            annee = date.today().year
        conges_approuves = DemandeConge.objects.filter(
            employe=self,
            statut=DemandeConge.Statut.APPROUVE,
            date_debut__year=annee
        )
        total_jours = sum(self.calculer_jours_ouvrables(c.date_debut, c.date_fin) for c in conges_approuves)
        return total_jours

    def conges_restants(self):
        return self.jours_conges_annuels - self.conges_consommes_annee()

    def calculer_jours_ouvrables(self, date_debut, date_fin):
        jours_total = 0
        current_date = date_debut
        jours_feries = holidays.BI(years=current_date.year)
        while current_date <= date_fin:
            if current_date.weekday() < 5 and current_date not in jours_feries:
                jours_total += 1
            current_date += timedelta(days=1)
        return jours_total


class TypeConge(models.Model):
    class Type(models.TextChoices):
        ANNUEL = 'ANNUEL', 'Congé annuel'
        MALADIE = 'MALADIE', 'Congé maladie'
        MATERNITE = 'MATERNITE', 'Congé maternité'
        PATERNITE = 'PATERNITE', 'Congé paternité'
        FORMATION = 'FORMATION', 'Formation'
        SANS_SOLDE = 'SANS_SOLDE', 'Congé sans solde'
        DEUIL = 'DEUIL', 'Congé de deuil'
        EXCEPTIONNEL = 'EXCEPTIONNEL', 'Congé exceptionnel'

    class Approbateur(models.TextChoices):
        MANAGER = 'MANAGER', 'Manager direct'
        SECRETAIRE = 'SECRETAIRE', 'Secrétaire'
        RH = 'RH', 'Ressources Humaines'
        CHEF_DEPT = 'CHEF_DEPT', 'Chef de département'
        CHEF_SERV = 'CHEF_SERV', 'Chef de service'
        DIRECTEUR = 'DIRECTEUR', 'Directeur'

    nom = models.CharField(max_length=50, choices=Type.choices, unique=True)
    description = models.TextField(blank=True)
    necessite_justificatif = models.BooleanField(default=False)
    duree_max_jours = models.PositiveSmallIntegerField(null=True, blank=True,
                                                      help_text="Durée maximale en jours (optionnel)")
    approbateur_requis = models.CharField(max_length=20, choices=Approbateur.choices,
                                         default=Approbateur.MANAGER,
                                         help_text="Qui peut approuver ce type de congé")
    delai_prevenance_jours = models.PositiveSmallIntegerField(default=7,
                                                             help_text="Délai de préavis en jours")
    actif = models.BooleanField(default=True)

    def __str__(self):
        return self.get_nom_display()

    def get_approbateurs_possibles(self, employe):
        """Retourne la liste des utilisateurs pouvant approuver ce type de congé pour cet employé"""
        approbateurs = []
        
        if self.approbateur_requis == self.Approbateur.MANAGER:
            if employe.manager:
                approbateurs.append(employe.manager)
        elif self.approbateur_requis == self.Approbateur.SECRETAIRE:
            approbateurs.extend(User.objects.filter(role=User.Role.SECRETAIRE))
        elif self.approbateur_requis == self.Approbateur.RH:
            approbateurs.extend(User.objects.filter(role=User.Role.RH))
        elif self.approbateur_requis == self.Approbateur.CHEF_DEPT:
            if employe.departement and employe.departement.chef_departement:
                approbateurs.append(employe.departement.chef_departement)
        elif self.approbateur_requis == self.Approbateur.CHEF_SERV:
            if employe.service and employe.service.chef_service:
                approbateurs.append(employe.service.chef_service)
        elif self.approbateur_requis == self.Approbateur.DIRECTEUR:
            if employe.direction and employe.direction.directeur:
                approbateurs.append(employe.direction.directeur)
        
        return approbateurs


class DemandeConge(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        APPROUVE = 'APPROUVE', 'Approuvé'
        REJETE = 'REJETE', 'Rejeté'
        ANNULE = 'ANNULE', 'Annulé'

    class Priorite(models.TextChoices):
        NORMALE = 'NORMALE', 'Normale'
        URGENTE = 'URGENTE', 'Urgente'
        CRITIQUE = 'CRITIQUE', 'Critique'

    employe = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demandes_conge')
    type_conge = models.ForeignKey(TypeConge, on_delete=models.CASCADE, related_name='demandes')
    date_debut = models.DateField()
    date_fin = models.DateField()
    motif_demande = models.TextField()
    justificatif = models.FileField(upload_to='justificatifs/', blank=True, null=True)

    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    priorite = models.CharField(max_length=20, choices=Priorite.choices, default=Priorite.NORMALE)
    date_demande = models.DateTimeField(auto_now_add=True)

    # Traitement de la demande
    approbateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='demandes_approuvees')
    date_traitement = models.DateTimeField(null=True, blank=True)
    motif_rejet = models.TextField(blank=True, help_text="Obligatoire en cas de rejet")
    commentaire_approbateur = models.TextField(blank=True)

    # Remplacement
    remplacant = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='remplacements')
    instructions_remplacement = models.TextField(blank=True)

    class Meta:
        ordering = ['-date_demande']
        verbose_name = "Demande de congé"
        verbose_name_plural = "Demandes de congé"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.date_fin < self.date_debut:
            raise ValidationError("La date de fin doit être postérieure à la date de début")
        if self.statut == self.Statut.REJETE and not self.motif_rejet:
            raise ValidationError("Le motif de rejet est obligatoire")
        
        # Vérifier le délai de préavis
        if self.date_debut and self.type_conge:
            delai_requis = timedelta(days=self.type_conge.delai_prevenance_jours)
            if self.date_debut - date.today() < delai_requis:
                if self.priorite != self.Priorite.URGENTE:
                    raise ValidationError(f"Un préavis de {self.type_conge.delai_prevenance_jours} jours est requis")

    def nombre_jours_demandes(self):
        return self.employe.calculer_jours_ouvrables(self.date_debut, self.date_fin)

    def peut_etre_approuve(self):
        if self.type_conge.nom == TypeConge.Type.ANNUEL:
            return self.nombre_jours_demandes() <= self.employe.conges_restants()
        return True

    def get_approbateurs_possibles(self):
        """Retourne la liste des approbateurs possibles pour cette demande"""
        return self.type_conge.get_approbateurs_possibles(self.employe)

    def __str__(self):
        return f"{self.employe.get_full_name()} - {self.type_conge} ({self.date_debut} au {self.date_fin})"


class NotificationConge(models.Model):
    class TypeNotification(models.TextChoices):
        NOUVELLE_DEMANDE = 'NOUVELLE_DEMANDE', 'Nouvelle demande'
        DEMANDE_APPROUVEE = 'DEMANDE_APPROUVEE', 'Demande approuvée'
        DEMANDE_REJETEE = 'DEMANDE_REJETEE', 'Demande rejetée'
        RAPPEL_APPROBATION = 'RAPPEL_APPROBATION', 'Rappel d\'approbation'
        DEMANDE_ANNULEE = 'DEMANDE_ANNULEE', 'Demande annulée'

    class Destinataire(models.TextChoices):
        EMPLOYE = 'EMPLOYE', 'Employé'
        MANAGER = 'MANAGER', 'Manager'
        APPROBATEUR = 'APPROBATEUR', 'Approbateur'

    demande = models.ForeignKey(DemandeConge, on_delete=models.CASCADE, related_name='notifications')
    destinataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type_notification = models.CharField(max_length=30, choices=TypeNotification.choices)
    destinataire_type = models.CharField(max_length=20, choices=Destinataire.choices)
    
    titre = models.CharField(max_length=200)
    message = models.TextField()
    
    lu = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_lecture = models.DateTimeField(null=True, blank=True)
    
    # Pour éviter la surcharge admin
    visible_admin = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_type_notification_display()} pour {self.destinataire.username} - {'Lu' if self.lu else 'Non lu'}"

    def marquer_comme_lu(self):
        if not self.lu:
            self.lu = True
            self.date_lecture = timezone.now()
            self.save()

    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    @classmethod
    def creer_notifications(cls, demande, type_notification, exclure_admin=True):
        """
        Crée les notifications appropriées selon le type d'événement
        exclure_admin: Si True, n'envoie pas de notifications à l'admin
        """
        notifications_creees = []
        
        if type_notification == cls.TypeNotification.NOUVELLE_DEMANDE:
            # Notifier les approbateurs possibles
            approbateurs = demande.get_approbateurs_possibles()
            for approbateur in approbateurs:
                if not (exclure_admin and approbateur.is_admin()):
                    notification = cls.objects.create(
                        demande=demande,
                        destinataire=approbateur,
                        type_notification=type_notification,
                        destinataire_type=cls.Destinataire.APPROBATEUR,
                        titre=f"Nouvelle demande de congé - {demande.employe.get_full_name()}",
                        message=f"Une nouvelle demande de {demande.type_conge} a été soumise par {demande.employe.get_full_name()} du {demande.date_debut} au {demande.date_fin}.",
                        visible_admin=not exclure_admin
                    )
                    notifications_creees.append(notification)
        
        elif type_notification in [cls.TypeNotification.DEMANDE_APPROUVEE, cls.TypeNotification.DEMANDE_REJETEE]:
            # Notifier l'employé
            notification = cls.objects.create(
                demande=demande,
                destinataire=demande.employe,
                type_notification=type_notification,
                destinataire_type=cls.Destinataire.EMPLOYE,
                titre=f"Demande de congé {demande.get_statut_display().lower()}",
                message=f"Votre demande de {demande.type_conge} du {demande.date_debut} au {demande.date_fin} a été {demande.get_statut_display().lower()}.",
                visible_admin=not exclure_admin
            )
            notifications_creees.append(notification)
            
            # Notifier le manager s'il est différent de l'approbateur
            if demande.employe.manager and demande.employe.manager != demande.approbateur:
                if not (exclure_admin and demande.employe.manager.is_admin()):
                    notification = cls.objects.create(
                        demande=demande,
                        destinataire=demande.employe.manager,
                        type_notification=type_notification,
                        destinataire_type=cls.Destinataire.MANAGER,
                        titre=f"Demande de congé {demande.get_statut_display().lower()} - {demande.employe.get_full_name()}",
                        message=f"La demande de {demande.type_conge} de {demande.employe.get_full_name()} du {demande.date_debut} au {demande.date_fin} a été {demande.get_statut_display().lower()}.",
                        visible_admin=not exclure_admin
                    )
                    notifications_creees.append(notification)
        
        return notifications_creees


class HistoriqueConge(models.Model):
    """Historique des actions sur les demandes de congé"""
    demande = models.ForeignKey(DemandeConge, on_delete=models.CASCADE, related_name='historique')
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)
    ancien_statut = models.CharField(max_length=20, blank=True)
    nouveau_statut = models.CharField(max_length=20, blank=True)
    commentaire = models.TextField(blank=True)
    date_action = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.action} par {self.utilisateur.username} le {self.date_action}"
    
    class Meta:
        ordering = ['-date_action']
        verbose_name = "Historique de congé"
        verbose_name_plural = "Historique des congés"