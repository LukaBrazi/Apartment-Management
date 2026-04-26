import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_feedback_notification_task(self, feedback_pkid: int) -> None:
    """Send a notification email when a new feedback is submitted.

    Arguments:
        feedback_pkid (int): The primary key of the feedback.
    """

    from apps.feedback.emails import send_feedback_notification_email
    from apps.feedback.models import Feedback

    try:
        feedback = Feedback.objects.select_related("user").get(pkid=feedback_pkid)
        send_feedback_notification_email(feedback)
    except Feedback.DoesNotExist:
        logger.warning(f"Feedback pkid={feedback_pkid} not found, skipping email.")
    except Exception as exc:
        logger.error(f"Failed to send feedback notification: {exc}", exc_info=True)
        raise self.retry(exc=exc)
