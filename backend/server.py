from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext
import io
import csv
import json
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest
import pandas as pd

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"

# LLM and Payment Keys
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', '')

# Upload directory
UPLOAD_DIR = Path("/app/backend/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Subscription Plans
SUBSCRIPTION_PLANS = {
    "free": {"name": "Gratuito", "pages_limit": 50, "price": 0.0, "currency": "eur"},
    "starter": {"name": "Inicial", "pages_limit": 400, "price": 30.0, "currency": "eur"},
    "pro": {"name": "Profissional", "pages_limit": 4000, "price": 99.0, "currency": "eur"}
}

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    created_at: str

class Subscription(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    plan_type: str
    status: str
    pages_limit: int
    pages_used_this_month: int
    current_period_start: str
    current_period_end: str

class Conversion(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    original_filename: str
    bank_name: str
    pages_count: int
    status: str
    created_at: str
    extracted_data: Optional[Dict] = None

class CheckoutRequest(BaseModel):
    plan_type: str
    origin_url: str

class PaymentTransaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    session_id: str
    amount: float
    currency: str
    payment_status: str
    status: str
    metadata: Dict[str, Any]
    created_at: str

# Helper functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_user_subscription(user_id: str):
    subscription = await db.subscriptions.find_one({"user_id": user_id, "status": "active"}, {"_id": 0})
    if not subscription:
        # Create free subscription
        subscription = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "plan_type": "free",
            "status": "active",
            "pages_limit": 50,
            "pages_used_this_month": 0,
            "current_period_start": datetime.now(timezone.utc).isoformat(),
            "current_period_end": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        }
        await db.subscriptions.insert_one(subscription)
    return subscription

async def extract_transactions_from_pdf(file_path: str, bank_name: str) -> Dict:
    """Extract transactions from PDF using Gemini AI"""
    
    prompt = f"""
Analise este extrato bancário do banco {bank_name} (Portugal) e extraia TODAS as transações visíveis.

INSTRUÇÕES IMPORTANTES:
1. Extraia TODAS as transações que encontrar no documento
2. Para cada transação, identifique: data, descrição completa, valor (débito ou crédito)
3. Identifique o saldo inicial e final se visível
4. Se possível, identifique categorias fiscais portuguesas (IRS, Segurança Social)

Retorne APENAS um objeto JSON válido, sem texto adicional, neste formato exato:
{{
  "banco": "{bank_name}",
  "conta": "número da conta se visível",
  "periodo": "DD/MM/YYYY - DD/MM/YYYY",
  "saldo_inicial": 0.00,
  "saldo_final": 0.00,
  "transacoes": [
    {{
      "data": "DD/MM/YYYY",
      "descricao": "descrição completa da transação",
      "valor": 0.00,
      "tipo": "débito",
      "categoria_fiscal": null
    }},
    {{
      "data": "DD/MM/YYYY", 
      "descricao": "descrição completa",
      "valor": 0.00,
      "tipo": "crédito",
      "categoria_fiscal": null
    }}
  ]
}}

IMPORTANTE: Retorne APENAS o JSON, sem explicações ou texto adicional.
"""
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=str(uuid.uuid4()),
            system_message="És um assistente especializado em análise de extratos bancários portugueses. Retorna APENAS JSON válido, sem texto adicional."
        ).with_model("gemini", "gemini-2.0-flash")
        
        pdf_file = FileContentWithMimeType(
            file_path=file_path,
            mime_type="application/pdf"
        )
        
        user_message = UserMessage(
            text=prompt,
            file_contents=[pdf_file]
        )
        
        response = await chat.send_message(user_message)
        
        # Parse JSON from response - handle various formats
        response_text = response.strip()
        
        # Remove markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Remove any leading/trailing text before/after JSON
        # Find the first { and last }
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            response_text = response_text[start_idx:end_idx+1]
        
        # Try to parse JSON
        try:
            extracted_data = json.loads(response_text)
        except json.JSONDecodeError as je:
            logging.error(f"JSON parse error: {str(je)}")
            logging.error(f"Response text: {response_text[:500]}")
            
            # Return a basic structure with error info
            extracted_data = {
                "banco": bank_name,
                "periodo": "Não identificado",
                "saldo_inicial": 0.0,
                "saldo_final": 0.0,
                "transacoes": [],
                "erro": "Erro ao processar resposta da IA. Por favor, tente novamente."
            }
        
        return extracted_data
    except Exception as e:
        logging.error(f"Error extracting PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar PDF: {str(e)}")

# Auth Routes
@api_router.post("/auth/register")
async def register(user_data: UserRegister):
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email já registrado")
    
    # Create user
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": user_data.email,
        "password_hash": pwd_context.hash(user_data.password),
        "name": user_data.name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user)
    
    # Create free subscription
    subscription = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "plan_type": "free",
        "status": "active",
        "pages_limit": 50,
        "pages_used_this_month": 0,
        "current_period_start": datetime.now(timezone.utc).isoformat(),
        "current_period_end": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    }
    await db.subscriptions.insert_one(subscription)
    
    # Create token
    token = create_access_token({"sub": user_id})
    
    return {
        "token": token,
        "user": {"id": user_id, "email": user_data.email, "name": user_data.name}
    }

