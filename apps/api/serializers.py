from rest_framework import serializers

from apps.audit_logs.models import JobLog
from apps.insta_monitor.models import InstaContent, InstaObservedUser, InstaSubscription
from apps.monitors.models import CheckerQuery, FoundAd
from apps.telegram_users.models import TelegramUser


class TelegramUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramUser
        fields = '__all__'
        read_only_fields = ('created_at',)


class CheckerQuerySerializer(serializers.ModelSerializer):
    user_telegram_id = serializers.IntegerField(source='user_id', read_only=True)

    class Meta:
        model = CheckerQuery
        fields = (
            'id', 'user', 'user_telegram_id', 'query_name', 'query_url',
            'source', 'is_active', 'is_deleted', 'created_at',
        )
        read_only_fields = ('source', 'created_at')


class CheckerQueryCreateSerializer(serializers.Serializer):
    user_telegram_id = serializers.IntegerField()
    query_name = serializers.CharField(max_length=500)
    query_url = serializers.CharField(required=False, allow_blank=True)
    query_text = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get('query_url') and not attrs.get('query_text'):
            raise serializers.ValidationError('Потрібно передати query_url або query_text')
        return attrs


class FoundAdSerializer(serializers.ModelSerializer):
    query_name = serializers.CharField(source='query.query_name', read_only=True)

    class Meta:
        model = FoundAd
        fields = (
            'id', 'query', 'query_name', 'ad_url', 'ad_description',
            'ad_price', 'currency', 'is_active', 'created_at',
        )
        read_only_fields = fields


class InstaObservedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstaObservedUser
        fields = '__all__'
        read_only_fields = ('created_at',)


class InstaSubscriptionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='observed_user.username', read_only=True)
    telegram_user = serializers.SerializerMethodField()

    class Meta:
        model = InstaSubscription
        fields = (
            'id', 'observed_user', 'username', 'user', 'telegram_user',
            'is_active', 'is_deleted', 'created_at',
        )
        read_only_fields = fields

    def get_telegram_user(self, obj):
        return str(obj.user)


class InstaContentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='observed_user.username', read_only=True)

    class Meta:
        model = InstaContent
        fields = (
            'id', 'observed_user', 'username', 'content_type', 'media_type',
            'file_name', 'url', 'created_at',
        )
        read_only_fields = fields


class JobLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobLog
        fields = '__all__'
        read_only_fields = fields
