from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from studies.models import StudyPhrase
from studies.random_short_deck import RANDOM_SHORT_SOURCE_TITLE, iter_random_short_cards


class Command(BaseCommand):
    help = 'Importa frases curtas aleatorias em italiano preservando revisoes existentes.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50, help='Quantidade maxima de cards a importar.')

    def handle(self, *args, **options):
        cards = list(iter_random_short_cards(options['limit']))
        if not cards:
            raise CommandError('Nenhum card de frases curtas foi encontrado.')

        created, updated = self.upsert_cards(cards)
        self.stdout.write(
            self.style.SUCCESS(
                f'Importacao de {RANDOM_SHORT_SOURCE_TITLE}: {created} criados, {updated} atualizados, historico preservado.'
            )
        )

    def upsert_cards(self, cards):
        deck_keys = [card['deck_key'] for card in cards]
        created = 0
        updated = 0
        with transaction.atomic():
            existing = {
                phrase.deck_key: phrase
                for phrase in StudyPhrase.objects.select_for_update().filter(deck_key__in=deck_keys)
            }
            for card in cards:
                phrase = existing.get(card['deck_key'])
                if phrase is None:
                    StudyPhrase.objects.create(**card)
                    created += 1
                    continue

                changed = False
                for field, value in card.items():
                    if getattr(phrase, field) != value:
                        setattr(phrase, field, value)
                        changed = True
                if changed:
                    phrase.save(
                        update_fields=[
                            'order',
                            'italian_text',
                            'portuguese_text',
                            'study_note',
                            'source_title',
                            'chapter',
                        ]
                    )
                    updated += 1
        return created, updated