@api_router.post("/auth/login")
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not pwd_context.verify(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    
    token = create_access_token({"sub": user["id"]})
    
    return {
        "token": token,
        "user": {"id": user["id"], "email": user["email"], "name": user["name"]}
    }

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {"id": current_user["id"], "email": current_user["email"], "name": current_user["name"]}

# Subscription Routes
@api_router.get("/subscriptions/plans")
async def get_plans():
    return SUBSCRIPTION_PLANS

@api_router.get("/subscriptions/current")
async def get_current_subscription(current_user: dict = Depends(get_current_user)):
    subscription = await get_user_subscription(current_user["id"])
    return subscription

# Payment Routes
@api_router.post("/payments/checkout/session")
async def create_checkout_session(checkout_req: CheckoutRequest, current_user: dict = Depends(get_current_user)):
    if checkout_req.plan_type not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="Plano inválido")
    
    plan = SUBSCRIPTION_PLANS[checkout_req.plan_type]
    if plan["price"] == 0:
        raise HTTPException(status_code=400, detail="Plano gratuito não requer pagamento")
    
    # Create URLs
    success_url = f"{checkout_req.origin_url}/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{checkout_req.origin_url}/pricing"
    
    # Initialize Stripe
    stripe_checkout = StripeCheckout(
        api_key=STRIPE_API_KEY,
        webhook_url=f"{checkout_req.origin_url}/api/webhook/stripe"
    )
    
    # Create checkout session
    session_request = CheckoutSessionRequest(
        amount=plan["price"],
        currency=plan["currency"],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": current_user["id"],
            "plan_type": checkout_req.plan_type
        }
    )
    
    session = await stripe_checkout.create_checkout_session(session_request)
    
    # Create payment transaction
    transaction = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "session_id": session.session_id,
        "amount": plan["price"],
        "currency": plan["currency"],
        "payment_status": "pending",
        "status": "initiated",
        "metadata": {"plan_type": checkout_req.plan_type},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.payment_transactions.insert_one(transaction)
    
    return {"url": session.url, "session_id": session.session_id}

@api_router.get("/payments/checkout/status/{session_id}")
async def get_checkout_status(session_id: str, current_user: dict = Depends(get_current_user)):
    # Check if already processed
    transaction = await db.payment_transactions.find_one({"session_id": session_id, "user_id": current_user["id"]}, {"_id": 0})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    
    if transaction["payment_status"] == "paid":
        return transaction
    
    # Get status from Stripe
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
    checkout_status = await stripe_checkout.get_checkout_status(session_id)
    
    # Update transaction
    if checkout_status.payment_status == "paid" and transaction["payment_status"] != "paid":
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "paid", "status": "completed"}}
        )
        
        # Update subscription
        plan_type = transaction["metadata"]["plan_type"]
        plan = SUBSCRIPTION_PLANS[plan_type]
        
        # Deactivate old subscriptions
        await db.subscriptions.update_many(
            {"user_id": current_user["id"], "status": "active"},
            {"$set": {"status": "cancelled"}}
        )
        
        # Create new subscription
        new_subscription = {
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "plan_type": plan_type,
            "status": "active",
            "pages_limit": plan["pages_limit"],
            "pages_used_this_month": 0,
            "current_period_start": datetime.now(timezone.utc).isoformat(),
            "current_period_end": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        }
        await db.subscriptions.insert_one(new_subscription)
    
    updated_transaction = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    return updated_transaction

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
    webhook_response = await stripe_checkout.handle_webhook(body, signature)
    
    if webhook_response.payment_status == "paid":
        # Update transaction
        await db.payment_transactions.update_one(
            {"session_id": webhook_response.session_id},
            {"$set": {"payment_status": "paid", "status": "completed"}}
        )
    
    return {"status": "ok"}

