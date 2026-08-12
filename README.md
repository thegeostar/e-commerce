# ecomprj — Django E-commerce Platform

A multi-vendor e-commerce site built with Django 4.2. Coursework for
DITE Year 2, Semester 2, Royal University of Phnom Penh.

Storefront with product catalog, search and filtering, cart, wishlist, reviews,
coupons, a customer dashboard, a separate vendor dashboard for managing products
and orders, and a built-in shop assistant chatbot.

Checkout takes **KHQR** (any Cambodian banking app) and **cash on delivery**.
Neither settles automatically: the seller confirms the KHQR transaction ID — or
the collected cash — from `/useradmin/`, and only that marks an order paid.

## Setup

```bash
git clone <your-repo-url>
cd Y2-PP

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env      # optional; sensible defaults are built in

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/

> **Ubuntu/Debian note:** if `python3 -m venv venv` fails with
> "ensurepip is not available", run `sudo apt install python3-venv` first.
> See [HOW-TO-RUN.md](HOW-TO-RUN.md) for a no-sudo workaround.

## Dependencies

`requirements.txt` lists only what the code actually imports. The version that
shipped with the course pinned ~50 packages — most unused, and several
(`Pillow==9.1.0`, `pandas==2.1.1`, `django-heroku`) with no wheels for modern
Python. Verified on Python 3.12.3 / Django 4.2.30.

## Project layout

| Path | Purpose |
|---|---|
| `core/` | Products, categories, vendors, cart, orders, checkout, reviews |
| `userauths/` | Custom `User` model, profiles, sign-in/sign-up |
| `useradmin/` | Vendor dashboard — product CRUD, order management, settings |
| `blog/` | Blog posts and blog categories, managed from `/admin/` |
| `chatbot/` | Shop assistant — intent matching, entity lookup, policy answers |
| `ecomprj/` | Project settings, root URLconf, WSGI/ASGI |
| `templates/` | Django templates; shared card/deal markup in `templates/core/partials/` |
| `static/` | CSS, JS, fonts, theme images |
| `media/` | Uploaded product and profile images |

## Routes

- `/` — homepage; `/products/`, `/category/`, `/vendors/`
- `/product/<pid>/` — product detail
- `/blog/` — blog index; `/blog/<slug>/` post detail, `/blog/category/<cid>/`
- `/cart/`, `/wishlist/`, `/checkout/<oid>/`
- `/khqr/<oid>/` — KHQR payment; `/cash-on-delivery/<oid>/` — place a COD order
- `/dashboard/` — customer dashboard (login required)
- `/useradmin/` — vendor dashboard (login required)
- `/chatbot/ask/` — shop assistant endpoint (POST, JSON)
- `/admin/` — Django admin

Sign-in uses **email**, not username.

## Shop assistant

A chat bubble sits in the bottom-right corner of every storefront page. It
answers questions about products, prices, stock, discounts, coupons, categories,
vendors, blog posts, delivery, payment, returns and accounts.

**There is no language model involved.** Nothing is hosted, no API key is
needed, and no request leaves the machine — it runs inside this Django project
like any other app. A question is answered in three steps:

1. **Intent scoring** (`chatbot/engine.py`) — the words typed are matched against
   keyword sets and phrase patterns to work out what is being asked.
2. **Entity lookup** (`chatbot/matching.py`) — the same words are matched against
   names in the database: product titles, categories, vendors, tags, post titles.
   Matching is fuzzy, so "chiken pizaa" still finds *Chicken Pizza*.
3. **Answering** — the intent and the entities are combined into a reply built
   from live database values, with product cards linking to the real pages.

Because prices, stock and coupons are read at question time, **a product added
through the vendor dashboard is answerable immediately** — no retraining, no
data file to regenerate. Shop policies that are not in the database (delivery
times, returns window, payment methods) live in `chatbot/knowledge.py`; edit
that file if those pages change. Anything the assistant cannot place gets an
honest "I did not understand" with suggestions, rather than a guess.

The last product mentioned is kept in the session, so follow-ups work:

> **You:** how much is sushi?
> **Assistant:** Sushi is $10.96 — reduced from $20.99, so you save 48%.
> **You:** is it in stock?
> **Assistant:** Yes — Sushi is in stock (100 available) at $10.96.

Run its tests with:

```bash
python manage.py test chatbot
```

## The database is not in this repo

`db.sqlite3` is gitignored. The course ships it pre-seeded with demo products and
vendors, but it also holds 12 real email addresses and password hashes, which do
not belong in a public repo.

So a fresh clone starts empty. After `migrate` and `createsuperuser`, add products
through `/admin/` or the vendor dashboard.

The blog ships with a seeder, so that part does not have to be retyped by hand:

```bash
python manage.py seed_blog     # 4 categories + 6 starter posts, safe to re-run
```

Images for the catalogue live in `media/` and **are** committed, so product,
category and vendor pictures survive a fresh clone even though the database does
not.

To publish the demo data anyway, remove the `db.sqlite3` line from `.gitignore`.
Only do that on a **private** repo, and change every account password first.

## Credits

Built by following Destiny Franks' Django e-commerce course. The course source
code and design assets belong to their original author — keep this repository
**private** unless you have permission to redistribute them.
