from django.urls import path, include
from rest_framework.routers import DefaultRouter

from transcription.apps import TranscriptionConfig
from transcription.views import FileViewSet

app_name = TranscriptionConfig.name

router = DefaultRouter()
router.register(r'file', FileViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
