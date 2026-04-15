# chat/models.py
from django.db import models
from django.contrib.auth import get_user_model
from clinics.models import Clinic
from pets.models import Pet

User = get_user_model()

class Chat(models.Model):
    """Один чат = владелец + ветеринар + (опционально) питомец + клиника"""
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='started_chats',
        limit_choices_to={'user_type': 'owner'}
    )
    vet = models.ForeignKey(
        User,
        on_delete= models.CASCADE,
        related_name='received_chats',
        limit_choices_to={'user_type__in': ['vet', 'clinic_admin']}
    )
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    pet = models.ForeignKey(Pet, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('owner', 'vet', 'clinic')  # нельзя создать 2 чата с одним ветом

    def __str__(self):
        return f"{self.owner} ↔ {self.vet} ({self.clinic})"


class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender}: {self.text[:30]}"