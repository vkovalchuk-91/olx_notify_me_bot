import pytest
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from apps.web.forms import TelegramWebRegistrationForm
from apps.monitors.models import CheckerQuery, FoundAd, QuerySource
from apps.monitors.services import MonitorService
from apps.telegram_users.models import TelegramUser, WebRegistrationRequest


@pytest.fixture
def telegram_user(db):
    return TelegramUser.objects.create(
        user_telegram_id=123456,
        username='testuser',
        full_name='Test User',
        is_active=True,
    )


@pytest.mark.django_db
def test_create_query_with_ads(telegram_user):
    parsed_ads = [{
        'ad_url': 'https://www.olx.ua/test-ad',
        'ad_description': 'Test ad',
        'ad_price': '1000',
        'currency': 'грн.',
    }]
    query = MonitorService.create_query_with_ads(
        telegram_user.user_telegram_id,
        'Test Query',
        'https://www.olx.ua/uk/list/q-test/',
        parsed_ads,
    )
    assert query.query_name == 'Test Query'
    assert query.source == QuerySource.OLX
    assert FoundAd.objects.filter(query=query).count() == 1


@pytest.mark.django_db
def test_soft_delete_and_restore(telegram_user):
    query = CheckerQuery.objects.create(
        user=telegram_user,
        query_name='Q1',
        query_url='https://www.olx.ua/uk/list/q-one/',
    )
    MonitorService.soft_delete_query(query.pk)
    query.refresh_from_db()
    assert query.is_deleted is True
    assert query.is_active is False

    restored = MonitorService.restore_query(telegram_user.user_telegram_id, query.query_url)
    assert restored.is_deleted is False
    assert restored.is_active is True


@pytest.mark.django_db
def test_transform_query_text_to_olx_url():
    url = MonitorService.transform_query_text_to_olx_url('test query')
    assert url.startswith('https://www.olx.ua/uk/list/q-')
    assert url.endswith('/')


@pytest.mark.django_db
def test_api_checker_queries_list(client, telegram_user):
    user = User.objects.create_user(username='admin', password='pass', is_staff=True)
    client.force_login(user)
    CheckerQuery.objects.create(
        user=telegram_user,
        query_name='API Query',
        query_url='https://www.olx.ua/uk/list/q-api/',
    )
    response = client.get('/api/checker-queries/')
    assert response.status_code == 200
    assert response.json()['count'] == 1


@pytest.mark.django_db
def test_web_registration_requires_telegram_code(telegram_user):
    registration_request = WebRegistrationRequest.objects.create(
        token='test-token',
        telegram_user=telegram_user,
    )

    form = TelegramWebRegistrationForm(data={
        'token': registration_request.token,
        'password1': 'strong-test-password',
        'password2': 'strong-test-password',
    })

    assert form.is_valid(), form.errors
    user = form.save()
    telegram_user.refresh_from_db()
    registration_request.refresh_from_db()
    assert telegram_user.web_user == user
    assert registration_request.is_used is True


@pytest.mark.django_db
def test_login_is_case_insensitive():
    User.objects.create_user(username='TestUser', password='pass')

    user = authenticate(username='testuser', password='pass')

    assert user is not None
    assert user.username == 'TestUser'
