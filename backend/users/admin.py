from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.forms import CustomUserForm, SubscriptionForm
from users.models import CustomUser, Subscription


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    form = CustomUserForm
    list_display = ('username', 'email', 'first_name', 'last_name')
    search_fields = ('username', 'email')
    ordering = ('username',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    form = SubscriptionForm
    list_display = ('user', 'author')
    search_fields = ('user__username', 'author__username')
    ordering = ('user',)
