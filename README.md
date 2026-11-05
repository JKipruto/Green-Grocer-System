# GreenBasket — Green Grocer Management & Shopping System

A full-stack starter application built with **Python, FastAPI, SQLite, HTML, CSS and vanilla JavaScript**.

## Features

- Customer and vendor registration and sign-in (email + password).
- Password hashing with bcrypt and role-based page/API access.
- Vendor catalogue: add, edit, delete products and update stock.
- Customer product browsing, search and category filtering.
- Browser-persisted cart with quantity controls and remove action.
- Server-side price calculation and stock validation at checkout.
- Order history and vendor order overview.
- M-Pesa Daraja STK Push integration scaffold, plus pay-on-delivery option.
- Responsive GreenBasket storefront with produce photography.

## Run locally

Python 3.10+ is recommended.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 2. Install packages
pip install -r requirements.txt

# 3. Create your environment file
cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env

# 4. Set APP_SECRET_KEY in .env to a long random value.
# Leave Daraja values empty to test the rest of the application.

# 5. Start the server from the project root
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

The SQLite database (`green_grocer.db`) and sample products are created automatically on first startup.

### Demo vendor account

- Email: `market@example.com`
- Password: `Market123!`

Register a separate customer account to test shopping and checkout. Change or remove the demo account before deploying publicly.

## M-Pesa setup (Daraja)

1. Create an app in Safaricom Daraja and obtain the Consumer Key and Consumer Secret.
2. Configure a PayBill/Till shortcode and the matching STK Push passkey.
3. Set `MPESA_ENV=sandbox` for testing, then fill in the Daraja values in `.env`.
4. Deploy the app behind HTTPS and set `MPESA_CALLBACK_URL` to the public URL ending in `/api/mpesa/callback`.
5. Test with the Daraja sandbox test credentials and test phone numbers. Move to production only after Safaricom approval and live credentials are issued.

The checkout endpoint calculates the amount from SQLite; it does not trust the amount sent by the browser. A successful Daraja callback changes the order payment status to `Paid`. Pay-on-delivery is also available.

## Important production work

This is a learning/starter implementation, not a fully audited commerce platform. Before public deployment:

- Use a strong unique `APP_SECRET_KEY`, HTTPS, secure cookie settings, CSRF protection, rate limiting and login throttling.
- Add phone-number normalization/validation (Kenyan format), address/delivery zones and delivery pricing.
- Verify Daraja callback authenticity and reconcile callbacks using `MerchantRequestID` / `CheckoutRequestID`; store raw provider references and idempotently process callbacks.
- Add transaction-safe stock reservation/expiry and a refund/stock-restoration workflow if payment fails or times out. The sample reserves stock when an order is created.
- Use database migrations (Alembic), backups, monitoring and a production database if traffic grows.
- Add vendor-specific order line views and order fulfilment statuses.
- Review privacy, consumer protection, tax and payment compliance obligations.

## Project structure

```text
green_grocer_system/
├── app/
│   ├── main.py             # FastAPI routes and checkout workflow
│   ├── models.py           # SQLAlchemy database models
│   ├── database.py         # SQLite connection and session
│   ├── security.py         # Password hashing and verification
│   ├── mpesa.py            # Safaricom Daraja STK Push client
│   ├── templates/          # Jinja2 HTML pages
│   └── static/             # CSS and browser JavaScript
├── docs/
│   └── SYSTEM_DOCUMENTATION.md
├── .env.example
├── requirements.txt
└── README.md
```

## Useful endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Product catalogue |
| GET/POST | `/register` | Create customer/vendor account |
| GET/POST | `/login` | Sign in |
| POST | `/logout` | Sign out |
| GET | `/vendor` | Vendor dashboard |
| POST | `/vendor/products` | Add product |
| POST | `/vendor/products/{id}/update` | Update product |
| POST | `/vendor/products/{id}/delete` | Delete product |
| GET | `/orders` | Customer order history |
| POST | `/api/checkout` | Create order and start payment |
| POST | `/api/mpesa/callback` | Daraja payment callback |
| GET | `/health` | Health check |

Interactive API documentation is available at `/docs`.
