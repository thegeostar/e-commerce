"""Seed the blog with starter categories and posts.

Idempotent: matches on slug, so running it twice will not create duplicates.
Images are expected to already sit in media/blog/ (see the paths below).

    ./venv/bin/python manage.py seed_blog
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.models import Category, Post
from userauths.models import User

CATEGORIES = [
    ("Recipes", "blog/fried-rice.jpg"),
    ("Fresh Produce", "blog/market-greens.jpg"),
    ("Vendor Stories", "blog/fresh-fish.jpg"),
    ("Shopping Tips", "blog/baking.jpg"),
]

POSTS = [
    {
        "title": "Five Khmer breakfasts you can cook in under twenty minutes",
        "slug": "five-khmer-breakfasts-under-twenty-minutes",
        "category": "Recipes",
        "image": "blog/fried-rice.jpg",
        "days_ago": 2,
        "featured": True,
        "description": (
            "Bai sach chrouk, kuy teav, num pang — the classics are quicker than their "
            "reputation suggests, as long as you do the shopping the night before."
        ),
        "content": """
<p>Breakfast in Phnom Penh is a street-food event, but there are mornings when you would
rather not queue. The good news is that most of the staples are assembled rather than
cooked, so the work happens once and the mornings stay short.</p>

<h3>1. Bai sach chrouk (pork and rice)</h3>
<p>Marinate thin pork slices in garlic, palm sugar and a splash of coconut milk overnight.
In the morning they need four minutes on a hot grill pan. Serve over broken rice with
pickled cucumber and a bowl of clear broth.</p>

<h3>2. Kuy teav</h3>
<p>The broth is the only slow part, and it freezes well &mdash; make a large pot on a Sunday
and portion it. Rice noodles soften in a minute of boiling water; add bean sprouts, spring
onion and whatever protein you have.</p>

<h3>3. Num pang pate</h3>
<p>A split baguette, pate, cucumber, coriander, pickled carrot and chilli. No cooking at all
if the pate is already made.</p>

<h3>4. Fried rice with egg</h3>
<p>Yesterday's rice is better than fresh rice here &mdash; drier grains separate properly in
the wok. High heat, garlic first, rice second, egg pushed to the side and folded through at
the end.</p>

<h3>5. Rice porridge (bobor)</h3>
<p>A cup of rice and eight cups of stock, left on the lowest heat while you shower. Finish
with ginger, fried garlic and fish sauce.</p>

<p>All five rely on the same short shopping list: rice, eggs, garlic, spring onion, a
protein and something pickled. Order it once a week and breakfast stops being a decision.</p>
""",
    },
    {
        "title": "How to pick fresh fish at a Phnom Penh market",
        "slug": "how-to-pick-fresh-fish-phnom-penh-market",
        "category": "Fresh Produce",
        "image": "blog/fresh-fish.jpg",
        "days_ago": 6,
        "featured": True,
        "description": (
            "Clear eyes, red gills, firm flesh. Three checks that take ten seconds each and "
            "save you a disappointing dinner."
        ),
        "content": """
<p>Freshwater fish from the Tonle Sap reaches the city's markets within hours, but stalls
turn over at different speeds. These are the checks worth making before you hand over money.</p>

<h3>Look at the eyes</h3>
<p>They should be clear and slightly domed. Cloudy, sunken eyes mean the fish has been out of
the water too long. This is the fastest signal and it is hard to fake.</p>

<h3>Lift the gill cover</h3>
<p>Bright red or deep pink is what you want. Brown or grey gills mean age. A vendor who is
confident in their stock will not mind you looking.</p>

<h3>Press the flesh</h3>
<p>A gentle press should spring back. If your fingerprint stays, the texture has already gone
and it will fall apart in the pan.</p>

<h3>Trust your nose</h3>
<p>Fresh freshwater fish smells of river water and almost nothing else. A strong fishy smell
is the first sign of spoilage, not a normal characteristic.</p>

