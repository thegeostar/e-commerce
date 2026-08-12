"""Text matching helpers for the shop assistant.

Standard library only — no machine-learning model, no API key, nothing to
host. The assistant understands a question by scoring the words the customer
typed against two things: the keyword sets of the intents it knows, and the
names already stored in the database (products, categories, vendors, posts).

Because the names come from the database, the assistant automatically knows
about any product added later without a single line of code changing.
"""

import re
import unicodedata
from difflib import SequenceMatcher

# Words that carry no meaning for matching. Dropping them stops "the price of
# the sushi" from scoring against every product whose title contains "the".
STOPWORDS = {
    "a", "an", "and", "any", "are", "as", "at", "be", "but", "by", "can",
    "could", "did", "do", "does", "for", "from", "get", "give", "has", "have",
    "how", "i", "if", "in", "is", "it", "its", "me", "much", "my", "of", "on",
    "or", "please", "pls", "so", "some", "tell", "than", "that", "the", "their",
    "them", "then", "there", "these", "they", "this", "to", "up", "want", "was",
    "we", "were", "what", "whats", "when", "where", "which", "who", "will",
    "with", "would", "you", "your", "u", "im", "am", "hi", "hey",
}

_WORD_RE = re.compile(r"[a-z0-9]+")

# Irregular plurals worth spelling out; everything else goes through the
# suffix rules in singular().
_IRREGULAR = {
    "children": "child",
    "men": "man",
    "women": "woman",
    "people": "person",
    "fish": "fish",
    "clothes": "cloth",
    "cloths": "cloth",
    "noddles": "noddle",
}


def normalize(text):
    """Lowercase, strip accents and punctuation, collapse whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def singular(word):
    """A rough singulariser so "shoes" matches a product called "Shoe".

    Deliberately crude — it only has to make two spellings of the same word
    collide, and a wrong guess just means a slightly weaker match.
    """
    if word in _IRREGULAR:
        return _IRREGULAR[word]
    if len(word) > 3:
        if word.endswith("ies"):
            return word[:-3] + "y"
        if word.endswith(("ches", "shes", "sses", "xes", "zes")):
            return word[:-2]
        if word.endswith("s") and not word.endswith(("ss", "us", "is")):
            return word[:-1]
    return word


def tokenize(text, keep_stopwords=False):
    """Split text into normalised, singularised tokens."""
    words = _WORD_RE.findall(normalize(text))
    tokens = []
    for word in words:
        if not keep_stopwords and word in STOPWORDS:
            continue
        tokens.append(singular(word))
    return tokens


def token_set(text, keep_stopwords=False):
    return set(tokenize(text, keep_stopwords=keep_stopwords))


def ratio(a, b):
    """Character-level similarity, used to forgive typos."""
    return SequenceMatcher(None, a, b).ratio()


def build_idf(documents):
    """Inverse document frequency over a list of names.

    A token shared by many product titles ("chicken" across three of them)
    should count for less than a rare one ("jollof"). Without this, asking
    for "jollof rice" ranks every rice dish equally.
    """
    import math

    total = max(len(documents), 1)
    counts = {}
    for doc in documents:
        for tok in set(tokenize(doc)):
            counts[tok] = counts.get(tok, 0) + 1
    return {tok: math.log(1 + total / n) for tok, n in counts.items()}


def phrase_score(name, query_tokens, query_norm, idf=None):
    """How strongly `name` is referred to by the customer's message.

    Returns 0..1+. Every token of the name has to be accounted for in the
    query, weighted by how distinctive that token is, so "chicken" partially
    matches "Chicken Pizza" while "chicken pizza" matches it fully.
    """
    name_tokens = tokenize(name)
    if not name_tokens:
        return 0.0

    matched_weight = 0.0
    total_weight = 0.0
    for tok in name_tokens:
        weight = idf.get(tok, 1.0) if idf else 1.0
        total_weight += weight
        if tok in query_tokens:
            matched_weight += weight
        else:
            # Forgive a misspelling ("sushii", "chiken", "pizaa"). Credit drops
            # as the spelling drifts, so a bad guess weakens the match instead
            # of pulling in an unrelated product.
            near = max((ratio(tok, q) for q in query_tokens), default=0.0)
            if near >= 0.85:
                matched_weight += weight * 0.85
            elif near >= 0.78:
                matched_weight += weight * 0.65
            elif near >= 0.72 and len(tok) > 4:
                matched_weight += weight * 0.45

    if not total_weight:
        return 0.0

    score = matched_weight / total_weight

    # The whole name appearing verbatim is the strongest signal there is.
    # Word boundaries matter here: without them the category "Food" scores a
    # perfect match on the vendor name "XFood".
    name_norm = normalize(name)
    if name_norm and re.search(r"\b{}\b".format(re.escape(name_norm)), query_norm):
        score = max(score, 1.0) + 0.25

    return score


def rank(candidates, query, key=None, idf=None, threshold=0.55, limit=5):
    """Score candidates against the query, best first.

    `key` pulls the searchable name out of each candidate; the default treats
    the candidate itself as the name.
    """
    query_tokens = token_set(query)
    query_norm = normalize(query)
    if not query_tokens:
        return []

    getter = key or (lambda c: c)
    scored = []
    for candidate in candidates:
        score = phrase_score(getter(candidate), query_tokens, query_norm, idf)
        if score >= threshold:
            scored.append((score, candidate))

    # Sort on score only — candidates are model instances and are not orderable.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [(score, candidate) for score, candidate in scored[:limit]]
