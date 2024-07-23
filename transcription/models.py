from django.conf import settings
from django.db import models

NULLABLE = {'blank': True, 'null': True}


class File(models.Model):
    file = models.FileField(upload_to='media/')
    transcription = models.TextField(**NULLABLE, verbose_name='транскрипция')
    summary = models.TextField(**NULLABLE)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='associated_files')
    language_code = models.CharField(max_length=10, default='ru', **NULLABLE, verbose_name='код языка')

    def __str__(self):
        return f"{self.file}"

    class Meta:
        verbose_name = 'файл'
        verbose_name_plural = 'файлы'
        ordering = ('pk',)
