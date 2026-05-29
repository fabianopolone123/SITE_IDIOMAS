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
    ImageAuthorizationConsultForm,
    ImageAuthorizationForm,
    ImageAuthorizationSignedTermForm,
    LoginForm,
    RegisterForm,
    VanAdminLoginForm,
    VanConsultForm,
    VanRegistrationForm,
    VanSettingsForm,
    VanSignedTermForm,
)
from .image_authorization_pdf import build_image_authorization_pdf
from .models import ImageAuthorization, ReviewState, StudyPhrase, VanRegistration, VanSettings
from .van_pdf import build_authorization_pdf

NEW_CARDS_BLOCK_SIZE = 20
VAN_REGISTRATION_LIMIT = 17
ALICE_DECK_PREFIX = 'alice-'
TECH_DECK_PREFIX = 'tech-'
RANDOM_SHORT_DECK_PREFIX = 'random-'


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
    alice_stats = deck_stats(request.user, ALICE_DECK_PREFIX)
    tech_stats = deck_stats(request.user, TECH_DECK_PREFIX)
    random_short_stats = deck_stats(request.user, RANDOM_SHORT_DECK_PREFIX)
    states = ReviewState.objects.filter(user=request.user, phrase__deck_key__startswith=ALICE_DECK_PREFIX)
    total_phrases = alice_stats['total_phrases']
    studied_count = states.count()
    due_count = alice_stats['due_count']
    new_today = new_cards_started_today(request.user)
    new_available = alice_stats['new_available']
    next_due = alice_stats['next_due']

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
            'alice_stats': alice_stats,
            'tech_stats': tech_stats,
            'random_short_stats': random_short_stats,
        },
    )


@login_required
def study(request):
    allow_new_block = request.GET.get('continue_new') == '1'
    state = next_due_state(request.user, deck_prefix=ALICE_DECK_PREFIX, allow_new_block=allow_new_block)
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

    return render_study(request, state, stage, deck='alice')


@login_required
def due_reviews(request):
    state = next_due_review_state(request.user, ALICE_DECK_PREFIX)
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

    return render_study(request, state, stage, deck='alice', review_only=True)


@login_required
def tech_study(request):
    state = next_due_state(request.user, deck_prefix=TECH_DECK_PREFIX, allow_new_block=True)
    if state is None:
        return render(
            request,
            'studies/no_cards.html',
            {
                'title': 'Nenhum card de tecnologia disponível agora.',
                'message': 'Quando novos cards de TI forem importados, eles aparecerão neste módulo.',
            },
        )

    stage = request.GET.get('stage', 'audio')
    if request.GET.get('reveal') == '1':
        stage = 'answer'
    if stage not in {'audio', 'text', 'answer'}:
        stage = 'audio'

    return render_study(request, state, stage, deck='tech')


@login_required
def tech_due_reviews(request):
    state = next_due_review_state(request.user, TECH_DECK_PREFIX)
    if state is None:
        return render(
            request,
            'studies/no_cards.html',
            {
                'title': 'Revisões de tecnologia concluídas',
                'message': 'Não há cards de entrevista em TI vencidos agora. Você pode voltar ao dashboard ou iniciar cards novos.',
            },
        )

    stage = request.GET.get('stage', 'audio')
    if request.GET.get('reveal') == '1':
        stage = 'answer'
    if stage not in {'audio', 'text', 'answer'}:
        stage = 'audio'

    return render_study(request, state, stage, deck='tech', review_only=True)


@login_required
def random_short_study(request):
    state = next_due_state(
        request.user,
        deck_prefix=RANDOM_SHORT_DECK_PREFIX,
        allow_new_block=True,
        random_new=True,
    )
    if state is None:
        return render(
            request,
            'studies/no_cards.html',
            {
                'title': 'Nenhuma frase curta disponível agora.',
                'message': 'Quando novas frases curtas forem importadas, elas aparecerão neste módulo.',
            },
        )

    stage = request.GET.get('stage', 'audio')
    if request.GET.get('reveal') == '1':
        stage = 'answer'
    if stage not in {'audio', 'text', 'answer'}:
        stage = 'audio'

    return render_study(request, state, stage, deck='random')


@login_required
def random_short_due_reviews(request):
    state = next_due_review_state(request.user, RANDOM_SHORT_DECK_PREFIX)
    if state is None:
        return render(
            request,
            'studies/no_cards.html',
            {
                'title': 'Revisões de frases curtas concluídas',
                'message': 'Não há frases curtas vencidas agora. Você pode voltar ao dashboard ou sortear uma frase nova.',
            },
        )

    stage = request.GET.get('stage', 'audio')
    if request.GET.get('reveal') == '1':
        stage = 'answer'
    if stage not in {'audio', 'text', 'answer'}:
        stage = 'audio'

    return render_study(request, state, stage, deck='random', review_only=True)


