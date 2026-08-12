"""The shop assistant's brain.

There is no language model here and nothing to host. A question is answered
in three steps:

1. **Intent scoring** — the words the customer typed are matched against the
   keyword sets and phrase patterns of the intents below ("price", "delivery",
   "deals", ...). Each match adds to that intent's score.
2. **Entity lookup** — the same words are matched against names that live in
   the database: product titles, category titles, vendor names, tags and blog
   post titles. This is what lets the assistant quote a real price rather
   than a canned sentence, and it keeps working when new products are added.
3. **Routing** — the winning intent and the entities found are combined into
   an answer, usually with product cards and a link to the real page.

Anything the assistant cannot place falls through to the policy knowledge
base in knowledge.py, and finally to an honest "I did not understand that"
with suggestions, rather than a made-up answer.
"""

import re
from decimal import Decimal

from django.db.models import Max, Min, Q
from django.urls import NoReverseMatch, reverse

from blog.models import Post
from core.models import Category, Coupon, Product, Vendor

from chatbot import knowledge
from chatbot.matching import build_idf, normalize, rank, singular, tokenize

# How many results to show before saying "and N more".
MAX_CARDS = 4

# Words that mean "the thing we were just talking about".
PRONOUNS = {"it", "its", "that", "this", "them", "they", "one", "same"}


# --------------------------------------------------------------------------
# Intents
# --------------------------------------------------------------------------

class Intent:
    """One thing a customer might be trying to do.

    `patterns` are phrases that are strong evidence on their own ("how much");
    `keywords` are single words that each nudge the score up. Keywords are
    singularised on both sides so "coupons" and "coupon" behave identically.
    """

    PATTERN_WEIGHT = 3.0
    KEYWORD_WEIGHT = 1.0

    def __init__(self, name, keywords="", patterns=()):
        self.name = name
        self.keywords = {singular(w) for w in normalize(keywords).split()}
        self.patterns = [re.compile(p) for p in patterns]

    def score(self, norm_text, word_set):
        score = sum(self.PATTERN_WEIGHT for p in self.patterns if p.search(norm_text))
        score += sum(self.KEYWORD_WEIGHT for w in self.keywords if w in word_set)
        return score


