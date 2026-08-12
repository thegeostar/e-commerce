"""Regression tests for the storefront.

These cover input that arrives from a query string or a form. Every value here
can be typed straight into the address bar, and each one used to reach the ORM
unparsed and raise a 500 instead of a plain "bad request".
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from core.models import (Address, CartOrder, Category, Coupon, Product,
                         ProductReview, Vendor)
from userauths.models import User


class JunkInputTests(TestCase):
    """Nothing a customer can type should ever produce a 500."""

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(title="Food")
        cls.vendor = Vendor.objects.create(title="Nature Foods")
        cls.product = Product.objects.create(
            title="Sushi", price="10.96", old_price="20.99",
            category=cls.category, vendor=cls.vendor,
            product_status="published")
        cls.user = User.objects.create_user(
            username="buyer", email="buyer@example.com", password="pw-for-tests")

    def assertNotServerError(self, response):
        self.assertLess(response.status_code, 500,
                        f"got {response.status_code} for a bad request")

    # -- anonymous endpoints ------------------------------------------------

    def test_add_to_cart_rejects_a_non_numeric_id(self):
        self.assertNotServerError(
            self.client.get(reverse("core:add-to-cart"), {"id": "abc"}))

    def test_add_to_cart_rejects_a_missing_id(self):
        self.assertNotServerError(self.client.get(reverse("core:add-to-cart")))

    def test_add_to_cart_rejects_an_unknown_id(self):
        self.assertNotServerError(
            self.client.get(reverse("core:add-to-cart"), {"id": 99999}))

    def test_filter_products_survives_a_non_numeric_price(self):
        for params in ({"min_price": "abc"}, {"max_price": "abc"},
                       {"min_price": "1", "max_price": "nope"}):
            with self.subTest(params=params):
                self.assertNotServerError(
                    self.client.get(reverse("core:filter-product"), params))

    def test_filter_products_survives_a_non_numeric_facet(self):
        for params in ({"category[]": "abc"}, {"vendor[]": "abc"}):
            with self.subTest(params=params):
                self.assertNotServerError(
                    self.client.get(reverse("core:filter-product"), params))

    def test_filter_products_still_filters_on_good_input(self):
        Product.objects.create(title="Expensive", price="500.00",
                               category=self.category, product_status="published")
        response = self.client.get(reverse("core:filter-product"),
                                   {"max_price": "50"})
        self.assertContains(response, "Sushi")
        self.assertNotContains(response, "Expensive")

    def test_cart_quantity_is_capped(self):
        self.client.get(reverse("core:add-to-cart"),
                        {"id": self.product.id, "qty": "10" * 12})
        cart = self.client.session["cart_data_obj"]
        self.assertEqual(int(cart[str(self.product.id)]["qty"]), 999)

    def test_cart_quantity_falls_back_on_junk(self):
        for raw in ("abc", "-5", "0", ""):
            with self.subTest(qty=raw):
                # Emptied each time: adding tops the line up, so without this
                # the cases would accumulate instead of each starting at zero.
                self.client.get(reverse("core:delete-from-cart"),
                                {"id": self.product.id})
                self.client.get(reverse("core:add-to-cart"),
                                {"id": self.product.id, "qty": raw})
                cart = self.client.session["cart_data_obj"]
                self.assertEqual(int(cart[str(self.product.id)]["qty"]), 1)

    # -- endpoints that need a login ----------------------------------------

    def test_wishlist_endpoints_survive_junk_ids(self):
        self.client.force_login(self.user)
        for name in ("core:add-to-wishlist", "core:remove-from-wishlist"):
            with self.subTest(view=name):
                self.assertNotServerError(
                    self.client.get(reverse(name), {"id": "abc"}))

    def test_make_default_address_survives_a_junk_id(self):
        self.client.force_login(self.user)
        self.assertNotServerError(
            self.client.get(reverse("core:make-default-address"), {"id": "abc"}))

    def test_a_bad_id_does_not_clear_the_existing_default_address(self):
        """The old code cleared every default before checking the target."""
        self.client.force_login(self.user)
        default = Address.objects.create(user=self.user, address="Street 271",
                                         status=True)

        self.client.get(reverse("core:make-default-address"), {"id": 99999})

        default.refresh_from_db()
        self.assertTrue(default.status)

    def test_make_default_address_still_works(self):
        self.client.force_login(self.user)
        first = Address.objects.create(user=self.user, address="One", status=True)
        second = Address.objects.create(user=self.user, address="Two", status=False)

        self.client.get(reverse("core:make-default-address"), {"id": second.id})

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.status)
        self.assertTrue(second.status)

    # -- reviews -------------------------------------------------------------

    def test_review_rejects_a_non_numeric_rating(self):
        self.client.force_login(self.user)
        self.assertNotServerError(self.client.post(
            reverse("core:ajax-add-review", args=[self.product.id]),
            {"review": "Nice", "rating": "abc"}))

    def test_review_rejects_a_rating_outside_the_scale(self):
        self.client.force_login(self.user)
        for rating in ("0", "6", "99", "-3"):
            with self.subTest(rating=rating):
                response = self.client.post(
                    reverse("core:ajax-add-review", args=[self.product.id]),
                    {"review": "Nice", "rating": rating})
                self.assertEqual(response.status_code, 400)
        self.assertFalse(ProductReview.objects.exists())

    def test_review_accepts_a_valid_rating(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("core:ajax-add-review", args=[self.product.id]),
            {"review": "Nice", "rating": "5"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ProductReview.objects.get().rating, 5)

    def test_a_second_review_of_the_same_product_is_refused(self):
        """The template hides the form; the endpoint has to refuse it too."""
        self.client.force_login(self.user)
        url = reverse("core:ajax-add-review", args=[self.product.id])

        self.client.post(url, {"review": "Nice", "rating": "5"})
        response = self.client.post(url, {"review": "Also nice", "rating": "1"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ProductReview.objects.count(), 1)


class CartQuantityTests(TestCase):
    """"Add to cart" tops the line up; the cart's own box sets it exactly."""

    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(title="Food")
        cls.product = Product.objects.create(
            title="Sushi", price="10.00", category=category,
            product_status="published")

    def line(self):
        return self.client.session["cart_data_obj"][str(self.product.id)]

    def add(self, qty=None):
        params = {"id": self.product.id}
        if qty is not None:
            params["qty"] = qty
        return self.client.get(reverse("core:add-to-cart"), params)

    def test_adding_twice_from_a_listing_card_makes_two(self):
        self.add(1)
        self.add(1)
        self.assertEqual(self.line()["qty"], 2)

    def test_adding_a_chosen_quantity_accumulates(self):
        self.add(3)
        self.add(2)
        self.assertEqual(self.line()["qty"], 5)

    def test_topping_up_never_passes_the_cap(self):
        self.add(900)
        self.add(900)
        self.assertEqual(self.line()["qty"], 999)

    def test_the_cart_quantity_box_sets_an_exact_value(self):
        self.add(5)
        self.client.get(reverse("core:update-cart"),
                        {"id": self.product.id, "qty": 2})
        self.assertEqual(self.line()["qty"], 2)

    def test_adding_a_second_product_does_not_disturb_the_first(self):
        self.add(2)
        other = Product.objects.create(title="Cake", price="4.00",
                                       product_status="published")
        self.client.get(reverse("core:add-to-cart"), {"id": other.id, "qty": 1})

        cart = self.client.session["cart_data_obj"]
        self.assertEqual(cart[str(self.product.id)]["qty"], 2)
        self.assertEqual(cart[str(other.id)]["qty"], 1)

    def test_the_price_is_refreshed_from_the_database(self):
        self.add(1)
        Product.objects.filter(pk=self.product.pk).update(price="99.00")
        self.add(1)
        self.assertEqual(self.line()["price"], "99.00")


