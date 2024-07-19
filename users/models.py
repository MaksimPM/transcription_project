from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta

from transcription.models import File

NULLABLE = {'blank': True, 'null': True}


class User(AbstractUser):
    username = None
    name = models.CharField(max_length=100, verbose_name='имя')
    email = models.EmailField(unique=True, verbose_name='email')
    password = models.CharField(max_length=100, **NULLABLE, verbose_name='пароль')
    email_validated = models.BooleanField(default=False, verbose_name='статус верификации email')
    confirmation_code = models.CharField(max_length=6, **NULLABLE, verbose_name='код подтверждения')
    confirmation_code_created_at = models.DateTimeField(**NULLABLE, verbose_name='время создания кода')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='время регистрации')
    JWTToken = models.CharField(max_length=350, **NULLABLE, verbose_name='JWT Token')
    files = models.ManyToManyField(File, related_name='user_files', verbose_name='файлы')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def is_confirmation_code_valid(self):
        return (
            self.confirmation_code is not None and
            timezone.now() < self.confirmation_code_created_at + timedelta(minutes=10)
        )

    def __str__(self):
        return f"{self.email}"

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'пользователи'
        ordering = ('pk',)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