INTENTS = [
    Intent(
        "greeting",
        "hi hello hey yo hallo sup morning afternoon evening greetings",
        [r"^(hi|hello|hey|yo|hola)\b", r"\bgood (morning|afternoon|evening)\b"],
    ),
    Intent(
        "thanks",
        "thanks thank thx appreciate cheers awesome perfect",
        [r"\bthank(s| you)?\b", r"\bnice one\b"],
    ),
    Intent(
        "farewell",
        "bye goodbye later cya",
        [r"\b(bye|goodbye|see you|good night)\b"],
    ),
    Intent(
        "capabilities",
        "help capable capability ask commands menu options guide",
        [r"\bwhat can (you|u) (do|help)\b", r"\bhow (do|does) (you|this) work\b",
         r"\bwho are you\b", r"\bare you (a )?(bot|robot|human|ai)\b",
         r"\bwhat (can|should) i ask\b", r"\bhelp me\b"],
    ),
    Intent(
        "price",
        "price cost costs pricing dollar dollars usd expensive cheap worth",
        [r"\bhow much\b", r"\bprice of\b", r"\bwhat.{0,12}price\b", r"\bhow expensive\b"],
    ),
    Intent(
        "stock",
        "stock available availability left remaining supply sold",
        [r"\bin stock\b", r"\bsold out\b", r"\bdo you still have\b",
         r"\bis it available\b", r"\bhow many.{0,15}left\b"],
    ),
    Intent(
        "product_search",
        "product products item items sell sells selling stock catalogue "
        "catalog find search show list looking want need buy anything",
        [r"\bdo you (have|sell|stock)\b", r"\blooking for\b", r"\bshow me\b",
         r"\bi want\b", r"\bi need\b", r"\bfind me\b", r"\bsearch for\b",
         r"\bwhat.{0,15}(do you sell|products)\b"],
    ),
    Intent(
        "budget",
        "under below cheaper less budget max maximum affordable",
        [r"\b(under|below|less than|cheaper than|up to|max|maximum|no more than)"
         r"\s*\$?\s*\d+", r"\bbetween\s*\$?\s*\d+\s*(and|-|to)\s*\$?\s*\d+",
         r"\b(over|above|more than|at least)\s*\$?\s*\d+"],
    ),
    Intent(
        "superlative",
        "cheapest lowest priciest dearest costliest",
        [r"\b(cheapest|lowest price|least expensive|most affordable)\b",
         r"\b(most expensive|highest price|priciest|dearest)\b",
         r"\b(cheap|affordable|budget|low price)\b"],
    ),
    Intent(
        "deals",
        "deal deals discount discounts sale sales offer offers promotion "
        "promo bargain reduced clearance off",
        [r"\bon (sale|offer)\b", r"\bany (deal|discount|offer|sale)",
         r"\bwhat.{0,15}(sale|discount|deal)\b", r"\bbest (deal|offer|price)\b"],
    ),
    Intent(
        "coupon",
        "coupon coupons voucher vouchers promocode",
        [r"\b(coupon|promo|discount|voucher)\s*code\b", r"\bany coupon",
         r"\bcode\b.{0,15}\b(discount|off)\b"],
    ),
    Intent(
        "category",
        "category categories kind kinds type types section sections "
        "department departments range",
        [r"\bwhat (kind|type|sort)s? of\b", r"\bwhat categor", r"\blist.{0,10}categor",
         r"\bwhat do you (sell|have|offer)\b"],
    ),
    Intent(
        "vendor",
        "vendor vendors seller sellers shop shops store stores supplier "
        "suppliers merchant brand farm",
        [r"\bwho (sells|makes|supplies)\b",
         r"\b(who|what|which)\s+(are|is)\s+(your|the|our)?\s*"
         r"(vendor|seller|shop|store|supplier|merchant)s?\b",
         r"\bwhich (vendor|seller|shop|store)\b",
         # "shop"/"store" are left out here on purpose: "tell me about the
         # shop" is a question about us, not about our vendors.
         r"\b(list|show|tell me about)\b.{0,15}\b(vendor|seller|supplier)s?\b",
         r"\bvendors\b"],
    ),
    Intent(
        "blog",
        "blog blogs article articles post posts recipe recipes news tip tips "
        "story stories read reading",
        [r"\b(blog|article|recipe)s?\b", r"\b(tips?|advice)\b",
         r"\bhow (do|to) (i |you )?(cook|make|roll|store|pick|choose|prepare)\b",
         r"\bwhat.{0,15}to read\b"],
    ),
    Intent(
        "recommend",
        "recommend recommendation suggest suggestion popular best top "
        "favourite favorite trending featured good",
        [r"\bwhat should i (buy|get|order|try)\b", r"\brecommend\b",
         r"\bwhat.{0,10}(popular|best|good)\b", r"\bsurprise me\b"],
    ),
]

# Policy questions come from the knowledge base. They are scored the same way,
# but their vocabulary is defined next to the answers it belongs to.
FAQ_INTENTS = [
    Intent(entry["id"], entry["keywords"], entry.get("patterns", ()))
    for entry in knowledge.ENTRIES
]

FAQ_BY_ID = {entry["id"]: entry for entry in knowledge.ENTRIES}

# The chips offered when the assistant opens, and when it is lost.
DEFAULT_CHIPS = [
    "What is on sale?",
    "What categories do you have?",
    "How long is delivery?",
    "How do I pay?",
]


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def published_products():
    """Only products a customer can actually buy, as the site itself does."""
    return Product.objects.filter(product_status="published").select_related(
        "category", "vendor")


def money(value):
    try:
        return "${:,.2f}".format(Decimal(value))
    except Exception:
        return "${}".format(value)


def safe_url(name, *args):
    """reverse() that returns "" instead of raising.

    A missing URL should degrade the answer, never break the chat window.
    """
    try:
        return reverse(name, args=args) if args else reverse(name)
    except NoReverseMatch:
        return ""


def image_url(field):
    try:
        return field.url if field else ""
    except (ValueError, AttributeError):
        return ""