# Conversion Routes
@api_router.post("/conversions/upload")
async def upload_statement(
    file: UploadFile = File(...),
    bank_name: str = "Millennium",
    current_user: dict = Depends(get_current_user)
):
    # Check subscription
    subscription = await get_user_subscription(current_user["id"])
    
    # Estimate pages (rough estimate: 1 page per 50KB)
    file_content = await file.read()
    estimated_pages = max(1, len(file_content) // (50 * 1024))
    
    if subscription["pages_used_this_month"] + estimated_pages > subscription["pages_limit"]:
        raise HTTPException(status_code=403, detail="Limite de páginas atingido. Faça upgrade do seu plano.")
    
    # Save file
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}.pdf"
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Create conversion record
    conversion = {
        "id": file_id,
        "user_id": current_user["id"],
        "original_filename": file.filename,
        "bank_name": bank_name,
        "pages_count": estimated_pages,
        "status": "processing",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.conversions.insert_one(conversion)
    
    try:
        # Extract transactions
        extracted_data = await extract_transactions_from_pdf(str(file_path), bank_name)
        
        # Generate CSV
        csv_path = UPLOAD_DIR / f"{file_id}.csv"
        df = pd.DataFrame(extracted_data.get("transacoes", []))
        df.to_csv(csv_path, index=False)
        
        # Generate Excel
        excel_path = UPLOAD_DIR / f"{file_id}.xlsx"
        df.to_excel(excel_path, index=False, sheet_name="Transações")
        
        # Update conversion
        await db.conversions.update_one(
            {"id": file_id},
            {"$set": {
                "status": "completed",
                "extracted_data": extracted_data
            }}
        )
        
        # Update subscription usage
        await db.subscriptions.update_one(
            {"id": subscription["id"]},
            {"$inc": {"pages_used_this_month": estimated_pages}}
        )
        
        return {"conversion_id": file_id, "status": "completed"}
    except Exception as e:
        await db.conversions.update_one(
            {"id": file_id},
            {"$set": {"status": "failed"}}
        )
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/conversions")
async def get_conversions(current_user: dict = Depends(get_current_user)):
    conversions = await db.conversions.find({"user_id": current_user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return conversions

@api_router.get("/conversions/{conversion_id}")
async def get_conversion(conversion_id: str, current_user: dict = Depends(get_current_user)):
    conversion = await db.conversions.find_one({"id": conversion_id, "user_id": current_user["id"]}, {"_id": 0})
    if not conversion:
        raise HTTPException(status_code=404, detail="Conversão não encontrada")
    return conversion

@api_router.get("/conversions/{conversion_id}/download/csv")
async def download_csv(conversion_id: str, current_user: dict = Depends(get_current_user)):
    conversion = await db.conversions.find_one({"id": conversion_id, "user_id": current_user["id"]}, {"_id": 0})
    if not conversion:
        raise HTTPException(status_code=404, detail="Conversão não encontrada")
    
    csv_path = UPLOAD_DIR / f"{conversion_id}.csv"
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo CSV não encontrado")
    
    return FileResponse(csv_path, media_type="text/csv", filename=f"{conversion['original_filename']}.csv")

@api_router.get("/conversions/{conversion_id}/download/excel")
async def download_excel(conversion_id: str, current_user: dict = Depends(get_current_user)):
    conversion = await db.conversions.find_one({"id": conversion_id, "user_id": current_user["id"]}, {"_id": 0})
    if not conversion:
        raise HTTPException(status_code=404, detail="Conversão não encontrada")
    
    excel_path = UPLOAD_DIR / f"{conversion_id}.xlsx"
    if not excel_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo Excel não encontrado")
    
    return FileResponse(excel_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=f"{conversion['original_filename']}.xlsx")

    @app.get("/health")
async def health():
    db_ok = False
    try:
        if db:
            await db.command("ping")
            db_ok = True
    except Exception:
        db_ok = False
    return {"ok": True, "db": db_ok}

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
