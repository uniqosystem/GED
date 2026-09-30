from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = (
        'Cria (ou garante) o superusuário definido em ADMIN_SEED_USERNAME/ADMIN_SEED_PASSWORD. '
        'Idempotente: não altera a senha de um usuário existente, salvo com ADMIN_SEED_RESET_PASSWORD=True.'
    )

    def handle(self, *args, **options):
        username = settings.ADMIN_SEED_USERNAME
        password = settings.ADMIN_SEED_PASSWORD
        email = settings.ADMIN_SEED_EMAIL

        if not username or not password:
            self.stdout.write('Seed do admin ignorado: ADMIN_SEED_USERNAME/ADMIN_SEED_PASSWORD não definidos.')
            return

        with transaction.atomic():
            usuario = User.objects.filter(username=username).first()
            criado = usuario is None
            if criado:
                usuario = User(username=username)

            definir_senha = criado or settings.ADMIN_SEED_RESET_PASSWORD
            if definir_senha:
                try:
                    validate_password(password, user=usuario)
                except ValidationError as erro:
                    raise CommandError('ADMIN_SEED_PASSWORD inválida: ' + ' '.join(erro.messages))
                usuario.set_password(password)

            if email:
                usuario.email = email
            usuario.is_staff = True
            usuario.is_superuser = True
            usuario.is_active = True
            usuario.save()

            if definir_senha:
                # Senha vinda do .env é provisória: força a troca no primeiro acesso.
                usuario.perfil.password_changed = False
                usuario.perfil.password_change_date = None
                usuario.perfil.save(update_fields=['password_changed', 'password_change_date'])

        if criado:
            self.stdout.write(self.style.SUCCESS(f'Superusuário {username} criado.'))
        elif definir_senha:
            self.stdout.write(self.style.SUCCESS(f'Superusuário {username} atualizado com nova senha.'))
        else:
            self.stdout.write(f'Superusuário {username} já existente; permissões garantidas.')