def discount_percent(product):
    if not product.old_price or not product.price:
        return 0
    if product.price >= product.old_price:
        return 0
    return int(round((1 - (product.price / product.old_price)) * 100))


def product_card(product):
    off = discount_percent(product)
    meta = []
    if product.category:
        meta.append(product.category.title)
    if product.vendor:
        meta.append(product.vendor.title)

    return {
        "type": "product",
        "title": product.title,
        "url": safe_url("core:product-detail", product.pid),
        "image": image_url(product.image),
        "price": money(product.price),
        "old_price": money(product.old_price) if off else "",
        "badge": "-{}% off".format(off) if off else ("" if product.in_stock else "Sold out"),
        "meta": " · ".join(meta),
    }


def vendor_card(vendor):
    return {
        "type": "vendor",
        "title": vendor.title,
        "url": safe_url("core:vendor-detail", vendor.vid),
        "image": image_url(vendor.image),
        "price": "",
        "old_price": "",
        "badge": "",
        "meta": "{} product{}".format(
            vendor.product.count(), "" if vendor.product.count() == 1 else "s"),
    }


def category_card(category):
    return {
        "type": "category",
        "title": category.title,
        "url": safe_url("core:category-product-list", category.cid),
        "image": image_url(category.image),
        "price": "",
        "old_price": "",
        "badge": "",
        "meta": "{} product{}".format(
            category.product_count(), "" if category.product_count() == 1 else "s"),
    }


def post_card(post):
    return {
        "type": "post",
        "title": post.title,
        "url": safe_url("blog:post-detail", post.slug),
        "image": image_url(post.image),
        "price": "",
        "old_price": "",
        "badge": "",
        "meta": post.category.title if post.category else "Blog",
    }


def reply(text, cards=None, links=None, chips=None, intent="", context=None):
    """The single shape every answer takes, ready to be sent as JSON."""
    return {
        "reply": text,
        "cards": cards or [],
        "links": [{"label": label, "url": url} for label, url in (links or []) if url],
        "chips": chips or [],
        "intent": intent,
        "context": context or {},
    }


def faq_reply(entry_id, intent=None, context=None):
    """Answer straight from the policy knowledge base."""
    entry = FAQ_BY_ID[entry_id]
    links = [(label, safe_url(name)) for label, name in entry.get("links", [])]
    return reply(
        knowledge.render(entry["answer"]),
        links=links,
        chips=entry.get("chips", []),
        intent=intent or entry_id,
        context=context,
    )


# --------------------------------------------------------------------------
# Entity lookup — matching what was typed against what is in the database
# --------------------------------------------------------------------------

def find_entities(text):
    """Match the message against every name the shop knows about."""
    products = list(published_products())
    categories = list(Category.objects.all())
    vendors = list(Vendor.objects.all())
    posts = list(Post.objects.filter(status="published"))

    return {
        "products": rank(products, text, key=lambda p: p.title,
                         idf=build_idf([p.title for p in products]),
                         threshold=0.62, limit=8),
        "categories": rank(categories, text, key=lambda c: c.title,
                           threshold=0.75, limit=3),
        # Vendor names here are near-anagrams of each other and of the word
        # "food" (XFood, NestFOOD, DestFood), so a fuzzy match is far too
        # eager. Require a near-exact hit.
        "vendors": rank(vendors, text, key=lambda v: v.title,
                        threshold=0.92, limit=3),
        "posts": rank(posts, text, key=lambda p: p.title,
                      idf=build_idf([p.title for p in posts]),
                      threshold=0.5, limit=4),
    }


def products_by_keyword(text):
    """Second chance for product search, the way the site's own search works.

    Full-title matching needs most of the title to be mentioned, so "chicken"
    alone never reaches it. Here each word is looked up inside product titles
    and tags instead, and results are ordered by how many words they matched.
    """
    words = [w for w in set(tokenize(text)) if len(w) >= 3]
    if not words:
        return []

    hits = {}
    for word in words:
        matched = published_products().filter(
            Q(title__icontains=word) | Q(tags__name__iexact=word)).distinct()
        for product in matched:
            entry = hits.setdefault(product.pid, [0, product])
            entry[0] += 1

    ordered = sorted(hits.values(), key=lambda pair: pair[0], reverse=True)
    return [product for _, product in ordered]


