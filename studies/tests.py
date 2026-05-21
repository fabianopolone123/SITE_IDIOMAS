from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from .alice_deck import ALICE_CARDS, iter_alice_cards
from .tech_deck import iter_tech_cards
from .models import Profile, ReviewState, StudyPhrase, VanRegistration
from .views import NEW_CARDS_BLOCK_SIZE


class ReviewStateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ana', password='123')
        self.phrase = StudyPhrase.objects.create(
            deck_key='alice-test-review',
            order=1,
            italian_text='Alice guardo il coniglio bianco.',
        )

    def test_good_first_review_schedules_two_days(self):
        state = ReviewState.objects.create(user=self.user, phrase=self.phrase)
        state.schedule(ReviewState.GOOD)

        self.assertEqual(state.interval_days, 2)
        self.assertEqual(state.repetitions, 1)
        self.assertGreater(state.due_at, timezone.now())

    def test_again_returns_card_to_learning_queue(self):
        state = ReviewState.objects.create(user=self.user, phrase=self.phrase, interval_days=5)
        state.schedule(ReviewState.AGAIN)

        self.assertEqual(state.interval_days, 0)
        self.assertEqual(state.lapses, 1)
        self.assertLess((state.due_at - timezone.now()).total_seconds(), 660)


class AccountAndStudyFlowTests(TestCase):
    def setUp(self):
        self.phrase = StudyPhrase.objects.create(
            deck_key='alice-test-flow',
            order=1,
            italian_text='Il coniglio bianco guardo l orologio.',
            study_note='coniglio = coelho',
        )

    def test_register_creates_profile_and_logs_user_in(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'maria',
                'password': '1',
                'full_name': 'Maria Rossi',
                'whatsapp': '11999999999',
                'email': 'maria@example.com',
            },
            follow=True,
        )

        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(Profile.objects.filter(full_name='Maria Rossi').exists())

    def test_study_page_creates_first_review_state(self):
        user = User.objects.create_user(username='joao', password='123')
        self.client.force_login(user)

        response = self.client.get(reverse('study'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ReviewState.objects.filter(user=user, phrase=self.phrase).count(), 1)

    def test_new_card_gate_after_twenty_new_cards_today(self):
        user = User.objects.create_user(username='lia', password='123')
        phrases = [
            StudyPhrase(deck_key=f'alice-new-{index}', order=index + 2, italian_text=f'Frase nova {index}.')
            for index in range(NEW_CARDS_BLOCK_SIZE)
        ]
        StudyPhrase.objects.bulk_create(phrases)
        for phrase in StudyPhrase.objects.order_by('order')[:NEW_CARDS_BLOCK_SIZE]:
            ReviewState.objects.create(user=user, phrase=phrase, due_at=timezone.now() + timedelta(days=1))
        self.client.force_login(user)

        response = self.client.get(reverse('study'))

        self.assertTemplateUsed(response, 'studies/new_limit.html')

    def test_new_card_gate_can_be_bypassed_by_confirmation(self):
        user = User.objects.create_user(username='leo', password='123')
        phrases = [
            StudyPhrase(deck_key=f'alice-extra-{index}', order=index + 2, italian_text=f'Frase extra {index}.')
            for index in range(NEW_CARDS_BLOCK_SIZE + 1)
        ]
        StudyPhrase.objects.bulk_create(phrases)
        for phrase in StudyPhrase.objects.order_by('order')[:NEW_CARDS_BLOCK_SIZE]:
            ReviewState.objects.create(user=user, phrase=phrase, due_at=timezone.now() + timedelta(days=1))
        self.client.force_login(user)

        response = self.client.get(f"{reverse('study')}?continue_new=1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ReviewState.objects.filter(user=user).count(), NEW_CARDS_BLOCK_SIZE + 1)

    def test_due_reviews_does_not_create_new_cards(self):
        user = User.objects.create_user(username='bia', password='123')
        self.client.force_login(user)

        response = self.client.get(reverse('due_reviews'))

        self.assertTemplateUsed(response, 'studies/no_cards.html')
        self.assertEqual(ReviewState.objects.filter(user=user).count(), 0)

    def test_due_reviews_shows_only_due_cards_and_keeps_flow(self):
        user = User.objects.create_user(username='caio', password='123')
        due_phrase = StudyPhrase.objects.create(deck_key='alice-due', order=2, italian_text='Carta vencida.')
        future_phrase = StudyPhrase.objects.create(deck_key='alice-future', order=3, italian_text='Carta futura.')
        due_state = ReviewState.objects.create(user=user, phrase=due_phrase, due_at=timezone.now() - timedelta(minutes=1))
        ReviewState.objects.create(user=user, phrase=future_phrase, due_at=timezone.now() + timedelta(days=1))
        self.client.force_login(user)

        response = self.client.get(reverse('due_reviews'))
        self.assertContains(response, due_phrase.italian_text)

        response = self.client.post(
            reverse('review', args=[due_state.id]),
            {'grade': ReviewState.GOOD, 'review_only': '1'},
        )

        self.assertRedirects(response, reverse('due_reviews'))
        self.assertEqual(ReviewState.objects.filter(user=user).count(), 2)


class ImportDeckTests(TestCase):
    def test_import_updates_existing_cards_without_deleting_review_history(self):
        user = User.objects.create_user(username='nina', password='123')
        italian_text = ALICE_CARDS[0][0]
        phrase = StudyPhrase.objects.create(
            order=99,
            italian_text=italian_text,
            portuguese_text='traducao antiga',
            study_note='nota antiga',
        )
        review = ReviewState.objects.create(user=user, phrase=phrase, repetitions=3)

        call_command('import_alice_phrases', limit=2, stdout=StringIO())

        phrase.refresh_from_db()
        review.refresh_from_db()
        self.assertEqual(review.phrase_id, phrase.id)
        self.assertEqual(review.repetitions, 3)
        self.assertEqual(phrase.deck_key, 'alice-0001')
        self.assertEqual(phrase.portuguese_text, ALICE_CARDS[0][1])
        self.assertEqual(StudyPhrase.objects.count(), 2)

    def test_import_uses_deck_key_when_text_changes(self):
        user = User.objects.create_user(username='paolo', password='123')
        card = next(iter_alice_cards(limit=1))
        phrase = StudyPhrase.objects.create(
            deck_key=card['deck_key'],
            order=card['order'],
            italian_text='Texto antigo do mesmo card.',
            portuguese_text='traducao antiga',
            study_note='nota antiga',
        )
        review = ReviewState.objects.create(user=user, phrase=phrase, repetitions=5)

        call_command('import_alice_phrases', limit=1, stdout=StringIO())

        phrase.refresh_from_db()
        review.refresh_from_db()
        self.assertEqual(review.phrase_id, phrase.id)
        self.assertEqual(review.repetitions, 5)
        self.assertEqual(phrase.italian_text, card['italian_text'])

    def test_import_tech_cards_creates_separate_deck(self):
        call_command('import_tech_phrases', limit=200, stdout=StringIO())

        self.assertEqual(StudyPhrase.objects.filter(deck_key__startswith='tech-').count(), 200)
        first = StudyPhrase.objects.get(deck_key='tech-0001')
        last = StudyPhrase.objects.get(deck_key='tech-0200')
        self.assertIn('Entrevista de TI', first.source_title)
        self.assertIn('Vocabulário desta frase', first.study_note)
        self.assertLessEqual(len(first.italian_text), 30)
        self.assertIn('apprendimento continuo', last.italian_text)


class TechStudyFlowTests(TestCase):
    def setUp(self):
        self.tech_phrase = StudyPhrase.objects.create(
            deck_key='tech-test-001',
            source_title='Entrevista de TI em italiano',
            chapter='Tecnologia e entrevista',
            order=10001,
            italian_text='Ho esperienza con API.',
            portuguese_text='Tenho experiência com API.',
            study_note='Vocabulário palavra por palavra:\n- API = API',
        )
        self.alice_phrase = StudyPhrase.objects.create(
            deck_key='alice-test-separate',
            order=1,
            italian_text='Alice studia italiano.',
        )

    def test_tech_study_creates_only_tech_review_state(self):
        user = User.objects.create_user(username='techuser', password='123')
        self.client.force_login(user)

        response = self.client.get(reverse('tech_study'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ReviewState.objects.filter(user=user, phrase=self.tech_phrase).count(), 1)
        self.assertFalse(ReviewState.objects.filter(user=user, phrase=self.alice_phrase).exists())

    def test_tech_again_returns_card_immediately(self):
        user = User.objects.create_user(username='techagain', password='123')
        state = ReviewState.objects.create(user=user, phrase=self.tech_phrase, interval_days=4)
        self.client.force_login(user)

        response = self.client.post(reverse('tech_review', args=[state.id]), {'grade': ReviewState.AGAIN})

        state.refresh_from_db()
        self.assertRedirects(response, reverse('tech_study'))
        self.assertLessEqual(state.due_at, timezone.now())
        self.assertEqual(state.interval_days, 0)


class VanRegistrationTests(TestCase):
    def registration_payload(self):
        return {
            'responsible_name': 'Responsavel Teste',
            'responsible_cpf': '12345678900',
            'responsible_phone': '16999999999',
            'responsible_phone_alt': '1633334444',
            'minor_name': 'Adolescente Teste',
            'minor_cpf': '98765432100',
            'event_name': 'Passaporte: Sua Identidade em Alta Definição',
            'event_start_date': '2026-06-01',
            'event_end_date': '2026-06-02',
            'health_info': 'Alergia a amendoim.',
            'city': 'São Carlos',
            'signature_date': '2026-05-21',
        }

    def test_van_registration_creates_pending_record(self):
        response = self.client.post(reverse('van_register'), self.registration_payload())

        registration = VanRegistration.objects.get()
        self.assertRedirects(response, reverse('van_signature', args=[registration.public_id]))
        self.assertEqual(registration.status, VanRegistration.PENDING_SIGNATURE)

    def test_van_transport_is_forced_to_van(self):
        payload = self.registration_payload()
        payload['transport_by'] = 'outro transporte'

        self.client.post(reverse('van_register'), payload)

        registration = VanRegistration.objects.get()
        self.assertEqual(registration.transport_by, 'van')

    def test_van_term_download_returns_pdf(self):
        registration = VanRegistration.objects.create(**self.registration_payload())

        response = self.client.get(reverse('van_download_term', args=[registration.public_id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_van_upload_signed_term_marks_registration_complete(self):
        registration = VanRegistration.objects.create(**self.registration_payload())
        upload = SimpleUploadedFile('termo.pdf', b'%PDF-1.4 teste', content_type='application/pdf')

        response = self.client.post(
            reverse('van_signature', args=[registration.public_id]),
            {'signed_term': upload},
        )

        registration.refresh_from_db()
        self.assertRedirects(response, reverse('van_success', args=[registration.public_id]))
        self.assertEqual(registration.status, VanRegistration.SIGNED_RECEIVED)
        self.assertEqual(registration.signed_term.name, f'inscricao_van/termos_assinados/{registration.public_id}.pdf')

    def test_van_upload_storage_error_returns_form_with_message(self):
        registration = VanRegistration.objects.create(**self.registration_payload())
        upload = SimpleUploadedFile('termo.pdf', b'%PDF-1.4 teste', content_type='application/pdf')

        with patch('studies.views.VanSignedTermForm.save', side_effect=OSError):
            response = self.client.post(
                reverse('van_signature', args=[registration.public_id]),
                {'signed_term': upload},
                follow=True,
            )

        registration.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Não foi possível salvar o termo assinado agora')
        self.assertEqual(registration.status, VanRegistration.PENDING_SIGNATURE)

    def test_van_consult_finds_registration(self):
        VanRegistration.objects.create(**self.registration_payload())

        response = self.client.post(
            reverse('van_consult'),
            {'responsible_cpf': '12345678900', 'minor_cpf': '98765432100'},
        )

        self.assertContains(response, 'Adolescente Teste')

    def test_van_admin_requires_password_then_shows_dashboard(self):
        VanRegistration.objects.create(**self.registration_payload())

        login_response = self.client.post(reverse('van_admin_login'), {'password': '1580'})
        dashboard_response = self.client.get(reverse('van_admin_dashboard'))

        self.assertRedirects(login_response, reverse('van_admin_dashboard'))
        self.assertContains(dashboard_response, 'Adolescente Teste')
