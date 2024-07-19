import random
from celery import shared_task
from django.utils import timezone
from users.models import User
from config.mailgun import send_email


@shared_task
def send_confirmation_email(user_id):
    user = User.objects.get(id=user_id)
    confirmation_code = str(random.randint(100000, 999999)).zfill(6)

    user.confirmation_code = confirmation_code
    user.confirmation_code_created_at = timezone.now()
    user.save()

    subject = 'Добро пожаловать!'
    message = f'Ваш код для подтверждения почты:\n {confirmation_code}'
    to_email = user.email

    response = send_email(to_email, subject, message)
    if response.status_code != 200:
        print(f"Error sending confirmation email: {response.text}")


@shared_task
def send_password_reset_email(user_id):
    user = User.objects.get(id=user_id)
    print(f'Письмо для сброса пароля отправлено - {user.email}')

    subject = 'Cброс пароля'
    message = f'Перейдите по ссылке для сброса пароля: http://localhost:8000/users/recovery/{user.password}/'
    to_email = user.email

    response = send_email(to_email, subject, message)
    if response.status_code != 200:
        print(f"Error sending password reset email: {response.text}")
    