def posts_by_keyword(text):
    """The same idea for blog posts, which have long titles."""
    words = [w for w in set(tokenize(text)) if len(w) >= 4]
    if not words:
        return []

    hits = {}
    for word in words:
        matched = Post.objects.filter(status="published").filter(
            Q(title__icontains=word) | Q(description__icontains=word))
        for post in matched:
            entry = hits.setdefault(post.pk, [0, post])
            entry[0] += 1

    ordered = sorted(hits.values(), key=lambda pair: pair[0], reverse=True)
    return [post for _, post in ordered]


def top(matches):
    """The best match, if the list is not empty."""
    return matches[0][1] if matches else None


def objects(matches, limit=MAX_CARDS):
    return [obj for _, obj in matches[:limit]]


def stronger_of(entities):
    """Return (category, vendor) with only the better-scoring one filled in.

    A word like "food" is both a category and part of three vendor names, so
    picking the higher score stops the assistant answering about a vendor when
    the customer clearly meant a category.
    """
    cat = entities["categories"][0] if entities["categories"] else None
    ven = entities["vendors"][0] if entities["vendors"] else None

    if cat and (not ven or cat[0] >= ven[0]):
        return cat[1], None
    if ven:
        return None, ven[1]
    return None, None


def resolve_pronoun(text, context):
    """"Is it in stock?" — recover what "it" referred to."""
    words = set(tokenize(text, keep_stopwords=True))
    if not words & PRONOUNS:
        return None
    pid = context.get("product")
    if pid:
        return published_products().filter(pid=pid).first()
    return None


def price_limits(norm_text):
    """Pull a budget out of "under $20" / "between 10 and 30" / "over 50"."""
    between = re.search(
        r"between\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:and|-|to)\s*\$?\s*(\d+(?:\.\d+)?)",
        norm_text)
    if between:
        low, high = sorted([Decimal(between.group(1)), Decimal(between.group(2))])
        return low, high

    under = re.search(
        r"(?:under|below|less than|cheaper than|up to|max|maximum|no more than)"
        r"\s*\$?\s*(\d+(?:\.\d+)?)", norm_text)
    if under:
        return None, Decimal(under.group(1))

    over = re.search(
        r"(?:over|above|more than|at least|from)\s*\$?\s*(\d+(?:\.\d+)?)", norm_text)
    if over:
        return Decimal(over.group(1)), None

    return None, None


# --------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------

def handle_product_detail(product, ask):
    """Everything worth saying about one product, tuned to what was asked."""
    lines = []
    off = discount_percent(product)

    if ask == "stock":
        if product.in_stock:
            count = (product.stock_count or "").strip()
            if count.isdigit():
                lines.append("Yes — **{}** is in stock ({} available) at {}.".format(
                    product.title, count, money(product.price)))
            else:
                lines.append("Yes — **{}** is in stock at {}.".format(
                    product.title, money(product.price)))
        else:
            lines.append("**{}** is sold out at the moment. "
                         "Try a similar item below, or check back soon.".format(product.title))
    else:
        if off:
            lines.append("**{}** is {} — reduced from {}, so you save {}%.".format(
                product.title, money(product.price), money(product.old_price), off))
        else:
            lines.append("**{}** is {}.".format(product.title, money(product.price)))

        if not product.in_stock:
            lines.append("It is sold out at the moment.")

    details = []
    if product.vendor:
        details.append("sold by {}".format(product.vendor.title))
    if product.category:
        details.append("listed under {}".format(product.category.title))
    if details:
        lines.append("It is " + " and ".join(details) + ".")

    if product.life:
        lines.append("Shelf life: {}.".format(product.life))

    chips = ["Is it in stock?" if ask != "stock" else "Who sells it?",
             "What is on sale?", "How long is delivery?"]

    return reply(
        "\n".join(lines),
        cards=[product_card(product)],
        chips=chips,
        intent="product_detail",
        context={"product": product.pid,
                 "vendor": product.vendor.vid if product.vendor else "",
                 "category": product.category.cid if product.category else ""},
    )


