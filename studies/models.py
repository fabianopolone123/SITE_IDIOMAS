import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField('nome completo', max_length=160)
    whatsapp = models.CharField('telefone WhatsApp', max_length=30)

    def __str__(self):
        return self.full_name


class StudyPhrase(models.Model):
    deck_key = models.CharField(max_length=40, unique=True, null=True, blank=True, db_index=True)
    source_title = models.CharField(max_length=180, default='Le avventure di Alice nel paese delle meraviglie')
    order = models.PositiveIntegerField(default=0, db_index=True)
    italian_text = models.TextField()
    portuguese_text = models.TextField(blank=True)
    study_note = models.TextField(blank=True)
    chapter = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.italian_text[:80]


class ReviewState(models.Model):
    AGAIN = 'again'
    HARD = 'hard'
    GOOD = 'good'
    EASY = 'easy'
    GRADE_CHOICES = [
        (AGAIN, 'Errei'),
        (HARD, 'Difícil'),
        (GOOD, 'Bom'),
        (EASY, 'Fácil'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phrase = models.ForeignKey(StudyPhrase, on_delete=models.CASCADE)
    first_seen_at = models.DateTimeField(default=timezone.now, db_index=True)
    due_at = models.DateTimeField(default=timezone.now, db_index=True)
    interval_days = models.PositiveIntegerField(default=0)
    ease_factor = models.FloatField(default=2.3)
    repetitions = models.PositiveIntegerField(default=0)
    lapses = models.PositiveIntegerField(default=0)
    last_grade = models.CharField(max_length=12, choices=GRADE_CHOICES, blank=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'phrase']
        ordering = ['due_at', 'phrase__order']

    @property
    def is_due(self):
        return self.due_at <= timezone.now()

    def schedule(self, grade):
        now = timezone.now()
        self.last_grade = grade
        self.last_reviewed_at = now
        self.repetitions += 1

        if grade == self.AGAIN:
            self.lapses += 1
            self.ease_factor = max(1.3, self.ease_factor - 0.2)
            self.interval_days = 0
            self.due_at = now + timedelta(minutes=10)
            return

        if grade == self.HARD:
            self.ease_factor = max(1.3, self.ease_factor - 0.15)
            self.interval_days = 1 if self.interval_days == 0 else max(1, round(self.interval_days * 1.2))
        elif grade == self.GOOD:
            self.interval_days = 2 if self.interval_days == 0 else max(2, round(self.interval_days * self.ease_factor))
        elif grade == self.EASY:
            self.ease_factor = min(3.0, self.ease_factor + 0.15)
            self.interval_days = 4 if self.interval_days == 0 else max(4, round(self.interval_days * self.ease_factor * 1.5))
        else:
            raise ValueError(f'Nota de revisão inválida: {grade}')

        self.due_at = now + timedelta(days=self.interval_days)

    def __str__(self):
        return f'{self.user} -> {self.phrase_id} em {self.due_at:%Y-%m-%d}'


class VanRegistration(models.Model):
    PENDING_SIGNATURE = 'pending_signature'
    SIGNED_RECEIVED = 'signed_received'
    STATUS_CHOICES = [
        (PENDING_SIGNATURE, 'Falta enviar termo assinado'),
        (SIGNED_RECEIVED, 'Inscricao da van feita'),
    ]

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    responsible_name = models.CharField('nome do responsavel', max_length=180)
    responsible_rg = models.CharField('RG do responsavel', max_length=40)
    responsible_cpf = models.CharField('CPF do responsavel', max_length=20, db_index=True)
    responsible_phone = models.CharField('telefone/WhatsApp', max_length=30, blank=True)
    responsible_email = models.EmailField('email', blank=True)
    minor_name = models.CharField('nome do menor', max_length=180)
    minor_birth_date = models.DateField('data de nascimento do menor', db_index=True)
    minor_document = models.CharField('RG/CPF do menor', max_length=60, blank=True)
    transport_by = models.CharField('transporte realizado por', max_length=120, default='van')
    signed_term = models.FileField('termo assinado', upload_to='inscricao_van/termos_assinados/', blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=PENDING_SIGNATURE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def mark_signed_if_needed(self):
        if self.signed_term and self.status != self.SIGNED_RECEIVED:
            self.status = self.SIGNED_RECEIVED

    def save(self, *args, **kwargs):
        self.mark_signed_if_needed()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.minor_name} - {self.responsible_name}'
