from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """Current querystring with some keys swapped out.

    Lets the "Sort by" links keep whatever else is in the URL — the search
    term, the tag — instead of throwing it away:

        <a href="?{% query_replace sort='price' %}">Price: Low to High</a>
    """
    query = context["request"].GET.copy()

    for key, value in kwargs.items():
        if value in (None, ""):
            query.pop(key, None)
        else:
            query[key] = value

    return query.urlencode()
