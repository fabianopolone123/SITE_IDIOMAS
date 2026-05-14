import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from studies.alice_deck import ALICE_CARDS, iter_alice_cards
from studies.models import StudyPhrase


COMMON_WORDS = {
    'alice': 'nome da personagem',
    'coniglio': 'coelho',
    'sorella': 'irma',
    'libro': 'livro',
    'figure': 'figuras',
    'domande': 'perguntas',
    'porta': 'porta',
    'chiave': 'chave',
    'casa': 'casa',
    'tempo': 'tempo',
    'occhi': 'olhos',
    'mano': 'mao',
    'voce': 'voz',
    'tavolo': 'mesa',
    'giardino': 'jardim',
    'regina': 'rainha',
    'gatto': 'gato',
    'cappellaio': 'chapeleiro',
    'pensava': 'pensava',
    'diceva': 'dizia',
    'andare': 'ir',
    'vedere': 'ver',
    'parlare': 'falar',
}


class Command(BaseCommand):
    help = 'Importa frases curtas do PDF local de Alice para o banco de estudos.'

    def add_arguments(self, parser):
        parser.add_argument('--pdf', type=str, help='Caminho do PDF. Por padrao usa o primeiro PDF da pasta do projeto.')
        parser.add_argument('--limit', type=int, default=len(ALICE_CARDS), help='Quantidade maxima de frases a importar.')
        parser.add_argument(
            '--reset',
            action='store_true',
            help='PERIGOSO: remove frases existentes e apaga o historico de revisao ligado a elas.',
        )
        parser.add_argument('--from-pdf', action='store_true', help='Extrai automaticamente do PDF em vez de usar frases curtas curadas.')

    def handle(self, *args, **options):
        limit = options['limit']

        if options['from_pdf']:
            pdf_path = self.resolve_pdf(options.get('pdf'))
            phrases = [
                {
                    'deck_key': f'pdf-{index:04d}',
                    'order': index,
                    'italian_text': text,
                    'portuguese_text': '',
                    'study_note': self.build_note(text),
                }
                for index, text in enumerate(self.extract_phrases(pdf_path, limit), start=1)
            ]
            source_name = pdf_path.name
        else:
            phrases = list(iter_alice_cards(limit))
            source_name = 'frases curtas curadas de Alice'

        if not phrases:
            raise CommandError('Nenhuma frase adequada foi encontrada.')

        created, updated = self.upsert_phrases(phrases, reset=options['reset'])

        suffix = 'historico preservado' if not options['reset'] else 'historico apagado por --reset'
        self.stdout.write(
            self.style.SUCCESS(f'Importacao de {source_name}: {created} criadas, {updated} atualizadas, {suffix}.')
        )

    def upsert_phrases(self, phrases, reset=False):
        chapter = 'Alice nel paese delle meraviglie'
        with transaction.atomic():
            if reset:
                StudyPhrase.objects.all().delete()

            deck_keys = [phrase['deck_key'] for phrase in phrases]
            italian_texts = [phrase['italian_text'] for phrase in phrases]
            existing_by_key = {
                phrase.deck_key: phrase
                for phrase in StudyPhrase.objects.select_for_update().filter(deck_key__in=deck_keys)
            }
            existing_by_text = {
                phrase.italian_text: phrase
                for phrase in StudyPhrase.objects.select_for_update().filter(
                    deck_key__isnull=True,
                    italian_text__in=italian_texts,
                )
            }

            created = 0
            updated = 0
            for card in phrases:
                phrase = existing_by_key.get(card['deck_key']) or existing_by_text.get(card['italian_text'])
                if phrase is None:
                    StudyPhrase.objects.create(
                        deck_key=card['deck_key'],
                        order=card['order'],
                        italian_text=card['italian_text'],
                        portuguese_text=card['portuguese_text'],
                        study_note=card['study_note'],
                        chapter=chapter,
                    )
                    created += 1
                    continue

                changed = False
                for field, value in {
                    'deck_key': card['deck_key'],
                    'order': card['order'],
                    'italian_text': card['italian_text'],
                    'portuguese_text': card['portuguese_text'],
                    'study_note': card['study_note'],
                    'chapter': chapter,
                }.items():
                    if getattr(phrase, field) != value:
                        setattr(phrase, field, value)
                        changed = True

                if changed:
                    phrase.save(update_fields=['deck_key', 'order', 'italian_text', 'portuguese_text', 'study_note', 'chapter'])
                    updated += 1

        return created, updated

    def resolve_pdf(self, explicit_path):
        if explicit_path:
            path = Path(explicit_path)
            if not path.is_absolute():
                path = settings.BASE_DIR / path
        else:
            pdfs = sorted(settings.BASE_DIR.glob('*.pdf'))
            if not pdfs:
                raise CommandError('Nenhum PDF encontrado na pasta do projeto.')
            path = pdfs[0]

        if not path.exists():
            raise CommandError(f'PDF nao encontrado: {path}')
        return path

    def extract_phrases(self, pdf_path, limit):
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise CommandError('Instale pypdf para importar o livro: python -m pip install pypdf') from exc

        reader = PdfReader(str(pdf_path))
        raw_text = []
        for page in reader.pages:
            text = page.extract_text() or ''
            raw_text.append(text)

        text = '\n'.join(raw_text)
        text = re.sub(r'www\.writingshome\.com', ' ', text, flags=re.I)
        text = re.sub(r'Lewis Carroll\s+.\s+Le avventure.*?\n', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('•', ' ')

        candidates = re.split(r'(?<=[.!?])\s+', text)
        phrases = []
        seen = set()
        for candidate in candidates:
            cleaned = self.clean_sentence(candidate)
            if not self.is_good_phrase(cleaned):
                continue
            if cleaned in seen:
                continue
            seen.add(cleaned)
            phrases.append(cleaned)
            if len(phrases) >= limit:
                break
        return phrases

    def clean_sentence(self, sentence):
        sentence = re.sub(r'\b\d+\b', ' ', sentence)
        sentence = re.sub(r'\s+', ' ', sentence).strip()
        sentence = sentence.strip(' -"')
        return sentence

    def is_good_phrase(self, sentence):
        if not 35 <= len(sentence) <= 190:
            return False
        lowered = sentence.lower()
        blocked = ['capitolo', 'le avventure', 'paese delle meraviglie', 'writingshome']
        if any(term in lowered for term in blocked):
            return False
        if sentence.isupper():
            return False
        words = re.findall(r'[A-Za-zÀ-ÿ]+', sentence)
        return len(words) >= 7

    def build_note(self, sentence):
        words = re.findall(r'[A-Za-zÀ-ÿ]+', sentence.lower())
        matches = []
        for word in words:
            if word in COMMON_WORDS and word not in {item.split(' = ')[0] for item in matches}:
                matches.append(f'{word} = {COMMON_WORDS[word]}')
            if len(matches) >= 4:
                break

        vocabulary = '; '.join(matches) if matches else 'marque palavras conhecidas e tente inferir o restante pelo contexto'
        return (
            'Antes de avaliar, diga em voz alta o sentido geral da frase em portugues.\n'
            f'Vocabulário de apoio: {vocabulary}.\n'
            'Observe a ordem das palavras, o verbo principal e uma expressao que voce conseguiria reutilizar.'
        )
