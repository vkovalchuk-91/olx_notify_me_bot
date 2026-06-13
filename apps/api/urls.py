from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CheckerQueryViewSet,
    FoundAdViewSet,
    InstaContentViewSet,
    InstaObservedUserViewSet,
    JobLogViewSet,
    TelegramUserViewSet,
    TriggerCheckAdsView,
    TriggerCheckInstaView,
)

router = DefaultRouter()
router.register('users', TelegramUserViewSet, basename='telegram-user')
router.register('checker-queries', CheckerQueryViewSet, basename='checker-query')
router.register('found-ads', FoundAdViewSet, basename='found-ad')
router.register('insta/observed-users', InstaObservedUserViewSet, basename='insta-observed-user')
router.register('insta/content', InstaContentViewSet, basename='insta-content')
router.register('logs', JobLogViewSet, basename='job-log')

urlpatterns = [
    path('', include(router.urls)),
    path('jobs/check-ads/', TriggerCheckAdsView.as_view(), name='trigger-check-ads'),
    path('jobs/check-insta/', TriggerCheckInstaView.as_view(), name='trigger-check-insta'),
]
