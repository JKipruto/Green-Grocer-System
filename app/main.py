import os, json
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
from starlette.middleware.sessions import SessionMiddleware
from .database import Base, engine, get_db, SessionLocal
from .models import User, Product, Order, OrderItem
from .security import hash_password, verify_password
from .mpesa import initiate_stk_push

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Product).count() == 0:
            vendor = db.query(User).filter(User.email == "market@example.com").first()
            if not vendor:
                vendor = User(name="Green Market Demo", email="market@example.com",
                              password_hash=hash_password("Market123!"), role="vendor")
                db.add(vendor)
                db.commit()
                db.refresh(vendor)
            samples = [
                ("Avocados", "Fruits", "Creamy, farm-fresh avocados.", 30, 45, "https://images.unsplash.com/photo-1523049673857-eb18f1d7b578?w=800"),
                ("Red tomatoes", "Vegetables", "Juicy tomatoes for everyday cooking.", 20, 120, "https://images.unsplash.com/photo-1546094096-0df4bcaaa337?w=800"),
                ("Carrots", "Vegetables", "Crunchy, naturally sweet carrots.", 15, 80, "https://images.unsplash.com/photo-1445282768818-728615cc910a?w=800"),
                ("Fresh bananas", "Fruits", "Naturally sweet ripe bananas.", 10, 150, "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=800"),
                ("Spinach", "Leafy greens", "Fresh leafy greens, picked with care.", 25, 55, "https://images.unsplash.com/photo-1576045057995-568f588f82fb?w=800"),
                ("Red onions", "Vegetables", "A kitchen staple with rich flavour.", 12, 100, "https://images.unsplash.com/photo-1508747703725-719777637510?w=800"),
            ]
            for name, cat, desc, price, qty, img in samples:
                db.add(Product(vendor_id=vendor.id, name=name, category=cat, description=desc,
                               price=price, quantity=qty, image_url=img))
            db.commit()
    finally:
        db.close()
    yield

app = FastAPI(title="GreenBasket Grocer", version="1.0.0", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("APP_SECRET_KEY", "dev-only-change-this-secret"))
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

def current_user(request: Request, db: Session):
    uid = request.session.get("user_id")
    return db.query(User).filter(User.id == uid).first() if uid else None

def require_user(request: Request, db: Session, role=None):
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Please sign in.")
    if role and user.role != role:
        raise HTTPException(status_code=403, detail="You do not have permission to access this page.")
    return user

def page(request, name, **context):
    return templates.TemplateResponse(name, {"request": request, **context})

@app.get("/", response_class=HTMLResponse)
def home(request: Request, q: str = "", category: str = "", db: Session = Depends(get_db)):
    query = db.query(Product).filter(Product.quantity > 0)
    if q:
        query = query.filter(or_(Product.name.ilike(f"%{q}%"), Product.description.ilike(f"%{q}%")))
    if category:
        query = query.filter(Product.category == category)
    products = query.order_by(Product.name).all()
    categories = [r[0] for r in db.query(Product.category).distinct().all()]
    user = current_user(request, db)
    return page(request, "index.html", user=user, products=products, categories=categories, q=q, selected_category=category)

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return page(request, "auth.html", mode="register", error=None)

@app.post("/register")
def register(request: Request, name: str = Form(...), email: str = Form(...),
             password: str = Form(...), role: str = Form(...), db: Session = Depends(get_db)):
    email = email.strip().lower()
    if role not in ("vendor", "customer"):
        return page(request, "auth.html", mode="register", error="Choose a valid account type.")
    if len(password) < 8:
        return page(request, "auth.html", mode="register", error="Use a password with at least 8 characters.")
    if db.query(User).filter(User.email == email).first():
        return page(request, "auth.html", mode="register", error="That email is already registered. Please sign in.")
    user = User(name=name.strip(), email=email, password_hash=hash_password(password), role=role)
    db.add(user); db.commit()
    request.session["user_id"] = user.id
    return RedirectResponse("/vendor" if role == "vendor" else "/", status_code=303)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return page(request, "auth.html", mode="login", error=None)

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if not user or not verify_password(password, user.password_hash):
        return page(request, "auth.html", mode="login", error="Email or password is incorrect.")
    request.session["user_id"] = user.id
    return RedirectResponse("/vendor" if user.role == "vendor" else "/", status_code=303)

@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)

@app.get("/vendor", response_class=HTMLResponse)
def vendor_dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db, "vendor")
    products = db.query(Product).filter(Product.vendor_id == user.id).order_by(Product.id.desc()).all()
    orders = db.query(Order).join(OrderItem).join(Product, OrderItem.product_id == Product.id)\
        .filter(Product.vendor_id == user.id).distinct().order_by(Order.created_at.desc()).limit(30).all()
    return page(request, "vendor.html", user=user, products=products, orders=orders)

