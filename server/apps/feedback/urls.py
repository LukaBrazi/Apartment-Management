from django.urls import path

from .views import FeedbackCreateAPIView

app_name = "feedback"

urlpatterns = [
    path("create/", FeedbackCreateAPIView.as_view(), name="feedback-create"),
]
