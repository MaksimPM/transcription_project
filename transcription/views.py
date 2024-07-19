from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from transcription.models import File
from transcription.serializers import FileSerializer
from django.conf import settings
import whisper
import datetime
import subprocess
import torch
from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding
from pyannote.audio import Audio
from pyannote.core import Segment
import wave
import contextlib
from sklearn.cluster import AgglomerativeClustering
import numpy as np
import os
from config.mailgun import send_email


class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        return File.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        media = serializer.save(user=self.request.user)
        file_instance = File.objects.get(pk=media.id)
        path = file_instance.file.path
        user_email = self.request.user.email
        num_speakers = 2
        language = 'English'
        model_size = 'large'

        model_name = model_size
        if language == 'English' and model_size != 'large':
            model_name += '.en'

        if path[-3:] != 'wav':
            subprocess.call(['ffmpeg', '-i', path, 'audio.wav', '-y'])
            path = 'audio.wav'

        model = whisper.load_model(model_size)
        result = model.transcribe(path)
        segments = result["segments"]

        with contextlib.closing(wave.open(path, 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            duration = frames / float(rate)

        audio = Audio()
        embedding_model = PretrainedSpeakerEmbedding("speechbrain/spkrec-ecapa-voxceleb", device=torch.device("cuda"))

        def segment_embedding(segment):
            start = segment["start"]
            end = min(duration, segment["end"])
            clip = Segment(start, end)
            waveform, sample_rate = audio.crop(path, clip)
            return embedding_model(waveform[None])

        embeddings = np.zeros(shape=(len(segments), 192))
        for i, segment in enumerate(segments):
            embeddings[i] = segment_embedding(segment)

        embeddings = np.nan_to_num(embeddings)
        clustering = AgglomerativeClustering(num_speakers).fit(embeddings)
        labels = clustering.labels_

        for i in range(len(segments)):
            segments[i]["speaker"] = 'SPEAKER ' + str(labels[i] + 1)

        def time(secs):
            return datetime.timedelta(seconds=round(secs))

        transcript_path = os.path.join(settings.MEDIA_ROOT, 'transcripts', f"{file_instance.id}_transcript.txt")
        os.makedirs(os.path.dirname(transcript_path), exist_ok=True)
        with open(transcript_path, "w") as f:
            for (i, segment) in enumerate(segments):
                if i == 0 or segments[i - 1]["speaker"] != segment["speaker"]:
                    f.write("\n" + segment["speaker"] + ' ' + str(time(segment["start"])) + '\n')
                f.write(segment["text"][1:] + ' ')

        file_instance.transcription = transcript_path
        file_instance.save()

        email_subject = "Транскрипция файла"
        email_text = "Вот результаты обработки вашего файла. Пожалуйста, ознакомьтесь с прикрепленным файлом."
        send_email(user_email, email_subject, email_text, file_instance)
