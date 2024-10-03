import re

from django import forms
from django.core.exceptions import ValidationError

from api.constants import USERNAME_REGEX
from users.models import CustomUser, Subscription


class CustomUserForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('username',)

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not re.match(USERNAME_REGEX, username):
            raise ValidationError(
                'Имя пользователя может содержать только буквы, '
                'а цифры, а также символы @ и -. '
            )
        return username


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ('user', 'author')

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        author = cleaned_data.get('author')

        if user and author and user == author:
            raise ValidationError('Нельзя подписаться на себя.')

        if user and author:
            if Subscription.objects.filter(user=user, author=author).exists():
                raise ValidationError(
                    'Вы уже подписаны на этого пользователя.'
                )

        return cleaned_data
