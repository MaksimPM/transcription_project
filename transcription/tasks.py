# import os
# import subprocess
# from tempfile import TemporaryDirectory
# from django.conf import settings
# from celery import shared_task
# from openai import OpenAI
# import magic
# from config.mailgun import send_email
# from .models import File
# from dotenv import load_dotenv
# import torch
# from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding
# from pyannote.audio import Audio
# from pyannote.core import Segment
# import wave
# import contextlib
# from sklearn.cluster import AgglomerativeClustering
# import numpy as np
#
# load_dotenv()
#
# client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
#
# # Initialize speaker embedding model
# embedding_model = PretrainedSpeakerEmbedding(
#     "speechbrain/spkrec-ecapa-voxceleb",
#     device=torch.device("cpu")
# )
#
# num_speakers = 2
#
#
# @shared_task
# def process_file(file_id, user_email):
#     media = File.objects.get(id=file_id)
#
#     mime_type = magic.from_file(media.file.path, mime=True)
#     if mime_type.startswith('video'):
#         media_type = 'video'
#     elif mime_type.startswith('audio'):
#         media_type = 'audio'
#     else:
#         print(f"Неизвестный тип медиафайла: {mime_type}")
#         return
#
#     if media_type == 'video':
#         audio_file = f'{media.file.path}.mp3'
#         try:
#             subprocess.run(['ffmpeg', '-y', '-i', media.file.path, audio_file], check=True)
#             print(f"Путь к аудиофайлу - {audio_file}")
#             audio_file_path = audio_file
#         except subprocess.CalledProcessError as e:
#             print(f"Ошибка конвертации видео в аудио: {e}")
#             audio_file_path = None
#     else:
#         audio_file_path = media.file.path
#
#     if client and audio_file_path:
#         with TemporaryDirectory() as tmpdirname:
#             chunked_audio_files = []
#             chunk_duration = 5 * 60
#             total_duration = get_audio_duration(audio_file_path)
#             start_time = 0
#             while start_time < total_duration:
#                 chunk_audio_path = os.path.join(tmpdirname, f"chunk_{start_time}.wav")
#                 try:
#                     subprocess.run(
#                         ['ffmpeg', '-i', audio_file_path, '-ss', str(start_time), '-t', str(chunk_duration),
#                          chunk_audio_path], check=True)
#                     chunked_audio_files.append(chunk_audio_path)
#                     start_time += chunk_duration
#                 except subprocess.CalledProcessError as e:
#                     print(f"Ошибка разделения аудио на части: {e}")
#
#             transcriptions = []
#             summaries = []
#
#             audio = Audio()
#
#             for chunk_audio_path in chunked_audio_files:
#                 response = client.audio.transcriptions.create(
#                     model="whisper-1",
#                     file=open(chunk_audio_path, 'rb'),
#                     language="ru"
#                 )
#
#                 transcription_text = response.text
#
#                 transcriptions.append(transcription_text)
#
#                 segments = [{"text": transcription_text, "start": 0, "end": get_audio_duration(chunk_audio_path)}]
#
#                 with contextlib.closing(wave.open(chunk_audio_path, 'r')) as f:
#                     frames = f.getnframes()
#                     rate = f.getframerate()
#                     duration = frames / float(rate)
#
#                 embeddings = np.zeros(shape=(len(segments), 192))
#                 for i, segment in enumerate(segments):
#                     start = segment["start"]
#                     end = min(duration, segment["end"])
#                     clip = Segment(start, end)
#                     waveform, sample_rate = audio.crop(chunk_audio_path, clip)
#                     embeddings[i] = embedding_model(waveform[None])
#
#                 embeddings = np.nan_to_num(embeddings)
#
#                 clustering = AgglomerativeClustering(num_speakers).fit(embeddings)
#                 labels = clustering.labels_
#
#                 for i, segment in enumerate(segments):
#                     segment["speaker"] = f'Спикер {labels[i] + 1}'
#
#                 for segment in segments:
#                     transcription = segment["text"]
#                     transcriptions.append(transcription)
#
#                     response_summary = client.chat.completions.create(
#                         model="gpt-4-turbo",
#                         messages=[
#                             {"role": "system", "content": "Необходимо определить, о чем идет речь в файле."},
#                             {"role": "user", "content": transcription}
#                         ]
#                     )
#                     summary = response_summary.choices[0].message.content
#                     summaries.append(summary)
#
#             media.transcription = "\n\n".join(transcriptions)
#             media.summary = "\n\n".join(summaries)
#
#     media.save()
#
#     original_file_name = os.path.basename(media.file.name)
#     result_dir = os.path.join(settings.MEDIA_ROOT, 'results', original_file_name)
#     os.makedirs(result_dir, exist_ok=True)
#     result_file_path = os.path.join(result_dir, f'{original_file_name}_results.txt')
#
#     with open(result_file_path, 'w', encoding='utf-8') as result_file:
#         result_file.write(f'Транскрипция: {media.transcription}\n\nСуммаризация: {media.summary}')
#
#     if media.file.path and os.path.exists(media.file.path):
#         os.remove(media.file.path)
#
#     email_subject = "Транскрипция файла"
#     email_text = "Вот результаты обработки вашего файла. Пожалуйста, ознакомьтесь с прикрепленным файлом."
#     send_email(user_email, email_subject, email_text, result_file_path)
#
#
# def get_audio_duration(audio_file_path):
#     try:
#         result = subprocess.run(
#             ['ffprobe', '-i', audio_file_path, '-show_entries', 'format=duration', '-v', 'quiet', '-of', 'csv=p=0'],
#             capture_output=True)
#         duration = float(result.stdout.decode('utf-8').strip())
#         return duration
#     except Exception as e:
#         print(f"Ошибка при получении длительности аудио: {e}")
#         return None
#
from celery import shared_task
from config.mailgun import send_email
from django.conf import settings
from transcription.models import File
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


@shared_task
def process_file(file_id, user_email):
    file_instance = File.objects.get(pk=file_id)
    path = file_instance.file.path
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
