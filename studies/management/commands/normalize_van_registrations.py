from django.core.management.base import BaseCommand
from django.db import transaction

from studies.formatters import only_digits
from studies.models import VanRegistration


class Command(BaseCommand):
    help = 'Normaliza CPFs e telefones das inscrições da van para armazenar somente números.'

    def handle(self, *args, **options):
        updated = 0
        with transaction.atomic():
            for registration in VanRegistration.objects.select_for_update().all():
                fields = {
                    'responsible_cpf': only_digits(registration.responsible_cpf),
                    'minor_cpf': only_digits(registration.minor_cpf),
                    'minor_document': only_digits(registration.minor_document),
                    'responsible_phone': only_digits(registration.responsible_phone),
                    'responsible_phone_alt': only_digits(registration.responsible_phone_alt),
                }
                changed_fields = []
                for field, value in fields.items():
                    if getattr(registration, field) != value:
                        setattr(registration, field, value)
                        changed_fields.append(field)
                if changed_fields:
                    registration.save(update_fields=changed_fields + ['updated_at'])
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f'{updated} inscrição(ões) normalizada(s).'))
