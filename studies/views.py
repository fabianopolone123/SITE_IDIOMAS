from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Min, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import LoginForm, RegisterForm
from .models import ReviewState, StudyPhrase

NEW_CARDS_BLOCK_SIZE = 20


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'studies/home.html')


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Conta criada. Ja da para comecar os estudos.')
        return redirect('dashboard')

    return render(request, 'studies/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('dashboard')

    return render(request, 'studies/login.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def dashboard(request):
    now = timezone.now()
    states = ReviewState.objects.filter(user=request.user)
    total_phrases = StudyPhrase.objects.count()
    studied_count = states.count()
    due_count = states.filter(due_at__lte=now).count()
    new_today = new_cards_started_today(request.user)
    new_available = max(total_phrases - studied_count, 0)
    next_due = states.filter(due_at__gt=now).aggregate(next=Min('due_at'))['next']

    recent_reviews = (
        states.filter(last_reviewed_at__isnull=False)
        .select_related('phrase')
        .order_by('-last_reviewed_at')[:6]
    )
    grade_counts = states.values('last_grade').annotate(total=Count('id'))

    return render(
        request,
        'studies/dashboard.html',
        {
            'total_phrases': total_phrases,
            'studied_count': studied_count,
            'due_count': due_count,
            'new_today': new_today,
            'new_cards_block_size': NEW_CARDS_BLOCK_SIZE,
            'new_available': new_available,
            'next_due': next_due,
            'recent_reviews': recent_reviews,
            'grade_counts': grade_counts,
        },
    )


@login_required
def study(request):
    allow_new_block = request.GET.get('continue_new') == '1'
    state = next_due_state(request.user, allow_new_block=allow_new_block)
    if state == 'new_limit':
        return render(
            request,
            'studies/new_limit.html',
            {
                'new_today': new_cards_started_today(request.user),
                'new_cards_block_size': NEW_CARDS_BLOCK_SIZE,
            },
        )
    if state is None:
        return render(request, 'studies/no_cards.html')

    stage = request.GET.get('stage', 'audio')
    if request.GET.get('reveal') == '1':
        stage = 'answer'
    if stage not in {'audio', 'text', 'answer'}:
        stage = 'audio'

    return render(request, 'studies/study.html', {'state': state, 'stage': stage})


@login_required
def due_reviews(request):
    state = next_due_review_state(request.user)
    if state is None:
        return render(
            request,
            'studies/no_cards.html',
            {
                'title': 'Revisoes concluidas',
                'message': 'Nao ha revisoes vencidas agora. Voce pode voltar ao dashboard ou iniciar cards novos.',
            },
        )

    stage = request.GET.get('stage', 'audio')
    if request.GET.get('reveal') == '1':
        stage = 'answer'
    if stage not in {'audio', 'text', 'answer'}:
        stage = 'audio'

    return render(request, 'studies/study.html', {'state': state, 'stage': stage, 'review_only': True})


@login_required
@require_POST
def review(request, state_id):
    state = get_object_or_404(ReviewState, id=state_id, user=request.user)
    grade = request.POST.get('grade')
    valid_grades = {choice[0] for choice in ReviewState.GRADE_CHOICES}
    if grade not in valid_grades:
        messages.error(request, 'Escolha uma nota valida para a revisao.')
        return redirect('study')

    state.schedule(grade)
    state.save()
    messages.success(request, 'Revisao registrada. A proxima data foi recalculada.')
    if request.POST.get('review_only') == '1':
        return redirect('due_reviews')
    return redirect('study')


def new_cards_started_today(user):
    return ReviewState.objects.filter(user=user, first_seen_at__date=timezone.localdate()).count()


def next_due_review_state(user):
    return (
        ReviewState.objects.filter(user=user, due_at__lte=timezone.now())
        .select_related('phrase')
        .order_by('due_at', 'phrase__order')
        .first()
    )


def next_due_state(user, allow_new_block=False):
    now = timezone.now()
    due_state = next_due_review_state(user)
    if due_state:
        return due_state

    studied_phrase_ids = ReviewState.objects.filter(user=user).values('phrase_id')
    next_phrase = (
        StudyPhrase.objects.exclude(id__in=studied_phrase_ids)
        .filter(Q(italian_text__isnull=False) & ~Q(italian_text=''))
        .order_by('order', 'id')
        .first()
    )
    if next_phrase is None:
        return None

    new_today = new_cards_started_today(user)
    if new_today and new_today % NEW_CARDS_BLOCK_SIZE == 0 and not allow_new_block:
        return 'new_limit'

    return ReviewState.objects.create(user=user, phrase=next_phrase, first_seen_at=now, due_at=now)
