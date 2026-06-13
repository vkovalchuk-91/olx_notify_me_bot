from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from apps.audit_logs.models import JobLog
from apps.insta_monitor.models import InstaContent, InstaObservedUser, InstaSubscription
from apps.insta_monitor.tasks import check_new_insta_content_task
from apps.monitors.models import CheckerQuery, FoundAd, QuerySource, detect_source
from apps.monitors.services import MonitorService
from apps.monitors.tasks import check_new_ads_task, initialize_query_ads_task
from apps.monitors.tasks_logic import InstaMonitorService
from apps.telegram_users.models import TelegramUser, WebRegistrationRequest

from .forms import TelegramUserAdminForm, TelegramWebRegistrationForm


PAGE_SIZE = 100


def register(request):
    if request.user.is_authenticated:
        return redirect('web:dashboard')
    if request.method == 'POST':
        form = TelegramWebRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Web-акаунт створено і прив’язано до Telegram')
            return redirect('web:dashboard')
    else:
        registration_request = _get_or_create_registration_request(request.GET.get('token'))
        form = TelegramWebRegistrationForm(initial={'token': registration_request.token})
    registration_request = _get_or_create_registration_request(
        request.POST.get('token') if request.method == 'POST' else request.GET.get('token')
    )
    telegram_user = registration_request.telegram_user if registration_request else None
    return render(request, 'web/register.html', {
        'form': form,
        'registration_request': registration_request,
        'telegram_user': telegram_user,
        'bot_link': _build_telegram_registration_link(registration_request),
        'bot_username': settings.TELEGRAM_BOT_USERNAME,
    })


@login_required
def dashboard(request):
    queries = CheckerQuery.objects.filter(is_deleted=False).select_related('user')
    if not request.user.is_staff:
        queries = queries.filter(user__web_user=request.user)
    recent_ads = FoundAd.objects.filter(is_active=True).select_related('query', 'query__user')[:20]
    context = {
        'active_queries_count': queries.filter(is_active=True).count(),
        'inactive_queries_count': queries.filter(is_active=False).count(),
        'olx_queries_count': queries.filter(source=QuerySource.OLX, is_active=True).count(),
        'rieltor_queries_count': queries.filter(source=QuerySource.RIELTOR, is_active=True).count(),
        'recent_ads': recent_ads,
        'insta_users_count': _get_user_insta_subscriptions_queryset(request).filter(is_active=True).count(),
    }
    return render(request, 'web/dashboard.html', context)


@login_required
def queries_list(request):
    return _queries_list(request, source=None, source_label='Всі моніторинги')


@login_required
def olx_queries_list(request):
    return _queries_list(request, source=QuerySource.OLX, source_label='OLX')


@login_required
def rieltor_queries_list(request):
    return _queries_list(request, source=QuerySource.RIELTOR, source_label='Rieltor.ua')


def _queries_list(request, source: str | None, source_label: str):
    queries = CheckerQuery.objects.filter(is_deleted=False).select_related('user')
    if not request.user.is_staff:
        queries = queries.filter(user__web_user=request.user)
    if source:
        queries = queries.filter(source=source)
    page_obj, queries = _paginate(request, queries)
    return render(request, 'web/queries_list.html', {
        'queries': queries,
        'page_obj': page_obj,
        'pagination_query': _pagination_query(request),
        'source': source or '',
        'source_label': source_label,
        'sources': QuerySource.choices,
    })


@login_required
def query_add_by_url(request):
    return _query_add_by_url(request, required_source=None)


@login_required
def olx_query_add_by_url(request):
    return _query_add_by_url(request, required_source=QuerySource.OLX)


@login_required
def rieltor_query_add_by_url(request):
    return _query_add_by_url(request, required_source=QuerySource.RIELTOR)


