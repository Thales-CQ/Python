from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
from enum import Enum
from validate_docbr import CPF
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
import re

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

# CPF validator
cpf_validator = CPF()

# Utility functions
def to_upper_case(value: str) -> str:
    """Convert string to uppercase"""
    return value.upper().strip() if value else value

def validate_cpf(cpf: str) -> bool:
    """Validate CPF"""
    if not cpf:
        return False
    # Remove formatting
    cpf_clean = re.sub(r'[^\d]', '', cpf)
    return cpf_validator.validate(cpf_clean)

def format_cpf(cpf: str) -> str:
    """Format CPF with dots and dash"""
    if not cpf:
        return cpf
    cpf_clean = re.sub(r'[^\d]', '', cpf)
    if len(cpf_clean) == 11:
        return f"{cpf_clean[:3]}.{cpf_clean[3:6]}.{cpf_clean[6:9]}-{cpf_clean[9:]}"
    return cpf

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

class ActivityType(str, Enum):
    USER_CREATED = "user_created"
    USER_DEACTIVATED = "user_deactivated"
    USER_ACTIVATED = "user_activated"
    TRANSACTION_CREATED = "transaction_created"
    TRANSACTION_MODIFIED = "transaction_modified"
    TRANSACTION_CANCELLED = "transaction_cancelled"
    PRODUCT_CREATED = "product_created"
    PRODUCT_MODIFIED = "product_modified"
    BILL_CREATED = "bill_created"
    BILL_PAID = "bill_paid"
    BILL_CANCELLED = "bill_cancelled"
    PAYMENT_CANCELLED = "payment_cancelled"
    LOGIN = "login"

class BillStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    role: UserRole
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    
    @validator('username', 'email', pre=True)
    def uppercase_fields(cls, v):
        return to_upper_case(v)

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: UserRole
    
    @validator('username', 'email', pre=True)
    def uppercase_fields(cls, v):
        return to_upper_case(v)

class UserUpdate(BaseModel):
    active: bool

class UserLogin(BaseModel):
    username: str
    password: str
    
    @validator('username', pre=True)
    def uppercase_username(cls, v):
        return to_upper_case(v)

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    name: str
    price: float
    description: Optional[str] = None
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    
    @validator('code', 'name', 'description', pre=True)
    def uppercase_fields(cls, v):
        return to_upper_case(v)

class ProductCreate(BaseModel):
    code: str
    name: str
    price: float
    description: Optional[str] = None
    
    @validator('code', 'name', 'description', pre=True)
    def uppercase_fields(cls, v):
        return to_upper_case(v)

class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: TransactionType
    amount: float
    description: str
    payment_method: PaymentMethod
    product_id: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    user_id: str
    user_name: str
    cancelled: bool = False
    cancelled_by: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('description', pre=True)
    def uppercase_description(cls, v):
        return to_upper_case(v)

class TransactionCreate(BaseModel):
    type: TransactionType
    amount: float
    description: str
    payment_method: PaymentMethod
    product_id: Optional[str] = None
    
    @validator('description', pre=True)
    def uppercase_description(cls, v):
        return to_upper_case(v)

