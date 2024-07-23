from rest_framework import viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from transcription.models import File
from transcription.serializers import FileSerializer
from transcription.tasks import process_file


class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        return File.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        media = serializer.save(user=self.request.user)
        language_code = self.request.data.get('language_code', 'ru')
        process_file.delay(media.id, self.request.user.email, language_code)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {"success": "Ожидайте, результат будет отправлен Вам на почту"},
            status=status.HTTP_201_CREATED,
            headers=headers
        )
