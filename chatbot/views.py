"""The one endpoint the chat widget talks to."""

import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from chatbot.engine import answer, handle_greeting

# Where the "what were we just talking about" state lives. It is per-session,
# so two customers browsing at once never see each other's context.
SESSION_KEY = "chatbot_context"

MAX_MESSAGE_LENGTH = 400


@require_POST
def ask(request):
    """Answer one message.

    Accepts JSON (`{"message": "..."}`) or a normal form post, so the widget
    keeps working even if a browser falls back to a plain form submission.
    """
    message = ""
    if request.content_type and "application/json" in request.content_type:
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
            message = str(payload.get("message", ""))
        except (ValueError, UnicodeDecodeError):
            return JsonResponse(
                {"reply": "I could not read that message. Please try again.",
                 "cards": [], "links": [], "chips": [], "intent": "error"},
                status=400,
            )
    else:
        message = request.POST.get("message", "")

    message = message.strip()[:MAX_MESSAGE_LENGTH]

    context = request.session.get(SESSION_KEY) or {}
    if not isinstance(context, dict):
        context = {}

    result = answer(message, context)

    # Carry forward what the customer last referred to, so "is it in stock?"
    # still means something on the next message. New values win; old ones
    # survive until they are replaced.
    new_context = result.pop("context", {}) or {}
    if new_context:
        context.update({k: v for k, v in new_context.items() if v})
        request.session[SESSION_KEY] = context
        request.session.modified = True

    return JsonResponse(result)


def welcome(request):
    """The opening message, fetched when the customer first opens the widget."""
    result = handle_greeting()
    result.pop("context", None)
    return JsonResponse(result)
