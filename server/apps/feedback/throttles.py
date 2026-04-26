# Imports
from rest_framework.throttling import UserRateThrottle


class FeedbackRateThrottle(UserRateThrottle):
    """Feedback Rate Throttle

    Custom throttle for feedback submissions.
    Allows 3 requests per 10 minutes (600 seconds) per user.

    Note: `rate` is set as a class attribute to bypass the settings lookup
    in `get_rate()`. Without it, DRF raises ImproperlyConfigured because
    "feedback" scope is not in DEFAULT_THROTTLE_RATES. `parse_rate()` then
    enforces the actual 600-second window regardless of the `rate` string.
    """

    scope = "feedback"
    rate = "3/hour"  # bypasses settings lookup; actual window set in parse_rate

    def parse_rate(self, rate):
        # 3 requests per 10 minutes (600 seconds)
        return (3, 600)
