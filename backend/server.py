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

# Email validation regex
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

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

def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email:
        return False
    return EMAIL_REGEX.match(email.lower()) is not None

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
    RECEPTION = "reception"  # Changed from salesperson to reception
    VENDAS = "vendas"  # New sales role

class TransactionType(str, Enum):
    ENTRADA = "entrada"
    SAIDA = "saida"
    PAGAMENTO_CLIENTE = "pagamento_cliente"

class PaymentMethod(str, Enum):
    DINHEIRO = "dinheiro"
    CARTAO = "cartao"
    PIX = "pix"
    BOLETO = "boleto"

class ActivityType(str, Enum):
    USER_CREATED = "user_created"
    USER_DEACTIVATED = "user_deactivated"
    USER_ACTIVATED = "user_activated"
    USER_DELETED = "user_deleted"
    USER_PASSWORD_CHANGED = "user_password_changed"
    USER_PERMISSIONS_CHANGED = "user_permissions_changed"
    TRANSACTION_CREATED = "transaction_created"
    TRANSACTION_MODIFIED = "transaction_modified"
    TRANSACTION_CANCELLED = "transaction_cancelled"
    PRODUCT_CREATED = "product_created"
    PRODUCT_MODIFIED = "product_modified"
    PRODUCT_DELETED = "product_deleted"
    BILL_CREATED = "bill_created"
    BILL_PAID = "bill_paid"
    BILL_CANCELLED = "bill_cancelled"
    PAYMENT_CANCELLED = "payment_cancelled"
    CLIENT_PAYMENT_RECEIVED = "client_payment_received"
    CLIENT_CREATED = "client_created"
    CLIENT_MODIFIED = "client_modified"
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    SALE_CREATED = "sale_created"  # New activity type for sales

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
    permissions: Optional[dict] = Field(default_factory=dict)
    active: bool = True
    require_password_change: bool = False  # Force password change on next login
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    
    @validator('username', 'email', pre=True)
    def uppercase_fields(cls, v):
        return to_upper_case(v)
    
    @validator('email')
    def validate_email_field(cls, v):
        if not validate_email(v):
            raise ValueError('Email inválido')
        return v.upper()

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: UserRole
    permissions: Optional[dict] = Field(default_factory=dict)
    
    @validator('username', 'email', pre=True)
    def uppercase_fields(cls, v):
        return to_upper_case(v)
    
    @validator('email')
    def validate_email_field(cls, v):
        if not validate_email(v):
            raise ValueError('Email inválido')
        return v.upper()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Senha deve ter pelo menos 6 caracteres')
        return v

class UserUpdate(BaseModel):
    active: Optional[bool] = None
    permissions: Optional[dict] = None
    require_password_change: Optional[bool] = None

class UserBasicUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    
    @validator('username', 'email', pre=True)
    def uppercase_fields(cls, v):
        return to_upper_case(v) if v else v
    
    @validator('email')
    def validate_email_field(cls, v):
        if v and not validate_email(v):
            raise ValueError('Email inválido')
        return v.upper() if v else v

class UserPasswordChange(BaseModel):
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Senha deve ter pelo menos 6 caracteres')
        return v

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
    quantity: Optional[int] = None  # None = infinite, integer = finite quantity
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    modified_at: Optional[datetime] = None
    modified_by: Optional[str] = None
    
    @validator('code', 'name', 'description', pre=True)
    def uppercase_fields(cls, v):
        return to_upper_case(v)
    
    @validator('price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Preço deve ser maior que zero')
        return v