<p>If you are buying through us instead, our vendors pack fish on ice the morning it is
listed and it travels in a cool box &mdash; but the same checks apply when it arrives.
Anything that fails them, tell us and we replace it.</p>
""",
    },
    {
        "title": "Meet Nature Foods, the family farm behind our leafy greens",
        "slug": "meet-nature-foods-family-farm",
        "category": "Vendor Stories",
        "image": "blog/market-greens.jpg",
        "days_ago": 11,
        "featured": False,
        "description": (
            "Three generations, two hectares in Kandal province, and a delivery run that "
            "starts at four in the morning."
        ),
        "content": """
<p>Nature Foods has been on the site since we opened, and they are still the vendor customers
ask about most often. The farm sits in Kandal province, about forty minutes south of the city,
and it has been in the same family since the 1980s.</p>

<h3>What they grow</h3>
<p>Water spinach, Chinese kale, mustard greens, lemongrass, and whatever herbs the season
allows. The plots rotate, so the listing changes week to week rather than staying static.</p>

<h3>Why the early start</h3>
<p>Greens are cut before sunrise, when the leaves still hold water and the heat has not yet
started pulling moisture out of them. The van leaves at four and reaches our Phnom Penh sorting
point before seven. Anything ordered before noon is at your door the same day.</p>

<h3>What we ask of them</h3>
<p>Every vendor is verified before their first listing goes live &mdash; we visit, we check how
produce is stored, and we agree what happens when an order is wrong. Nature Foods has had two
replacement requests in the last year, both handled the same day.</p>

<p>You can see their full range on their <a href="/vendors/">store page</a>, along with their
rating and response time.</p>
""",
    },
    {
        "title": "What same-day delivery actually means in Phnom Penh traffic",
        "slug": "same-day-delivery-phnom-penh-traffic",
        "category": "Shopping Tips",
        "image": "blog/grilling.jpg",
        "days_ago": 17,
        "featured": False,
        "description": (
            "Order before noon and it arrives today. Here is what happens in between, and "
            "why the cut-off is where it is."
        ),
        "content": """
<p>We promise same-day delivery across Phnom Penh for orders placed before noon. That cut-off
is not arbitrary &mdash; it is the latest point at which a basket can still clear the whole
chain before evening.</p>

<h3>The timeline</h3>
<ul>
    <li><strong>Before noon</strong> &mdash; your order reaches the vendor.</li>
    <li><strong>Noon to two</strong> &mdash; items are picked, packed and consolidated. A basket
    with four vendors in it becomes one parcel here.</li>
    <li><strong>Two to six</strong> &mdash; the delivery run. Riders work in loops by district
    rather than by order sequence, so the address matters more than the order time.</li>
</ul>

<h3>Why afternoons are slower</h3>
<p>Traffic between four and six is the constraint, particularly around Russian Market and along
Monivong. If your address is central and you need a tight window, ordering before ten gives the
rider a much better chance of an early loop.</p>

<h3>Outside the city</h3>
<p>Elsewhere in Cambodia we hand over to courier partners, who usually reach you within two
days. Chilled items are not sent outside Phnom Penh &mdash; the cold chain cannot be guaranteed
that far, so we would rather not sell you a spoiled parcel.</p>
""",
    },
    {
        "title": "Sushi at home: a beginner's guide to rolling",
        "slug": "sushi-at-home-beginners-guide-to-rolling",
        "category": "Recipes",
        "image": "blog/sushi.jpg",
        "days_ago": 24,
        "featured": False,
        "description": (
            "The rice is ninety percent of the job. Get that right and the rolling is a "
            "matter of practice."
        ),
        "content": """
<p>Home sushi fails at the rice far more often than at the rolling. Short-grain rice, seasoned
properly and cooled to body temperature, forgives a great deal of clumsy technique.</p>

<h3>The rice</h3>
<p>Rinse until the water runs clear &mdash; usually four or five changes. Cook with slightly
less water than usual. While it is still hot, fold through a mixture of rice vinegar, sugar and
salt (roughly 4:2:1 by volume), cutting rather than stirring so the grains stay whole.</p>