def handle_product_list(products, heading, intent="product_search", chips=None):
    """A short list of products with cards, plus a link to see them all."""
    shown = products[:MAX_CARDS]
    text = heading
    if len(products) > len(shown):
        text += "\nHere are {} of {} — the rest are on the products page.".format(
            len(shown), len(products))

    context = {}
    if len(shown) == 1:
        context = {"product": shown[0].pid}

    return reply(
        text,
        cards=[product_card(p) for p in shown],
        links=[("See all products", safe_url("core:product-list"))],
        chips=chips or ["What is on sale?", "How long is delivery?"],
        intent=intent,
        context=context,
    )


def handle_search(text, entities):
    """"Do you have sushi?" — search by name, then by word, then by section.

    Both searches are merged: a customer asking for "sushi" should see the
    product called exactly that *and* anything else with sushi in the name,
    with the closest name match first.
    """
    matches = objects(entities["products"], limit=8)
    seen = {p.pid for p in matches}
    for product in products_by_keyword(text):
        if product.pid not in seen:
            matches.append(product)
            seen.add(product.pid)

    if matches:
        if len(matches) == 1:
            return handle_product_detail(matches[0], ask="search")
        return handle_product_list(
            matches, "I found {} products that match:".format(len(matches)))

    category, vendor = stronger_of(entities)
    if category:
        return handle_category(category)
    if vendor:
        return handle_vendor(vendor)

    return None


def handle_category(category):
    products = list(published_products().filter(category=category))
    if not products:
        # Say so plainly, then point at sections that do have stock.
        stocked = [c for c in Category.objects.all() if c.product_count()][:3]
        suggestion = ""
        if stocked:
            suggestion = " Right now we have products in {}.".format(
                ", ".join(c.title for c in stocked))
        return reply(
            "We have a **{}** section, but nothing is listed in it at the "
            "moment.{}".format(category.title, suggestion),
            links=[("Browse all categories", safe_url("core:category-list"))],
            chips=[c.title for c in stocked] or DEFAULT_CHIPS,
            intent="category",
        )

    cheapest = min(products, key=lambda p: p.price)
    text = "We have **{}** product{} in **{}**, starting at {}.".format(
        len(products), "" if len(products) == 1 else "s", category.title,
        money(cheapest.price))

    return reply(
        text,
        cards=[product_card(p) for p in products[:MAX_CARDS]],
        links=[("See all {}".format(category.title),
                safe_url("core:category-product-list", category.cid))],
        chips=["What is on sale?", "Who are your vendors?", "How long is delivery?"],
        intent="category",
        context={"category": category.cid},
    )


def handle_category_list():
    categories = list(Category.objects.all())
    if not categories:
        return reply("No categories are set up yet.", chips=DEFAULT_CHIPS,
                     intent="category")

    names = ", ".join(c.title for c in categories)
    return reply(
        "We sell across **{}** categories: {}.\nTell me which one interests you "
        "and I will show you what is in it.".format(len(categories), names),
        cards=[category_card(c) for c in categories[:MAX_CARDS]],
        links=[("All categories", safe_url("core:category-list"))],
        chips=[c.title for c in categories[:3]] + ["What is on sale?"],
        intent="category",
    )


def handle_vendor(vendor):
    products = list(published_products().filter(vendor=vendor))
    lines = ["**{}** is one of our verified vendors.".format(vendor.title)]
    if vendor.address:
        lines.append("Address: {}".format(vendor.address))
    if vendor.contact:
        lines.append("Contact: {}".format(vendor.contact))
    lines.append("They ship on time {}% of the time and accept returns "
                 "within {} days.".format(vendor.shipping_on_time, vendor.days_return))
    if products:
        lines.append("They currently list {} product{}.".format(
            len(products), "" if len(products) == 1 else "s"))

    return reply(
        "\n".join(lines),
        cards=[product_card(p) for p in products[:MAX_CARDS]],
        links=[("Visit {}".format(vendor.title),
                safe_url("core:vendor-detail", vendor.vid))],
        chips=["Who are your vendors?", "What is on sale?"],
        intent="vendor",
        context={"vendor": vendor.vid},
    )


