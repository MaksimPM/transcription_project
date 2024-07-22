from rest_framework import serializers

from .models import File


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = '__all__'
        read_only_fields = ('user', 'transcription', 'summary')

    def validate_file(self, value):
        filename = value.name.lower()
        allowed_extensions = ['.mp4', '.mp3', '.wav', '.mov']
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                "Неподдерживаемый формат файла. Пожалуйста, загрузите файл в формате MP4, MOV, MP3 или WAV."
            )
        return value

    def create(self, validated_data):
        request = self.context.get('request', None)
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        return super().create(validated_data)