@login_required
@require_POST
def review(request, state_id):
    state = get_object_or_404(ReviewState, id=state_id, user=request.user)
    return handle_review(request, state, deck='alice')


@login_required
@require_POST
def tech_review(request, state_id):
    state = get_object_or_404(
        ReviewState,
        id=state_id,
        user=request.user,
        phrase__deck_key__startswith=TECH_DECK_PREFIX,
    )
    return handle_review(request, state, deck='tech')


@login_required
@require_POST
def random_short_review(request, state_id):
    state = get_object_or_404(
        ReviewState,
        id=state_id,
        user=request.user,
        phrase__deck_key__startswith=RANDOM_SHORT_DECK_PREFIX,
    )
    return handle_review(request, state, deck='random')


def handle_review(request, state, deck):
    grade = request.POST.get('grade')
    valid_grades = {choice[0] for choice in ReviewState.GRADE_CHOICES}
    if grade not in valid_grades:
        messages.error(request, 'Escolha uma nota válida para a revisão.')
        return redirect(study_route_for_deck(deck))

    state.schedule(grade, immediate_again=(deck in {'tech', 'random'}))
    state.save()
    messages.success(request, 'Revisão registrada. A próxima data foi recalculada.')
    if request.POST.get('review_only') == '1':
        return redirect(due_route_for_deck(deck))
    return redirect(study_route_for_deck(deck))


def study_route_for_deck(deck):
    return {
        'tech': 'tech_study',
        'random': 'random_short_study',
    }.get(deck, 'study')


def due_route_for_deck(deck):
    return {
        'tech': 'tech_due_reviews',
        'random': 'random_short_due_reviews',
    }.get(deck, 'due_reviews')


def render_study(request, state, stage, deck, review_only=False):
    if deck == 'tech':
        context = {
            'state': state,
            'stage': stage,
            'review_only': review_only,
            'deck': 'tech',
            'deck_label': 'Entrevista de TI',
            'study_url_name': 'tech_study',
            'due_url_name': 'tech_due_reviews',
            'review_url_name': 'tech_review',
            'again_label': 'volta agora',
        }
    elif deck == 'random':
        context = {
            'state': state,
            'stage': stage,
            'review_only': review_only,
            'deck': 'random',
            'deck_label': 'Frases curtas',
            'study_url_name': 'random_short_study',
            'due_url_name': 'random_short_due_reviews',
            'review_url_name': 'random_short_review',
            'again_label': 'volta agora',
        }
    else:
        context = {
            'state': state,
            'stage': stage,
            'review_only': review_only,
            'deck': 'alice',
            'deck_label': 'Alice',
            'study_url_name': 'study',
            'due_url_name': 'due_reviews',
            'review_url_name': 'review',
            'again_label': 'volta em 1 min',
        }
    return render(request, 'studies/study.html', context)


def new_cards_started_today(user):
    return ReviewState.objects.filter(
        user=user,
        first_seen_at__date=timezone.localdate(),
        phrase__deck_key__startswith=ALICE_DECK_PREFIX,
    ).count()


def next_due_review_state(user, deck_prefix):
    return (
        ReviewState.objects.filter(user=user, due_at__lte=timezone.now(), phrase__deck_key__startswith=deck_prefix)
        .select_related('phrase')
        .order_by('due_at', 'phrase__order')
        .first()
    )


def next_due_state(user, deck_prefix, allow_new_block=False, random_new=False):
    now = timezone.now()
    due_state = next_due_review_state(user, deck_prefix)
    if due_state:
        return due_state

    studied_phrase_ids = ReviewState.objects.filter(
        user=user,
        phrase__deck_key__startswith=deck_prefix,
    ).values('phrase_id')
    next_phrase = (
        StudyPhrase.objects.exclude(id__in=studied_phrase_ids)
        .filter(deck_key__startswith=deck_prefix)
        .filter(Q(italian_text__isnull=False) & ~Q(italian_text=''))
    )
    if random_new:
        next_phrase = next_phrase.order_by('?').first()
    else:
        next_phrase = next_phrase.order_by('order', 'id').first()
    if next_phrase is None:
        return None

    new_today = new_cards_started_today(user)
    if new_today and new_today % NEW_CARDS_BLOCK_SIZE == 0 and not allow_new_block:
        return 'new_limit'

    return ReviewState.objects.create(user=user, phrase=next_phrase, first_seen_at=now, due_at=now)


