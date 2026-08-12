"""The assistant's static knowledge: shop policies, in the shop's own words.

Everything here mirrors what the site already tells customers on the About,
Purchase Guide and Contact pages, so the assistant never invents a policy.
If one of those pages changes, change the matching entry here too.

Anything that varies — prices, stock, which vendors exist — is *not* in this
file. That is read live from the database in engine.py.
"""

# Facts reused in several answers, kept in one place so they cannot drift apart.
SHOP = {
    "name": "E-commerce",
    "city": "Phnom Penh",
    "phone": "061 756 481",
    "email": "daraeng054@gmail.com",
    "hours": "8:00 to 18:00, seven days a week",
    "office": "No. 25, Russian Federation Blvd (110), Sangkat Toul Kork, "
              "Khan Toul Kork, Phnom Penh 120404",
    "free_delivery_over": 20,
}

# Each entry is one thing a customer might ask about.
#   keywords  - the vocabulary that points at this entry (matched, weighted)
#   answer    - what the assistant says
#   links     - buttons offered under the answer
#   chips     - suggested follow-up questions
ENTRIES = [
    {
        "id": "delivery",
        "keywords": (
            "delivery deliver shipping ship arrive arrival courier send "
            "dispatch fast quick long time same day when receive"
        ),
        "answer": (
            "Delivery works like this:\n"
            "• Order before noon and we deliver the same day anywhere in Phnom Penh.\n"
            "• Elsewhere in Cambodia our courier partners usually arrive within two days.\n"
            "• Delivery is free in Phnom Penh on orders over ${free_delivery_over}.\n"
            "The courier calls the mobile number on your account, so keep it correct."
        ),
        "patterns": [
            r"\bhow long.{0,25}(delivery|deliver|ship|arrive|take)\b",
            r"\bwhen.{0,20}(arrive|deliver|get here|receive)\b",
            r"\bdo you deliver\b",
            r"\bdelivery (fee|cost|charge|time|price|option)\b",
            r"\bfree (delivery|shipping)\b",
            r"\bsame.?day\b",
        ],
        "links": [("Purchase guide", "core:purchase_guide")],
        "chips": ["How do I pay?", "Can I return something?"],
    },
    {
        "id": "returns",
        "keywords": (
            "return refund exchange replace damaged broken wrong item "
            "cancel money back complaint spoiled bad quality guarantee"
        ),
        "answer": (
            "If something arrives damaged, or it is not what you ordered, tell us "
            "within 24 hours and we will replace it or refund you.\n"
            "Message us on the contact page with your order ID and the date, or call "
            "{phone} between {hours}."
        ),
        "patterns": [
            r"\b(can|could|how do) i (return|refund|exchange|send.{0,10}back)\b",
            r"\breturn (policy|it|them)\b",
            r"\brefund\b",
            r"\b(arrived|came).{0,20}(damaged|broken|wrong)\b",
            r"\bcancel.{0,15}order\b",
        ],
        "links": [("Contact us", "core:contact")],
        "chips": ["Where is my order?", "How do I pay?"],
    },
    {
        "id": "payment",
        "keywords": (
            "pay payment paying khqr qr bank cash cod delivery money "
            "card visa mastercard transfer aba wing checkout charge"
        ),
        "answer": (
            "There are two ways to pay at checkout:\n"
            "• **KHQR** — scan the QR with your banking app, then upload the payment "
            "screenshot. We verify it and confirm the order.\n"
            "• **Cash on Delivery** — pay the courier in cash when your order arrives.\n"
            "You will see the item total, the delivery charge and the final amount "
            "before you pay anything."
        ),
        "patterns": [
            r"\bhow (do|can) i pay\b",
            r"\bpayment (method|option)\b",
            r"\bcash on delivery\b",
            r"\bdo you (accept|take)\b",
            r"\bkhqr\b",
            r"\bways? to pay\b",
        ],
        "links": [("Purchase guide", "core:purchase_guide")],
        "chips": ["Do you have any coupons?", "How long is delivery?"],
    },
    {
        "id": "how_to_order",
        "keywords": (
            "order buy purchase shop checkout cart basket add how process "
            "steps start place first"
        ),
        "answer": (
            "Ordering takes four steps:\n"
            "1. Find what you want — search by name, or browse a category.\n"
            "2. Choose the quantity on the product page and press **Add to Cart**. "
            "You can mix vendors in one basket and pay once.\n"
            "3. Open your cart, check it, and enter a coupon code if you have one.\n"
            "4. Go to checkout, confirm your address and phone, then pay by KHQR or "
            "cash on delivery."
        ),
        "patterns": [
            r"\bhow (do|can) i (order|buy|purchase|shop|check ?out)\b",
            r"\bhow to (order|buy|purchase)\b",
            r"\badd to cart\b",
            r"\bplace an order\b",
        ],
        "links": [("Browse products", "core:product-list"), ("Your cart", "core:cart")],
        "chips": ["What categories do you have?", "How do I pay?"],
    },
    {
        "id": "account",
        "keywords": (
            "account register sign signup signin login register password "
            "forgot email username profile create join member"
        ),
        "answer": (
            "You can browse without an account, but you need one to check out so we "
            "know where to deliver.\n"
            "Registering takes a minute and asks for your full name, email address "
            "(that is what you sign in with), mobile number and a password. Your "
            "delivery address is added at your first checkout."
        ),
        "patterns": [
            r"\b(create|make|open|register|need|want).{0,15}account\b",
            r"\bsign (up|in)\b",
            r"\bforgot.{0,15}password\b",
            r"\bhow (do|can) i (register|log ?in|sign)\b",
        ],
        "links": [("Sign up", "userauths:sign-up"), ("Sign in", "userauths:sign-in")],
        "chips": ["Where is my order?", "How do I order?"],
    },
    {
        "id": "order_status",
        "keywords": (
            "my order status track tracking where progress shipped history "
            "purchased bought invoice receipt orders dashboard"
        ),
        "answer": (
            "Sign in and open your dashboard — every order is listed there with its "
            "order ID and current status (processing, shipped or delivered). Click one "
            "to see the items and the delivery address.\n"
            "If something looks wrong, contact us with the order ID and we will check it."
        ),
        "patterns": [
            r"\bwhere is my (order|package|parcel|delivery)\b",
            r"\btrack.{0,15}\border\b",
            r"\bmy orders?\b",
            r"\border (status|history)\b",
        ],
        "links": [("Your dashboard", "core:dashboard"), ("Contact us", "core:contact")],
        "chips": ["Can I return something?", "How long is delivery?"],
    },
    {
        "id": "contact",
        "keywords": (
            "contact phone call email address location office map hour open "
            "close reach support help human staff talk speak team"
        ),
        "answer": (
            "Our team in Phnom Penh answers questions about orders, delivery and "
            "returns {hours}.\n"
            "• Phone: {phone}\n"
            "• Email: {email}\n"
            "• Office: {office}\n"
            "We usually reply to messages within one working day."
        ),
        "patterns": [
            r"\b(phone|telephone|contact) number\b",
            r"\bcontact (you|us|detail)\b",
            r"\bwhere are you (located|based)\b",
            r"\byour (address|email|phone|office)\b",
            r"\b(opening|business) hours\b",
            r"\btalk to (a )?(human|person|someone|staff|agent)\b",
        ],
        "links": [("Contact page", "core:contact")],
        "chips": ["Where is my order?", "Can I return something?"],
    },
    {
        "id": "about",
        "keywords": (
            "about who what shop store company marketplace business background "
            "history mission team you yourself information"
        ),
        "answer": (
            "{name} is an online marketplace based in {city}. We bring local vendors "
            "— market traders, family farms and neighbourhood shops — onto one site, so "
            "you can order from all of them in a single basket.\n"
            "Every vendor is verified before their first listing goes live, and their "
            "rating and response time are shown on their store page. The site began as "
            "a coursework project at the Royal University of Phnom Penh."
        ),
        "patterns": [
            r"\b(tell me |what is |what's )?about (the |your |this )?"
            r"(shop|store|company|site|business|marketplace|you)\b",
            r"\bwho (owns|runs|founded)\b",
            r"\bwhat is this (shop|site|store|marketplace)\b",
        ],
        "links": [("About us", "core:about_us"), ("Our vendors", "core:vendor-list")],
        "chips": ["Who are your vendors?", "What categories do you have?"],
    },
    {
        "id": "selling",
        "keywords": (
            "sell selling seller vendor become join list listing partner "
            "supplier my products my shop store open apply"
        ),
        "answer": (
            "We are always looking for new vendors. Send us a message through the "
            "contact page saying what you sell, and we will walk you through opening a "
            "vendor account.\n"
            "We handle the storefront, search, payments and delivery — you keep doing "
            "the sourcing and selling."
        ),
        "patterns": [
            r"\bhow (do|can) i (sell|list|become)\b",
            r"\bbecome a (vendor|seller|partner)\b",
            r"\bi want to sell\b",
            r"\bsell (on|with|through) (your|the|you|this)\b",
            r"\blist my (product|item|shop|store)\b",
        ],
        "links": [("Contact us", "core:contact")],
        "chips": ["Who are your vendors?", "Tell me about the shop"],
    },
    {
        "id": "reviews",
        "keywords": (
            "review rating rate star feedback comment opinion trust "
            "recommend good quality"
        ),
        "answer": (
            "Every product page has reviews from real buyers, with a star rating out of "
            "five. Sign in and you can leave your own rating and review at the bottom of "
            "any product page.\n"
            "Vendor pages show the store's overall rating, response time and how often "
            "they ship on time."
        ),
        "patterns": [
            r"\b(read|see|any|leave|write).{0,12}review\b",
            r"\bhow (do|can) i (review|rate)\b",
            r"\bstar rating\b",
        ],
        "links": [("Browse products", "core:product-list")],
        "chips": ["Who are your vendors?", "What is on sale?"],
    },
    {
        "id": "wishlist",
        "keywords": (
            "wishlist wish save saved favourite favorite heart like later "
            "bookmark keep"
        ),
        "answer": (
            "Sign in and press the heart icon on any product to save it to your "
            "wishlist. Everything you save is on the wishlist page, and you can move it "
            "into your cart from there whenever you are ready."
        ),
        "patterns": [
            r"\bwish ?list\b",
            r"\bsave (it |them )?for later\b",
            r"\bfavourite|favorite\b",
        ],
        "links": [("Your wishlist", "core:wishlist")],
        "chips": ["How do I order?", "What is on sale?"],
    },
    {
        "id": "privacy",
        "keywords": (
            "privacy data personal information secure security safe cookie "
            "term condition policy legal rule"
        ),
        "answer": (
            "Our privacy policy explains what we collect and why, and the terms of "
            "service cover the rules for using the site. Both are linked in the footer "
            "of every page."
        ),
        "patterns": [
            r"\bprivacy policy\b",
            r"\bterms (and conditions|of service)\b",
            r"\bmy (data|information) (safe|secure)\b",
            r"\bcookies?\b",
        ],
        "links": [
            ("Privacy policy", "core:privacy_policy"),
            ("Terms of service", "core:terms_of_service"),
        ],
        "chips": ["How do I pay?", "Tell me about the shop"],
    },
]


def render(text):
    """Fill the {placeholders} in an answer with the shop's real details."""
    return text.format(**SHOP)
