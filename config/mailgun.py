import requests
from django.conf import settings
from dotenv import load_dotenv

load_dotenv()


def send_email_from_file(to_email, subject, text, attachment_path):
    return requests.post(
        f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages",
        auth=("api", settings.MAILGUN_API_KEY),
        files=[("attachment", (attachment_path, open(attachment_path, "rb").read()))],
        data={"from": f"WebTranscription <mailgun@{settings.MAILGUN_DOMAIN}>",
              "to": [to_email],
              "subject": subject,
              "text": text})


def send_email_from_user(to_email, subject, text):
    return requests.post(
        f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages",
        auth=("api", settings.MAILGUN_API_KEY),
        data={"from": f"WebTranscription <mailgun@{settings.MAILGUN_DOMAIN}>",
              "to": [to_email],
              "subject": subject,
              "text": text})