<h3>Cooling</h3>
<p>Spread it out on a wide tray and fan it. You are aiming for body temperature, not cold. Cold
rice cracks the nori and refuses to stick to itself.</p>

<h3>Rolling</h3>
<p>Nori shiny side down, a thin layer of rice over three quarters of the sheet, filling in a line
one third up. Roll with the mat, tucking the near edge under the filling on the first turn, then
apply steady pressure rather than squeezing.</p>

<h3>Cutting</h3>
<p>Wet the knife between every cut. A dry blade drags and tears the nori. Cut the roll in half,
then each half into three.</p>

<p>Use fish you would be happy to eat raw &mdash; ask the vendor directly whether a fillet is
sashimi grade rather than assuming. If in doubt, cooked prawn, egg and cucumber make an
excellent roll and remove the question entirely.</p>
""",
    },
    {
        "title": "Storing rice, herbs and chillies in a tropical kitchen",
        "slug": "storing-rice-herbs-chillies-tropical-kitchen",
        "category": "Shopping Tips",
        "image": "blog/baking.jpg",
        "days_ago": 31,
        "featured": False,
        "description": (
            "Humidity is the enemy of a well-stocked kitchen. A few container decisions buy "
            "you weeks of extra shelf life."
        ),
        "content": """
<p>Buying in bulk saves money right up until the point where the rice weevils arrive. In a
climate this humid, storage is not an afterthought &mdash; it is most of the battle.</p>

<h3>Rice</h3>
<p>An airtight container, out of sunlight, with a couple of dried bay leaves tucked in. If you
buy a 25kg sack, decant it rather than leaving it open at the top. Freezing the first few
kilos for 48 hours kills any eggs already present.</p>

<h3>Soft herbs</h3>
<p>Coriander, mint and Thai basil last far longer standing in a glass of water with a loose bag
over the top, in the fridge. Treat them like cut flowers and they will give you a week instead
of two days.</p>

<h3>Chillies</h3>
<p>Fresh chillies keep about two weeks in the fridge in a paper bag &mdash; plastic traps
moisture and rots them. For longer storage, freeze them whole; they cut fine from frozen and
lose very little heat.</p>

<h3>Garlic and shallots</h3>
<p>Cool, dark, and above all dry, with air movement. A basket on a shelf beats any sealed
container. Never the fridge, which makes them sprout and soften.</p>

<h3>Palm sugar</h3>
<p>Airtight, always. Left open it draws water out of the air and turns into a single solid
block that you will end up attacking with a knife.</p>
""",
    },
]


class Command(BaseCommand):
    help = "Create the starter blog categories and posts (safe to re-run)."

    def handle(self, *args, **options):
        author = (
            User.objects.filter(email="daraeng054@gmail.com").first()
            or User.objects.filter(is_superuser=True).first()
        )
        if author is None:
            self.stderr.write("No superuser found - posts will have no author.")

        cats = {}
        for title, image in CATEGORIES:
            cat, created = Category.objects.get_or_create(
                title=title, defaults={"image": image}
            )
            cats[title] = cat
            self.stdout.write(f"{'+ ' if created else '= '}category {title}")

        now = timezone.now()
        for spec in POSTS:
            post, created = Post.objects.get_or_create(
                slug=spec["slug"],
                defaults={
                    "title": spec["title"],
                    "image": spec["image"],
                    "description": spec["description"],
                    "content": spec["content"].strip(),
                    "category": cats.get(spec["category"]),
                    "user": author,
                    "status": "published",
                    "featured": spec["featured"],
                    "date": now - timedelta(days=spec["days_ago"]),
                },
            )
            self.stdout.write(f"{'+ ' if created else '= '}post {post.title}")

        self.stdout.write(self.style.SUCCESS(
            f"\nBlog now has {Post.objects.filter(status='published').count()} published "
            f"post(s) across {Category.objects.count()} categories."
        ))