def _query_add_by_url(request, required_source: str | None):
    if request.method == 'POST':
        query_name = request.POST.get('query_name', '').strip()
        query_url = request.POST.get('query_url', '').strip()
        user_id = _get_selected_telegram_user_id(request)
        if not user_id:
            messages.error(request, 'Оберіть Telegram користувача')
            return redirect(_query_add_route(required_source))
        if MonitorService.query_url_exists(user_id, query_url):
            if MonitorService.query_url_is_deleted(user_id, query_url):
                MonitorService.restore_query(user_id, query_url)
                messages.success(request, 'Моніторинг відновлено')
            else:
                messages.warning(request, 'Моніторинг з таким URL вже існує')
            return redirect(_queries_list_route(required_source or detect_source(query_url)))
        if not MonitorService.is_supported_ads_url(query_url):
            messages.error(request, 'Підтримуються тільки URL з olx.ua або rieltor.ua')
            return redirect(_query_add_route(required_source))
        query_source = detect_source(query_url)
        if required_source and query_source != required_source:
            messages.error(request, f'Ця сторінка приймає тільки URL для {_source_label(required_source)}')
            return redirect(_query_add_route(required_source))
        query = MonitorService.create_query(user_id, query_name, query_url, is_active=False)
        initialize_query_ads_task.delay(query.pk)
        messages.success(request, f'Моніторинг "{query_name}" додано. Первинна перевірка запущена у фоні.')
        return redirect(_queries_list_route(query_source))
    users = _get_available_telegram_users(request)
    return render(request, 'web/query_add_url.html', {
        'users': users,
        'required_source': required_source or '',
        'source_label': _source_label(required_source) if required_source else 'OLX або Rieltor.ua',
    })


@login_required
def query_add_by_text(request):
    if request.method == 'POST':
        query_text = request.POST.get('query_text', '').strip()
        user_id = _get_selected_telegram_user_id(request)
        if not user_id:
            messages.error(request, 'Оберіть Telegram користувача')
            return redirect('web:query_add_text')
        query_url = MonitorService.transform_query_text_to_olx_url(query_text)
        if MonitorService.query_url_exists(user_id, query_url):
            messages.warning(request, 'Моніторинг з таким запитом вже існує')
            return redirect('web:olx_queries')
        query = MonitorService.create_query(user_id, query_text, query_url, is_active=False)
        initialize_query_ads_task.delay(query.pk)
        messages.success(request, f'Моніторинг "{query_text}" додано. Первинна перевірка запущена у фоні.')
        return redirect('web:olx_queries')
    users = _get_available_telegram_users(request)
    return render(request, 'web/query_add_text.html', {'users': users})


@login_required
def query_toggle(request, query_id):
    query = get_object_or_404(_get_user_queries_queryset(request), pk=query_id, is_deleted=False)
    MonitorService.toggle_query_active(query_id)
    messages.success(request, f'Моніторинг "{query.query_name}" оновлено')
    return redirect(_queries_list_route(query.source))


@login_required
def query_delete(request, query_id):
    query = get_object_or_404(_get_user_queries_queryset(request), pk=query_id)
    MonitorService.soft_delete_query(query_id)
    messages.success(request, f'Моніторинг "{query.query_name}" видалено')
    return redirect(_queries_list_route(query.source))


@login_required
def found_ads_list(request):
    return _found_ads_list(request, source=None, source_label='Всі оголошення')


@login_required
def olx_found_ads_list(request):
    return _found_ads_list(request, source=QuerySource.OLX, source_label='OLX')


@login_required
def rieltor_found_ads_list(request):
    return _found_ads_list(request, source=QuerySource.RIELTOR, source_label='Rieltor.ua')


def _found_ads_list(request, source: str | None, source_label: str):
    query_id = request.GET.get('query_id')
    ads = FoundAd.objects.select_related('query', 'query__user')
    if not request.user.is_staff:
        ads = ads.filter(query__user__web_user=request.user)
    if source:
        ads = ads.filter(query__source=source)
    if query_id:
        ads = ads.filter(query_id=query_id)
    page_obj, ads = _paginate(request, ads)
    return render(request, 'web/found_ads_list.html', {
        'ads': ads,
        'page_obj': page_obj,
        'pagination_query': _pagination_query(request),
        'query_id': query_id,
        'source_label': source_label,
    })


