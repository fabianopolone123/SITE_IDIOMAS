import zipfile

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Min, Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    LoginForm,
    RegisterForm,
    VanAdminLoginForm,
    VanConsultForm,
    VanRegistrationForm,
    VanSignedTermForm,
)
from .models import ReviewState, StudyPhrase, VanRegistration
from .van_pdf import build_authorization_pdf

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
        messages.success(request, 'Conta criada. Já dá para começar os estudos.')
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
                'title': 'Revisões concluídas',
                'message': 'Não há revisões vencidas agora. Você pode voltar ao dashboard ou iniciar cards novos.',
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
        messages.error(request, 'Escolha uma nota válida para a revisão.')
        return redirect('study')

    state.schedule(grade)
    state.save()
    messages.success(request, 'Revisão registrada. A próxima data foi recalculada.')
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


def van_home(request):
    return render(request, 'inscricao_van/home.html')


def van_register(request):
    form = VanRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        registration = form.save()
        return redirect('van_signature', public_id=registration.public_id)
    return render(request, 'inscricao_van/register.html', {'form': form})


def van_signature(request, public_id):
    registration = get_object_or_404(VanRegistration, public_id=public_id)
    form = VanSignedTermForm(request.POST or None, request.FILES or None, instance=registration)
    if request.method == 'POST' and form.is_valid():
        try:
            form.save()
        except OSError:
            messages.error(
                request,
                'Não foi possível salvar o termo assinado agora. Tente novamente em instantes ou avise a organização.',
            )
        else:
            return redirect('van_success', public_id=registration.public_id)
    return render(request, 'inscricao_van/signature.html', {'registration': registration, 'form': form})


def van_success(request, public_id):
    registration = get_object_or_404(VanRegistration, public_id=public_id)
    return render(request, 'inscricao_van/success.html', {'registration': registration})


def van_download_term(request, public_id):
    registration = get_object_or_404(VanRegistration, public_id=public_id)
    buffer = build_authorization_pdf(registration)
    filename = f'termo_autorizacao_{registration.minor_name.replace(" ", "_").lower()}.pdf'
    return FileResponse(buffer, as_attachment=True, filename=filename)


def van_consult(request):
    form = VanConsultForm(request.POST or None)
    registration = None
    if request.method == 'POST' and form.is_valid():
        registration = (
            VanRegistration.objects.filter(
                responsible_cpf=form.cleaned_data['responsible_cpf'],
                minor_birth_date=form.cleaned_data['minor_birth_date'],
            )
            .order_by('-created_at')
            .first()
        )
        if registration is None:
            messages.error(request, 'Inscrição não encontrada com esses dados.')
    return render(request, 'inscricao_van/consult.html', {'form': form, 'registration': registration})


def van_admin_login(request):
    if request.session.get('van_admin_ok'):
        return redirect('van_admin_dashboard')
    form = VanAdminLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        request.session['van_admin_ok'] = True
        return redirect('van_admin_dashboard')
    return render(request, 'inscricao_van/admin_login.html', {'form': form})


def van_admin_logout(request):
    request.session.pop('van_admin_ok', None)
    return redirect('van_admin_login')


def require_van_admin(request):
    if not request.session.get('van_admin_ok'):
        raise Http404()


def van_admin_dashboard(request):
    require_van_admin(request)
    registrations = VanRegistration.objects.all()
    totals = {
        'total': registrations.count(),
        'signed': registrations.filter(status=VanRegistration.SIGNED_RECEIVED).count(),
        'pending': registrations.filter(status=VanRegistration.PENDING_SIGNATURE).count(),
    }
    return render(
        request,
        'inscricao_van/admin_dashboard.html',
        {'registrations': registrations, 'totals': totals},
    )


def van_admin_download_signed(request, public_id):
    require_van_admin(request)
    registration = get_object_or_404(VanRegistration, public_id=public_id)
    if not registration.signed_term:
        raise Http404()
    filename = registration.signed_term.name.rsplit('/', 1)[-1]
    return FileResponse(registration.signed_term.open('rb'), as_attachment=True, filename=filename)


def van_admin_download_all(request):
    require_van_admin(request)
    response = HttpResponse(content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="termos_assinados_van.zip"'
    with zipfile.ZipFile(response, 'w', zipfile.ZIP_DEFLATED) as archive:
        for registration in VanRegistration.objects.filter(signed_term__gt=''):
            filename = f'{registration.minor_name}_{registration.public_id}.pdf'.replace(' ', '_')
            with registration.signed_term.open('rb') as uploaded:
                archive.writestr(filename, uploaded.read())
    return response
