from django.urls import path

from chatbot.views import ask, welcome

app_name = "chatbot"

urlpatterns = [
    path("ask/", ask, name="ask"),
    path("welcome/", welcome, name="welcome"),
]
