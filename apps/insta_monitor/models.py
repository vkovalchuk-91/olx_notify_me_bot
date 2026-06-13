from django.db import models


class ContentType(models.TextChoices):
    STORY = 'story', 'Story'
    POST = 'post', 'Post'


class MediaType(models.TextChoices):
    PHOTO = 'photo', 'Photo'
    VIDEO = 'video', 'Video'


class InstaObservedUser(models.Model):
    username = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'insta_observed_user'
        ordering = ['username']

    def __str__(self):
        return self.username


class InstaSubscription(models.Model):
    observed_user = models.ForeignKey(
        InstaObservedUser,
        on_delete=models.CASCADE,
        related_name='subscriptions',
    )
    user = models.ForeignKey(
        'telegram_users.TelegramUser',
        on_delete=models.CASCADE,
        related_name='insta_subscriptions',
    )
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'insta_subscription'
        ordering = ['observed_user__username']
        constraints = [
            models.UniqueConstraint(
                fields=['observed_user', 'user'],
                name='unique_insta_subscription_per_user',
            ),
        ]

    def __str__(self):
        return f'{self.user} -> @{self.observed_user.username}'


class InstaContent(models.Model):
    observed_user = models.ForeignKey(
        InstaObservedUser,
        on_delete=models.CASCADE,
        related_name='content_items',
    )
    content_type = models.CharField(max_length=20, choices=ContentType.choices)
    media_type = models.CharField(max_length=20, choices=MediaType.choices)
    file_name = models.CharField(max_length=500)
    url = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'insta_content'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['observed_user', 'content_type', 'media_type', 'file_name'],
                name='unique_insta_content_item',
            ),
        ]

    def __str__(self):
        return f'{self.observed_user.username} - {self.file_name}'
