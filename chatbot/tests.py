"""Tests for the shop assistant.

The fixtures below are deliberately tiny — the point is to prove the routing
picks the right handler and that answers are read from the database, not that
the real catalogue is in any particular state.
"""

import json

from django.test import TestCase
from django.urls import reverse

from blog.models import Category as BlogCategory, Post
from core.models import Category, Coupon, Product, Vendor

from chatbot.engine import answer
from chatbot.matching import normalize, phrase_score, singular, token_set


class MatchingTests(TestCase):
    def test_normalize_strips_punctuation_and_case(self):
        self.assertEqual(normalize("How MUCH is Sushi?!"), "how much is sushi")

    def test_singular_handles_common_plurals(self):
        self.assertEqual(singular("coupons"), "coupon")
        self.assertEqual(singular("categories"), "category")
        self.assertEqual(singular("boxes"), "box")
        # Words that only look plural must survive intact.
        self.assertEqual(singular("is"), "is")

    def test_phrase_score_rewards_a_full_name(self):
        query = "how much is chicken pizza"
        full = phrase_score("Chicken Pizza", token_set(query), normalize(query))
        partial = phrase_score("Chicken Soup", token_set(query), normalize(query))
        self.assertGreater(full, partial)

    def test_phrase_score_forgives_a_typo(self):
        query = "chiken pizaa"
        self.assertGreater(
            phrase_score("Chicken Pizza", token_set(query), normalize(query)), 0.6)

    def test_phrase_score_respects_word_boundaries(self):
        # "Food" must not score a perfect match on the vendor name "XFood".
        query = "tell me about xfood"
        self.assertLess(
            phrase_score("Food", token_set(query), normalize(query)), 1.0)


class EngineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.food = Category.objects.create(title="Food")
        cls.empty = Category.objects.create(title="Computers")
        cls.vendor = Vendor.objects.create(title="Nature Foods",
                                           address="Street 271, Phnom Penh",
                                           contact="061756481")

        cls.sushi = Product.objects.create(
            title="Sushi", price="10.96", old_price="20.99",
            category=cls.food, vendor=cls.vendor,
            product_status="published", in_stock=True, stock_count="7")
        cls.cake = Product.objects.create(
            title="Vanilla Cake", price="20.99", old_price="20.99",
            category=cls.food, vendor=cls.vendor,
            product_status="published", in_stock=False)
        # Never published, so it must not appear in any answer.
        cls.hidden = Product.objects.create(
            title="Secret Draft Pear", price="1.00",
            category=cls.food, product_status="draft")

        cls.coupon = Coupon.objects.create(code="CODE1", discount=25, active=True)

        blog_category = BlogCategory.objects.create(title="Recipes")
        cls.post = Post.objects.create(
            title="Sushi at home: a beginner's guide to rolling",
            description="The rice is ninety percent of the job.",
            category=blog_category, status="published")

    # -- product questions --------------------------------------------------

    def test_price_question_quotes_the_database(self):
        result = answer("how much is sushi?")
        self.assertIn("$10.96", result["reply"])
        self.assertEqual(result["cards"][0]["title"], "Sushi")

    def test_price_question_reports_the_discount(self):
        self.assertIn("48%", answer("how much is sushi?")["reply"])

    def test_stock_question_uses_the_stock_flag(self):
        self.assertIn("in stock", answer("is sushi available?")["reply"])
        self.assertIn("sold out", answer("do you have vanilla cake in stock")["reply"])

    def test_unpublished_products_are_never_offered(self):
        for question in ("do you sell pear", "what is your cheapest product"):
            self.assertNotIn("Secret Draft Pear", json.dumps(answer(question)))

    def test_partial_name_lists_every_match(self):
        Product.objects.create(title="Sushi Platter", price="30.00",
                               category=self.food, product_status="published")
        result = answer("do you have sushi")
        titles = [card["title"] for card in result["cards"]]
        self.assertIn("Sushi Platter", titles)

    def test_typo_still_finds_the_product(self):
        self.assertIn("Sushi", answer("how much is sushii")["reply"])

    # -- catalogue-wide questions -------------------------------------------

    def test_budget_filter_respects_the_ceiling(self):
        result = answer("do you have anything under $15")
        titles = [card["title"] for card in result["cards"]]
        self.assertIn("Sushi", titles)
        self.assertNotIn("Vanilla Cake", titles)

    def test_cheapest_picks_the_lowest_price(self):
        result = answer("what is your cheapest product?")
        self.assertEqual(result["intent"], "superlative")
        self.assertIn("Sushi", result["reply"])

    def test_deals_only_lists_reduced_products(self):
        result = answer("what is on sale?")
        titles = [card["title"] for card in result["cards"]]
        self.assertIn("Sushi", titles)
        self.assertNotIn("Vanilla Cake", titles)

    def test_coupon_reads_active_codes(self):
        self.assertIn("CODE1", answer("do you have any coupons?")["reply"])

    def test_inactive_coupons_are_not_offered(self):
        Coupon.objects.update(active=False)
        self.assertNotIn("CODE1", answer("any promo code?")["reply"])

    # -- browsing -----------------------------------------------------------

    def test_category_list_names_every_category(self):
        reply = answer("what categories do you have?")["reply"]
        self.assertIn("Food", reply)
        self.assertIn("Computers", reply)

    def test_empty_category_is_reported_honestly(self):
        self.assertIn("nothing is listed", answer("show me computers")["reply"])

    def test_vendor_lookup_returns_vendor_details(self):
        result = answer("tell me about Nature Foods")
        self.assertEqual(result["intent"], "vendor")
        self.assertIn("Street 271", result["reply"])

    def test_vendor_list_answers_who_are_your_vendors(self):
        self.assertIn("Nature Foods", answer("who are your vendors?")["reply"])

    def test_blog_search_finds_a_post(self):
        result = answer("any blog posts about sushi?")
        self.assertEqual(result["intent"], "blog")
        self.assertIn("Sushi at home", json.dumps(result["cards"]))

    # -- policy questions ---------------------------------------------------

    def test_policy_questions_route_to_the_knowledge_base(self):
        expected = {
            "how long is delivery?": "delivery",
            "how do I pay?": "payment",
            "can I return a damaged item?": "returns",
            "where is my order?": "order_status",
            "how do I create an account?": "account",
            "what is your phone number?": "contact",
            "how do I sell on your site?": "selling",
            "what is your privacy policy?": "privacy",
        }
        for question, intent in expected.items():
            with self.subTest(question=question):
                self.assertEqual(answer(question)["intent"], intent)

    # -- conversation -------------------------------------------------------

    def test_greeting_is_recognised(self):
        self.assertEqual(answer("hello")["intent"], "greeting")

    def test_context_resolves_a_follow_up_pronoun(self):
        first = answer("how much is sushi?")
        second = answer("is it in stock?", first["context"])
        self.assertIn("Sushi", second["reply"])

    def test_nonsense_falls_back_without_inventing(self):
        result = answer("qwerty zxcvb asdfg")
        self.assertEqual(result["intent"], "fallback")
        self.assertIn("did not understand", result["reply"])

    def test_empty_message_returns_the_greeting(self):
        self.assertEqual(answer("")["intent"], "greeting")


class ViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(title="Food")
        Product.objects.create(title="Sushi", price="10.96", old_price="20.99",
                               category=category, product_status="published")

    def test_ask_returns_json(self):
        response = self.client.post(
            reverse("chatbot:ask"),
            data=json.dumps({"message": "how much is sushi?"}),
            content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("$10.96", response.json()["reply"])

    def test_ask_accepts_a_form_post(self):
        response = self.client.post(reverse("chatbot:ask"),
                                    {"message": "what is on sale?"})
        self.assertEqual(response.status_code, 200)

    def test_ask_rejects_get(self):
        self.assertEqual(self.client.get(reverse("chatbot:ask")).status_code, 405)

    def test_ask_handles_broken_json(self):
        response = self.client.post(reverse("chatbot:ask"), data="{not json",
                                    content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_context_survives_between_requests(self):
        self.client.post(reverse("chatbot:ask"),
                         data=json.dumps({"message": "how much is sushi?"}),
                         content_type="application/json")
        follow_up = self.client.post(
            reverse("chatbot:ask"),
            data=json.dumps({"message": "is it in stock?"}),
            content_type="application/json")
        self.assertIn("Sushi", follow_up.json()["reply"])

    def test_welcome_returns_an_opening_message(self):
        response = self.client.get(reverse("chatbot:welcome"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["reply"])

    def test_widget_is_rendered_on_the_homepage(self):
        response = self.client.get(reverse("core:index"))
        self.assertContains(response, 'id="shopbot"')