class ProductCreate(BaseModel):
    code: str
    name: str
    price: float
    description: Optional[str] = None
    quantity: Optional[int] = None  # None = infinite, integer = finite quantity
    
    @validator('code', 'name', 'description', pre=True)
    def uppercase_fields(cls, v):
        return to_upper_case(v)
    
    @validator('price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Preço deve ser maior que zero')
        return v

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    quantity: Optional[int] = None
    active: Optional[bool] = None
    
    @validator('name', 'description', pre=True)
    def uppercase_fields(cls, v):
        return to_upper_case(v) if v else v
    
    @validator('price')
    def validate_price(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Preço deve ser maior que zero')
        return v

class Sale(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    vendedor_id: str
    product_id: str
    quantity: int
    unit_price: float
    total_value: float
    payment_method: str  # "dinheiro", "pix", "boleto", "cartao"
    sale_date: datetime = Field(default_factory=datetime.utcnow)
    status: str = "completed"  # "completed", "pending", "cancelled"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SaleCreate(BaseModel):
    client_id: str
    product_id: str
    quantity: int
    payment_method: str

class SaleReport(BaseModel):
    sale_id: str
    client_name: str
    client_cpf: str
    product_name: str
    quantity: int
    unit_price: float
    total_value: float
    payment_method: str
    sale_date: datetime
    vendedor_name: str

class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: TransactionType
    amount: float
    description: str
    payment_method: PaymentMethod
    product_id: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    client_cpf: Optional[str] = None
    installment_id: Optional[str] = None  # For client payments
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
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Valor deve ser maior que zero')
        return v

class ClientPaymentCreate(BaseModel):
    client_id: str
    product_id: str
    payment_method: PaymentMethod

class Client(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    cpf: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    modified_at: Optional[datetime] = None
    modified_by: Optional[str] = None
    
    @validator('name', 'email', 'address', pre=True)
    def uppercase_fields(cls, v):
        return to_upper_case(v)
    
    @validator('email')
    def validate_email_field(cls, v):
        if not validate_email(v):
            raise ValueError('Email inválido')
        return v.upper()
    
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
    
    @validator('email')
    def validate_email_field(cls, v):
        if not validate_email(v):
            raise ValueError('Email inválido')
        return v.upper()
    
    @validator('cpf')
    def validate_cpf_field(cls, v):
        if not validate_cpf(v):
            raise ValueError('CPF inválido')
        return format_cpf(v)

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    
    @validator('name', 'email', 'address', pre=True)
    def uppercase_fields(cls, v):
        return to_upper_case(v) if v else v
    
    @validator('email')
    def validate_email_field(cls, v):
        if v and not validate_email(v):
            raise ValueError('Email inválido')
        return v.upper() if v else v

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
    product_id: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
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
    product_id: Optional[str] = None
    total_amount: Optional[float] = None
    description: str
    installments: int
    
    @validator('description', pre=True)
    def uppercase_description(cls, v):
        return to_upper_case(v)
    
    @validator('installments')
    def validate_installments(cls, v):
        if v <= 0:
            raise ValueError('Número de parcelas deve ser maior que zero')
        return v

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

class ClientWithPendingBills(BaseModel):
    client: Client
    pending_bills: List[dict]
    oldest_overdue: Optional[dict] = None

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
            "password": get_password_hash("!$3man@d3c1%"),
            "role": "admin",
            "permissions": {},
            "active": True,
            "require_password_change": False,
            "created_at": datetime.utcnow(),
            "created_by": "system"
        }
        await db.users.insert_one(admin_user)
        print("Usuário admin criado: ADMIN/!$3man@d3c1%")

# Routes
@api_router.post("/register")
async def register(user: UserCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para criar usuários")
    
    # Manager role restrictions: can only create reception and vendas users
    if current_user.role == UserRole.MANAGER:
        if user.role not in [UserRole.RECEPTION, UserRole.VENDAS]:
            raise HTTPException(status_code=403, detail="Gerentes só podem criar usuários de recepção e vendas")
    
    # Check if user exists
    existing_user = await db.users.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Usuário já existe")
    
    # Check if email exists
    existing_email = await db.users.find_one({"email": user.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Create user
    user_dict = user.dict()
    user_dict["password"] = get_password_hash(user_dict["password"])
    user_dict["id"] = str(uuid.uuid4())
    user_dict["active"] = True
    user_dict["require_password_change"] = False
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
    if not db_user:
        # Log failed login attempt
        await log_activity(
            ActivityType.LOGIN_FAILED,
            f"Tentativa de login falhada para usuário '{user.username}'",
            "system",
            "system",
            {"username": user.username, "reason": "user_not_found"}
        )
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")
    
    if not verify_password(user.password, db_user["password"]):
        # Log failed login attempt
        await log_activity(
            ActivityType.LOGIN_FAILED,
            f"Tentativa de login falhada para usuário '{user.username}'",
            db_user["id"],
            db_user["username"],
            {"username": user.username, "reason": "wrong_password"}
        )
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")
    
    if not db_user["active"]:
        raise HTTPException(status_code=401, detail="Usuário desativado")
    
    # Check if password change is required
    if db_user.get("require_password_change", False):
        raise HTTPException(status_code=401, detail="É necessário alterar a senha antes de continuar")
    
    # Create token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user["username"]}, expires_delta=access_token_expires
    )
    
    # Log successful login
    await log_activity(
        ActivityType.LOGIN,
        f"Login realizado com sucesso",
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
            "role": db_user["role"],
            "permissions": db_user.get("permissions", {}),
            "require_password_change": db_user.get("require_password_change", False)
        }
    }

@api_router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

@api_router.post("/check-permission")
async def check_user_permission(permission_request: dict, current_user: User = Depends(get_current_user)):
    """Check if user has specific permission"""
    permission_name = permission_request.get("permission")
    
    # Admin has all permissions
    if current_user.role == UserRole.ADMIN:
        return {"has_permission": True}
    
    # Manager has management permissions
    if current_user.role == UserRole.MANAGER:
        manager_permissions = ["users", "products", "clients", "bills", "reports"]
        return {"has_permission": permission_name in manager_permissions}
    
    # Reception has basic permissions + specific granted permissions
    if current_user.role == UserRole.RECEPTION:
        basic_permissions = ["cash_operations", "clients"]
        specific_permissions = list(current_user.permissions.keys()) if current_user.permissions else []
        all_permissions = basic_permissions + specific_permissions
        return {"has_permission": permission_name in all_permissions}
    
    return {"has_permission": False}

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
    
    # Check permissions for managers  
    if current_user.role == UserRole.MANAGER and user["role"] not in ["reception", "salesperson", "vendas"]:
        raise HTTPException(status_code=403, detail="Gerentes só podem modificar recepção e vendas")
    
    # Managers cannot edit other managers or admins
    if current_user.role == UserRole.MANAGER and user["role"] in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Gerentes não podem editar outros gerentes ou administradores")
    
    # Update user
    update_data = {k: v for k, v in user_update.dict().items() if v is not None}
    if update_data:
        result = await db.users.update_one(
            {"id": user_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        # Log activity
        actions = []
        if user_update.active is not None:
            actions.append("ativado" if user_update.active else "desativado")
        if user_update.permissions is not None:
            actions.append("permissões alteradas")
        if user_update.require_password_change is not None:
            actions.append("nova senha obrigatória definida" if user_update.require_password_change else "nova senha obrigatória removida")
        
        await log_activity(
            ActivityType.USER_PERMISSIONS_CHANGED if user_update.permissions else ActivityType.USER_ACTIVATED if user_update.active else ActivityType.USER_DEACTIVATED,
            f"Usuário '{user['username']}' {', '.join(actions)}",
            current_user.id,
            current_user.username,
            {"target_user": user['username'], "actions": actions}
        )
    
    return {"message": "Usuário atualizado com sucesso"}

@api_router.put("/users/{user_id}/basic")
async def update_user_basic(user_id: str, user_update: UserBasicUpdate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para modificar usuários")
    
    # Find user
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Check permissions for managers  
    if current_user.role == UserRole.MANAGER and user["role"] not in ["reception", "salesperson", "vendas"]:
        raise HTTPException(status_code=403, detail="Gerentes só podem modificar recepção e vendas")
    
    # Managers cannot edit other managers or admins
    if current_user.role == UserRole.MANAGER and user["role"] in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Gerentes não podem editar outros gerentes ou administradores")
    
    # Managers cannot change roles to admin/manager
    if current_user.role == UserRole.MANAGER and user_update.role and user_update.role in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Gerentes não podem alterar função para administrador ou gerente")
    
    # Check for duplicate username
    if user_update.username and user_update.username != user["username"]:
        existing_user = await db.users.find_one({"username": user_update.username, "id": {"$ne": user_id}})
        if existing_user:
            raise HTTPException(status_code=400, detail="Nome de usuário já existe")
    
    # Check for duplicate email
    if user_update.email and user_update.email != user["email"]:
        existing_email = await db.users.find_one({"email": user_update.email, "id": {"$ne": user_id}})
        if existing_email:
            raise HTTPException(status_code=400, detail="Email já cadastrado")

    # Update user
    update_data = {k: v for k, v in user_update.dict().items() if v is not None}
    if update_data:
        result = await db.users.update_one(
            {"id": user_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        # Log activity
        changes = []
        if user_update.username:
            changes.append(f"nome alterado para '{user_update.username}'")
        if user_update.email:
            changes.append(f"email alterado para '{user_update.email}'")
        if user_update.role:
            changes.append(f"função alterada para '{user_update.role}'")
        
        await log_activity(
            ActivityType.USER_PERMISSIONS_CHANGED,
            f"Dados básicos do usuário '{user['username']}' alterados: {', '.join(changes)}",
            current_user.id,
            current_user.username,
            {"target_user": user['username'], "changes": changes}
        )
    
    return {"message": "Dados do usuário atualizados com sucesso"}

@api_router.put("/users/{user_id}/password")
async def change_user_password(user_id: str, password_change: UserPasswordChange, current_user: User = Depends(get_current_user)):
    # Find user
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Check permissions
    if current_user.role == UserRole.ADMIN:
        # Admin can change any password
        pass
    elif current_user.role == UserRole.MANAGER:
        # Manager can only change reception and vendas passwords
        if user["role"] not in ["reception", "salesperson", "vendas"]:
            raise HTTPException(status_code=403, detail="Gerentes só podem alterar senhas da recepção e vendas")
    else:
        # Reception can only change their own password
        if user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Sem permissão para alterar senha de outro usuário")
    
    # Update password and reset require_password_change flag
    hashed_password = get_password_hash(password_change.new_password)
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"password": hashed_password, "require_password_change": False}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Log activity
    await log_activity(
        ActivityType.USER_PASSWORD_CHANGED,
        f"Senha alterada para usuário '{user['username']}'",
        current_user.id,
        current_user.username,
        {"target_user": user['username']}
    )
    
    return {"message": "Senha alterada com sucesso"}

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas administradores podem excluir usuários")
    
    # Find user
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if user["username"] == "ADMIN":
        raise HTTPException(status_code=403, detail="Não é possível excluir o usuário administrador")
    
    # Delete user
    result = await db.users.delete_one({"id": user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Log activity
    await log_activity(
        ActivityType.USER_DELETED,
        f"Usuário '{user['username']}' excluído",
        current_user.id,
        current_user.username,
        {"deleted_user": user['username'], "deleted_role": user['role']}
    )
    
    return {"message": "Usuário excluído com sucesso"}

# Products
@api_router.post("/products")
async def create_product(product: ProductCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para criar produtos")
    
    # Check if product code exists
    existing_product = await db.products.find_one({"code": product.code, "active": True})
    if existing_product:
        raise HTTPException(status_code=400, detail="Código do produto já existe")
    
    # Check if product name exists
    existing_name = await db.products.find_one({"name": product.name, "active": True})
    if existing_name:
        raise HTTPException(status_code=400, detail="Produto com este nome já existe")
    
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

@api_router.put("/products/{product_id}")
async def update_product(product_id: str, product_update: ProductUpdate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para modificar produtos")
    
    # Find product
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # Check for duplicate name if updating name
    if product_update.name and product_update.name != product["name"]:
        existing_name = await db.products.find_one({"name": product_update.name, "active": True, "id": {"$ne": product_id}})
        if existing_name:
            raise HTTPException(status_code=400, detail="Produto com este nome já existe")
    
    # Update product
    update_data = {k: v for k, v in product_update.dict().items() if v is not None}
    if update_data:
        update_data["modified_at"] = datetime.utcnow()
        update_data["modified_by"] = current_user.id
        
        result = await db.products.update_one(
            {"id": product_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        # Log activity
        await log_activity(
            ActivityType.PRODUCT_MODIFIED,
            f"Produto '{product['code']} - {product['name']}' modificado",
            current_user.id,
            current_user.username,
            {"product_code": product['code'], "product_name": product['name'], "changes": update_data}
        )
    
    return {"message": "Produto atualizado com sucesso"}

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para excluir produtos")
    
    # Find product
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # Soft delete (deactivate)
    result = await db.products.update_one(
        {"id": product_id},
        {"$set": {"active": False, "modified_at": datetime.utcnow(), "modified_by": current_user.id}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # Log activity
    await log_activity(
        ActivityType.PRODUCT_DELETED,
        f"Produto '{product['code']} - {product['name']}' excluído",
        current_user.id,
        current_user.username,
        {"product_code": product['code'], "product_name": product['name']}
    )
    
    return {"message": "Produto excluído com sucesso"}

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

@api_router.post("/transactions/client-payment")
async def create_client_payment(payment: ClientPaymentCreate, current_user: User = Depends(get_current_user)):
    """Create a payment from client for a specific product"""
    # Get client info
    client = await db.clients.find_one({"id": payment.client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Get product info
    product = await db.products.find_one({"id": payment.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # Find the oldest overdue installment for this client and product
    pipeline = [
        {"$match": {"status": "pending", "cancelled": False}},
        {"$lookup": {
            "from": "bills",
            "localField": "bill_id",
            "foreignField": "id",
            "as": "bill"
        }},
        {"$unwind": "$bill"},
        {"$match": {
            "bill.cancelled": False,
            "bill.client_id": payment.client_id,
            "bill.product_id": payment.product_id
        }},
        {"$sort": {"due_date": 1}}
    ]
    
    installments = await db.bill_installments.aggregate(pipeline).to_list(1000)
    
    if not installments:
        raise HTTPException(status_code=404, detail="Nenhuma parcela pendente encontrada para este cliente e produto")
    
    # Get the oldest installment
    oldest_installment = installments[0]
    
    # Update installment as paid
    await db.bill_installments.update_one(
        {"id": oldest_installment["id"]},
        {"$set": {
            "status": "paid",
            "paid_date": datetime.utcnow(),
            "payment_method": payment.payment_method,
            "paid_by": current_user.id
        }}
    )
    
    # Create transaction record
    transaction_dict = {
        "id": str(uuid.uuid4()),
        "type": "pagamento_cliente",
        "amount": oldest_installment["amount"],
        "description": f"PAGAMENTO - {product['name']} - PARCELA {oldest_installment['installment_number']}",
        "payment_method": payment.payment_method,
        "product_id": payment.product_id,
        "product_code": product["code"],
        "product_name": product["name"],
        "client_id": payment.client_id,
        "client_name": client["name"],
        "client_cpf": client["cpf"],
        "installment_id": oldest_installment["id"],
        "user_id": current_user.id,
        "user_name": current_user.username,
        "cancelled": False,
        "created_at": datetime.utcnow()
    }
    
    await db.transactions.insert_one(transaction_dict)
    
    # Log activity
    await log_activity(
        ActivityType.CLIENT_PAYMENT_RECEIVED,
        f"Pagamento recebido de {client['name']} - {product['name']} - Parcela {oldest_installment['installment_number']} - R$ {oldest_installment['amount']:.2f}",
        current_user.id,
        current_user.username,
        {
            "client_name": client["name"],
            "client_cpf": client["cpf"],
            "product_name": product["name"],
            "installment_number": oldest_installment["installment_number"],
            "amount": oldest_installment["amount"],
            "payment_method": payment.payment_method
        }
    )
    
    return {
        "message": "Pagamento registrado com sucesso",
        "transaction": Transaction(**transaction_dict),
        "installment_paid": oldest_installment["installment_number"],
        "amount": oldest_installment["amount"]
    }

@api_router.get("/clients/{client_id}/pending-bills")
async def get_client_pending_bills(client_id: str, current_user: User = Depends(get_current_user)):
    """Get all pending bills for a specific client grouped by product"""
    # Get client info
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Get pending installments for this client
    pipeline = [
        {"$match": {"status": "pending", "cancelled": False}},
        {"$lookup": {
            "from": "bills",
            "localField": "bill_id",
            "foreignField": "id",
            "as": "bill"
        }},
        {"$unwind": "$bill"},
        {"$match": {
            "bill.cancelled": False,
            "bill.client_id": client_id
        }},
        {"$lookup": {
            "from": "products",
            "localField": "bill.product_id",
            "foreignField": "id",
            "as": "product"
        }},
        {"$sort": {"due_date": 1}}
    ]
    
    installments = await db.bill_installments.aggregate(pipeline).to_list(1000)
    
    # Group by product
    products_with_bills = {}
    for installment in installments:
        product_id = installment["bill"].get("product_id")
        if product_id:
            if product_id not in products_with_bills:
                product_info = installment.get("product", [{}])[0] if installment.get("product") else {}
                products_with_bills[product_id] = {
                    "product_id": product_id,
                    "product_code": product_info.get("code", "N/A"),
                    "product_name": product_info.get("name", "N/A"),
                    "product_price": product_info.get("price", 0),
                    "pending_installments": [],
                    "oldest_overdue": None
                }
            
            installment_info = {
                "installment_id": installment["id"],
                "installment_number": installment["installment_number"],
                "amount": installment["amount"],
                "due_date": installment["due_date"],
                "is_overdue": installment["due_date"] < datetime.utcnow()
            }
            
            products_with_bills[product_id]["pending_installments"].append(installment_info)
            
            # Set oldest overdue if not set and this is overdue
            if (installment_info["is_overdue"] and 
                products_with_bills[product_id]["oldest_overdue"] is None):
                products_with_bills[product_id]["oldest_overdue"] = installment_info
    
    return {
        "client": Client(**client),
        "products_with_bills": list(products_with_bills.values())
    }

@api_router.get("/transactions")
async def get_transactions(
    current_user: User = Depends(get_current_user),
    search: Optional[str] = Query(None),
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    transaction_type: Optional[TransactionType] = Query(None),
    payment_method: Optional[PaymentMethod] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """Get transactions with filters"""
    query = {"cancelled": False}
    
    # Build filters
    if search:
        query["$or"] = [
            {"description": {"$regex": search.upper(), "$options": "i"}},
            {"user_name": {"$regex": search.upper(), "$options": "i"}},
            {"product_name": {"$regex": search.upper(), "$options": "i"}},
            {"client_name": {"$regex": search.upper(), "$options": "i"}}
        ]
    
    if month and year:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        query["created_at"] = {"$gte": start_date, "$lt": end_date}
    elif date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = datetime.fromisoformat(date_from)
        if date_to:
            date_query["$lt"] = datetime.fromisoformat(date_to) + timedelta(days=1)
        query["created_at"] = date_query
    
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
    
    # If it's a client payment, we need to revert the installment payment
    if transaction.get("type") == "pagamento_cliente" and transaction.get("installment_id"):
        await db.bill_installments.update_one(
            {"id": transaction["installment_id"]},
            {"$set": {
                "status": "pending",
                "paid_date": None,
                "payment_method": None,
                "paid_by": None
            }}
        )
    
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
            "original_user": transaction.get('user_name', 'N/A'),
            "type": transaction.get('type', 'N/A')
        }
    )
    
    return {"message": "Transação cancelada com sucesso"}

@api_router.post("/bills/installments/{installment_id}/pay")
async def pay_installment(
    installment_id: str, 
    payment: BillPayment, 
    current_user: User = Depends(get_current_user)
):
    """Pay a specific installment"""
    # Find the installment
    installment = await db.bill_installments.find_one({"id": installment_id, "cancelled": False})
    if not installment:
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
    
    if installment["status"] != "pending":
        raise HTTPException(status_code=400, detail="Parcela já foi paga ou cancelada")
    
    # Get bill info
    bill = await db.bills.find_one({"id": installment["bill_id"]})
    if not bill:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")
    
    # Get client info
    client = await db.clients.find_one({"id": bill["client_id"]})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Get product info (if exists)
    product = None
    if bill.get("product_id"):
        product = await db.products.find_one({"id": bill["product_id"]})
    
    # Update installment as paid
    await db.bill_installments.update_one(
        {"id": installment_id},
        {"$set": {
            "status": "paid",
            "paid_date": datetime.utcnow(),
            "payment_method": payment.payment_method,
            "paid_by": current_user.id
        }}
    )
    
    # Create transaction record
    transaction_dict = {
        "id": str(uuid.uuid4()),
        "type": "pagamento_cliente",
        "amount": installment["amount"],
        "description": f"PAGAMENTO - {bill['description']} - PARCELA {installment['installment_number']}",
        "payment_method": payment.payment_method,
        "product_id": bill.get("product_id"),
        "product_code": product["code"] if product else None,
        "product_name": product["name"] if product else bill.get("product_name"),
        "client_id": bill["client_id"],
        "client_name": client["name"],
        "client_cpf": client["cpf"],
        "installment_id": installment_id,
        "user_id": current_user.id,
        "user_name": current_user.username,
        "cancelled": False,
        "created_at": datetime.utcnow()
    }
    
    await db.transactions.insert_one(transaction_dict)
    
    # Log activity
    await log_activity(
        ActivityType.CLIENT_PAYMENT_RECEIVED,
        f"Pagamento recebido de {client['name']} - Parcela {installment['installment_number']} - R$ {installment['amount']:.2f}",
        current_user.id,
        current_user.username,
        {
            "client_name": client["name"],
            "client_cpf": client["cpf"],
            "installment_number": installment["installment_number"],
            "amount": installment["amount"],
            "payment_method": payment.payment_method,
            "bill_description": bill["description"]
        }
    )
    
    return {
        "message": "Pagamento registrado com sucesso",
        "transaction": Transaction(**transaction_dict),
        "installment_paid": installment["installment_number"],
        "amount": installment["amount"]
    }

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get dashboard statistics for the homepage"""
    # Get current month transactions
    now = datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    transactions = await db.transactions.find({
        "created_at": {"$gte": start_of_month},
        "cancelled": False
    }).to_list(1000)
    
    # Get today's transactions
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_transactions = await db.transactions.find({
        "created_at": {"$gte": start_of_day},
        "cancelled": False
    }).to_list(1000)
    
    # Calculate totals
    total_entrada = sum(t["amount"] for t in transactions if t["type"] in ["entrada", "pagamento_cliente"])
    total_saida = sum(t["amount"] for t in transactions if t["type"] == "saida")
    saldo = total_entrada - total_saida
    
    # Get recent transactions for preview (last 10)
    recent_transactions = await db.transactions.find({
        "cancelled": False
    }).sort("created_at", -1).limit(10).to_list(10)
    
    return {
        "total_entrada": total_entrada,
        "total_saida": total_saida,
        "saldo": saldo,
        "total_transactions": len(transactions),
        "today_transactions": len(today_transactions),
        "current_datetime": now.isoformat(),
        "recent_transactions": [Transaction(**t) for t in recent_transactions]
    }

@api_router.get("/transactions/summary")
async def get_transactions_summary(current_user: User = Depends(get_current_user)):
    # Get current month transactions
    now = datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    transactions = await db.transactions.find({
        "created_at": {"$gte": start_of_month},
        "cancelled": False
    }).to_list(1000)
    
    # Get today's transactions
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_transactions = await db.transactions.find({
        "created_at": {"$gte": start_of_day},
        "cancelled": False
    }).to_list(1000)
    
    total_entrada = sum(t["amount"] for t in transactions if t["type"] in ["entrada", "pagamento_cliente"])
    total_saida = sum(t["amount"] for t in transactions if t["type"] == "saida")
    saldo = total_entrada - total_saida
    
    return {
        "total_entrada": total_entrada,
        "total_saida": total_saida,
        "saldo": saldo,
        "total_transactions": len(transactions),
        "today_transactions": len(today_transactions),
        "current_datetime": now.isoformat()
    }

# Clients
@api_router.post("/clients")
async def create_client(client: ClientCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.VENDAS]:
        raise HTTPException(status_code=403, detail="Sem permissão para criar clientes")
    
    # Check if CPF already exists
    existing_client = await db.clients.find_one({"cpf": client.cpf})
    if existing_client:
        raise HTTPException(status_code=400, detail="CPF já cadastrado")
    
    # Check if email already exists
    existing_email = await db.clients.find_one({"email": client.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    client_dict = client.dict()
    client_dict["id"] = str(uuid.uuid4())
    client_dict["created_at"] = datetime.utcnow()
    client_dict["created_by"] = current_user.id
    
    await db.clients.insert_one(client_dict)
    
    # Log activity
    await log_activity(
        ActivityType.CLIENT_CREATED,
        f"Cliente '{client.name}' criado - CPF: {client.cpf}",
        current_user.id,
        current_user.username,
        {"client_name": client.name, "client_cpf": client.cpf}
    )
    
    return Client(**client_dict)

@api_router.get("/clients")
async def get_clients(current_user: User = Depends(get_current_user)):
    clients = await db.clients.find().to_list(1000)
    # Filter out clients with missing required fields
    valid_clients = []
    for client in clients:
        try:
            valid_clients.append(Client(**client))
        except Exception as e:
            # Skip clients with invalid data (missing required fields)
            continue
    return valid_clients

@api_router.get("/clients/search")
async def search_clients(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user)
):
    """Search clients by name or CPF"""
    # Clean CPF for search
    cpf_clean = re.sub(r'[^\d]', '', q)
    
    query = {
        "$or": [
            {"name": {"$regex": q.upper(), "$options": "i"}},
            {"cpf": {"$regex": cpf_clean, "$options": "i"}}
        ]
    }
    
    clients = await db.clients.find(query).to_list(50)
    return [Client(**client) for client in clients]

@api_router.get("/clients/{client_id}")
async def get_client(client_id: str, current_user: User = Depends(get_current_user)):
    """Get client details with products and payment history"""
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Get client's bills and products
    bills = await db.bills.find({"client_id": client_id, "cancelled": False}).to_list(1000)
    
    # Get payment history
    payment_history = await db.transactions.find({
        "client_id": client_id,
        "type": "pagamento_cliente",
        "cancelled": False
    }).sort("created_at", -1).to_list(1000)
    
    return {
        "client": Client(**client),
        "bills": [Bill(**bill) for bill in bills],
        "payment_history": [Transaction(**payment) for payment in payment_history]
    }

@api_router.put("/clients/{client_id}")
async def update_client(client_id: str, client_update: ClientUpdate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.VENDAS]:
        raise HTTPException(status_code=403, detail="Sem permissão para modificar clientes")
    
    # Find client
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Check for duplicate email if updating email
    if client_update.email and client_update.email != client["email"]:
        existing_email = await db.clients.find_one({"email": client_update.email, "id": {"$ne": client_id}})
        if existing_email:
            raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Update client
    update_data = {k: v for k, v in client_update.dict().items() if v is not None}
    if update_data:
        update_data["modified_at"] = datetime.utcnow()
        update_data["modified_by"] = current_user.id
        
        result = await db.clients.update_one(
            {"id": client_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
        # Log activity
        await log_activity(
            ActivityType.CLIENT_MODIFIED,
            f"Cliente '{client['name']}' modificado",
            current_user.id,
            current_user.username,
            {"client_name": client['name'], "client_cpf": client['cpf'], "changes": update_data}
        )
    
    return {"message": "Cliente atualizado com sucesso"}

@api_router.get("/clients/with-bills")
async def get_clients_with_bills(current_user: User = Depends(get_current_user)):
    """Get clients that have pending bills"""
    # Get all clients with pending bills
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
        {"$group": {
            "_id": "$bill.client_id",
            "total_pending": {"$sum": 1}
        }},
        {"$lookup": {
            "from": "clients",
            "localField": "_id",
            "foreignField": "id",
            "as": "client"
        }},
        {"$unwind": "$client"},
        {"$project": {
            "client_id": "$_id",
            "client_name": "$client.name",
            "client_cpf": "$client.cpf",
            "total_pending": 1
        }}
    ]
    
    clients_with_bills = await db.bill_installments.aggregate(pipeline).to_list(1000)
    
    return clients_with_bills

# Bills
@api_router.post("/bills")
async def create_bill(bill: BillCreate, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para criar boletos")
    
    # Get client info
    client = await db.clients.find_one({"id": bill.client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Handle product selection
    product_code = None
    product_name = None
    total_amount = bill.total_amount
    
    if bill.product_id:
        product = await db.products.find_one({"id": bill.product_id})
        if not product:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        product_code = product["code"]
        product_name = product["name"]
        total_amount = product["price"]  # Use product price
    
    if not total_amount:
        raise HTTPException(status_code=400, detail="Valor total deve ser informado")
    
    # Create bill
    bill_id = str(uuid.uuid4())
    installment_amount = total_amount / bill.installments
    
    bill_dict = {
        "id": bill_id,
        "client_id": bill.client_id,
        "client_name": client["name"],
        "client_cpf": client["cpf"],
        "product_id": bill.product_id,
        "product_code": product_code,
        "product_name": product_name,
        "total_amount": total_amount,
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
    product_info = f" - {product_name}" if product_name else ""
    await log_activity(
        ActivityType.BILL_CREATED,
        f"Boleto criado para {client['name']}{product_info} - R$ {total_amount:.2f} em {bill.installments}x",
        current_user.id,
        current_user.username,
        {
            "client_name": client["name"],
            "client_cpf": client["cpf"],
            "product_name": product_name,
            "total_amount": total_amount,
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
            "product_name": bill.get("product_name"),
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
            "product_name": bill.get("product_name"),
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
            "product_name": bill.get("product_name"),
            "total_amount": bill["total_amount"]
        }
    )
    
    return {"message": "Boleto cancelado com sucesso"}

@api_router.get("/bills/pending")
async def get_pending_bills(
    current_user: User = Depends(get_current_user),
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    client_name: Optional[str] = Query(None)
):
    """Get pending bills with filters"""
    match_query = {"status": "pending", "cancelled": False}
    
    # Add month/year filter
    if month and year:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        match_query["due_date"] = {"$gte": start_date, "$lt": end_date}
    elif not month and not year:
        # Default to current month if no filters
        now = datetime.utcnow()
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        match_query["due_date"] = {"$gte": start_date}
    
    # Get pending installments with bill and client info
    pipeline = [
        {"$match": match_query},
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
        # Apply client name filter if provided
        if client_name and client_name.upper() not in installment["bill"]["client_name"].upper():
            continue
            
        # Check if overdue
        status = "overdue" if installment["due_date"] < datetime.utcnow() else "pending"
        
        result.append({
            "id": installment["id"],
            "bill_id": installment["bill_id"],
            "client_name": installment["bill"]["client_name"],
            "client_cpf": installment["bill"]["client_cpf"],
            "product_name": installment["bill"].get("product_name"),
            "product_code": installment["bill"].get("product_code"),
            "installment_number": installment["installment_number"],
            "amount": installment["amount"],
            "due_date": installment["due_date"],
            "status": status,
            "description": installment["bill"]["description"]
        })
    
    return result

@api_router.put("/bills/{bill_id}/pay-all")
async def pay_all_bill_installments(bill_id: str, payment: BillPayment, current_user: User = Depends(get_current_user)):
    """Pay all pending installments for a bill"""
    # Find bill
    bill = await db.bills.find_one({"id": bill_id})
    if not bill:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")
    
    if bill.get("cancelled", False):
        raise HTTPException(status_code=400, detail="Boleto cancelado")
    
    # Find all pending installments
    installments = await db.bill_installments.find({
        "bill_id": bill_id,
        "status": "pending",
        "cancelled": False
    }).to_list(1000)
    
    if not installments:
        raise HTTPException(status_code=400, detail="Nenhuma parcela pendente encontrada")
    
    # Update all installments as paid
    total_amount = 0
    for installment in installments:
        await db.bill_installments.update_one(
            {"id": installment["id"]},
            {"$set": {
                "status": "paid",
                "paid_date": datetime.utcnow(),
                "payment_method": payment.payment_method,
                "paid_by": current_user.id
            }}
        )
        total_amount += installment["amount"]
    
    # Log activity
    await log_activity(
        ActivityType.BILL_PAID,
        f"Boleto quitado - {bill['client_name']} - {len(installments)} parcelas - R$ {total_amount:.2f}",
        current_user.id,
        current_user.username,
        {
            "client_name": bill["client_name"],
            "client_cpf": bill["client_cpf"],
            "product_name": bill.get("product_name"),
            "installments_paid": len(installments),
            "total_amount": total_amount,
            "payment_method": payment.payment_method
        }
    )
    
    return {
        "message": "Boleto quitado com sucesso",
        "installments_paid": len(installments),
        "total_amount": total_amount
    }

# Sales Endpoints
@api_router.post("/sales")
async def create_sale(sale: SaleCreate, current_user: User = Depends(get_current_user)):
    """Create a new sale"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.VENDAS]:
        raise HTTPException(status_code=403, detail="Sem permissão para criar vendas")
    
    # Get client
    client = await db.clients.find_one({"id": sale.client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Get product
    product = await db.products.find_one({"id": sale.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # Check product quantity if finite
    if product.get("quantity") is not None and product["quantity"] < sale.quantity:
        raise HTTPException(status_code=400, detail="Quantidade insuficiente em estoque")
    
    # Calculate total
    unit_price = product["price"]
    total_value = unit_price * sale.quantity
    
    # Create sale record
    sale_data = Sale(
        client_id=sale.client_id,
        vendedor_id=current_user.id,
        product_id=sale.product_id,
        quantity=sale.quantity,
        unit_price=unit_price,
        total_value=total_value,
        payment_method=sale.payment_method
    )
    
    await db.sales.insert_one(sale_data.dict())
    
    # Update product quantity if finite
    if product.get("quantity") is not None:
        await db.products.update_one(
            {"id": sale.product_id},
            {"$inc": {"quantity": -sale.quantity}}
        )
    
    # If payment method is boleto, create bill automatically
    if sale.payment_method.lower() == "boleto":
        from datetime import timedelta
        
        bill_data = {
            "id": str(uuid.uuid4()),
            "client_id": sale.client_id,
            "client_name": client["name"],
            "client_cpf": client["cpf"],
            "client_email": client.get("email", ""),
            "product_id": sale.product_id,
            "product_name": product["name"],
            "total_amount": total_value,
            "installments": 1,
            "installment_value": total_value,
            "due_date": datetime.utcnow() + timedelta(days=30),
            "created_at": datetime.utcnow(),
            "created_by": current_user.id,
            "cancelled": False,
            "sale_id": sale_data.id  # Link to sale
        }
        
        await db.bills.insert_one(bill_data)
        
        # Create installment
        installment_data = {
            "id": str(uuid.uuid4()),
            "bill_id": bill_data["id"],
            "installment_number": 1,
            "amount": total_value,
            "due_date": bill_data["due_date"],
            "paid": False,
            "paid_at": None,
            "paid_amount": 0.0,
            "created_at": datetime.utcnow()
        }
        
        await db.bill_installments.insert_one(installment_data)
    
    # Log activity
    await log_activity(
        ActivityType.SALE_CREATED,
        f"Venda realizada: {product['name']} para {client['name']} - R$ {total_value:.2f}",
        current_user.id,
        current_user.username,
        {
            "client_id": sale.client_id,
            "client_name": client["name"],
            "product_id": sale.product_id,
            "product_name": product["name"],
            "quantity": sale.quantity,
            "total_value": total_value,
            "payment_method": sale.payment_method
        }
    )
    
    return {"message": "Venda realizada com sucesso", "sale_id": sale_data.id, "total_value": total_value}

@api_router.get("/sales/my-reports")
async def get_my_sales_reports(
    current_user: User = Depends(get_current_user),
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None)
):
    """Get sales reports for the current salesperson"""
    if current_user.role not in [UserRole.VENDAS]:
        raise HTTPException(status_code=403, detail="Sem permissão para visualizar relatórios")
    
    # Build query
    query = {"vendedor_id": current_user.id}
    
    if month and year:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        query["created_at"] = {"$gte": start_date, "$lt": end_date}
    
    # Get sales with client and product info
    pipeline = [
        {"$match": query},
        {"$lookup": {
            "from": "clients",
            "localField": "client_id",
            "foreignField": "id",
            "as": "client"
        }},
        {"$lookup": {
            "from": "products", 
            "localField": "product_id",
            "foreignField": "id",
            "as": "product"
        }},
        {"$unwind": "$client"},
        {"$unwind": "$product"},
        {"$sort": {"created_at": -1}}
    ]
    
    sales_raw = await db.sales.aggregate(pipeline).to_list(1000)
    
    # Calculate statistics
    total_sales = len(sales_raw)
    total_revenue = sum(sale["total_value"] for sale in sales_raw)
    
    # Group by product
    product_stats = {}
    for sale in sales_raw:
        product_id = sale["product_id"]
        if product_id not in product_stats:
            product_stats[product_id] = {
                "quantity": 0,
                "revenue": 0.0,
                "sales_count": 0
            }
        product_stats[product_id]["quantity"] += sale["quantity"]
        product_stats[product_id]["revenue"] += sale["total_value"]
        product_stats[product_id]["sales_count"] += 1
    
    # Convert sales to clean format (remove MongoDB ObjectId issues)
    sales = []
    for sale in sales_raw:
        sales.append({
            "sale_id": sale["id"],
            "client_name": sale["client"]["name"],
            "client_cpf": sale["client"]["cpf"],
            "product_name": sale["product"]["name"],
            "quantity": sale["quantity"],
            "unit_price": sale["unit_price"],
            "total_value": sale["total_value"], 
            "payment_method": sale["payment_method"],
            "sale_date": sale.get("sale_date", sale.get("created_at")),
            "vendedor_id": sale["vendedor_id"],
            "created_at": sale["created_at"]
        })
    
    return {
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "product_stats": product_stats,
        "sales": sales
    }

# Performance Dashboard Endpoints
@api_router.get("/performance/dashboard")
async def get_performance_dashboard(
    current_user: User = Depends(get_current_user),
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None)
):
    """Get comprehensive performance dashboard data for managers and admins"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para visualizar dashboard de performance")
    
    # Build date query
    date_query = {}
    if month and year:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        date_query = {"created_at": {"$gte": start_date, "$lt": end_date}}
    
    # Get all sales data
    sales_query = {**date_query}
    sales = await db.sales.find(sales_query).to_list(10000)
    
    # Get all transactions data
    transactions_query = {**date_query, "cancelled": False}
    transactions = await db.transactions.find(transactions_query).to_list(10000)
    
    # Calculate overall statistics
    total_sales = len(sales)
    total_sales_revenue = sum(sale["total_value"] for sale in sales)
    
    total_transactions = len(transactions)
    total_cash_in = sum(t["amount"] for t in transactions if t["type"] == "entrada")
    total_cash_out = sum(t["amount"] for t in transactions if t["type"] == "saída")
    cash_balance = total_cash_in - total_cash_out
    
    # Sales by salesperson
    salesperson_stats = {}
    for sale in sales:
        vendedor_id = sale["vendedor_id"]
        if vendedor_id not in salesperson_stats:
            salesperson_stats[vendedor_id] = {
                "sales_count": 0,
                "revenue": 0.0,
                "products_sold": 0
            }
        salesperson_stats[vendedor_id]["sales_count"] += 1
        salesperson_stats[vendedor_id]["revenue"] += sale["total_value"]
        salesperson_stats[vendedor_id]["products_sold"] += sale["quantity"]
    
    # Get salesperson names
    vendedor_ids = list(salesperson_stats.keys())
    vendedores = await db.users.find({"id": {"$in": vendedor_ids}}).to_list(100)
    vendedor_names = {v["id"]: v["username"] for v in vendedores}
    
    # Add names to stats
    for vendedor_id in salesperson_stats:
        salesperson_stats[vendedor_id]["name"] = vendedor_names.get(vendedor_id, "Usuário Removido")
    
    # Sales by product
    product_stats = {}
    for sale in sales:
        product_id = sale["product_id"]
        if product_id not in product_stats:
            product_stats[product_id] = {
                "sales_count": 0,
                "quantity_sold": 0,
                "revenue": 0.0
            }
        product_stats[product_id]["sales_count"] += 1
        product_stats[product_id]["quantity_sold"] += sale["quantity"]
        product_stats[product_id]["revenue"] += sale["total_value"]
    
    # Get product names
    product_ids = list(product_stats.keys())
    products = await db.products.find({"id": {"$in": product_ids}}).to_list(1000)
    product_names = {p["id"]: p["name"] for p in products}
    
    # Add names to stats
    for product_id in product_stats:
        product_stats[product_id]["name"] = product_names.get(product_id, "Produto Removido")
    
    # Sales by payment method
    payment_method_stats = {}
    for sale in sales:
        method = sale["payment_method"]
        if method not in payment_method_stats:
            payment_method_stats[method] = {
                "count": 0,
                "revenue": 0.0
            }
        payment_method_stats[method]["count"] += 1
        payment_method_stats[method]["revenue"] += sale["total_value"]
    
    # Daily sales trend (last 30 days)
    from datetime import timedelta
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    daily_sales = {}
    for sale in sales:
        if sale["created_at"] >= start_date:
            day_key = sale["created_at"].strftime("%Y-%m-%d")
            if day_key not in daily_sales:
                daily_sales[day_key] = {
                    "count": 0,
                    "revenue": 0.0
                }
            daily_sales[day_key]["count"] += 1
            daily_sales[day_key]["revenue"] += sale["total_value"]
    
    # Monthly comparison (current vs previous month)
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year
    
    # Current month
    current_month_start = datetime(current_year, current_month, 1)
    if current_month == 12:
        current_month_end = datetime(current_year + 1, 1, 1)
    else:
        current_month_end = datetime(current_year, current_month + 1, 1)
    
    # Previous month
    if current_month == 1:
        prev_month = 12
        prev_year = current_year - 1
    else:
        prev_month = current_month - 1
        prev_year = current_year
    
    prev_month_start = datetime(prev_year, prev_month, 1)
    prev_month_end = datetime(prev_year, prev_month + 1, 1) if prev_month < 12 else datetime(prev_year + 1, 1, 1)
    
    current_month_sales = await db.sales.find({
        "created_at": {"$gte": current_month_start, "$lt": current_month_end}
    }).to_list(10000)
    
    prev_month_sales = await db.sales.find({
        "created_at": {"$gte": prev_month_start, "$lt": prev_month_end}
    }).to_list(10000)
    
    current_month_revenue = sum(sale["total_value"] for sale in current_month_sales)
    prev_month_revenue = sum(sale["total_value"] for sale in prev_month_sales)
    
    revenue_growth = 0
    if prev_month_revenue > 0:
        revenue_growth = ((current_month_revenue - prev_month_revenue) / prev_month_revenue) * 100
    
    return {
        "overview": {
            "total_sales": total_sales,
            "total_sales_revenue": total_sales_revenue,
            "total_transactions": total_transactions,
            "cash_balance": cash_balance,
            "revenue_growth": revenue_growth
        },
        "salesperson_performance": salesperson_stats,
        "product_performance": product_stats,
        "payment_methods": payment_method_stats,
        "daily_trend": daily_sales,
        "monthly_comparison": {
            "current_month": {
                "revenue": current_month_revenue,
                "sales_count": len(current_month_sales)
            },
            "previous_month": {
                "revenue": prev_month_revenue,
                "sales_count": len(prev_month_sales)
            },
            "growth_percentage": revenue_growth
        }
    }

@api_router.get("/performance/top-performers")
async def get_top_performers(
    current_user: User = Depends(get_current_user),
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    limit: int = Query(10)
):
    """Get top performing salespeople"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para visualizar relatórios de performance")
    
    # Build date query
    date_query = {}
    if month and year:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        date_query = {"created_at": {"$gte": start_date, "$lt": end_date}}
    
    # Aggregate sales by salesperson
    pipeline = [
        {"$match": date_query},
        {"$group": {
            "_id": "$vendedor_id",
            "total_sales": {"$sum": 1},
            "total_revenue": {"$sum": "$total_value"},
            "total_quantity": {"$sum": "$quantity"}
        }},
        {"$sort": {"total_revenue": -1}},
        {"$limit": limit}
    ]
    
    results = await db.sales.aggregate(pipeline).to_list(limit)
    
    # Get user names
    vendedor_ids = [r["_id"] for r in results]
    vendedores = await db.users.find({"id": {"$in": vendedor_ids}}).to_list(100)
    vendedor_names = {v["id"]: v["username"] for v in vendedores}
    
    # Format results
    top_performers = []
    for result in results:
        vendedor_id = result["_id"]
        top_performers.append({
            "vendedor_id": vendedor_id,
            "name": vendedor_names.get(vendedor_id, "Usuário Removido"),
            "total_sales": result["total_sales"],
            "total_revenue": result["total_revenue"],
            "total_quantity": result["total_quantity"],
            "average_sale_value": result["total_revenue"] / result["total_sales"] if result["total_sales"] > 0 else 0
        })
    
    return top_performers

@api_router.get("/sales/reports/all")
async def get_all_sales_reports(
    current_user: User = Depends(get_current_user),
    vendedor_id: Optional[str] = Query(None),
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    payment_method: Optional[str] = Query(None)
):
    """Get sales reports for all salespersons (admin/manager only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para acessar relatórios gerais")
    
    # Build query
    query = {}
    
    if vendedor_id:
        query["vendedor_id"] = vendedor_id
    
    if month and year:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        query["sale_date"] = {"$gte": start_date, "$lt": end_date}
    
    if payment_method:
        query["payment_method"] = payment_method
    
    # Get sales with client, product, and salesperson info
    pipeline = [
        {"$match": query},
        {"$lookup": {
            "from": "clients",
            "localField": "client_id",
            "foreignField": "id",
            "as": "client"
        }},
        {"$lookup": {
            "from": "products", 
            "localField": "product_id",
            "foreignField": "id",
            "as": "product"
        }},
        {"$lookup": {
            "from": "users",
            "localField": "vendedor_id",
            "foreignField": "id", 
            "as": "vendedor"
        }},
        {"$unwind": "$client"},
        {"$unwind": "$product"},
        {"$unwind": "$vendedor"},
        {"$sort": {"sale_date": -1}}
    ]
    
    sales = await db.sales.aggregate(pipeline).to_list(1000)
    
    reports = []
    for sale in sales:
        reports.append({
            "sale_id": sale["id"],
            "client_name": sale["client"]["name"],
            "client_cpf": sale["client"]["cpf"],
            "product_name": sale["product"]["name"],
            "quantity": sale["quantity"],
            "unit_price": sale["unit_price"],
            "total_value": sale["total_value"], 
            "payment_method": sale["payment_method"],
            "sale_date": sale["sale_date"],
            "vendedor_name": sale["vendedor"]["username"],
            "vendedor_id": sale["vendedor_id"],
            "day": sale["sale_date"].day,
            "month": sale["sale_date"].month,
            "year": sale["sale_date"].year
        })
    
    return reports

@api_router.get("/sales/performance")
async def get_sales_performance(
    current_user: User = Depends(get_current_user),
    year: Optional[int] = Query(None)
):
    """Get sales performance metrics (admin/manager only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Sem permissão para acessar métricas de desempenho")
    
    current_year = year or datetime.utcnow().year
    
    # Performance by salesperson and month
    pipeline = [
        {"$match": {
            "sale_date": {
                "$gte": datetime(current_year, 1, 1),
                "$lt": datetime(current_year + 1, 1, 1)
            }
        }},
        {"$group": {
            "_id": {
                "vendedor_id": "$vendedor_id",
                "month": {"$month": "$sale_date"}
            },
            "total_sales": {"$sum": 1},
            "total_value": {"$sum": "$total_value"}
        }},
        {"$lookup": {
            "from": "users",
            "localField": "_id.vendedor_id",
            "foreignField": "id",
            "as": "vendedor"
        }},
        {"$unwind": "$vendedor"},
        {"$sort": {"_id.month": 1}}
    ]
    
    performance_data = await db.sales.aggregate(pipeline).to_list(1000)
    
    # Organize data by salesperson
    performance_by_salesperson = {}
    for data in performance_data:
        vendedor_id = data["_id"]["vendedor_id"]
        vendedor_name = data["vendedor"]["username"]
        month = data["_id"]["month"]
        
        if vendedor_id not in performance_by_salesperson:
            performance_by_salesperson[vendedor_id] = {
                "vendedor_name": vendedor_name,
                "monthly_data": [0] * 12,  # 12 months
                "monthly_values": [0.0] * 12,
                "total_sales": 0,
                "total_value": 0.0
            }
        
        performance_by_salesperson[vendedor_id]["monthly_data"][month - 1] = data["total_sales"]
        performance_by_salesperson[vendedor_id]["monthly_values"][month - 1] = data["total_value"]
        performance_by_salesperson[vendedor_id]["total_sales"] += data["total_sales"]
        performance_by_salesperson[vendedor_id]["total_value"] += data["total_value"]
    
    return {
        "year": current_year,
        "performance": performance_by_salesperson
    }

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
    total_entrada = sum(t["amount"] for t in transactions if t["type"] in ["entrada", "pagamento_cliente"])
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
        table_data = [["Data", "Tipo", "Valor", "Descrição", "Pagamento", "Cliente", "Usuário"]]
        
        for transaction in transactions:
            tipo = transaction["type"].upper()
            if tipo == "PAGAMENTO_CLIENTE":
                tipo = "PAG.CLIENTE"
            
            table_data.append([
                transaction["created_at"].strftime("%d/%m/%Y"),
                tipo,
                f"R$ {transaction['amount']:.2f}",
                (transaction["description"][:25] + "..." if len(transaction["description"]) > 25 else transaction["description"]),
                transaction["payment_method"].upper(),
                transaction.get("client_name", "")[:15] or "-",
                transaction.get("user_name", "SISTEMA")[:10]
            ])
        
        trans_table = Table(table_data, colWidths=[0.8*inch, 0.8*inch, 0.8*inch, 1.8*inch, 0.8*inch, 1*inch, 0.8*inch])
        trans_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
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
async def get_activity_logs(
    current_user: User = Depends(get_current_user),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    user_name: Optional[str] = Query(None, description="Filter by user name"),
    activity_type: Optional[str] = Query(None, description="Filter by activity type")
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas administradores podem ver logs de atividade")
    
    # Build query filters
    query = {}
    
    if start_date or end_date:
        date_filter = {}
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                date_filter["$gte"] = start_dt
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de data inválido para start_date")
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                date_filter["$lte"] = end_dt
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de data inválido para end_date")
        
        query["timestamp"] = date_filter
    
    if user_name:
        query["user_name"] = {"$regex": user_name.upper(), "$options": "i"}
    
    if activity_type:
        query["activity_type"] = activity_type
    
    logs = await db.activity_logs.find(query).sort("timestamp", -1).to_list(1000)
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