def handle_vendor_list():
    vendors = list(Vendor.objects.all())
    if not vendors:
        return reply("No vendors are listed yet.", chips=DEFAULT_CHIPS, intent="vendor")

    names = ", ".join(v.title for v in vendors)
    return reply(
        "We work with **{}** vendors: {}.\nEvery one is verified before their first "
        "listing goes live. Ask me about any of them by name.".format(
            len(vendors), names),
        cards=[vendor_card(v) for v in vendors[:MAX_CARDS]],
        links=[("All vendors", safe_url("core:vendor-list"))],
        chips=[v.title for v in vendors[:3]] + ["What categories do you have?"],
        intent="vendor",
    )


def handle_deals():
    deals = [p for p in published_products() if p.old_price and p.price < p.old_price]
    deals.sort(key=discount_percent, reverse=True)

    if not deals:
        return reply(
            "Nothing is discounted right now. New offers go up most mornings — "
            "the homepage countdown shows how long each one lasts.",
            links=[("Browse products", safe_url("core:product-list"))],
            chips=DEFAULT_CHIPS,
            intent="deals",
        )

    best = deals[0]
    return reply(
        "There {} **{}** item{} on offer right now. The biggest saving is "
        "**{}** at {}% off.".format(
            "is" if len(deals) == 1 else "are", len(deals),
            "" if len(deals) == 1 else "s", best.title, discount_percent(best)),
        cards=[product_card(p) for p in deals[:MAX_CARDS]],
        links=[("See all products", safe_url("core:product-list"))],
        chips=["Do you have any coupons?", "How long is delivery?"],
        intent="deals",
    )


def handle_coupon():
    coupons = list(Coupon.objects.filter(active=True))
    if not coupons:
        return reply(
            "There are no active coupon codes at the moment. Discounts still show "
            "directly on the product pages, so it is worth checking the deals.",
            chips=["What is on sale?", "How do I pay?"],
            intent="coupon",
        )

    listed = "\n".join("• **{}** — {}% off your order".format(c.code, c.discount)
                       for c in coupons)
    return reply(
        "Yes — {} code{} active right now:\n{}\nEnter the code in your cart, "
        "before you go to checkout.".format(
            len(coupons), " is" if len(coupons) == 1 else "s are", listed),
        links=[("Your cart", safe_url("core:cart"))],
        chips=["What is on sale?", "How do I pay?"],
        intent="coupon",
    )


def handle_budget(norm_text, entities):
    low, high = price_limits(norm_text)
    products = published_products()

    # If they also named a category, keep the filter narrow.
    category = top(entities["categories"])
    if category:
        products = products.filter(category=category)

    if low is not None:
        products = products.filter(price__gte=low)
    if high is not None:
        products = products.filter(price__lte=high)
    products = list(products.order_by("price"))

    scope = " in {}".format(category.title) if category else ""
    if low is not None and high is not None:
        band = "between {} and {}".format(money(low), money(high))
    elif high is not None:
        band = "under {}".format(money(high))
    else:
        band = "over {}".format(money(low))

    if not products:
        return reply(
            "I could not find anything{} {}. "
            "Try widening the range and I will look again.".format(scope, band),
            links=[("Browse products", safe_url("core:product-list"))],
            chips=["What is the cheapest thing you sell?", "What is on sale?"],
            intent="budget",
        )

    return handle_product_list(
        products,
        "There {} **{}** product{}{} {}, cheapest first:".format(
            "is" if len(products) == 1 else "are", len(products),
            "" if len(products) == 1 else "s", scope, band),
        intent="budget",
        chips=["What is on sale?", "Do you have any coupons?"],
    )


