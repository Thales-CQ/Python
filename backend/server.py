from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "sua-chave-secreta-aqui"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    SALESPERSON = "salesperson"

class TransactionType(str, Enum):
    ENTRADA = "entrada"
    SAIDA = "saida"

class PaymentMethod(str, Enum):
    DINHEIRO = "dinheiro"
    CARTAO = "cartao"
    PIX = "pix"
    BOLETO = "boleto"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    role: UserRole
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: UserRole

class UserLogin(BaseModel):
    username: str
    password: str

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    price: float
    description: Optional[str] = None
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProductCreate(BaseModel):
    name: str
    price: float
    description: Optional[str] = None

class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: TransactionType
    amount: float
    description: str
    payment_method: PaymentMethod
    product_id: Optional[str] = None
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TransactionCreate(BaseModel):
    type: TransactionType
    amount: float
    description: str
    payment_method: PaymentMethod
    product_id: Optional[str] = None

class Client(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    phone: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ClientCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None

class Bill(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    amount: float
    description: str
    due_date: datetime
    paid: bool = False
    paid_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class BillCreate(BaseModel):
    client_id: str
    amount: float
    description: str
    due_date: datetime

# Authentication functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    user = await db.users.find_one({"username": username})
    if user is None:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    
    return User(**user)

# Initialize admin user
async def create_admin_user():
    admin_exists = await db.users.find_one({"username": "admin"})
    if not admin_exists:
        admin_user = {
            "id": str(uuid.uuid4()),
            "username": "admin",
            "email": "admin@sistema.com",
            "password": get_password_hash("admin123"),
            "role": "admin",
            "active": True,
            "created_at": datetime.utcnow()
        }
        await db.users.insert_one(admin_user)
        print("Usuário admin criado: admin/admin123")

# Routes
@api_router.post("/register")
async def register(user: UserCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para criar usuários")
    
    # Check if user exists
    existing_user = await db.users.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Usuário já existe")
    
    # Create user
    user_dict = user.dict()
    user_dict["password"] = get_password_hash(user_dict["password"])
    user_dict["id"] = str(uuid.uuid4())
    user_dict["active"] = True
    user_dict["created_at"] = datetime.utcnow()
    
    await db.users.insert_one(user_dict)
    return {"message": "Usuário criado com sucesso"}

@api_router.post("/login")
async def login(user: UserLogin):
    # Find user
    db_user = await db.users.find_one({"username": user.username})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    if not db_user["active"]:
        raise HTTPException(status_code=401, detail="Usuário inativo")
    
    # Create token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user["username"]}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": db_user["id"],
            "username": db_user["username"],
            "email": db_user["email"],
            "role": db_user["role"]
        }
    }

@api_router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

@api_router.get("/users")
async def get_users(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão")
    
    users = await db.users.find().to_list(1000)
    return [User(**user) for user in users]

# Products
@api_router.post("/products")
async def create_product(product: ProductCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para criar produtos")
    
    product_dict = product.dict()
    product_dict["id"] = str(uuid.uuid4())
    product_dict["active"] = True
    product_dict["created_at"] = datetime.utcnow()
    
    await db.products.insert_one(product_dict)
    return Product(**product_dict)

@api_router.get("/products")
async def get_products(current_user: User = Depends(get_current_user)):
    products = await db.products.find({"active": True}).to_list(1000)
    return [Product(**product) for product in products]

# Transactions
@api_router.post("/transactions")
async def create_transaction(transaction: TransactionCreate, current_user: User = Depends(get_current_user)):
    transaction_dict = transaction.dict()
    transaction_dict["id"] = str(uuid.uuid4())
    transaction_dict["user_id"] = current_user.id
    transaction_dict["created_at"] = datetime.utcnow()
    
    await db.transactions.insert_one(transaction_dict)
    return Transaction(**transaction_dict)

@api_router.get("/transactions")
async def get_transactions(current_user: User = Depends(get_current_user)):
    transactions = await db.transactions.find().sort("created_at", -1).to_list(1000)
    return [Transaction(**transaction) for transaction in transactions]

@api_router.get("/transactions/summary")
async def get_transactions_summary(current_user: User = Depends(get_current_user)):
    # Get current month transactions
    now = datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    transactions = await db.transactions.find({
        "created_at": {"$gte": start_of_month}
    }).to_list(1000)
    
    total_entrada = sum(t["amount"] for t in transactions if t["type"] == "entrada")
    total_saida = sum(t["amount"] for t in transactions if t["type"] == "saida")
    saldo = total_entrada - total_saida
    
    return {
        "total_entrada": total_entrada,
        "total_saida": total_saida,
        "saldo": saldo,
        "total_transactions": len(transactions)
    }

# Clients
@api_router.post("/clients")
async def create_client(client: ClientCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para criar clientes")
    
    client_dict = client.dict()
    client_dict["id"] = str(uuid.uuid4())
    client_dict["created_at"] = datetime.utcnow()
    
    await db.clients.insert_one(client_dict)
    return Client(**client_dict)

@api_router.get("/clients")
async def get_clients(current_user: User = Depends(get_current_user)):
    clients = await db.clients.find().to_list(1000)
    return [Client(**client) for client in clients]

# Bills
@api_router.post("/bills")
async def create_bill(bill: BillCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para criar boletos")
    
    bill_dict = bill.dict()
    bill_dict["id"] = str(uuid.uuid4())
    bill_dict["paid"] = False
    bill_dict["created_at"] = datetime.utcnow()
    
    await db.bills.insert_one(bill_dict)
    return Bill(**bill_dict)

@api_router.get("/bills")
async def get_bills(current_user: User = Depends(get_current_user)):
    bills = await db.bills.find().sort("due_date", 1).to_list(1000)
    return [Bill(**bill) for bill in bills]

@api_router.get("/bills/pending")
async def get_pending_bills(current_user: User = Depends(get_current_user)):
    bills = await db.bills.find({"paid": False}).sort("due_date", 1).to_list(1000)
    return [Bill(**bill) for bill in bills]

@api_router.put("/bills/{bill_id}/pay")
async def pay_bill(bill_id: str, current_user: User = Depends(get_current_user)):
    result = await db.bills.update_one(
        {"id": bill_id},
        {"$set": {"paid": True, "paid_date": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")
    
    return {"message": "Boleto marcado como pago"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    await create_admin_user()

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()