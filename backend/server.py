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

class ActivityType(str, Enum):
    USER_CREATED = "user_created"
    USER_DEACTIVATED = "user_deactivated"
    USER_ACTIVATED = "user_activated"
    TRANSACTION_CREATED = "transaction_created"
    TRANSACTION_MODIFIED = "transaction_modified"
    PRODUCT_CREATED = "product_created"
    PRODUCT_MODIFIED = "product_modified"
    BILL_CREATED = "bill_created"
    BILL_PAID = "bill_paid"
    LOGIN = "login"

class BillStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    role: UserRole
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: UserRole

class UserUpdate(BaseModel):
    active: bool

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
    created_by: str

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
    user_name: str
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
    address: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str

class ClientCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None

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

class Bill(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    client_name: str
    total_amount: float
    description: str
    installments: int
    installment_amount: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str

class BillCreate(BaseModel):
    client_id: str
    total_amount: float
    description: str
    installments: int

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
    admin_exists = await db.users.find_one({"username": "admin"})
    if not admin_exists:
        admin_user = {
            "id": str(uuid.uuid4()),
            "username": "admin",
            "email": "admin@sistema.com",
            "password": get_password_hash("admin123"),
            "role": "admin",
            "active": True,
            "created_at": datetime.utcnow(),
            "created_by": "system"
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
    
    product_dict = product.dict()
    product_dict["id"] = str(uuid.uuid4())
    product_dict["active"] = True
    product_dict["created_at"] = datetime.utcnow()
    product_dict["created_by"] = current_user.id
    
    await db.products.insert_one(product_dict)
    
    # Log activity
    await log_activity(
        ActivityType.PRODUCT_CREATED,
        f"Produto '{product.name}' criado",
        current_user.id,
        current_user.username,
        {"product_name": product.name, "price": product.price}
    )
    
    return Product(**product_dict)

@api_router.get("/products")
async def get_products(current_user: User = Depends(get_current_user)):
    products = await db.products.find({"active": True}).to_list(1000)
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
    transaction_dict["created_at"] = datetime.utcnow()
    
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
        "total_amount": bill.total_amount,
        "description": bill.description,
        "installments": bill.installments,
        "installment_amount": installment_amount,
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
            "status": "pending"
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
            "total_amount": bill.total_amount,
            "installments": bill.installments
        }
    )
    
    return Bill(**bill_dict)

@api_router.get("/bills")
async def get_bills(current_user: User = Depends(get_current_user)):
    bills = await db.bills.find().sort("created_at", -1).to_list(1000)
    return [Bill(**bill) for bill in bills]

@api_router.get("/bills/{bill_id}/installments")
async def get_bill_installments(bill_id: str, current_user: User = Depends(get_current_user)):
    installments = await db.bill_installments.find({"bill_id": bill_id}).sort("installment_number", 1).to_list(1000)
    return [BillInstallment(**installment) for installment in installments]

@api_router.put("/installments/{installment_id}/pay")
async def pay_installment(installment_id: str, payment: BillPayment, current_user: User = Depends(get_current_user)):
    # Find installment
    installment = await db.bill_installments.find_one({"id": installment_id})
    if not installment:
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
    
    if installment["status"] == "paid":
        raise HTTPException(status_code=400, detail="Parcela já foi paga")
    
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
            "installment_number": installment["installment_number"],
            "amount": installment["amount"],
            "payment_method": payment.payment_method
        }
    )
    
    return {"message": "Parcela paga com sucesso"}

@api_router.get("/bills/pending")
async def get_pending_bills(current_user: User = Depends(get_current_user)):
    # Get pending installments with bill and client info
    pipeline = [
        {"$match": {"status": "pending"}},
        {"$lookup": {
            "from": "bills",
            "localField": "bill_id",
            "foreignField": "id",
            "as": "bill"
        }},
        {"$unwind": "$bill"},
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
            "installment_number": installment["installment_number"],
            "amount": installment["amount"],
            "due_date": installment["due_date"],
            "status": status,
            "description": installment["bill"]["description"]
        })
    
    return result

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