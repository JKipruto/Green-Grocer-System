# GreenBasket System Documentation

## 1. Introduction

GreenBasket is a web-based green-grocer management and online shopping system. It connects vendors (grocers) who maintain a catalogue and stock quantities with customers who browse products, manage a cart and place orders.

## 2. Technology stack

- **Backend:** Python 3, FastAPI
- **Database:** SQLite using SQLAlchemy ORM
- **Frontend:** HTML5, CSS3, JavaScript and Jinja2 templates
- **Authentication:** Starlette signed sessions and bcrypt password hashing
- **Payments:** Safaricom Daraja M-Pesa STK Push integration
- **Server:** Uvicorn

## 3. User roles

### Vendor / Grocer
A vendor can register, sign in, add products, edit product details, change prices, update available quantities and delete products. The dashboard shows catalogue totals, stock levels and recent orders.

### Customer
A customer can register and sign in, browse and search the catalogue, filter by category, add products to a basket, change quantities, remove products, view the calculated total, choose M-Pesa or pay on delivery, and review order history.

## 4. Main workflow

1. A visitor creates an account and chooses **Customer** or **Vendor**.
2. The system stores the account with a bcrypt password hash.
3. A vendor adds products and stock to the SQLite database.
4. Customers see available products and add them to a browser-side cart.
5. At checkout, the backend reloads product prices and quantities from the database, validates stock and calculates the total.
6. The backend creates an order and order-item records, then reserves the requested stock.
7. For M-Pesa, the backend requests an STK Push and the customer approves it on their phone. A Daraja callback marks the payment as paid when the provider reports success.
8. For pay on delivery, the order is recorded with that payment option.
9. Customers can inspect their order history; vendors can review recent marketplace orders.

## 5. Database design

| Table | Important fields | Purpose |
|---|---|---|
| `users` | id, name, email, password_hash, role | Stores vendor and customer accounts |
| `products` | id, vendor_id, name, category, price, quantity, image_url | Product catalogue and stock |
| `orders` | id, customer_id, total, status, payment_method, payment_status | Order header and payment tracking |
| `order_items` | id, order_id, product_id, product_name, unit_price, quantity | Snapshot of products purchased |

Relationships:
- One vendor can own many products.
- One customer can place many orders.
- One order contains many order items.
- Each order item references a product and stores the product name and unit price at purchase time.

## 6. Payment options

### M-Pesa
The app uses the Daraja STK Push endpoint. The customer provides a phone number, the server requests an STK Push, and the customer enters their M-Pesa PIN on their handset. The Daraja callback updates the order's payment status.

Required configuration is stored in `.env`:
- `MPESA_ENV`
- `MPESA_CONSUMER_KEY`
- `MPESA_CONSUMER_SECRET`
- `MPESA_SHORTCODE`
- `MPESA_PASSKEY`
- `MPESA_CALLBACK_URL`

Never commit real credentials to source control. A publicly reachable HTTPS callback URL is required for end-to-end payment testing.

### Pay on delivery
Customers may choose cash/M-Pesa on delivery. The order is saved with `Pay on delivery` as its payment status. The vendor can see the selected method in the order list.

## 7. Security and validation

- Passwords are hashed; plaintext passwords are not stored.
- Role checks protect vendor and customer routes.
- Product updates are restricted to the vendor who owns the product.
- Checkout validates stock and calculates prices on the server.
- The backend rejects invalid quantities and unavailable stock.

Additional controls required before production include CSRF protection, secure cookie flags, rate limiting, callback verification, robust stock reservation expiry, audit logging and security testing.

## 8. Installation and execution

Follow the complete commands in the project `README.md`. In brief:

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Browse to `http://127.0.0.1:8000`. The database and sample catalogue are created automatically on first startup.

Demo vendor:
- `market@example.com`
- `Market123!`

Register a customer account to test the shopping flow.

## 9. Limitations and future enhancements

- Add delivery addresses, delivery fee calculation and delivery tracking.
- Add pagination, product image upload and category administration.
- Add vendor-scoped order details and fulfilment status updates.
- Add cancellation, refund and stock restoration logic.
- Add robust payment callback validation and idempotency.
- Add automated tests, Alembic migrations and production database deployment.
- Add email/SMS notifications and downloadable sales reports.

## 10. Conclusion

GreenBasket provides the core workflow for a small online grocery marketplace: account registration, role-based dashboards, product and inventory management, customer shopping cart, order creation and payment selection. It is suitable as a foundation for a school project, prototype or further development, with the production safeguards described above to be completed before handling real customer payments.