def deck_stats(user, deck_prefix):
    now = timezone.now()
    phrases = StudyPhrase.objects.filter(deck_key__startswith=deck_prefix)
    states = ReviewState.objects.filter(user=user, phrase__deck_key__startswith=deck_prefix)
    total = phrases.count()
    studied = states.count()
    return {
        'total_phrases': total,
        'studied_count': studied,
        'due_count': states.filter(due_at__lte=now).count(),
        'new_available': max(total - studied, 0),
        'next_due': states.filter(due_at__gt=now).aggregate(next=Min('due_at'))['next'],
    }


def van_home(request):
    return render(request, 'inscricao_van/home.html', van_registration_capacity_context())


def van_register(request):
    form = VanRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        existing_registration = find_existing_pending_registration(form)
        if existing_registration:
            form.existing_registration = existing_registration
        elif van_registration_remaining_slots() <= 0:
            capacity = van_settings().capacity
            messages.error(request, f'As {capacity} vagas da van ja foram preenchidas.')
            return render(
                request,
                'inscricao_van/register.html',
                {'form': form, **van_registration_capacity_context()},
            )
        registration = form.save()
        return redirect('van_signature', public_id=registration.public_id)
    return render(request, 'inscricao_van/register.html', {'form': form, **van_registration_capacity_context()})


def van_registration_capacity_context():
    capacity = van_settings().capacity
    registrations_count = VanRegistration.objects.count()
    remaining_slots = max(capacity - registrations_count, 0)
    return {
        'van_registration_limit': capacity,
        'van_registrations_count': registrations_count,
        'van_remaining_slots': remaining_slots,
        'van_registration_full': remaining_slots <= 0,
    }


def van_settings():
    return VanSettings.load()


def van_registration_remaining_slots():
    return van_registration_capacity_context()['van_remaining_slots']


def find_existing_pending_registration(form):
    return (
        VanRegistration.objects.filter(
            responsible_cpf=form.cleaned_data['responsible_cpf'],
            minor_birth_date=form.cleaned_data['minor_birth_date'],
            status=VanRegistration.PENDING_SIGNATURE,
        )
        .order_by('-created_at')
        .first()
    )


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


def term_home(request):
    return render(request, 'termo/home.html')


def term_register(request):
    form = ImageAuthorizationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        authorization = form.save()
        return redirect('term_signature', public_id=authorization.public_id)
    return render(request, 'termo/register.html', {'form': form})


def term_consult(request):
    form = ImageAuthorizationConsultForm(request.POST or None)
    authorization = None
    if request.method == 'POST' and form.is_valid():
        authorization = (
            ImageAuthorization.objects.filter(
                responsible_cpf=form.cleaned_data['responsible_cpf'],
                minor_cpf=form.cleaned_data['minor_cpf'],
            )
            .order_by('-created_at')
            .first()
        )
        if authorization is None:
            messages.error(request, 'Termo não encontrado com esses dados.')
    return render(request, 'termo/consult.html', {'form': form, 'authorization': authorization})


def term_signature(request, public_id):
    authorization = get_object_or_404(ImageAuthorization, public_id=public_id)
    form = ImageAuthorizationSignedTermForm(request.POST or None, request.FILES or None, instance=authorization)
    if request.method == 'POST' and form.is_valid():
        try:
            form.save()
        except OSError:
            messages.error(
                request,
                'Não foi possível salvar o termo assinado agora. Tente novamente em instantes ou avise a organização.',
            )
        else:
            return redirect('term_success', public_id=authorization.public_id)
    return render(request, 'termo/signature.html', {'authorization': authorization, 'form': form})


def term_success(request, public_id):
    authorization = get_object_or_404(ImageAuthorization, public_id=public_id)
    return render(request, 'termo/success.html', {'authorization': authorization})


def term_download(request, public_id):
    authorization = get_object_or_404(ImageAuthorization, public_id=public_id)
    buffer = build_image_authorization_pdf(authorization)
    filename = f'termo_imagem_{authorization.minor_name.replace(" ", "_").lower()}.pdf'
    return FileResponse(buffer, as_attachment=True, filename=filename)


def van_admin_login(request):
    if request.session.get('van_admin_ok'):
        return redirect('van_admin_choice')
    form = VanAdminLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        request.session['van_admin_ok'] = True
        return redirect('van_admin_choice')
    return render(request, 'inscricao_van/admin_login.html', {'form': form})


def van_admin_logout(request):
    request.session.pop('van_admin_ok', None)
    return redirect('van_admin_login')


def require_van_admin(request):
    if not request.session.get('van_admin_ok'):
        raise Http404()


