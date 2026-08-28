from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .access import Perfil


@receiver(post_save, sender=User)
def criar_ou_atualizar_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(user=instance)
    else:
        Perfil.objects.get_or_create(user=instance)
