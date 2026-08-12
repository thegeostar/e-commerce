# ecomprj — Django E-commerce Platform

A multi-vendor e-commerce site built with Django 4.2. Coursework for
DITE Year 2, Semester 2, Royal University of Phnom Penh.

Storefront with product catalog, search and filtering, cart, wishlist, reviews,
coupons, Stripe/PayPal checkout, a customer dashboard, and a separate vendor
dashboard for managing products and orders.

## Setup

```bash
git clone <your-repo-url>
cd Y2-PP

python3 -m venv venv
source venv/bin/activate

pip install -r requirements-local.txt

cp .env.example .env      # then add your Stripe test keys

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/

> **Ubuntu/Debian note:** if `python3 -m venv venv` fails with
> "ensurepip is not available", run `sudo apt install python3-venv` first.
> See [HOW-TO-RUN.md](HOW-TO-RUN.md) for a no-sudo workaround.

## Dependencies

Install from **`requirements-local.txt`**, not `requirements.txt`.

`requirements.txt` is the file that shipped with the course. It targets Python 3.9
(see `runtime.txt`) and will not install on Python 3.11+: `Pillow==9.1.0` and
`pandas==2.1.1` have no wheels for those versions, and `django-heroku` pulls in
`psycopg2`, which needs Postgres headers. It also lists `django-environ` while
`settings.py` imports `environs`, and omits `django-ckeditor`, which
`core/migrations/0010` imports at load time.

`requirements-local.txt` lists only what the code actually imports, at versions
that install cleanly on Python 3.12. Verified on Python 3.12.3 / Django 4.2.30.

## Project layout

| Path | Purpose |
|---|---|
| `core/` | Products, categories, vendors, cart, orders, checkout, reviews |
| `userauths/` | Custom `User` model, profiles, sign-in/sign-up |
| `useradmin/` | Vendor dashboard — product CRUD, order management, settings |
| `ecomprj/` | Project settings, root URLconf, WSGI/ASGI |
| `templates/` | Django templates for all three apps |
| `static/` | CSS, JS, fonts, theme images |
| `media/` | Uploaded product and profile images |
| `Ztemplate/` | Original unconverted HTML, kept for reference — not served |

## Routes

- `/` — homepage; `/products/`, `/category/`, `/vendors/`
- `/product/<pid>/` — product detail
- `/cart/`, `/wishlist/`, `/checkout/<oid>/`
- `/dashboard/` — customer dashboard (login required)
- `/useradmin/` — vendor dashboard (login required)
- `/admin/` — Django admin

Sign-in uses **email**, not username. `/cart/` redirects to the homepage when the
cart is empty — that is intended, not a bug.

## The database is not in this repo

`db.sqlite3` is gitignored. The course ships it pre-seeded with demo products and
vendors, but it also holds 12 real email addresses and password hashes, which do
not belong in a public repo.

So a fresh clone starts empty. After `migrate` and `createsuperuser`, add products
through `/admin/` or the vendor dashboard.

To publish the demo data anyway, remove the `db.sqlite3` line from `.gitignore`.
Only do that on a **private** repo, and change every account password first.

## Credits

Built by following Destiny Franks' Django e-commerce course. The course source
code and design assets belong to their original author — keep this repository
**private** unless you have permission to redistribute them.