def handle_superlative(norm_text, entities):
    """"What is your cheapest product?" — optionally inside a category."""
    wants_expensive = bool(re.search(
        r"\b(most expensive|highest price|priciest|dearest|costliest)\b", norm_text))

    products = published_products()
    scope = ""

    # "the cheapest food" names a category; "the cheapest from XFood" names a
    # vendor. Both can match at once, so the stronger match wins.
    category, vendor = stronger_of(entities)
    if category:
        products = products.filter(category=category)
        scope = " in {}".format(category.title)
    elif vendor:
        products = products.filter(vendor=vendor)
        scope = " from {}".format(vendor.title)

    products = list(products.order_by("-price" if wants_expensive else "price"))
    if not products:
        return reply("I could not find any products{} to compare.".format(scope),
                     chips=DEFAULT_CHIPS, intent="superlative")

    winner = products[0]
    label = "most expensive" if wants_expensive else "cheapest"
    return handle_product_list(
        products,
        "The {} thing we sell{} is **{}** at {}.".format(
            label, scope, winner.title, money(winner.price)),
        intent="superlative",
        chips=["What is on sale?", "What categories do you have?"],
    )


def handle_recommend():
    """Featured products first, then whatever is newest."""
    featured = list(published_products().filter(featured=True)[:MAX_CARDS])
    products = featured or list(published_products().order_by("-date")[:MAX_CARDS])

    if not products:
        return reply("There is nothing listed yet for me to recommend.",
                     chips=DEFAULT_CHIPS, intent="recommend")

    heading = ("These are the ones we are featuring right now:" if featured
               else "Here is what has arrived most recently:")
    return handle_product_list(products, heading, intent="recommend",
                               chips=["What is on sale?", "What is the cheapest thing you sell?"])


def handle_blog(text, entities):
    # Blog titles are long sentences, so full-title matching rarely fires.
    # Fall back to looking the words up inside titles and teasers.
    matches = objects(entities["posts"]) or posts_by_keyword(text)[:MAX_CARDS]
    if matches:
        if len(matches) == 1:
            post = matches[0]
            teaser = (post.description or "").strip()
            return reply(
                "**{}**\n{}".format(post.title, teaser),
                cards=[post_card(post)],
                links=[("Read the post", safe_url("blog:post-detail", post.slug))],
                chips=["What else is on the blog?", "What is on sale?"],
                intent="blog",
            )
        return reply(
            "I found {} posts about that:".format(len(matches)),
            cards=[post_card(p) for p in matches],
            links=[("All posts", safe_url("blog:post-list"))],
            chips=["What is on sale?", "How long is delivery?"],
            intent="blog",
        )

    posts = list(Post.objects.filter(status="published")[:MAX_CARDS])
    if not posts:
        return reply("There are no blog posts published yet.",
                     chips=DEFAULT_CHIPS, intent="blog")

    return reply(
        "Our blog has recipes, market tips and stories about our vendors. "
        "Here are the latest posts:",
        cards=[post_card(p) for p in posts],
        links=[("All posts", safe_url("blog:post-list"))],
        chips=["What is on sale?", "Who are your vendors?"],
        intent="blog",
    )


def handle_capabilities():
    return reply(
        "I am the shop assistant — I read this shop's own database, so what I "
        "tell you is always current. Try asking me:\n"
        "• *How much is sushi?* — prices, discounts and stock\n"
        "• *Do you have anything under $20?* — search by budget\n"
        "• *What categories do you have?* — browse the range\n"
        "• *Who are your vendors?* — vendor details and their products\n"
        "• *What is on sale?* — live discounts and coupon codes\n"
        "• *How long is delivery?* — delivery, payment, returns and accounts",
        chips=DEFAULT_CHIPS,
        intent="capabilities",
    )


def handle_greeting():
    count = published_products().count()
    return reply(
        "Hello! I am the shop assistant. I can look up any of our **{}** products, "
        "check prices and stock, explain delivery and payment, or point you at the "
        "right vendor. What are you looking for?".format(count),
        chips=DEFAULT_CHIPS,
        intent="greeting",
    )


def handle_fallback():
    """Say honestly that the question was not understood — never invent."""
    limits = published_products().aggregate(low=Min("price"), high=Max("price"))
    range_hint = ""
    if limits["low"] is not None and limits["high"] is not None:
        range_hint = " Our products run from {} to {}.".format(
            money(limits["low"]), money(limits["high"]))

    return reply(
        "Sorry, I did not understand that one. I am a simple assistant, so I do "
        "best with short questions about products, prices, vendors, delivery or "
        "payment.{}\nTry one of these, or use the search box at the top of the "
        "page.".format(range_hint),
        links=[("Browse products", safe_url("core:product-list")),
               ("Contact a human", safe_url("core:contact"))],
        chips=DEFAULT_CHIPS,
        intent="fallback",
    )


