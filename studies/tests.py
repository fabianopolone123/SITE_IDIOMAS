from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .alice_deck import ALICE_CARDS, iter_alice_cards
from .models import Profile, ReviewState, StudyPhrase
from .views import NEW_CARDS_BLOCK_SIZE


class ReviewStateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ana', password='123')
        self.phrase = StudyPhrase.objects.create(order=1, italian_text='Alice guardo il coniglio bianco.')

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
            StudyPhrase(order=index + 2, italian_text=f'Frase nuova {index}.')
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
            StudyPhrase(order=index + 2, italian_text=f'Frase extra {index}.')
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
        due_phrase = StudyPhrase.objects.create(order=2, italian_text='Carta vencida.')
        future_phrase = StudyPhrase.objects.create(order=3, italian_text='Carta futura.')
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
