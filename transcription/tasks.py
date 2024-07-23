import subprocess
from celery import shared_task
import assemblyai as aai
from django.conf import settings
from transcription.models import File
from config.mailgun import send_email_from_file
import os
import magic
import openai

aai.settings.api_key = settings.ASSEMBLYAI_API_KEY
openai.api_key = settings.OPENAI_API_KEY


@shared_task
def process_file(file_id, user_email, language_code):
    transcriber = aai.Transcriber()

    file_instance = File.objects.get(id=file_id)

    mime_type = magic.from_file(file_instance.file.path, mime=True)
    if mime_type.startswith('video'):
        media_type = 'video'
    elif mime_type.startswith('audio'):
        media_type = 'audio'
    else:
        print(f"Unknown type of media: {mime_type}")
        return

    if media_type == 'video':
        audio_file = f'{file_instance.file.path}.mp3'
        try:
            subprocess.run(['ffmpeg', '-y', '-i', file_instance.file.path, audio_file], check=True)
            audio_file_path = audio_file
        except subprocess.CalledProcessError as e:
            print(f"Error converting video to audio: {e}")
            audio_file_path = None
    else:
        audio_file_path = file_instance.file.path

    if audio_file_path is None:
        return

    config = aai.TranscriptionConfig(
        speaker_labels=True,
        language_code=language_code
    )

    try:
        audio_url = transcriber.upload_file(audio_file_path)
        transcript = transcriber.transcribe(audio_url, config)

        transcription_text = transcript.text
        summary_text = summarize_text(transcription_text)

        file_instance.transcription = transcription_text
        file_instance.summary = summary_text
        file_instance.save()

        original_file_name = os.path.basename(file_instance.file.name)
        result_dir = os.path.join(settings.MEDIA_ROOT, 'results', original_file_name)
        os.makedirs(result_dir, exist_ok=True)
        result_file_path = os.path.join(result_dir, f'{original_file_name}_results.txt')

        with open(result_file_path, "w", encoding="utf-8") as f:
            f.write(f"Транскрипция:\n{transcription_text}\n\nСводка:\n{summary_text}\n\nДневник спикеров:\n")
            for utterance in transcript.utterances:
                f.write(f"SPEAKER - {utterance.speaker}: {utterance.text}\n")

        send_email_from_file(
            to_email=user_email,
            subject='Ваш файл с транскрибацией готов!',
            text='Расшифровка и краткое содержание приведены в полном объеме. Смотрите прикрепленный файл.',
            attachment_path=result_file_path
        )
        print(f'Файл с транскрбацией готов и отправлен на почту - {user_email}')

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        if os.path.exists(audio_file_path):
            os.remove(audio_file_path)
        if os.path.exists(file_instance.file.path):
            os.remove(file_instance.file.path)


def summarize_text(transcription_text):
    response = openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes text in Russian."},
            {"role": "user", "content": f"Summarize the following text in Russian:\n\n{transcription_text}"}
        ],
        max_tokens=150,
        temperature=0.7
    )
    summary = response.choices[0].message.content
    return summary
