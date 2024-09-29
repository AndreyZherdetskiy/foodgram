from django.contrib.auth.models import AbstractUser
from django.db import models

from api.constants import CUSTOMUSER_MAX_LENGTH


class CustomUser(AbstractUser):
    first_name = models.CharField(
        max_length=CUSTOMUSER_MAX_LENGTH,
        verbose_name='Имя',
        blank=False
    )
    last_name = models.CharField(
        max_length=CUSTOMUSER_MAX_LENGTH,
        verbose_name='Фамилия',
        blank=False
    )
    username = models.CharField(
        max_length=CUSTOMUSER_MAX_LENGTH,
        unique=True,
        blank=False
    )
    email = models.EmailField(
        unique=True,
        verbose_name='Электронная почта',
        blank=False
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        default='avatar-icon.png',
        verbose_name='Аватар',
        blank=True
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата создания',
        auto_now_add=True
    )
    update_date = models.DateTimeField(
        verbose_name='Дата обновления',
        auto_now=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = (
        'username',
        'first_name',
        'last_name',
        'password'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f'Пользователь: {self.username}'


class Subscription(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name='Автор'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_subscription'
            )
        ]
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f'{self.user.username} подписан на {self.author.username}'