class CheckoutIdempotencyTests(TestCase):
    """Submitting the checkout form twice must not leave two orders."""

    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(title="Food")
        cls.product = Product.objects.create(
            title="Sushi", price="10.00", category=category,
            product_status="published")
        cls.user = User.objects.create_user(
            username="buyer", email="buyer@example.com", password="pw-for-tests")

    def setUp(self):
        self.client.force_login(self.user)
        self.client.get(reverse("core:add-to-cart"),
                        {"id": self.product.id, "qty": 2})

    def submit(self, **overrides):
        data = {"full_name": "Dara", "email": "buyer@example.com",
                "mobile": "061756481", "address": "Street 271",
                "city": "Phnom Penh", "state": "PP", "country": "Cambodia"}
        data.update(overrides)
        return self.client.post(reverse("core:save_checkout_info"), data)

    def test_submitting_twice_reuses_the_same_order(self):
        first = self.submit()
        second = self.submit()

        self.assertEqual(CartOrder.objects.count(), 1)
        self.assertEqual(first.url, second.url)

    def test_submitting_twice_does_not_duplicate_the_line_items(self):
        self.submit()
        self.submit()

        order = CartOrder.objects.get()
        self.assertEqual(order.cartorderproducts_set.count(), 1)
        self.assertEqual(order.cartorderproducts_set.get().qty, 2)

    def test_resubmitting_picks_up_the_new_cart_total(self):
        self.submit()
        self.client.get(reverse("core:update-cart"),
                        {"id": self.product.id, "qty": 5})
        self.submit()

        order = CartOrder.objects.get()
        self.assertEqual(order.price, Decimal("50.00"))

    def test_resubmitting_releases_a_coupon_so_it_can_be_used_again(self):
        """The recalculated price has no discount in it, so the coupon must go."""
        coupon = Coupon.objects.create(code="SAVE25", discount=25, active=True)
        self.submit()
        order = CartOrder.objects.get()

        self.client.post(reverse("core:checkout", args=[order.oid]),
                         {"code": "SAVE25"})
        order.refresh_from_db()
        self.assertEqual(order.price, Decimal("15.00"))
        self.assertIn(coupon, order.coupons.all())

        self.submit()

        order.refresh_from_db()
        self.assertEqual(order.price, Decimal("20.00"))
        self.assertEqual(order.saved, Decimal("0"))
        self.assertNotIn(coupon, order.coupons.all())

    def test_a_paid_order_is_never_reused(self):
        self.submit()
        CartOrder.objects.update(paid_status=True, payment_method="cod")

        self.client.get(reverse("core:add-to-cart"), {"id": self.product.id})
        self.submit()

        self.assertEqual(CartOrder.objects.count(), 2)

    def test_an_order_awaiting_payment_is_never_reused(self):
        """Once KHQR proof is submitted the order is committed, not a draft."""
        self.submit()
        CartOrder.objects.update(payment_method="khqr", khqr_status="pending")

        self.client.get(reverse("core:add-to-cart"), {"id": self.product.id})
        self.submit()

        self.assertEqual(CartOrder.objects.count(), 2)

    def test_an_empty_cart_creates_nothing(self):
        self.client.get(reverse("core:delete-from-cart"),
                        {"id": self.product.id})
        self.submit()
        self.assertEqual(CartOrder.objects.count(), 0)


class SortingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(title="Food")
        Product.objects.create(title="Cheap", price="5.00", old_price="6.00",
                               category=category, product_status="published")
        Product.objects.create(title="Pricey", price="50.00", old_price="90.00",
                               category=category, product_status="published")

    def test_every_sort_option_renders(self):
        for key in ("featured", "price", "-price", "newest", "discount",
                    "rating", "bogus", ""):
            with self.subTest(sort=key):
                response = self.client.get(reverse("core:product-list"),
                                           {"sort": key})
                self.assertEqual(response.status_code, 200)


class OrderImageTests(TestCase):
    def test_order_img_does_not_double_the_media_prefix(self):
        from core.models import CartOrder, CartOrderProducts

        user = User.objects.create_user(username="b", email="b@example.com",
                                        password="pw-for-tests")
        order = CartOrder.objects.create(user=user, price="10.00")
        line = CartOrderProducts.objects.create(
            order=order, invoice_no="INV-1", item="Sushi",
            image="/media/user_1/sushi.jpg", qty=1, price="10.00", total="10.00")

        self.assertNotIn("/media//media/", line.order_img())
        self.assertIn('src="/media/user_1/sushi.jpg"', line.order_img())
