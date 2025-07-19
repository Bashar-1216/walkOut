# ===================================================================
# 1. Imports
# ===================================================================
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Dict, List
from . import models, schemas, database
from datetime import datetime, timedelta
import uuid
from jose import jwt, JWTError
import os
SECRET_KEY = os.environ.get("SECRET_KEY")
# ===================================================================
# 2. Configuration & App Instance
# ===================================================================
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Create database tables on startup
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="WalkOut Store API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# ===================================================================
# 3. WebSocket Connection Manager
# ===================================================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, session_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"WebSocket connected for session {session_id}")

    def disconnect(self, session_id: int):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        print(f"WebSocket disconnected for session {session_id}")

    async def send_cart_update(self, session_id: int, cart_data: dict):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(cart_data)
            print(f"Sent cart update to session {session_id}")

manager = ConnectionManager()

# ===================================================================
# 4. Auth Helper Functions & Dependencies
# ===================================================================
bearer_scheme = HTTPBearer()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(database.get_db)):
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

# ===================================================================
# 5. API Endpoints
# ===================================================================

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Welcome to WalkOut Store API!"}

@app.websocket("/ws/cart/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: int):
    await manager.connect(session_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(session_id)

@app.post("/auth/register", status_code=status.HTTP_201_CREATED, response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    existing_user = db.query(models.User).filter(models.User.phone_number == user.phone_number).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone number already registered.")
    
    new_user = models.User(phone_number=user.phone_number)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    print(f"--- OTP for {user.phone_number} is: 1234 ---")
    return new_user

@app.post("/auth/verify", response_model=schemas.Token)
def verify_user(verification_data: schemas.UserVerify, db: Session = Depends(database.get_db)):
    dummy_otp = "1234"
    user = db.query(models.User).filter(models.User.phone_number == verification_data.phone_number).first()
    
    if not user or verification_data.otp_code != dummy_otp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid phone number or OTP code.")
    
    access_token = create_access_token(data={"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.get("/products", response_model=List[schemas.ProductResponse])
def get_products(db: Session = Depends(database.get_db)):
    products = db.query(models.Product).all()
    if not products:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No products found.")
    return products

@app.post("/sessions/start", status_code=status.HTTP_201_CREATED, response_model=schemas.SessionResponse)
def start_shopping_session(session_data: schemas.SessionCreate, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == session_data.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    
    active_session = db.query(models.Shopping_Session).filter(
        models.Shopping_Session.user_id == session_data.user_id,
        models.Shopping_Session.status == 'active'
    ).first()
    if active_session:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already has an active session.")
        
    new_session = models.Shopping_Session(user_id=session_data.user_id)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

@app.post("/sessions/{session_id}/cart/items", response_model=schemas.CartResponse)
async def add_item_to_cart(session_id: int, item: schemas.CartItemCreate, db: Session = Depends(database.get_db)):
    session = db.query(models.Shopping_Session).filter(models.Shopping_Session.id == session_id, models.Shopping_Session.status == 'active').first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Active session {session_id} not found")
    
    product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

    cart_item = db.query(models.Cart_Item).filter(models.Cart_Item.session_id == session_id, models.Cart_Item.product_id == item.product_id).first()
    if cart_item:
        cart_item.quantity += item.quantity
    else:
        new_cart_item = models.Cart_Item(session_id=session_id, product_id=item.product_id, quantity=item.quantity, price_at_pickup=product.price)
        db.add(new_cart_item)
    
    db.commit()

    cart_items_db = db.query(models.Cart_Item, models.Product.name).join(models.Product).filter(models.Cart_Item.session_id == session_id).all()
    response_items = [schemas.CartItemResponse(name=name, **ci.__dict__) for ci, name in cart_items_db]
    current_total = sum(i.quantity * i.price for i in response_items)
    updated_cart = schemas.CartResponse(session_id=session_id, items=response_items, current_total=round(current_total, 2))
    
    await manager.send_cart_update(session_id, updated_cart.model_dump())
    return updated_cart

@app.delete("/sessions/{session_id}/cart/items/{product_id}", response_model=schemas.CartResponse)
async def remove_item_from_cart(session_id: int, product_id: int, db: Session = Depends(database.get_db)):
    cart_item = db.query(models.Cart_Item).filter(models.Cart_Item.session_id == session_id, models.Cart_Item.product_id == product_id).first()
    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not in cart.")
    
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
    else:
        db.delete(cart_item)
    
    db.commit()

    cart_items_db = db.query(models.Cart_Item, models.Product.name).join(models.Product).filter(models.Cart_Item.session_id == session_id).all()
    response_items = [schemas.CartItemResponse(name=name, **ci.__dict__) for ci, name in cart_items_db]
    current_total = sum(i.quantity * i.price for i in response_items)
    updated_cart = schemas.CartResponse(session_id=session_id, items=response_items, current_total=round(current_total, 2))

    await manager.send_cart_update(session_id, updated_cart.model_dump())
    return updated_cart

@app.post("/sessions/{session_id}/checkout", response_model=schemas.ReceiptResponse)
def checkout(session_id: int, db: Session = Depends(database.get_db)):
    session = db.query(models.Shopping_Session).filter(models.Shopping_Session.id == session_id, models.Shopping_Session.status == 'active').first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active session not found.")
    
    cart_items = db.query(models.Cart_Item).filter(models.Cart_Item.session_id == session_id).all()
    if not cart_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty.")
    
    total_amount = round(sum(item.quantity * float(item.price_at_pickup) for item in cart_items), 2)
    
    print(f"--- Simulating Payment for user {session.user_id} with amount {total_amount} ---")
    dummy_transaction_id = f"txn_{uuid.uuid4()}"
    print(f"--- Payment Successful: {dummy_transaction_id} ---")

    new_receipt = models.Receipt(session_id=session_id, total_amount=total_amount, transaction_id=dummy_transaction_id)
    db.add(new_receipt)
    db.flush()

    receipt_details_for_response = []
    for item in cart_items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        subtotal = item.quantity * float(item.price_at_pickup)
        detail = models.Receipt_Details(receipt_id=new_receipt.id, product_name=product.name, quantity=item.quantity, price=item.price_at_pickup, subtotal=subtotal)
        db.add(detail)
        receipt_details_for_response.append(detail)

    session.status = 'completed'
    db.commit()
    db.refresh(new_receipt)
    
    return new_receipt




@app.get("/sessions/active", response_model=schemas.SessionResponse)
def get_active_session(db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    active_session = db.query(models.Shopping_Session).filter(
        models.Shopping_Session.user_id == current_user.id,
        models.Shopping_Session.status == 'active'
    ).first()
    
    if not active_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session found for this user.")
        
    return active_session  
    
      

@app.patch("/users/me/payment-token", response_model=schemas.UserResponse)
def update_payment_token(
    request: schemas.PaymentTokenUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    current_user.payment_token = request.payment_token
    db.commit()
    db.refresh(current_user)
    return current_user      
