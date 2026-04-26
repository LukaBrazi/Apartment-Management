# Imports
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

# Get the logger
logger = logging.getLogger(__name__)


def send_feedback_notification_email(feedback) -> None:
    """Send a notification email to admins when a new feedback is submitted.

    Arguments:
        feedback: Feedback -- The feedback that was submitted.

    Raises:
        Exception: If there was an error sending the email.
    """

    try:
        subject = f"[ApartmentOS] Новий відгук від {feedback.user.email}"
        context = {"feedback": feedback, "site_name": settings.SITE_NAME}

        html_email = render_to_string("feedback/feedback_notification_email.html", context)
        text_email = strip_tags(html_email)

        from_email = settings.DEFAULT_FROM_EMAIL

        # Відправляємо адміну — fallback на DEFAULT_FROM_EMAIL якщо ADMINS порожній
        admin_emails = [email for _, email in getattr(settings, "ADMINS", [])]
        to = admin_emails if admin_emails else [settings.DEFAULT_FROM_EMAIL]

        email = EmailMultiAlternatives(subject, text_email, from_email, to)
        email.attach_alternative(html_email, "text/html")
        email.send()

    except Exception as e:
        logger.error(f"Failed to send feedback notification email: {e}", exc_info=True)