class Client(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    cpf: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    
    @validator('name', 'email', 'address', pre=True)
    def uppercase_fields(cls, v):
        return to_upper_case(v)
    
    @validator('cpf')
    def validate_cpf_field(cls, v):
        if not validate_cpf(v):
            raise ValueError('CPF inválido')
        return format_cpf(v)

class ClientCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    cpf: str
    
    @validator('name', 'email', 'address', pre=True)
    def uppercase_fields(cls, v):
        return to_upper_case(v)
    
    @validator('cpf')
    def validate_cpf_field(cls, v):
        if not validate_cpf(v):
            raise ValueError('CPF inválido')
        return format_cpf(v)

class BillInstallment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bill_id: str
    installment_number: int
    amount: float
    due_date: datetime
    status: BillStatus = BillStatus.PENDING
    paid_date: Optional[datetime] = None
    payment_method: Optional[PaymentMethod] = None
    paid_by: Optional[str] = None
    cancelled: bool = False
    cancelled_by: Optional[str] = None
    cancelled_at: Optional[datetime] = None

class Bill(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    client_name: str
    client_cpf: str
    total_amount: float
    description: str
    installments: int
    installment_amount: float
    cancelled: bool = False
    cancelled_by: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    
    @validator('description', pre=True)
    def uppercase_description(cls, v):
        return to_upper_case(v)

class BillCreate(BaseModel):
    client_id: str
    total_amount: float
    description: str
    installments: int
    
    @validator('description', pre=True)
    def uppercase_description(cls, v):
        return to_upper_case(v)

class BillPayment(BaseModel):
    payment_method: PaymentMethod

class ActivityLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    activity_type: ActivityType
    description: str
    user_id: str
    user_name: str
    details: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

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

async def log_activity(activity_type: ActivityType, description: str, user_id: str, user_name: str, details: Optional[dict] = None):
    """Log user activity"""
    activity = ActivityLog(
        activity_type=activity_type,
        description=description,
        user_id=user_id,
        user_name=user_name,
        details=details
    )
    await db.activity_logs.insert_one(activity.dict())

# Initialize admin user
async def create_admin_user():
    admin_exists = await db.users.find_one({"username": "ADMIN"})
    if not admin_exists:
        admin_user = {
            "id": str(uuid.uuid4()),
            "username": "ADMIN",
            "email": "ADMIN@SISTEMA.COM",
            "password": get_password_hash("admin123"),
            "role": "admin",
            "active": True,
            "created_at": datetime.utcnow(),
            "created_by": "system"
        }
        await db.users.insert_one(admin_user)
        print("Usuário admin criado: ADMIN/admin123")

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
    user_dict["created_by"] = current_user.id
    
    await db.users.insert_one(user_dict)
    
    # Log activity
    await log_activity(
        ActivityType.USER_CREATED,
        f"Usuário '{user.username}' criado com role '{user.role}'",
        current_user.id,
        current_user.username,
        {"new_user": user.username, "role": user.role}
    )
    
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
    
    # Log activity
    await log_activity(
        ActivityType.LOGIN,
        f"Login realizado",
        db_user["id"],
        db_user["username"]
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

@api_router.put("/users/{user_id}")
async def update_user(user_id: str, user_update: UserUpdate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para modificar usuários")
    
    # Find user
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Update user
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": user_update.dict()}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Log activity
    action = "ativado" if user_update.active else "desativado"
    await log_activity(
        ActivityType.USER_ACTIVATED if user_update.active else ActivityType.USER_DEACTIVATED,
        f"Usuário '{user['username']}' {action}",
        current_user.id,
        current_user.username,
        {"target_user": user['username'], "action": action}
    )
    
    return {"message": f"Usuário {action} com sucesso"}

# Products
@api_router.post("/products")
async def create_product(product: ProductCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para criar produtos")
    
    # Check if product code exists
    existing_product = await db.products.find_one({"code": product.code})
    if existing_product:
        raise HTTPException(status_code=400, detail="Código do produto já existe")
    
    product_dict = product.dict()
    product_dict["id"] = str(uuid.uuid4())
    product_dict["active"] = True
    product_dict["created_at"] = datetime.utcnow()
    product_dict["created_by"] = current_user.id
    
    await db.products.insert_one(product_dict)
    
    # Log activity
    await log_activity(
        ActivityType.PRODUCT_CREATED,
        f"Produto '{product.code} - {product.name}' criado",
        current_user.id,
        current_user.username,
        {"product_code": product.code, "product_name": product.name, "price": product.price}
    )
    
    return Product(**product_dict)

@api_router.get("/products")
async def get_products(current_user: User = Depends(get_current_user)):
    products = await db.products.find({"active": True}).to_list(1000)
    return [Product(**product) for product in products]

@api_router.get("/products/search")
async def search_products(q: str = Query(..., min_length=1), current_user: User = Depends(get_current_user)):
    """Search products by code or name"""
    query = {
        "active": True,
        "$or": [
            {"code": {"$regex": q.upper(), "$options": "i"}},
            {"name": {"$regex": q.upper(), "$options": "i"}}
        ]
    }
    products = await db.products.find(query).to_list(50)
    return [Product(**product) for product in products]

# Transactions
@api_router.post("/transactions")
async def create_transaction(transaction: TransactionCreate, current_user: User = Depends(get_current_user)):
    # Validate payment method for saida
    if transaction.type == TransactionType.SAIDA and transaction.payment_method not in [PaymentMethod.DINHEIRO, PaymentMethod.PIX]:
        raise HTTPException(status_code=400, detail="Saída permitida apenas com dinheiro ou PIX")
    
    transaction_dict = transaction.dict()
    transaction_dict["id"] = str(uuid.uuid4())
    transaction_dict["user_id"] = current_user.id
    transaction_dict["user_name"] = current_user.username
    transaction_dict["cancelled"] = False
    transaction_dict["created_at"] = datetime.utcnow()
    
    # Get product details if product_id is provided
    if transaction.product_id:
        product = await db.products.find_one({"id": transaction.product_id})
        if product:
            transaction_dict["product_code"] = product["code"]
            transaction_dict["product_name"] = product["name"]
    
    await db.transactions.insert_one(transaction_dict)
    
    # Log activity
    await log_activity(
        ActivityType.TRANSACTION_CREATED,
        f"Transação de {transaction.type} criada - R$ {transaction.amount:.2f}",
        current_user.id,
        current_user.username,
        {
            "type": transaction.type,
            "amount": transaction.amount,
            "payment_method": transaction.payment_method,
            "description": transaction.description
        }
    )
    
    return Transaction(**transaction_dict)

@api_router.get("/transactions")
async def get_transactions(
    current_user: User = Depends(get_current_user),
    search: Optional[str] = Query(None),
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    transaction_type: Optional[TransactionType] = Query(None),
    payment_method: Optional[PaymentMethod] = Query(None)
):
    """Get transactions with filters"""
    query = {"cancelled": False}
    
    # Build filters
    if search:
        query["$or"] = [
            {"description": {"$regex": search.upper(), "$options": "i"}},
            {"user_name": {"$regex": search.upper(), "$options": "i"}},
            {"product_name": {"$regex": search.upper(), "$options": "i"}}
        ]
    
    if month and year:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        query["created_at"] = {"$gte": start_date, "$lt": end_date}
    
    if transaction_type:
        query["type"] = transaction_type
    
    if payment_method:
        query["payment_method"] = payment_method
    
    transactions = await db.transactions.find(query).sort("created_at", -1).to_list(1000)
    
    # Handle legacy transactions without user_name field
    for transaction in transactions:
        if 'user_name' not in transaction:
            transaction['user_name'] = 'SISTEMA'
    
    return [Transaction(**transaction) for transaction in transactions]

@api_router.delete("/transactions/{transaction_id}")
async def cancel_transaction(transaction_id: str, current_user: User = Depends(get_current_user)):
    """Cancel a transaction (only admin and manager)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para cancelar transações")
    
    # Find transaction
    transaction = await db.transactions.find_one({"id": transaction_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    
    if transaction.get("cancelled", False):
        raise HTTPException(status_code=400, detail="Transação já cancelada")
    
    # Update transaction
    result = await db.transactions.update_one(
        {"id": transaction_id},
        {"$set": {
            "cancelled": True,
            "cancelled_by": current_user.id,
            "cancelled_at": datetime.utcnow()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    
    # Log activity
    await log_activity(
        ActivityType.TRANSACTION_CANCELLED,
        f"Transação cancelada - R$ {transaction['amount']:.2f} - {transaction['description']}",
        current_user.id,
        current_user.username,
        {
            "transaction_id": transaction_id,
            "amount": transaction['amount'],
            "original_user": transaction.get('user_name', 'N/A')
        }
    )
    
    return {"message": "Transação cancelada com sucesso"}

@api_router.get("/transactions/summary")
async def get_transactions_summary(current_user: User = Depends(get_current_user)):
    # Get current month transactions
    now = datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    transactions = await db.transactions.find({
        "created_at": {"$gte": start_of_month},
        "cancelled": False
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
    
    # Check if CPF already exists
    existing_client = await db.clients.find_one({"cpf": client.cpf})
    if existing_client:
        raise HTTPException(status_code=400, detail="CPF já cadastrado")
    
    client_dict = client.dict()
    client_dict["id"] = str(uuid.uuid4())
    client_dict["created_at"] = datetime.utcnow()
    client_dict["created_by"] = current_user.id
    
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
    
    # Get client info
    client = await db.clients.find_one({"id": bill.client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Create bill
    bill_id = str(uuid.uuid4())
    installment_amount = bill.total_amount / bill.installments
    
    bill_dict = {
        "id": bill_id,
        "client_id": bill.client_id,
        "client_name": client["name"],
        "client_cpf": client["cpf"],
        "total_amount": bill.total_amount,
        "description": bill.description,
        "installments": bill.installments,
        "installment_amount": installment_amount,
        "cancelled": False,
        "created_at": datetime.utcnow(),
        "created_by": current_user.id
    }
    
    await db.bills.insert_one(bill_dict)
    
    # Create installments
    installments = []
    for i in range(bill.installments):
        due_date = datetime.utcnow() + timedelta(days=30 * (i + 1))
        installment = {
            "id": str(uuid.uuid4()),
            "bill_id": bill_id,
            "installment_number": i + 1,
            "amount": installment_amount,
            "due_date": due_date,
            "status": "pending",
            "cancelled": False
        }
        installments.append(installment)
    
    await db.bill_installments.insert_many(installments)
    
    # Log activity
    await log_activity(
        ActivityType.BILL_CREATED,
        f"Boleto criado para {client['name']} - R$ {bill.total_amount:.2f} em {bill.installments}x",
        current_user.id,
        current_user.username,
        {
            "client_name": client["name"],
            "client_cpf": client["cpf"],
            "total_amount": bill.total_amount,
            "installments": bill.installments
        }
    )
    
    return Bill(**bill_dict)

@api_router.get("/bills")
async def get_bills(current_user: User = Depends(get_current_user)):
    bills = await db.bills.find({"cancelled": False}).sort("created_at", -1).to_list(1000)
    return [Bill(**bill) for bill in bills]

@api_router.get("/bills/{bill_id}/installments")
async def get_bill_installments(bill_id: str, current_user: User = Depends(get_current_user)):
    installments = await db.bill_installments.find({
        "bill_id": bill_id,
        "cancelled": False
    }).sort("installment_number", 1).to_list(1000)
    return [BillInstallment(**installment) for installment in installments]

@api_router.put("/installments/{installment_id}/pay")
async def pay_installment(installment_id: str, payment: BillPayment, current_user: User = Depends(get_current_user)):
    # Find installment
    installment = await db.bill_installments.find_one({"id": installment_id})
    if not installment:
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
    
    if installment["status"] == "paid":
        raise HTTPException(status_code=400, detail="Parcela já foi paga")
    
    if installment.get("cancelled", False):
        raise HTTPException(status_code=400, detail="Parcela cancelada")
    
    # Update installment
    result = await db.bill_installments.update_one(
        {"id": installment_id},
        {"$set": {
            "status": "paid",
            "paid_date": datetime.utcnow(),
            "payment_method": payment.payment_method,
            "paid_by": current_user.id
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
    
    # Get bill info for logging
    bill = await db.bills.find_one({"id": installment["bill_id"]})
    
    # Log activity
    await log_activity(
        ActivityType.BILL_PAID,
        f"Parcela {installment['installment_number']} paga - {bill['client_name']} - R$ {installment['amount']:.2f}",
        current_user.id,
        current_user.username,
        {
            "client_name": bill["client_name"],
            "client_cpf": bill["client_cpf"],
            "installment_number": installment["installment_number"],
            "amount": installment["amount"],
            "payment_method": payment.payment_method
        }
    )
    
    return {"message": "Parcela paga com sucesso"}

@api_router.delete("/installments/{installment_id}/cancel")
async def cancel_installment_payment(installment_id: str, current_user: User = Depends(get_current_user)):
    """Cancel installment payment (only admin and manager)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para cancelar pagamentos")
    
    # Find installment
    installment = await db.bill_installments.find_one({"id": installment_id})
    if not installment:
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
    
    if installment["status"] != "paid":
        raise HTTPException(status_code=400, detail="Parcela não está paga")
    
    # Update installment
    result = await db.bill_installments.update_one(
        {"id": installment_id},
        {"$set": {
            "status": "pending",
            "paid_date": None,
            "payment_method": None,
            "paid_by": None
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
    
    # Get bill info for logging
    bill = await db.bills.find_one({"id": installment["bill_id"]})
    
    # Log activity
    await log_activity(
        ActivityType.PAYMENT_CANCELLED,
        f"Pagamento cancelado - Parcela {installment['installment_number']} - {bill['client_name']} - R$ {installment['amount']:.2f}",
        current_user.id,
        current_user.username,
        {
            "client_name": bill["client_name"],
            "client_cpf": bill["client_cpf"],
            "installment_number": installment["installment_number"],
            "amount": installment["amount"]
        }
    )
    
    return {"message": "Pagamento cancelado com sucesso"}

@api_router.delete("/bills/{bill_id}/cancel")
async def cancel_bill(bill_id: str, current_user: User = Depends(get_current_user)):
    """Cancel entire bill (only admin and manager)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para cancelar boletos")
    
    # Find bill
    bill = await db.bills.find_one({"id": bill_id})
    if not bill:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")
    
    if bill.get("cancelled", False):
        raise HTTPException(status_code=400, detail="Boleto já cancelado")
    
    # Update bill
    await db.bills.update_one(
        {"id": bill_id},
        {"$set": {
            "cancelled": True,
            "cancelled_by": current_user.id,
            "cancelled_at": datetime.utcnow()
        }}
    )
    
    # Cancel all installments
    await db.bill_installments.update_many(
        {"bill_id": bill_id},
        {"$set": {
            "cancelled": True,
            "cancelled_by": current_user.id,
            "cancelled_at": datetime.utcnow()
        }}
    )
    
    # Log activity
    await log_activity(
        ActivityType.BILL_CANCELLED,
        f"Boleto cancelado - {bill['client_name']} - R$ {bill['total_amount']:.2f}",
        current_user.id,
        current_user.username,
        {
            "client_name": bill["client_name"],
            "client_cpf": bill["client_cpf"],
            "total_amount": bill["total_amount"]
        }
    )
    
    return {"message": "Boleto cancelado com sucesso"}

@api_router.get("/bills/pending")
async def get_pending_bills(current_user: User = Depends(get_current_user)):
    # Get pending installments with bill and client info
    pipeline = [
        {"$match": {"status": "pending", "cancelled": False}},
        {"$lookup": {
            "from": "bills",
            "localField": "bill_id",
            "foreignField": "id",
            "as": "bill"
        }},
        {"$unwind": "$bill"},
        {"$match": {"bill.cancelled": False}},
        {"$sort": {"due_date": 1}}
    ]
    
    installments = await db.bill_installments.aggregate(pipeline).to_list(1000)
    
    result = []
    for installment in installments:
        # Check if overdue
        status = "overdue" if installment["due_date"] < datetime.utcnow() else "pending"
        
        result.append({
            "id": installment["id"],
            "bill_id": installment["bill_id"],
            "client_name": installment["bill"]["client_name"],
            "client_cpf": installment["bill"]["client_cpf"],
            "installment_number": installment["installment_number"],
            "amount": installment["amount"],
            "due_date": installment["due_date"],
            "status": status,
            "description": installment["bill"]["description"]
        })
    
    return result

# Generate PDF Reports
@api_router.get("/reports/transactions/pdf")
async def generate_transactions_pdf(
    current_user: User = Depends(get_current_user),
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None)
):
    """Generate PDF report of transactions"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para gerar relatórios")
    
    # Build query
    query = {"cancelled": False}
    if month and year:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        query["created_at"] = {"$gte": start_date, "$lt": end_date}
    
    transactions = await db.transactions.find(query).sort("created_at", -1).to_list(1000)
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        alignment=1,
        fontSize=16,
        textColor=colors.blue
    )
    
    # Title
    period = f" - {month:02d}/{year}" if month and year else ""
    title = Paragraph(f"RELATÓRIO DE TRANSAÇÕES{period}", title_style)
    story.append(title)
    story.append(Spacer(1, 20))
    
    # Summary
    total_entrada = sum(t["amount"] for t in transactions if t["type"] == "entrada")
    total_saida = sum(t["amount"] for t in transactions if t["type"] == "saida")
    saldo = total_entrada - total_saida
    
    summary_data = [
        ["RESUMO", ""],
        ["Total Entradas", f"R$ {total_entrada:.2f}"],
        ["Total Saídas", f"R$ {total_saida:.2f}"],
        ["Saldo", f"R$ {saldo:.2f}"],
        ["Total Transações", str(len(transactions))]
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # Transactions table
    if transactions:
        table_data = [["Data", "Tipo", "Valor", "Descrição", "Pagamento", "Usuário"]]
        
        for transaction in transactions:
            table_data.append([
                transaction["created_at"].strftime("%d/%m/%Y %H:%M"),
                transaction["type"].upper(),
                f"R$ {transaction['amount']:.2f}",
                transaction["description"][:30] + "..." if len(transaction["description"]) > 30 else transaction["description"],
                transaction["payment_method"].upper(),
                transaction.get("user_name", "SISTEMA")
            ])
        
        trans_table = Table(table_data, colWidths=[1.2*inch, 0.8*inch, 1*inch, 2*inch, 1*inch, 1*inch])
        trans_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        
        story.append(trans_table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    filename = f"transacoes_{month:02d}_{year}.pdf" if month and year else "transacoes.pdf"
    
    return StreamingResponse(
        io.BytesIO(buffer.read()),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# Activity Logs (Admin only)
@api_router.get("/activity-logs")
async def get_activity_logs(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas administradores podem ver logs de atividade")
    
    logs = await db.activity_logs.find().sort("timestamp", -1).to_list(1000)
    return [ActivityLog(**log) for log in logs]

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