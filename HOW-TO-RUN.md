# How to run this project

**Use `V2 - Complete Source Code` only.** V2 already contains everything in V1 plus
more (see "V1 vs V2" below). There is nothing to merge.

## Run it

```bash
cd "V2 - Complete Source Code"
./venv/bin/python manage.py runserver
```

Then open http://127.0.0.1:8000/

To activate the venv instead of using the full path:

```bash
source venv/bin/activate
python manage.py runserver
```

## Logins

| Where | URL | Credentials |
|---|---|---|
| Storefront / vendor dashboard | `/user/sign-in/` | `daraeng054@gmail.com` / `admin12345` |
| Django admin | `/admin/` | `admin` / `admin12345` |

Sign-in uses **email**, not username. Change this password before putting anything online.

The tutor's original account (`destiny` / `desphixs@gmail.com`) is still in the
database but its password is unknown.

## Key URLs

- `/` homepage, `/products/`, `/category/`, `/vendors/`
- `/dashboard/` customer dashboard (login required)
- `/useradmin/` vendor dashboard (login required) — note: **not** `/useradmin/dashboard/`
- `/admin/` Django admin

## What was changed to make it run

1. **Created `ecomprj/__init__.py`** — it was missing from the V2 download (it
   exists in V1). Without it, `ecomprj` is not a package and nothing imports.
2. **Rewrote `requirements.txt`** to list only what the code imports. The
   shipped file targeted Python 3.9 (`runtime.txt`) and could not install on
   this machine's Python 3.12: `Pillow==9.1.0` and `pandas==2.1.1` have no 3.12
   wheels, and `django-heroku` drags in `psycopg2`, which needs Postgres
   headers. It also listed `django-environ` while `settings.py` imports
   `environs`, and omitted `django-ckeditor`, which `core/migrations/0010`
   imports at load time.
3. **Applied one pending `taggit` migration** that ships with the newer
   django-taggit. Original database saved as `db.sqlite3.original-backup`.
4. **Created the `admin` superuser** listed above.

No application code (models, views, templates) was modified.

## Recreating the venv from scratch

This machine has no `python3-venv` package, so `python3 -m venv venv` fails on
the pip bootstrap step. Either install it (`sudo apt install python3.12-venv`)
or repeat the workaround used here:

```bash
python3 -m venv --without-pip venv
curl -sS -o /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py
./venv/bin/python /tmp/get-pip.py
./venv/bin/pip install -r requirements.txt
```

## Payments

Stripe and PayPal have been removed. Checkout offers **KHQR** and **cash on
delivery**, and neither needs an API key — but neither settles by itself:

- **KHQR** — the buyer scans the static QR in `static/assets/imgs/khqr/` and
  submits their transaction ID. The seller checks it against the bank statement
  and approves it at `/useradmin/order_detail/<id>/`.
- **Cash on delivery** — the seller marks the cash collected on the same page
  once the courier hands it over.

Approving is the only thing that sets `paid_status`.

## V1 vs V2

V2 is a strict superset. Compared to V1 it adds 9 `core` migrations (order
address/city/country, `oid`, shipping method, coupons), 2 `userauths`
migrations, `useradmin/decorators.py`, and renamed vendor-dashboard templates
(`dashboard-products.html` → `products.html`, etc.).

The only file in V1 and not in V2 is the empty `ecomprj/__init__.py` restored in
step 1. Keep `V1 - Complete Source Code` and the two `Frontend Template` folders
as reference material — the running site does not read from them.