@app.post("/vendor/products")
def add_product(request: Request, name: str = Form(...), category: str = Form("Vegetables"),
                description: str = Form(""), price: float = Form(...), quantity: int = Form(...),
                image_url: str = Form(""), db: Session = Depends(get_db)):
    user = require_user(request, db, "vendor")
    if price <= 0 or quantity < 0:
        raise HTTPException(400, "Price must be positive and quantity cannot be negative.")
    db.add(Product(vendor_id=user.id, name=name.strip(), category=category.strip(),
                   description=description.strip(), price=price, quantity=quantity,
                   image_url=image_url.strip()))
    db.commit()
    return RedirectResponse("/vendor", status_code=303)

@app.post("/vendor/products/{product_id}/update")
def update_product(product_id: int, request: Request, name: str = Form(...),
                   category: str = Form(...), price: float = Form(...),
                   quantity: int = Form(...), db: Session = Depends(get_db)):
    user = require_user(request, db, "vendor")
    product = db.query(Product).filter(Product.id == product_id, Product.vendor_id == user.id).first()
    if not product: raise HTTPException(404, "Product not found.")
    if price <= 0 or quantity < 0: raise HTTPException(400, "Invalid price or stock quantity.")
    product.name, product.category, product.price, product.quantity = name.strip(), category.strip(), price, quantity
    db.commit()
    return RedirectResponse("/vendor", status_code=303)

@app.post("/vendor/products/{product_id}/delete")
def delete_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db, "vendor")
    product = db.query(Product).filter(Product.id == product_id, Product.vendor_id == user.id).first()
    if product:
        db.delete(product); db.commit()
    return RedirectResponse("/vendor", status_code=303)

@app.get("/api/products")
def products_api(q: str = "", db: Session = Depends(get_db)):
    rows = db.query(Product).filter(Product.quantity > 0)
    if q: rows = rows.filter(Product.name.ilike(f"%{q}%"))
    return [{"id":p.id,"name":p.name,"price":p.price,"quantity":p.quantity} for p in rows.limit(50).all()]

@app.post("/api/checkout")
async def checkout(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db, "customer")
    data = await request.json()
    items = data.get("items", [])
    method = data.get("payment_method", "mpesa")
    phone = (data.get("phone") or "").strip()
    if method not in ("mpesa", "delivery"):
        raise HTTPException(400, "Invalid payment method.")
    if method == "mpesa" and not phone:
        raise HTTPException(400, "Enter the M-Pesa phone number.")
    if not items:
        raise HTTPException(400, "Your cart is empty.")
    # Validate every line and compute the amount on the server; never trust browser totals.
    validated, total = [], 0.0
    for item in items:
        product = db.query(Product).filter(Product.id == int(item.get("id"))).with_for_update().first()
        qty = int(item.get("quantity", 0))
        if not product or qty < 1 or qty > product.quantity:
            raise HTTPException(400, f"Not enough stock for {product.name if product else 'a selected item'}.")
        validated.append((product, qty))
        total += product.price * qty
    order = Order(customer_id=user.id, total=round(total, 2), payment_method=method,
                  payment_status="Pending" if method == "mpesa" else "Pay on delivery")
    db.add(order); db.flush()
    for product, qty in validated:
        product.quantity -= qty
        db.add(OrderItem(order_id=order.id, product_id=product.id, product_name=product.name,
                         unit_price=product.price, quantity=qty))
    db.commit()
    if method == "mpesa":
        try:
            result = initiate_stk_push(phone, total, f"ORDER{order.id}", "GreenBasket order")
            order.mpesa_checkout_id = result.get("CheckoutRequestID", "")
            db.commit()
            return {"ok": True, "message": result.get("CustomerMessage", "Check your phone and enter your M-Pesa PIN."),
                    "order_id": order.id, "total": total}
        except Exception as exc:
            # Order remains recorded and stock reserved; customer can contact the vendor to arrange payment.
            order.payment_status = "M-Pesa initiation failed"
            db.commit()
            return JSONResponse(status_code=502, content={"ok": False, "order_id": order.id,
                "message": f"Order #{order.id} was saved, but M-Pesa could not be started. Check Daraja settings or contact the grocer."})
    return {"ok": True, "message": f"Order #{order.id} placed. Pay on delivery selected.", "order_id": order.id, "total": total}

@app.post("/api/mpesa/callback")
async def mpesa_callback(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    body = payload.get("Body", {}).get("stkCallback", {})
    checkout_id = body.get("CheckoutRequestID")
    result_code = body.get("ResultCode")
    order = db.query(Order).filter(Order.mpesa_checkout_id == checkout_id).first()
    if order and result_code == 0:
        order.payment_status = "Paid"
        order.status = "Confirmed"
        db.commit()
    elif order:
        order.payment_status = "Failed"
        db.commit()
    return {"ResultCode": 0, "ResultDesc": "Accepted"}

@app.get("/orders", response_class=HTMLResponse)
def my_orders(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db, "customer")
    orders = db.query(Order).filter(Order.customer_id == user.id).order_by(Order.created_at.desc()).all()
    return page(request, "orders.html", user=user, orders=orders)

@app.get("/health")
def health():
    return {"status": "ok"}
