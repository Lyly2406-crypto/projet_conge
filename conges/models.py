from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import date, timedelta
import holidays
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYE = "EMP", "Employé"
        MANAGER = "MAN", "Manager"
        RH = "RH", "Ressources Humaines"
        ADMIN = "ADM", "Administrateur"

    role = models.CharField(max_length=3, choices=Role.choices, default=Role.EMPLOYE)
    department = models.CharField(max_length=100, blank=True, null=True)
    jours_conges_annuels = models.PositiveSmallIntegerField(default=21)

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

    def is_manager(self):
        return self.role == self.Role.MANAGER

    def is_rh(self):
        return self.role == self.Role.RH

    def is_admin(self):
        return self.role == self.Role.ADMIN

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
        FORMATION = 'FORMATION', 'Formation'
        SANS_SOLDE = 'SANS_SOLDE', 'Congé sans solde'

    nom = models.CharField(max_length=50, choices=Type.choices, unique=True)
    description = models.TextField(blank=True)
    necessite_justificatif = models.BooleanField(default=False)

    def __str__(self):
        return self.get_nom_display()


class DemandeConge(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        APPROUVE = 'APPROUVE', 'Approuvé'
        REJETE = 'REJETE', 'Rejeté'

    employe = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demandes_conge')
    type_conge = models.ForeignKey(TypeConge, on_delete=models.CASCADE, related_name='demandes')
    date_debut = models.DateField()
    date_fin = models.DateField()
    motif_demande = models.TextField()
    justificatif = models.FileField(upload_to='justificatifs/', blank=True, null=True)

    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    date_demande = models.DateTimeField(auto_now_add=True)

    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='demandes_gerees')
    date_traitement = models.DateTimeField(null=True, blank=True)
    motif_rejet = models.TextField(blank=True, help_text="Obligatoire en cas de rejet")

    class Meta:
        ordering = ['-date_demande']

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.date_fin < self.date_debut:
            raise ValidationError("La date de fin doit être postérieure à la date de début")
        if self.statut == self.Statut.REJETE and not self.motif_rejet:
            raise ValidationError("Le motif de rejet est obligatoire")

    def nombre_jours_demandes(self):
        return self.employe.calculer_jours_ouvrables(self.date_debut, self.date_fin)

    def peut_etre_approuve(self):
        if self.type_conge.nom == TypeConge.Type.ANNUEL:
            return self.nombre_jours_demandes() <= self.employe.conges_restants()
        return True


class NotificationConge(models.Model):
    demande = models.ForeignKey(DemandeConge, on_delete=models.CASCADE, related_name='notifications')
    employe = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    lu = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_lecture = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Notification pour {self.employe.username} - {'Lu' if self.lu else 'Non lu'}"

    def marquer_comme_lu(self):
        if not self.lu:
            self.lu = True
            self.date_lecture = timezone.now()
            self.save()
