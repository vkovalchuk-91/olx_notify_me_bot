from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit_logs.models import JobLog
from apps.insta_monitor.models import InstaContent, InstaObservedUser
from apps.insta_monitor.tasks import check_new_insta_content_task
from apps.monitors.models import CheckerQuery, FoundAd
from apps.monitors.services import MonitorService
from apps.monitors.tasks import check_new_ads_task, initialize_query_ads_task
from apps.monitors.tasks_logic import InstaMonitorService
from apps.telegram_users.models import TelegramUser

from .serializers import (
    CheckerQueryCreateSerializer,
    CheckerQuerySerializer,
    FoundAdSerializer,
    InstaContentSerializer,
    InstaObservedUserSerializer,
    InstaSubscriptionSerializer,
    JobLogSerializer,
    TelegramUserSerializer,
)


class TelegramUserViewSet(viewsets.ModelViewSet):
    queryset = TelegramUser.objects.all()
    serializer_class = TelegramUserSerializer
    lookup_field = 'user_telegram_id'


class CheckerQueryViewSet(viewsets.ModelViewSet):
    serializer_class = CheckerQuerySerializer

    def get_queryset(self):
        qs = CheckerQuery.objects.filter(is_deleted=False).select_related('user')
        user_id = self.request.query_params.get('user_telegram_id')
        source = self.request.query_params.get('source')
        if user_id:
            qs = qs.filter(user_id=user_id)
        if source:
            qs = qs.filter(source=source)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = CheckerQueryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user_id = data['user_telegram_id']
        query_name = data['query_name']
        query_url = data.get('query_url') or MonitorService.transform_query_text_to_olx_url(data['query_text'])

        if MonitorService.query_url_exists(user_id, query_url):
            if MonitorService.query_url_is_deleted(user_id, query_url):
                query = MonitorService.restore_query(user_id, query_url)
                return Response(CheckerQuerySerializer(query).data, status=status.HTTP_200_OK)
            return Response({'detail': 'Моніторинг з таким URL вже існує'}, status=status.HTTP_400_BAD_REQUEST)

        if not MonitorService.is_supported_ads_url(query_url):
            return Response({'detail': 'Підтримуються тільки URL з olx.ua або rieltor.ua'}, status=status.HTTP_400_BAD_REQUEST)

        query = MonitorService.create_query(user_id, query_name, query_url, is_active=False)
        task = initialize_query_ads_task.delay(query.pk)
        response_data = CheckerQuerySerializer(query).data
        response_data['task_id'] = task.id
        response_data['detail'] = 'Моніторинг створено. Первинна перевірка запущена у фоні.'
        return Response(response_data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        query = CheckerQuery.objects.get(pk=pk, is_deleted=False)
        query.is_active = True
        query.save(update_fields=['is_active'])
        return Response(CheckerQuerySerializer(query).data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        query = CheckerQuery.objects.get(pk=pk, is_deleted=False)
        query.is_active = False
        query.save(update_fields=['is_active'])
        return Response(CheckerQuerySerializer(query).data)

    @action(detail=True, methods=['post'])
    def soft_delete(self, request, pk=None):
        query = MonitorService.soft_delete_query(int(pk))
        return Response(CheckerQuerySerializer(query).data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        query = CheckerQuery.objects.get(pk=pk)
        query.is_deleted = False
        query.is_active = True
        query.save(update_fields=['is_deleted', 'is_active'])
        return Response(CheckerQuerySerializer(query).data)


class FoundAdViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FoundAdSerializer

    def get_queryset(self):
        qs = FoundAd.objects.select_related('query')
        query_id = self.request.query_params.get('query_id')
        is_active = self.request.query_params.get('is_active')
        source = self.request.query_params.get('source')
        if query_id:
            qs = qs.filter(query_id=query_id)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ('1', 'true', 'yes'))
        if source:
            qs = qs.filter(query__source=source)
        return qs


class InstaObservedUserViewSet(viewsets.ModelViewSet):
    serializer_class = InstaObservedUserSerializer
    lookup_field = 'username'

    def get_queryset(self):
        qs = InstaObservedUser.objects.filter(is_deleted=False)
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ('1', 'true', 'yes'))
        return qs

    def create(self, request, *args, **kwargs):
        username = request.data.get('username', '')
        user_telegram_id = request.data.get('user_telegram_id')
        if not username:
            return Response({'detail': 'username is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not user_telegram_id:
            return Response({'detail': 'user_telegram_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        observed_user, _, _ = InstaMonitorService.add_observed_user(username, int(user_telegram_id))
        subscription = InstaMonitorService.get_subscription(
            observed_user.subscriptions.get(user_id=user_telegram_id).pk,
            int(user_telegram_id),
        )
        return Response(InstaSubscriptionSerializer(subscription).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def activate(self, request, username=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response(InstaObservedUserSerializer(user).data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, username=None):
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response(InstaObservedUserSerializer(user).data)

    @action(detail=True, methods=['post'])
    def soft_delete(self, request, username=None):
        user = self.get_object()
        InstaMonitorService.soft_delete_observed_user(user.pk)
        user.refresh_from_db()
        return Response(InstaObservedUserSerializer(user).data)


class InstaContentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InstaContentSerializer

    def get_queryset(self):
        qs = InstaContent.objects.filter(observed_user__is_deleted=False).select_related('observed_user')
        username = self.request.query_params.get('username')
        if username:
            qs = qs.filter(observed_user__username=username)
        return qs


class JobLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = JobLogSerializer

    def get_queryset(self):
        qs = JobLog.objects.all()
        level = self.request.query_params.get('level')
        source = self.request.query_params.get('source')
        job_name = self.request.query_params.get('job_name')
        if level:
            qs = qs.filter(level=level)
        if source:
            qs = qs.filter(source=source)
        if job_name:
            qs = qs.filter(job_name=job_name)
        return qs


class TriggerCheckAdsView(APIView):
    def post(self, request):
        task = check_new_ads_task.delay()
        return Response({'task_id': task.id, 'status': 'queued'})


class TriggerCheckInstaView(APIView):
    def post(self, request):
        task = check_new_insta_content_task.delay()
        return Response({'task_id': task.id, 'status': 'queued'})
