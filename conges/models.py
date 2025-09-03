from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from datetime import date, timedelta
import holidays


class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYE = "EMP", "Employé"
        MANAGER = "MAN", "Manager"
        RH = "RH", "Ressources Humaines"
        ADMIN = "ADM", "Administrateur"

    role = models.CharField(
        max_length=3,
        choices=Role.choices,
        default=Role.EMPLOYE
    )
    department = models.CharField(max_length=100, blank=True, null=True)
    jours_conges_annuels = models.IntegerField(default=30)  # ex: 30 jours par an

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
            statut='APPROUVE',
            date_debut__year=annee
        )

        total_jours = 0
        for conge in conges_approuves:
            total_jours += self.calculer_jours_ouvrables(conge.date_debut, conge.date_fin)

        return total_jours

    def conges_restants(self):
        return self.jours_conges_annuels - self.conges_consommes_annee()

    def calculer_jours_ouvrables(self, date_debut, date_fin):
        jours_total = 0
        current_date = date_debut

        # Jours fériés au Burundi (adapter si nécessaire)
        jours_feries = holidays.BI(years=current_date.year)

        while current_date <= date_fin:
            if current_date.weekday() < 5 and current_date not in jours_feries:
                jours_total += 1
            current_date += timedelta(days=1)

        return jours_total


class TypeConge(models.Model):
    TYPES_CHOICES = [
        ('ANNUEL', 'Congé annuel'),
        ('MALADIE', 'Congé maladie'),
        ('MATERNITE', 'Congé maternité'),
        ('FORMATION', 'Formation'),
        ('SANS_SOLDE', 'Congé sans solde'),
    ]

    nom = models.CharField(max_length=50, choices=TYPES_CHOICES, unique=True)
    description = models.TextField(blank=True)
    necessite_justificatif = models.BooleanField(default=False)

    def __str__(self):
        return self.get_nom_display()


class DemandeConge(models.Model):
    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('APPROUVE', 'Approuvé'),
        ('REJETE', 'Rejeté'),
    ]

    employe = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demandes_conge')
    type_conge = models.ForeignKey(TypeConge, on_delete=models.CASCADE)
    date_debut = models.DateField()
    date_fin = models.DateField()
    motif_demande = models.TextField()
    justificatif = models.FileField(upload_to='justificatifs/', blank=True, null=True)

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='EN_ATTENTE')
    date_demande = models.DateTimeField(auto_now_add=True)

    # Gestion par manager
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='demandes_gerees')
    date_traitement = models.DateTimeField(null=True, blank=True)
    motif_rejet = models.TextField(blank=True, help_text="Obligatoire en cas de rejet")

    class Meta:
        ordering = ['-date_demande']

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.date_fin < self.date_debut:
            raise ValidationError("La date de fin doit être postérieure à la date de début")

        if self.statut == 'REJETE' and not self.motif_rejet:
            raise ValidationError("Le motif de rejet est obligatoire")

    def nombre_jours_demandes(self):
        return self.employe.calculer_jours_ouvrables(self.date_debut, self.date_fin)

    def peut_etre_approuve(self):
        if self.type_conge.nom == 'ANNUEL':
            jours_demandes = self.nombre_jours_demandes()
            conges_restants = self.employe.conges_restants()
            return jours_demandes <= conges_restants
        return True


class NotificationConge(models.Model):
    demande = models.ForeignKey(DemandeConge, on_delete=models.CASCADE)
    employe = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    lu = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_lecture = models.DateTimeField(null=True, blank=True)
 