# --------------------------------------------------------------------------
# Routing
# --------------------------------------------------------------------------

def score_intents(norm_text, word_set):
    scores = {}
    for intent in INTENTS + FAQ_INTENTS:
        value = intent.score(norm_text, word_set)
        if value:
            scores[intent.name] = value
    return scores


def answer(message, context=None):
    """Turn one customer message into one reply. The only public entry point."""
    context = context or {}
    text = (message or "").strip()
    if not text:
        return handle_greeting()

    # Overlong input is almost always a paste; trim rather than scan it all.
    text = text[:400]
    norm = normalize(text)
    words = set(tokenize(text, keep_stopwords=True))

    scores = score_intents(norm, words)
    best = max(scores, key=scores.get) if scores else ""
    strength = scores.get(best, 0)
    entities = find_entities(text)

    named_product = top(entities["products"])
    remembered = resolve_pronoun(text, context) if not named_product else None
    product = named_product or remembered

    # --- social openers, only when that is all the message is ----------------
    if best in ("greeting", "farewell", "thanks") and len(words) <= 4 and not product:
        if best == "greeting":
            return handle_greeting()
        if best == "thanks":
            return reply(
                "Happy to help! Ask me anything else about the shop.",
                chips=DEFAULT_CHIPS, intent="thanks")
        return reply("Goodbye — enjoy your shopping!", chips=DEFAULT_CHIPS,
                     intent="farewell")

    if best == "capabilities" and strength >= 3:
        return handle_capabilities()

    # --- questions about one named product ----------------------------------
    # A product name plus "price"/"stock" is unambiguous, so it is checked
    # before the broader intents that share vocabulary with it.
    if product and scores.get("stock", 0) >= 1:
        return handle_product_detail(product, ask="stock")
    if product and scores.get("price", 0) >= 1:
        return handle_product_detail(product, ask="price")

    # --- filters that only make sense as whole-catalogue queries ------------
    if scores.get("budget", 0) >= 3:
        return handle_budget(norm, entities)
    if scores.get("superlative", 0) >= 3:
        return handle_superlative(norm, entities)
    if scores.get("coupon", 0) >= 3:
        return handle_coupon()
    if scores.get("deals", 0) >= 3 and not product:
        return handle_deals()

    # --- browsing the shape of the shop -------------------------------------
    if best == "blog" and strength >= 3:
        return handle_blog(text, entities)
    if scores.get("vendor", 0) >= 3 and not product:
        vendor = top(entities["vendors"])
        return handle_vendor(vendor) if vendor else handle_vendor_list()
    if scores.get("category", 0) >= 3 and not product:
        category = top(entities["categories"])
        return handle_category(category) if category else handle_category_list()
    if best == "recommend" and strength >= 3:
        return handle_recommend()

    # --- searching the catalogue --------------------------------------------
    # "Do you have chicken?" is a browse, not a question about one product,
    # so it is answered with a list even when one product matched by name.
    if scores.get("product_search", 0) >= 3:
        found = handle_search(text, entities)
        if found:
            return found

    # --- anything else that named something in the database -----------------
    if product:
        return handle_product_detail(product, ask="price")

    category, vendor = stronger_of(entities)
    if vendor:
        return handle_vendor(vendor)
    if category:
        return handle_category(category)

    if entities["posts"] and (scores.get("blog", 0) or len(words) > 3):
        return handle_blog(text, entities)

    # --- policy questions ----------------------------------------------------
    faq_scores = {name: value for name, value in scores.items() if name in FAQ_BY_ID}
    if faq_scores:
        best_faq = max(faq_scores, key=faq_scores.get)
        if faq_scores[best_faq] >= 1:
            return faq_reply(best_faq)

    # --- last chance: treat it as a product search ---------------------------
    found = handle_search(text, entities)
    if found:
        return found

    return handle_fallback()
