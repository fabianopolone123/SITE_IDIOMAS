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
from .random_short_deck import iter_random_short_cards
from .tech_deck import iter_tech_cards
from .models import ImageAuthorization, Profile, ReviewState, StudyPhrase, VanRegistration, VanSettings
from .views import NEW_CARDS_BLOCK_SIZE, VAN_REGISTRATION_LIMIT


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

    def test_again_returns_card_in_one_minute(self):
        state = ReviewState.objects.create(user=self.user, phrase=self.phrase, interval_days=5)
        state.schedule(ReviewState.AGAIN)

        self.assertEqual(state.interval_days, 0)
        self.assertEqual(state.lapses, 1)
        seconds_until_due = (state.due_at - timezone.now()).total_seconds()
        self.assertGreater(seconds_until_due, 45)
        self.assertLess(seconds_until_due, 75)


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

    def test_import_random_short_cards_creates_separate_deck_with_detailed_notes(self):
        call_command('import_random_short_phrases', limit=50, stdout=StringIO())

        self.assertEqual(StudyPhrase.objects.filter(deck_key__startswith='random-').count(), 50)
        first = StudyPhrase.objects.get(deck_key='random-0001')
        last = StudyPhrase.objects.get(deck_key='random-0050')
        self.assertIn('Frases curtas', first.source_title)
        self.assertIn('Vocabulário', first.study_note)
        self.assertIn('Treino', first.study_note)
        self.assertIn('Ci vediamo', last.italian_text)