@login_required
def insta_users_list(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        user_id = _get_selected_telegram_user_id(request)
        if not user_id:
            messages.error(request, 'Оберіть Telegram користувача')
            return redirect('web:insta_users')
        if username:
            user, created, restored = InstaMonitorService.add_observed_user(username, user_id)
            if created:
                messages.success(request, f'Додано Instagram моніторинг @{user.username}')
            elif restored:
                messages.success(request, f'Відновлено Instagram моніторинг @{user.username}')
            else:
                messages.success(request, f'Підписку на Instagram моніторинг @{user.username} оновлено')
        return redirect('web:insta_users')
    subscriptions = list(
        _get_user_insta_subscriptions_queryset(request)
        .select_related('observed_user', 'user')
        .order_by('observed_user__username', 'user__created_at')
    )
    page_obj, subscriptions = _paginate(request, subscriptions)
    return render(request, 'web/insta_users.html', {
        'subscriptions': subscriptions,
        'users': _get_available_telegram_users(request),
        'page_obj': page_obj,
        'pagination_query': _pagination_query(request),
    })


@login_required
def insta_user_toggle(request, user_id):
    telegram_user_id = None if request.user.is_staff else _get_selected_telegram_user_id(request)
    subscription = InstaMonitorService.toggle_subscription_active(user_id, telegram_user_id)
    messages.success(
        request,
        f'Instagram моніторинг @{subscription.observed_user.username} '
        f'{"активовано" if subscription.is_active else "деактивовано"}',
    )
    return redirect('web:insta_users')


@login_required
def insta_user_delete(request, user_id):
    telegram_user_id = None if request.user.is_staff else _get_selected_telegram_user_id(request)
    subscription = InstaMonitorService.soft_delete_subscription(user_id, telegram_user_id)
    messages.success(request, f'Підписку на Instagram моніторинг @{subscription.observed_user.username} видалено')
    return redirect('web:insta_users')


@login_required
def insta_content_list(request):
    username = request.GET.get('username')
    content = InstaContent.objects.filter(observed_user__is_deleted=False).select_related('observed_user')
    if not request.user.is_staff:
        content = content.filter(
            observed_user__subscriptions__user__web_user=request.user,
            observed_user__subscriptions__is_deleted=False,
        )
    if username:
        content = content.filter(observed_user__username=username)
    content = content.distinct()
    page_obj, content_items = _paginate(request, content)
    return render(request, 'web/insta_content.html', {
        'content_items': content_items,
        'page_obj': page_obj,
        'pagination_query': _pagination_query(request),
        'username': username,
    })


@login_required
def insta_content_preview(request, content_id):
    content = InstaContent.objects.select_related('observed_user').filter(observed_user__is_deleted=False)
    if not request.user.is_staff:
        content = content.filter(
            observed_user__subscriptions__user__web_user=request.user,
            observed_user__subscriptions__is_deleted=False,
        )
    content_item = get_object_or_404(content.distinct(), pk=content_id)
    return render(request, 'web/insta_content_preview.html', {'item': content_item})


@login_required
def trigger_check_ads(request):
    check_new_ads_task.delay()
    messages.info(request, 'Запущено перевірку OLX/rieltor оголошень')
    return redirect('web:dashboard')


@login_required
def trigger_check_olx(request):
    check_new_ads_task.delay(QuerySource.OLX)
    messages.info(request, 'Запущено перевірку OLX оголошень')
    return redirect('web:olx_queries')


@login_required
def trigger_check_rieltor(request):
    check_new_ads_task.delay(QuerySource.RIELTOR)
    messages.info(request, 'Запущено перевірку Rieltor.ua оголошень')
    return redirect('web:rieltor_queries')


@login_required
def trigger_check_insta(request):
    check_new_insta_content_task.delay()
    messages.info(request, 'Запущено перевірку Instagram контенту')
    return redirect('web:dashboard')


@staff_member_required
def admin_users(request):
    users = TelegramUser.objects.select_related('web_user').all()
    page_obj, users = _paginate(request, users)
    return render(request, 'web/admin_users.html', {
        'users': users,
        'page_obj': page_obj,
        'pagination_query': _pagination_query(request),
    })


@staff_member_required
def admin_user_edit(request, user_id):
    telegram_user = get_object_or_404(TelegramUser.objects.select_related('web_user'), pk=user_id)
    if request.method == 'POST':
        form = TelegramUserAdminForm(request.POST, instance=telegram_user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Користувача {telegram_user} оновлено')
            return redirect('web:admin_users')
    else:
        form = TelegramUserAdminForm(instance=telegram_user)
    return render(request, 'web/admin_user_edit.html', {
        'form': form,
        'telegram_user': telegram_user,
    })


@staff_member_required
def admin_logs(request):
    from apps.audit_logs.models import LogLevel, LogSource

    logs = JobLog.objects.all()
    level = request.GET.get('level')
    source = request.GET.get('source')
    job_name = request.GET.get('job_name')
    if level:
        logs = logs.filter(level=level)
    if source:
        logs = logs.filter(source=source)
    if job_name:
        logs = logs.filter(job_name__icontains=job_name)
    page_obj, logs = _paginate(request, logs)
    return render(request, 'web/admin_logs.html', {
        'logs': logs,
        'page_obj': page_obj,
        'pagination_query': _pagination_query(request),
        'level': level or '',
        'source': source or '',
        'job_name': job_name or '',
        'log_levels': LogLevel.choices,
        'log_sources': LogSource.choices,
    })


def _get_available_telegram_users(request):
    users = TelegramUser.objects.filter(is_active=True)
    if request.user.is_staff:
        return users
    return users.filter(web_user=request.user)


def _get_selected_telegram_user_id(request) -> int:
    if request.user.is_staff:
        return int(request.POST.get('user_telegram_id', 0))
    telegram_user = TelegramUser.objects.filter(web_user=request.user, is_active=True).first()
    return telegram_user.user_telegram_id if telegram_user else 0


def _get_user_queries_queryset(request):
    queries = CheckerQuery.objects.all()
    if request.user.is_staff:
        return queries
    return queries.filter(user__web_user=request.user)


def _get_user_insta_subscriptions_queryset(request):
    subscriptions = InstaSubscription.objects.filter(is_deleted=False, observed_user__is_deleted=False)
    if request.user.is_staff:
        return subscriptions
    return subscriptions.filter(user__web_user=request.user)


def _source_label(source: str | None) -> str:
    if source == QuerySource.OLX:
        return 'OLX'
    if source == QuerySource.RIELTOR:
        return 'Rieltor.ua'
    return 'OLX або Rieltor.ua'


def _queries_list_route(source: str | None) -> str:
    if source == QuerySource.OLX:
        return 'web:olx_queries'
    if source == QuerySource.RIELTOR:
        return 'web:rieltor_queries'
    return 'web:queries_list'


def _query_add_route(source: str | None) -> str:
    if source == QuerySource.OLX:
        return 'web:olx_query_add_url'
    if source == QuerySource.RIELTOR:
        return 'web:rieltor_query_add_url'
    return 'web:query_add_url'


def _get_or_create_registration_request(token: str | None) -> WebRegistrationRequest:
    if token:
        registration_request = WebRegistrationRequest.objects.filter(token=token, is_used=False).first()
        if registration_request:
            return registration_request
    return MonitorService.create_web_registration_request()


def _build_telegram_registration_link(registration_request: WebRegistrationRequest | None) -> str:
    if not registration_request or not settings.TELEGRAM_BOT_USERNAME:
        return ''
    return f'https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start=webreg_{registration_request.token}'


def _paginate(request, items, per_page: int = PAGE_SIZE):
    paginator = Paginator(items, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))
    return page_obj, page_obj.object_list


def _pagination_query(request) -> str:
    query = request.GET.copy()
    query.pop('page', None)
    encoded = query.urlencode()
    return f'{encoded}&' if encoded else ''
