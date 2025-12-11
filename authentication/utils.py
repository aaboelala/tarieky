import threading
from django.core.mail import send_mail

def send_async_email(subject, message, from_email, recipient_list):
    def _send():
        try:
            send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            print("EMAIL SENT SUCCESSFULLY")
        except Exception as e:
            print("EMAIL ERROR:", e)

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()
