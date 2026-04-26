# Imports
from rest_framework.throttling import UserRateThrottle


class FeedbackRateThrottle(UserRateThrottle):
    """Feedback Rate Throttle

    Custom throttle for feedback submissions.
    Allows 3 requests per 10 minutes (600 seconds) per user.
    """

    scope = "feedback"

    def parse_rate(self, rate):
        # 3 requests per 10 minutes (600 seconds)
        return (3, 600)