def van_admin_choice(request):
    require_van_admin(request)
    return render(request, 'inscricao_van/admin_choice.html')


def van_admin_dashboard(request):
    require_van_admin(request)
    registrations = VanRegistration.objects.all()
    settings = van_settings()
    pending_registrations = registrations.filter(status=VanRegistration.PENDING_SIGNATURE)
    signed_registrations = registrations.filter(status=VanRegistration.SIGNED_RECEIVED)
    totals = {
        'total': registrations.count(),
        'signed': signed_registrations.count(),
        'pending': pending_registrations.count(),
        'remaining_slots': van_registration_remaining_slots(),
        'limit': settings.capacity,
    }
    return render(
        request,
        'inscricao_van/admin_dashboard.html',
        {
            'capacity_form': VanSettingsForm(instance=settings),
            'pending_registrations': pending_registrations,
            'registrations': registrations,
            'signed_registrations': signed_registrations,
            'totals': totals,
        },
    )


@require_POST
def van_admin_update_capacity(request):
    require_van_admin(request)
    settings = van_settings()
    form = VanSettingsForm(request.POST, instance=settings)
    if form.is_valid():
        form.save()
        messages.success(request, 'Quantidade de vagas da van atualizada.')
    else:
        messages.error(request, 'Nao foi possivel atualizar a quantidade de vagas.')
    return redirect('van_admin_dashboard')


def term_admin_dashboard(request):
    require_van_admin(request)
    authorizations = ImageAuthorization.objects.all()
    image_totals = {
        'total': authorizations.count(),
        'signed': authorizations.filter(status=ImageAuthorization.SIGNED_RECEIVED).count(),
        'pending': authorizations.filter(status=ImageAuthorization.PENDING_SIGNATURE).count(),
    }
    return render(
        request,
        'termo/admin_dashboard.html',
        {
            'authorizations': authorizations,
            'image_totals': image_totals,
        },
    )


def van_admin_download_signed(request, public_id):
    require_van_admin(request)
    registration = get_object_or_404(VanRegistration, public_id=public_id)
    if not registration.signed_term:
        raise Http404()
    filename = registration.signed_term.name.rsplit('/', 1)[-1]
    return FileResponse(registration.signed_term.open('rb'), as_attachment=True, filename=filename)


@require_POST
def van_admin_reject_signed(request, public_id):
    require_van_admin(request)
    registration = get_object_or_404(VanRegistration, public_id=public_id)
    if registration.signed_term:
        registration.signed_term.delete(save=False)
    registration.status = VanRegistration.PENDING_SIGNATURE
    registration.save(update_fields=['signed_term', 'status', 'updated_at'])
    messages.success(
        request,
        'Termo assinado desaprovado. A inscricao voltou para pendente de envio.',
    )
    return redirect('van_admin_dashboard')


@require_POST
def van_admin_delete_registration(request, public_id):
    require_van_admin(request)
    registration = get_object_or_404(VanRegistration, public_id=public_id)
    minor_name = registration.minor_name
    if registration.signed_term:
        registration.signed_term.delete(save=False)
    registration.delete()
    messages.success(request, f'Inscricao de {minor_name} excluida. A vaga foi liberada.')
    return redirect('van_admin_dashboard')


def term_admin_download_signed(request, public_id):
    require_van_admin(request)
    authorization = get_object_or_404(ImageAuthorization, public_id=public_id)
    if not authorization.signed_term:
        raise Http404()
    filename = authorization.signed_term.name.rsplit('/', 1)[-1]
    return FileResponse(authorization.signed_term.open('rb'), as_attachment=True, filename=filename)


@require_POST
def term_admin_reject_signed(request, public_id):
    require_van_admin(request)
    authorization = get_object_or_404(ImageAuthorization, public_id=public_id)
    if authorization.signed_term:
        authorization.signed_term.delete(save=False)
    authorization.status = ImageAuthorization.PENDING_SIGNATURE
    authorization.save(update_fields=['signed_term', 'status', 'updated_at'])
    messages.success(
        request,
        'Termo de imagem desaprovado. O envio voltou para pendente.',
    )
    return redirect('term_admin_dashboard')


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


def term_admin_download_all(request):
    require_van_admin(request)
    response = HttpResponse(content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="termos_imagem_assinados.zip"'
    with zipfile.ZipFile(response, 'w', zipfile.ZIP_DEFLATED) as archive:
        for authorization in ImageAuthorization.objects.filter(signed_term__gt=''):
            filename = f'{authorization.minor_name}_{authorization.public_id}.pdf'.replace(' ', '_')
            with authorization.signed_term.open('rb') as uploaded:
                archive.writestr(filename, uploaded.read())
    return response