class TechStudyFlowTests(TestCase):
    def setUp(self):
        self.tech_phrase = StudyPhrase.objects.create(
            deck_key='tech-test-001',
            source_title='Entrevista de TI em italiano',
            chapter='Tecnologia e entrevista',
            order=10001,
            italian_text='Ho esperienza con API.',
            portuguese_text='Tenho experiÃªncia com API.',
            study_note='VocabulÃ¡rio palavra por palavra:\n- API = API',
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


class RandomShortStudyFlowTests(TestCase):
    def setUp(self):
        self.random_phrase = StudyPhrase.objects.create(
            deck_key='random-test-001',
            source_title='Frases curtas aleatorias em italiano',
            chapter='Frases curtas aleatorias',
            order=20001,
            italian_text='Grazie mille.',
            portuguese_text='Muito obrigado.',
            study_note='Vocabulário: grazie = obrigado.\nTreino: use como agradecimento forte.',
        )
        self.alice_phrase = StudyPhrase.objects.create(
            deck_key='alice-random-separate',
            order=1,
            italian_text='Alice studia italiano.',
        )

    def test_random_short_study_creates_only_random_review_state(self):
        user = User.objects.create_user(username='randomuser', password='123')
        self.client.force_login(user)

        response = self.client.get(reverse('random_short_study'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ReviewState.objects.filter(user=user, phrase=self.random_phrase).count(), 1)
        self.assertFalse(ReviewState.objects.filter(user=user, phrase=self.alice_phrase).exists())

    def test_random_short_again_returns_card_immediately(self):
        user = User.objects.create_user(username='randomagain', password='123')
        state = ReviewState.objects.create(user=user, phrase=self.random_phrase, interval_days=4)
        self.client.force_login(user)

        response = self.client.post(reverse('random_short_review', args=[state.id]), {'grade': ReviewState.AGAIN})

        state.refresh_from_db()
        self.assertRedirects(response, reverse('random_short_study'))
        self.assertLessEqual(state.due_at, timezone.now())
        self.assertEqual(state.interval_days, 0)


class VanRegistrationTests(TestCase):
    def registration_payload(self):
        return {
            'responsible_name': 'Responsavel Teste',
            'responsible_rg': '12.345.678-9',
            'responsible_cpf': '123.456.789-00',
            'responsible_phone': '(16) 99999-9999',
            'responsible_email': 'responsavel@example.com',
            'minor_name': 'Adolescente Teste',
            'minor_birth_date': '2010-05-10',
            'minor_document': '98.765.432-1',
        }

    def test_van_registration_creates_pending_record(self):
        response = self.client.post(reverse('van_register'), self.registration_payload())

        registration = VanRegistration.objects.get()
        self.assertRedirects(response, reverse('van_signature', args=[registration.public_id]))
        self.assertEqual(registration.status, VanRegistration.PENDING_SIGNATURE)
        self.assertEqual(registration.responsible_cpf, '12345678900')
        self.assertEqual(registration.responsible_rg, '12.345.678-9')
        self.assertEqual(registration.minor_document, '987654321')
        self.assertEqual(registration.responsible_phone, '16999999999')

    def test_van_home_shows_remaining_slots(self):
        for index in range(3):
            payload = self.registration_payload()
            payload['minor_name'] = f'Adolescente {index}'
            payload['minor_birth_date'] = f'2010-05-{10 + index:02d}'
            VanRegistration.objects.create(**payload)

        response = self.client.get(reverse('van_home'))

        self.assertContains(response, 'Vagas restantes')
        self.assertContains(response, f'<strong>{VAN_REGISTRATION_LIMIT - 3}</strong>', html=True)
        self.assertContains(response, f'de {VAN_REGISTRATION_LIMIT} vagas na van')

    def test_van_registration_blocks_new_record_when_limit_is_reached(self):
        for index in range(VAN_REGISTRATION_LIMIT):
            payload = self.registration_payload()
            payload['responsible_cpf'] = f'900000000{index:02d}'
            payload['minor_name'] = f'Adolescente {index}'
            payload['minor_birth_date'] = f'2009-05-{index + 1:02d}'
            VanRegistration.objects.create(**payload)

        response = self.client.post(reverse('van_register'), self.registration_payload(), follow=True)

        self.assertEqual(VanRegistration.objects.count(), VAN_REGISTRATION_LIMIT)
        self.assertContains(response, 'Vagas restantes')
        self.assertContains(response, '<strong>0</strong>', html=True)
        self.assertContains(response, 'As 17 vagas da van ja foram preenchidas')

    def test_van_registration_uses_admin_capacity_setting(self):
        VanSettings.load().save()
        settings = VanSettings.load()
        settings.capacity = 2
        settings.save()
        for index in range(2):
            payload = self.registration_payload()
            payload['responsible_cpf'] = f'700000000{index:02d}'
            payload['minor_name'] = f'Adolescente limite {index}'
            payload['minor_birth_date'] = f'2009-07-{index + 1:02d}'
            VanRegistration.objects.create(**payload)

        response = self.client.post(reverse('van_register'), self.registration_payload(), follow=True)

        self.assertEqual(VanRegistration.objects.count(), 2)
        self.assertContains(response, 'As 2 vagas da van ja foram preenchidas')
        self.assertContains(response, '2 inscri')

    def test_van_registration_reuses_pending_record_even_when_limit_is_reached(self):
        existing = VanRegistration.objects.create(**self.registration_payload())
        for index in range(VAN_REGISTRATION_LIMIT - 1):
            payload = self.registration_payload()
            payload['responsible_cpf'] = f'123456789{index:02d}'
            payload['minor_name'] = f'Outro adolescente {index}'
            payload['minor_birth_date'] = f'2010-06-{index + 1:02d}'
            VanRegistration.objects.create(**payload)

        response = self.client.post(reverse('van_register'), self.registration_payload())

        self.assertRedirects(response, reverse('van_signature', args=[existing.public_id]))
        self.assertEqual(VanRegistration.objects.count(), VAN_REGISTRATION_LIMIT)

    def test_van_registration_reuses_pending_record_for_double_submit(self):
        first_response = self.client.post(reverse('van_register'), self.registration_payload())
        payload = self.registration_payload()
        payload['responsible_email'] = 'novo@example.com'
        second_response = self.client.post(reverse('van_register'), payload)

        registration = VanRegistration.objects.get()
        self.assertRedirects(first_response, reverse('van_signature', args=[registration.public_id]))
        self.assertRedirects(second_response, reverse('van_signature', args=[registration.public_id]))
        self.assertEqual(VanRegistration.objects.count(), 1)
        self.assertEqual(registration.responsible_email, 'novo@example.com')

    def test_van_registration_allows_new_record_after_signed_term_received(self):
        registration = VanRegistration.objects.create(**self.registration_payload())
        registration.status = VanRegistration.SIGNED_RECEIVED
        registration.save(update_fields=['status'])

        self.client.post(reverse('van_register'), self.registration_payload())

        self.assertEqual(VanRegistration.objects.count(), 2)

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
            {'responsible_cpf': '123.456.789-00', 'minor_birth_date': '2010-05-10'},
        )

        self.assertContains(response, 'Adolescente Teste')

    def test_normalize_van_registrations_command_updates_existing_data(self):
        registration = VanRegistration.objects.create(
            **{
                **self.registration_payload(),
                'responsible_cpf': '123.456.789-00',
                'responsible_phone': '(16) 99999-9999',
            }
        )

        call_command('normalize_van_registrations', stdout=StringIO())

        registration.refresh_from_db()
        self.assertEqual(registration.responsible_cpf, '12345678900')
        self.assertEqual(registration.responsible_phone, '16999999999')
        self.assertEqual(registration.responsible_phone_formatted, '(16) 99999-9999')

    def test_van_admin_requires_password_then_shows_choice_and_dashboard(self):
        VanRegistration.objects.create(**self.registration_payload())

        login_response = self.client.post(reverse('van_admin_login'), {'password': '1580'})
        choice_response = self.client.get(reverse('van_admin_choice'))
        dashboard_response = self.client.get(reverse('van_admin_dashboard'))

        self.assertRedirects(login_response, reverse('van_admin_choice'))
        self.assertContains(choice_response, 'Dashboard da van')
        self.assertContains(choice_response, 'Dashboard dos termos')
        self.assertContains(dashboard_response, 'Adolescente Teste')
        self.assertContains(dashboard_response, 'Quantidade de vagas')
        self.assertContains(dashboard_response, 'Faltam enviar termo')

    def test_van_admin_can_update_capacity(self):
        self.client.post(reverse('van_admin_login'), {'password': '1580'})

        response = self.client.post(reverse('van_admin_update_capacity'), {'capacity': 22}, follow=True)

        self.assertRedirects(response, reverse('van_admin_dashboard'))
        self.assertEqual(VanSettings.load().capacity, 22)
        self.assertContains(response, 'Quantidade de vagas da van atualizada')
        self.assertContains(response, 'Vagas restantes de 22')

    def test_van_admin_dashboard_lists_pending_signed_terms(self):
        pending = VanRegistration.objects.create(**self.registration_payload())
        signed_payload = self.registration_payload()
        signed_payload['responsible_cpf'] = '99988877766'
        signed_payload['minor_name'] = 'Adolescente Assinado'
        signed_payload['minor_birth_date'] = '2010-06-10'
        signed = VanRegistration.objects.create(**signed_payload)
        upload = SimpleUploadedFile('termo.pdf', b'%PDF-1.4 teste', content_type='application/pdf')
        signed.signed_term.save('termo.pdf', upload, save=True)

        self.client.post(reverse('van_admin_login'), {'password': '1580'})
        response = self.client.get(reverse('van_admin_dashboard'))

        self.assertContains(response, 'Faltam enviar termo assinado')
        self.assertContains(response, pending.minor_name)
        self.assertNotContains(response, 'Adolescente Assinado</strong>')

    def test_van_admin_dashboard_has_copy_name_lists(self):
        pending = VanRegistration.objects.create(**self.registration_payload())
        signed_payload = self.registration_payload()
        signed_payload['responsible_cpf'] = '99988877766'
        signed_payload['minor_name'] = 'Adolescente Assinado'
        signed_payload['minor_birth_date'] = '2010-06-10'
        signed = VanRegistration.objects.create(**signed_payload)
        upload = SimpleUploadedFile('termo.pdf', b'%PDF-1.4 teste', content_type='application/pdf')
        signed.signed_term.save('termo.pdf', upload, save=True)

        self.client.post(reverse('van_admin_login'), {'password': '1580'})
        response = self.client.get(reverse('van_admin_dashboard'))
        html = response.content.decode()

        self.assertContains(response, 'Copiar todos')
        self.assertContains(response, 'Copiar com termo')
        self.assertContains(response, 'Copiar faltando termo')
        self.assertIn(f'id="copy-all-names" readonly hidden>{pending.minor_name}', html)
        self.assertIn('Adolescente Assinado', html)
        self.assertIn('id="copy-signed-names" readonly hidden>Adolescente Assinado', html)
        self.assertIn(f'id="copy-pending-names" readonly hidden>{pending.minor_name}', html)

    def test_van_admin_can_reject_signed_term_and_restore_pending_upload(self):
        registration = VanRegistration.objects.create(**self.registration_payload())
        upload = SimpleUploadedFile('termo.pdf', b'%PDF-1.4 teste', content_type='application/pdf')
        registration.signed_term.save('termo.pdf', upload, save=True)
        registration.refresh_from_db()
        signed_name = registration.signed_term.name
        storage = registration.signed_term.storage
        self.assertEqual(registration.status, VanRegistration.SIGNED_RECEIVED)

        self.client.post(reverse('van_admin_login'), {'password': '1580'})
        response = self.client.post(reverse('van_admin_reject_signed', args=[registration.public_id]))

        registration.refresh_from_db()
        self.assertRedirects(response, reverse('van_admin_dashboard'))
        self.assertEqual(registration.status, VanRegistration.PENDING_SIGNATURE)
        self.assertFalse(registration.signed_term)
        self.assertFalse(storage.exists(signed_name))

        consult_response = self.client.post(
            reverse('van_consult'),
            {'responsible_cpf': '123.456.789-00', 'minor_birth_date': '2010-05-10'},
        )
        self.assertContains(consult_response, 'Falta enviar termo assinado')
        self.assertContains(consult_response, 'Enviar termo agora')

    def test_van_admin_can_delete_registration_and_free_slot(self):
        registrations = []
        for index in range(VAN_REGISTRATION_LIMIT):
            payload = self.registration_payload()
            payload['responsible_cpf'] = f'800000000{index:02d}'
            payload['minor_name'] = f'Adolescente excluir {index}'
            payload['minor_birth_date'] = f'2008-05-{index + 1:02d}'
            registrations.append(VanRegistration.objects.create(**payload))
        registration = registrations[0]
        upload = SimpleUploadedFile('termo.pdf', b'%PDF-1.4 teste', content_type='application/pdf')
        registration.signed_term.save('termo.pdf', upload, save=True)
        registration.refresh_from_db()
        signed_name = registration.signed_term.name
        storage = registration.signed_term.storage

        self.client.post(reverse('van_admin_login'), {'password': '1580'})
        response = self.client.post(reverse('van_admin_delete_registration', args=[registration.public_id]), follow=True)

        self.assertRedirects(response, reverse('van_admin_dashboard'))
        self.assertEqual(VanRegistration.objects.count(), VAN_REGISTRATION_LIMIT - 1)
        self.assertFalse(VanRegistration.objects.filter(public_id=registration.public_id).exists())
        self.assertFalse(storage.exists(signed_name))
        self.assertContains(response, 'A vaga foi liberada')
        self.assertContains(response, 'Vagas restantes de 17')
        self.assertContains(response, '<span>1</span>', html=True)


class ImageAuthorizationTests(TestCase):
    def authorization_payload(self):
        return {
            'responsible_name': 'Responsavel Imagem',
            'responsible_cpf': '222.333.444-05',
            'minor_name': 'Adolescente Imagem',
            'minor_cpf': '333.444.555-06',
            'event_name': 'Evento Teste',
            'event_start_date': '2026-06-10',
            'event_end_date': '2026-06-12',
            'health_info': 'Sem alergias informadas.',
            'responsible_phone': '(16) 98888-7777',
            'responsible_phone_alt': '(16) 3333-2222',
            'city': 'SÃ£o Carlos',
            'signature_date': '2026-05-22',
        }

    def test_term_register_creates_pending_authorization(self):
        response = self.client.post(reverse('term_register'), self.authorization_payload())

        authorization = ImageAuthorization.objects.get()
        self.assertRedirects(response, reverse('term_signature', args=[authorization.public_id]))
        self.assertEqual(authorization.status, ImageAuthorization.PENDING_SIGNATURE)
        self.assertEqual(authorization.responsible_cpf, '22233344405')
        self.assertEqual(authorization.minor_cpf, '33344455506')
        self.assertEqual(authorization.responsible_phone, '16988887777')

    def test_term_home_links_to_fill_and_consult(self):
        response = self.client.get(reverse('term_home'))

        self.assertContains(response, 'Preencher termo')
        self.assertContains(response, 'Consultar termo')

    def test_term_consult_finds_pending_authorization(self):
        authorization = ImageAuthorization.objects.create(**self.authorization_payload())

        response = self.client.post(
            reverse('term_consult'),
            {'responsible_cpf': '222.333.444-05', 'minor_cpf': '333.444.555-06'},
        )

        self.assertContains(response, authorization.minor_name)
        self.assertContains(response, 'Falta enviar o termo assinado')
        self.assertContains(response, 'Enviar termo agora')

    def test_term_download_returns_pdf(self):
        authorization = ImageAuthorization.objects.create(**self.authorization_payload())

        response = self.client.get(reverse('term_download', args=[authorization.public_id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_term_upload_signed_marks_authorization_complete(self):
        authorization = ImageAuthorization.objects.create(**self.authorization_payload())
        upload = SimpleUploadedFile('termo.pdf', b'%PDF-1.4 teste', content_type='application/pdf')

        response = self.client.post(
            reverse('term_signature', args=[authorization.public_id]),
            {'signed_term': upload},
        )

        authorization.refresh_from_db()
        self.assertRedirects(response, reverse('term_success', args=[authorization.public_id]))
        self.assertEqual(authorization.status, ImageAuthorization.SIGNED_RECEIVED)
        self.assertEqual(authorization.signed_term.name, f'termo_imagem/termos_assinados/{authorization.public_id}.pdf')

    def test_term_admin_dashboard_shows_image_authorization_report(self):
        ImageAuthorization.objects.create(**self.authorization_payload())

        self.client.post(reverse('van_admin_login'), {'password': '1580'})
        response = self.client.get(reverse('term_admin_dashboard'))

        self.assertContains(response, 'Autorizações de imagem e emergência')
        self.assertContains(response, 'Adolescente Imagem')
