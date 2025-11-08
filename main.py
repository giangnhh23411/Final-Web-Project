# main.py (FastAPI + Motor)
import os
import uvicorn
from typing import List, Optional, Any, Dict, Literal
from fastapi import FastAPI, HTTPException, status, Body, Query, Form, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from bson import ObjectId
import re
import aiofiles
import bleach
from contextlib import asynccontextmanager
import datetime
from passlib.hash import bcrypt
from passlib.context import CryptContext

# -------- CONFIG --------
MONGO_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://plwebdatabase123:PLWebsite123@plweb.escgc7n.mongodb.net/?retryWrites=true&w=majority&appName=PLWeb"
)
DB_NAME = os.getenv("MONGODB_DB", "plweb")
API_PREFIX = "/api"
PAGE_SIZE_DEFAULT = 20

# Project paths - detect workspace root dynamically
# Get the directory where main.py is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Project files are in Final-Web-Project-main subdirectory (same level as main.py)
PROJECT_DIR = os.path.join(SCRIPT_DIR, "Final-Web-Project-main")

# Static directories
ASSETS_DIR = os.path.join(PROJECT_DIR, "Assets")
CLIENTSITE_DIR = os.path.join(PROJECT_DIR, "ClientSite")
ADMINSITE_DIR = os.path.join(PROJECT_DIR, "AdminSite")
INDEX_HTML = os.path.join(PROJECT_DIR, "index.html")

# Figma/Admin paths (for backward compatibility)
PROJECT_ROOT = PROJECT_DIR
figma_dir = os.path.join(PROJECT_ROOT, "Figma")
AVATAR_DIR = os.path.join(ADMINSITE_DIR, "images", "avatar")
os.makedirs(AVATAR_DIR, exist_ok=True)

MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2 MB
ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "gif"}

# Uploads cho blog images/files
BLOG_UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")
os.makedirs(BLOG_UPLOAD_DIR, exist_ok=True)
# public url base (dùng để build link trả về sau upload)
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# -------- Lifespan handler (thay thế on_event) --------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code: ensure unique index on sku/slug (safe-guarded with try/except)
    try:
        await products_col.create_index("sku", unique=True)
        await categories_col.create_index("slug", unique=True)
    except Exception:
        pass
    yield
    # Optional shutdown code

# -------- FastAPI app --------
app = FastAPI(title="Products API (FastAPI + MongoDB)", lifespan=lifespan)

# Mount static directories
print(f"[DEBUG] ASSETS_DIR: {ASSETS_DIR}")
print(f"[DEBUG] ASSETS_DIR exists: {os.path.isdir(ASSETS_DIR)}")
if os.path.isdir(ASSETS_DIR):
    app.mount("/Assets", StaticFiles(directory=ASSETS_DIR, html=True), name="assets")
    print(f"[DEBUG] Mounted /Assets -> {ASSETS_DIR}")
if os.path.isdir(CLIENTSITE_DIR):
    app.mount("/ClientSite", StaticFiles(directory=CLIENTSITE_DIR, html=True), name="clientsite")
    print(f"[DEBUG] Mounted /ClientSite -> {CLIENTSITE_DIR}")
if os.path.isdir(ADMINSITE_DIR):
    app.mount("/AdminSite", StaticFiles(directory=ADMINSITE_DIR, html=True), name="adminsite")
    print(f"[DEBUG] Mounted /AdminSite -> {ADMINSITE_DIR}")
# Mount static Figma folder so frontend can request /Figma/... (for backward compatibility)
if os.path.isdir(figma_dir):
    app.mount("/Figma", StaticFiles(directory=figma_dir, html=True), name="figma")
    print(f"[DEBUG] Mounted /Figma -> {figma_dir}")

# CORS - chỉnh origin khi deploy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve index.html at root and /index.html
@app.get("/")
async def root_index():
    if os.path.isfile(INDEX_HTML):
        return FileResponse(INDEX_HTML)
    # Fallback redirect
    return RedirectResponse(url="/index.html")

@app.get("/index.html")
async def index_html():
    if os.path.isfile(INDEX_HTML):
        return FileResponse(INDEX_HTML)
    raise HTTPException(status_code=404, detail="index.html not found")

# Handle directory access for ClientSite and AdminSite
@app.get("/ClientSite/")
async def clientsite_index():
    # Redirect to main index or show available pages
    return RedirectResponse(url="/")

@app.get("/AdminSite/")
async def adminsite_index():
    # Check if there's a dashboard or index in AdminSite
    admin_index = os.path.join(ADMINSITE_DIR, "HTML", "dashboard.html")
    if os.path.isfile(admin_index):
        return FileResponse(admin_index)
    return RedirectResponse(url="/")

# -------- Mongo client (motor) --------
client = AsyncIOMotorClient(MONGO_URI, server_api=ServerApi("1"))
db = client[DB_NAME]
products_col = db["products"]
categories_col = db["categories"]
users_col = db["users"]

# Password context for verification
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
carts_col = db["carts"]
orders_col = db["orders"]
order_items_col = db["order_items"]
vouchers_col = db["vouchers"]
blogs_col = db["blogs"]
invoices_col = db["invoices"]

# -------- Helpers --------
def voucher_to_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = doc_to_dict(doc)
    for k in ('start_at', 'end_at'):
        if k in out and isinstance(out[k], datetime.datetime):
            out[k] = out[k].isoformat() + "Z"
    # convert product ids to strings if present
    if "applicable_product_ids" in out and isinstance(out["applicable_product_ids"], list):
        out["applicable_product_ids"] = [str(x) if isinstance(x, ObjectId) else x for x in out["applicable_product_ids"]]
    # ensure numeric fields are present for UI formatting (toFixed)
    try:
        out["value"] = float(out.get("value", 0) or 0)
    except Exception:
        out["value"] = 0.0
    try:
        out["usage_limit"] = int(out.get("usage_limit", 0) or 0)
    except Exception:
        out["usage_limit"] = 0
    try:
        out["min_order_value"] = float(out.get("min_order_value", 0) or 0)
    except Exception:
        out["min_order_value"] = 0.0
    return out

# --- simple HTML sanitizer (bleach) ---
def normalize_ymd(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    try:
        # accept YYYY-MM-DD or ISO-like -> return YYYY-MM-DD
        d = datetime.date.fromisoformat(s)
        return d.isoformat()
    except Exception:
        return None

ALLOWED_TAGS = list(bleach.sanitizer.ALLOWED_TAGS) + [
    "p","div","span","br","h1","h2","h3","h4","h5","img",
    "ul","ol","li","strong","em","a","blockquote","pre","code"
]
ALLOWED_ATTRS = {
    "*": ["class","style"],
    "a": ["href","title","target","rel"],
    "img": ["src","alt","width","height"]
}
def sanitize_html(html: Optional[str]) -> str:
    if not html:
        return ""
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


def extract_date(value: Any) -> Optional[datetime.datetime]:
    if isinstance(value, str):
        try:
            return datetime.datetime.fromisoformat(value)
        except ValueError:
            return None
    return None

def order_doc_to_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return {}
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    if "user_id" in out and isinstance(out["user_id"], ObjectId):
        out["user_id"] = str(out["user_id"])
    for k in ("created_at", "updated_at"):
        if k in out and isinstance(out[k], datetime.datetime):
            out[k] = out[k].isoformat() + "Z"
    if "items" in out and isinstance(out["items"], list):
        for it in out["items"]:
            if "unit_price" in it:
                it["unit_price"] = float(it["unit_price"])
            if "line_total" in it:
                it["line_total"] = float(it["line_total"])
            if "quantity" in it:
                it["quantity"] = int(it["quantity"])
    return out

def oid_from_str(s: Optional[str]) -> Optional[ObjectId]:
    if not s:
        return None
    if isinstance(s, ObjectId):
        return s
    if isinstance(s, str) and re.fullmatch(r"[0-9a-fA-F]{24}", s):
        return ObjectId(s)
    return None

def doc_to_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return {}
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    if "category_id" in out and isinstance(out["category_id"], ObjectId):
        out["category_id"] = str(out["category_id"])
    if "user_id" in out and isinstance(out["user_id"], ObjectId):
        out["user_id"] = str(out["user_id"])
    if "order_id" in out and isinstance(out["order_id"], ObjectId):
        out["order_id"] = str(out["order_id"])
    if "product_id" in out and isinstance(out["product_id"], ObjectId):
        out["product_id"] = str(out["product_id"])
    return out

def blog_doc_to_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return {}
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    # convert datetime if present
    for k in ("created_at", "updated_at"):
        if k in out and isinstance(out[k], datetime.datetime):
            out[k] = out[k].isoformat() + "Z"
    return out

# -------- Pydantic models --------
# -------- Pydantic models for Vouchers --------
class VoucherBase(BaseModel):
    code: Optional[str] = None
    type: Optional[Literal['percent', 'fixed']] = None
    value: Optional[float] = 0.0
    description: Optional[str] = None
    start_at: Optional[datetime.datetime] = None
    end_at: Optional[datetime.datetime] = None
    usage_limit: Optional[int] = 0
    min_order_value: Optional[float] = 0.0
    status: Optional[Literal['active', 'expired', 'disabled']] = 'active'
    applicable_product_ids: Optional[List[str]] = None

class VoucherCreate(VoucherBase):
    code: str = Field(..., description="Voucher code required")
    type: Literal['percent', 'fixed'] = Field(...)
    value: float = Field(..., gt=0)
    start_at: datetime.datetime
    end_at: datetime.datetime
    usage_limit: int = Field(..., ge=0)

class VoucherUpdate(BaseModel):
    type: Optional[str]
    value: Optional[float]
    description: Optional[str]
    start_at: Optional[datetime.datetime]
    end_at: Optional[datetime.datetime]
    usage_limit: Optional[int]
    min_order_value: Optional[float]
    status: Optional[str]
    applicable_product_ids: Optional[List[str]]

class ProductBase(BaseModel):
    sku: Optional[str] = Field(None, description="Unique SKU")
    name: Optional[str] = None
    description: Optional[str] = None
    images: Optional[List[str]] = []
    price: Optional[float] = 0.0
    stock_quantity: Optional[int] = 0
    is_active: Optional[bool] = True
    category_id: Optional[str] = None

    @field_validator("price", mode="before")
    def price_to_float(cls, v):
        try:
            return float(v) if v is not None else 0.0
        except:
            raise ValueError("price must be numeric")

    @field_validator("stock_quantity", mode="before")
    def qty_to_int(cls, v):
        try:
            return int(v or 0)
        except:
            raise ValueError("stock_quantity must be integer")

class ProductCreate(ProductBase):
    sku: str = Field(..., description="SKU is required")
    name: str = Field(..., description="Name is required")

class ProductUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    images: Optional[List[str]]
    price: Optional[float]
    stock_quantity: Optional[int]
    is_active: Optional[bool]
    category_id: Optional[str]

class CategoryBase(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    is_active: Optional[bool] = True

class CategoryCreate(CategoryBase):
    name: str = Field(..., description="Name is required")
    slug: str = Field(..., description="Slug is required")

class CategoryUpdate(BaseModel):
    name: Optional[str]
    slug: Optional[str]
    is_active: Optional[bool]

class UserBase(BaseModel):
    email: Optional[str] = None
    password_hash: Optional[str] = None
    full_name: Optional[str] = None
    status: Optional[str] = "active"
    role: Optional[str] = "customer"
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None

class UserCreate(UserBase):
    email: str = Field(..., description="Email is required")
    password_hash: str = Field(..., description="Password hash is required")
    full_name: str = Field(..., description="Full name is required")

class UserUpdate(BaseModel):
    password_hash: Optional[str]
    full_name: Optional[str]
    status: Optional[str]
    role: Optional[str]
    updated_at: Optional[Any]

class OrderBase(BaseModel):
    order_no: Optional[str] = None
    user_id: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = []
    shipping_address: Optional[str] = None
    payment_method: Optional[str] = None
    shipping_fee: Optional[float] = 0.0
    subtotal: Optional[float] = 0.0
    total_amount: Optional[float] = 0.0
    order_status: Optional[str] = "Pending"
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None

class OrderCreate(OrderBase):
    order_no: str = Field(..., description="Order number is required")
    user_id: str = Field(..., description="User ID is required")

class OrderUpdate(BaseModel):
    subtotal: Optional[float]
    total_amount: Optional[float]
    order_status: Optional[str]
    updated_at: Optional[Any]

# -------- Blog models --------
class BlogBase(BaseModel):
    title: str
    category: str
    content: str
    lead: Optional[str] = None
    date_display: Optional[str] = None
    attached_file: Optional[str] = None
    tags: Optional[List[str]] = None
    like_count: Optional[int] = 0
    comment_count: Optional[int] = 0
    share_count: Optional[int] = 0

class BlogCreate(BlogBase):
    pass

class BlogUpdate(BaseModel):
    title: Optional[str]
    category: Optional[str]
    content: Optional[str]
    lead: Optional[str]
    date_display: Optional[str]
    attached_file: Optional[str]
    tags: Optional[List[str]]
    like_count: Optional[int]
    comment_count: Optional[int]
    share_count: Optional[int]

# -------- Blog endpoints --------
@app.get(API_PREFIX + "/blogs", status_code=200)
async def list_blogs(
    page: int = Query(1, ge=1),
    limit: int = Query(PAGE_SIZE_DEFAULT, ge=1, le=500),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort: Optional[str] = Query(None)   # likes-desc, comments-desc, shares-desc
):
    skip = (page - 1) * limit
    q: Dict[str, Any] = {}

    if category:
        q["category"] = category

    if search:
        q["$or"] = [
            {"title": {"$regex": re.escape(search), "$options": "i"}},
            {"lead": {"$regex": re.escape(search), "$options": "i"}},
            {"content": {"$regex": re.escape(search), "$options": "i"}}
        ]

    # date range filtering: assume date_display stored as 'YYYY-MM-DD' or similar.
    df = normalize_ymd(date_from)
    dt = normalize_ymd(date_to)
    if df or dt:
        # if date_display stored as string 'YYYY-MM-DD', lexicographic compare works
        range_q = {}
        if df:
            range_q["$gte"] = df
        if dt:
            range_q["$lte"] = dt
        q["date_display"] = range_q

    # sort specification
    sort_spec = []
    if sort == "likes-desc":
        sort_spec = [("like_count", -1)]
    elif sort == "comments-desc":
        sort_spec = [("comment_count", -1)]
    elif sort == "shares-desc":
        sort_spec = [("share_count", -1)]
    else:
        # default: newest by created_at then _id
        sort_spec = [("created_at", -1), ("_id", -1)]

    # fetch
    total = await blogs_col.count_documents(q)
    cursor = blogs_col.find(q).sort(sort_spec).skip(skip).limit(limit)
    items = []
    async for doc in cursor:
        items.append(blog_doc_to_dict(doc))
    return {"items": items, "total": total, "page": page, "limit": limit}

@app.get(API_PREFIX + "/blogs/{id}", status_code=200)
async def get_blog(id: str):
    oid = oid_from_str(id)
    if not oid:
        raise HTTPException(status_code=400, detail="Invalid blog id")
    doc = await blogs_col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Blog not found")
    return blog_doc_to_dict(doc)

@app.post(API_PREFIX + "/blogs", status_code=201)
async def create_blog(payload: BlogCreate = Body(...)):
    data = payload.dict()
    data["content"] = sanitize_html(data.get("content", ""))
    # normalize date_display to YYYY-MM-DD if possible
    if data.get("date_display"):
        nd = normalize_ymd(data["date_display"])
        if nd:
            data["date_display"] = nd
    now = datetime.datetime.utcnow()
    data["created_at"] = now
    data["updated_at"] = now
    try:
        res = await blogs_col.insert_one(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    doc = await blogs_col.find_one({"_id": res.inserted_id})
    return blog_doc_to_dict(doc)

@app.put(API_PREFIX + "/blogs/{id}", status_code=200)
@app.patch(API_PREFIX + "/blogs/{id}", status_code=200)
async def update_blog(id: str, payload: BlogUpdate = Body(...)):
    oid = oid_from_str(id)
    if not oid:
        raise HTTPException(status_code=400, detail="Invalid blog id")
    update_data = {k: v for k, v in payload.dict().items() if v is not None}
    if "content" in update_data:
        update_data["content"] = sanitize_html(update_data["content"])
    if "date_display" in update_data:
        nd = normalize_ymd(update_data.get("date_display"))
        if nd:
            update_data["date_display"] = nd
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_data["updated_at"] = datetime.datetime.utcnow()
    res = await blogs_col.update_one({"_id": oid}, {"$set": update_data})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Blog not found")
    doc = await blogs_col.find_one({"_id": oid})
    return blog_doc_to_dict(doc)

@app.delete(API_PREFIX + "/blogs/{id}", status_code=200)
async def delete_blog(id: str):
    oid = oid_from_str(id)
    if not oid:
        raise HTTPException(status_code=400, detail="Invalid blog id")
    res = await blogs_col.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Blog not found")
    return {"deleted": True}

# -------- Vouchers endpoints --------
@app.get(API_PREFIX + "/vouchers", status_code=200)
async def list_vouchers(
    page: int = Query(1, ge=1),
    limit: int = Query(PAGE_SIZE_DEFAULT, ge=1, le=500),
    code: Optional[str] = Query(None),
    status_q: Optional[str] = Query(None),
    type_q: Optional[str] = Query(None),
    start_from: Optional[str] = Query(None),
    end_to: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None)
):
    skip = (page - 1) * limit
    q: Dict[str, Any] = {}
    if code:
        q["code"] = {"$regex": re.escape(code), "$options": "i"}
    if status_q:
        q["status"] = status_q
    if type_q:
        q["type"] = type_q
    # date range filters (ISO datetime expected)
    if start_from:
        dt = extract_date(start_from)
        if dt:
            q["start_at"] = {"$gte": dt}
    if end_to:
        dt = extract_date(end_to)
        if dt:
            q.setdefault("end_at", {})["$lte"] = dt
    if product_id:
        pid = oid_from_str(product_id)
        q["applicable_product_ids"] = pid if pid else product_id
    total = await vouchers_col.count_documents(q)
    cursor = vouchers_col.find(q).sort([("start_at", -1), ("_id", -1)]).skip(skip).limit(limit)
    items = []
    async for doc in cursor:
        items.append(voucher_to_dict(doc))
    return {"data": items, "paging": {"total": total, "page": page, "pageSize": limit}}

@app.get(API_PREFIX + "/vouchers/{code}", status_code=200)
async def get_voucher(code: str):
    doc = await vouchers_col.find_one({"code": code})
    if not doc:
        raise HTTPException(status_code=404, detail="Voucher not found")
    return voucher_to_dict(doc)

@app.post(API_PREFIX + "/vouchers", status_code=201)
async def create_voucher(payload: VoucherCreate = Body(...)):
    data = payload.dict()
    # basic normalization
    if data.get("type") not in ("percent", "fixed"):
        raise HTTPException(status_code=400, detail="type must be 'percent' or 'fixed'")
    try:
        data["value"] = float(data.get("value", 0))
        data["usage_limit"] = int(data.get("usage_limit", 0))
        if data.get("min_order_value") is not None:
            data["min_order_value"] = float(data.get("min_order_value") or 0)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid numeric fields")
    # map product ids if provided
    apids = data.get("applicable_product_ids")
    if isinstance(apids, list):
        mapped: List[Any] = []
        for s in apids:
            o = oid_from_str(s)
            mapped.append(o if o else s)
        data["applicable_product_ids"] = mapped
    try:
        res = await vouchers_col.insert_one(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    doc = await vouchers_col.find_one({"_id": res.inserted_id})
    return voucher_to_dict(doc)

@app.put(API_PREFIX + "/vouchers/{code}", status_code=200)
@app.patch(API_PREFIX + "/vouchers/{code}", status_code=200)
async def update_voucher(code: str, payload: VoucherUpdate = Body(...)):
    update_data = {k: v for k, v in payload.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "type" in update_data and update_data["type"] not in ("percent", "fixed"):
        raise HTTPException(status_code=400, detail="type must be 'percent' or 'fixed'")
    if "value" in update_data:
        try:
            update_data["value"] = float(update_data["value"])
        except Exception:
            raise HTTPException(status_code=400, detail="value must be numeric")
    if "usage_limit" in update_data:
        try:
            update_data["usage_limit"] = int(update_data["usage_limit"])
        except Exception:
            raise HTTPException(status_code=400, detail="usage_limit must be integer")
    if "min_order_value" in update_data and update_data["min_order_value"] is not None:
        try:
            update_data["min_order_value"] = float(update_data["min_order_value"])
        except Exception:
            raise HTTPException(status_code=400, detail="min_order_value must be numeric")
    if "applicable_product_ids" in update_data and isinstance(update_data["applicable_product_ids"], list):
        mapped: List[Any] = []
        for s in update_data["applicable_product_ids"]:
            o = oid_from_str(s)
            mapped.append(o if o else s)
        update_data["applicable_product_ids"] = mapped
    res = await vouchers_col.update_one({"code": code}, {"$set": update_data})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Voucher not found")
    doc = await vouchers_col.find_one({"code": code})
    return voucher_to_dict(doc)

@app.delete(API_PREFIX + "/vouchers/{code}", status_code=200)
async def delete_voucher(code: str):
    res = await vouchers_col.delete_one({"code": code})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Voucher not found")
    return {"deleted": True}

# -------- Invoices models + endpoints --------
class InvoiceBase(BaseModel):
    serial_no: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[int] = 0
    base_cost: Optional[float] = 0.0
    total_cost: Optional[float] = 0.0
    action: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    serial_no: str
    description: str
    quantity: int
    base_cost: float
    total_cost: float

class InvoiceUpdate(BaseModel):
    description: Optional[str]
    quantity: Optional[int]
    base_cost: Optional[float]
    total_cost: Optional[float]
    action: Optional[str]

def invoice_doc_to_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
    return doc_to_dict(doc)

@app.get(API_PREFIX + "/invoices", status_code=200)
async def list_invoices(
    page: int = Query(1, ge=1),
    limit: int = Query(PAGE_SIZE_DEFAULT, ge=1, le=500),
    serial_no: Optional[str] = Query(None)
):
    skip = (page - 1) * limit
    q: Dict[str, Any] = {}
    if serial_no:
        q["serial_no"] = {"$regex": re.escape(serial_no), "$options": "i"}
    total = await invoices_col.count_documents(q)
    cursor = invoices_col.find(q).sort([("_id", -1)]).skip(skip).limit(limit)
    items = []
    async for doc in cursor:
        items.append(invoice_doc_to_dict(doc))
    return {"items": items, "total": total, "page": page, "limit": limit}

@app.get(API_PREFIX + "/invoices/{serial_no}", status_code=200)
async def get_invoice(serial_no: str):
    doc = await invoices_col.find_one({"serial_no": serial_no})
    if not doc:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice_doc_to_dict(doc)

@app.post(API_PREFIX + "/invoices", status_code=201)
async def create_invoice(payload: InvoiceCreate = Body(...)):
    data = payload.dict()
    try:
        data["quantity"] = int(data.get("quantity", 0))
        data["base_cost"] = float(data.get("base_cost", 0))
        data["total_cost"] = float(data.get("total_cost", 0))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid numeric fields")
    try:
        res = await invoices_col.insert_one(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    doc = await invoices_col.find_one({"_id": res.inserted_id})
    return invoice_doc_to_dict(doc)

@app.put(API_PREFIX + "/invoices/{serial_no}", status_code=200)
@app.patch(API_PREFIX + "/invoices/{serial_no}", status_code=200)
async def update_invoice(serial_no: str, payload: InvoiceUpdate = Body(...)):
    update_data = {k: v for k, v in payload.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "quantity" in update_data:
        try:
            update_data["quantity"] = int(update_data["quantity"])
        except Exception:
            raise HTTPException(status_code=400, detail="quantity must be integer")
    for k in ("base_cost", "total_cost"):
        if k in update_data:
            try:
                update_data[k] = float(update_data[k])
            except Exception:
                raise HTTPException(status_code=400, detail=f"{k} must be numeric")
    res = await invoices_col.update_one({"serial_no": serial_no}, {"$set": update_data})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    doc = await invoices_col.find_one({"serial_no": serial_no})
    return invoice_doc_to_dict(doc)

@app.delete(API_PREFIX + "/invoices/{serial_no}", status_code=200)
async def delete_invoice(serial_no: str):
    res = await invoices_col.delete_one({"serial_no": serial_no})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"deleted": True}

# uploads endpoint (local save) - accepts single file, returns {"url": "..."}
@app.post(API_PREFIX + "/uploads", status_code=200)
async def uploads_endpoint(file: UploadFile = File(...)):
    # sanitize filename
    orig = os.path.basename(file.filename or "upload")
    name, ext = os.path.splitext(orig)
    ext = ext if ext else ".png"
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)[:50]
    fname = f"{safe_name}_{int(datetime.datetime.utcnow().timestamp())}{ext}"
    dest = os.path.join(BLOG_UPLOAD_DIR, fname)
    try:
        async with aiofiles.open(dest, "wb") as out:
            content = await file.read()
            await out.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
    public_url = f"{BASE_URL}/uploads/{fname}"
    return {"url": public_url}

# ensure uploads static is mounted (if not already)
try:
    app.mount("/uploads", StaticFiles(directory=BLOG_UPLOAD_DIR), name="uploads")
except Exception:
    # if already mounted earlier, ignore
    pass


# -------- Endpoints for Products (unchanged logic) --------
@app.get(API_PREFIX + "/products", status_code=200)
async def list_products(
    page: int = Query(1, ge=1), 
    pageSize: int = Query(PAGE_SIZE_DEFAULT, ge=1, le=500),
    category_slug: Optional[str] = Query(None, description="Filter by category slug")
):
    skip = (page - 1) * pageSize
    query = {}
    
    # Filter by category_slug if provided
    if category_slug:
        # Tìm category theo slug để lấy _id
        category = await categories_col.find_one({"slug": category_slug})
        if category:
            query["category_id"] = category["_id"]
        else:
            # Nếu không tìm thấy category, trả về empty
            return {"data": [], "paging": {"total": 0, "page": page, "pageSize": pageSize}}
    
    cursor = products_col.find(query).skip(skip).limit(pageSize)
    items = []
    async for doc in cursor:
        items.append(doc_to_dict(doc))
    total = await products_col.count_documents(query)
    return {"data": items, "paging": {"total": total, "page": page, "pageSize": pageSize}}

# API để lấy danh sách categories từ products (distinct category slugs)
@app.get(API_PREFIX + "/products/categories", status_code=200)
async def get_product_categories():
    """Lấy danh sách categories từ products (các category có sản phẩm)"""
    # Lấy tất cả category_id unique từ products
    category_ids = await products_col.distinct("category_id")
    
    if not category_ids:
        return {"data": []}
    
    # Lấy thông tin categories
    categories = []
    async for cat in categories_col.find({"_id": {"$in": category_ids}, "is_active": True}):
        categories.append(doc_to_dict(cat))
    
    return {"data": categories}

# Search products endpoint
@app.get(API_PREFIX + "/search", status_code=200)
async def search_products(
    q: str = Query("", min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results")
):
    """Search products by name (realtime search for autocomplete)"""
    if not q or len(q.strip()) < 1:
        return {"data": []}
    
    query_text = q.strip()
    # Case-insensitive search using regex
    search_pattern = {"$regex": query_text, "$options": "i"}
    
    # Search in product name
    query = {"name": search_pattern}
    
    cursor = products_col.find(query).limit(limit)
    items = []
    async for doc in cursor:
        items.append(doc_to_dict(doc))
    
    return {"data": items}

@app.get(API_PREFIX + "/products/{sku}", status_code=200)
async def get_product(sku: str):
    doc = await products_col.find_one({"sku": sku})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return doc_to_dict(doc)

@app.post(API_PREFIX + "/products", status_code=201)
async def create_product(payload: ProductCreate = Body(...)):
    doc = payload.dict()
    cat = oid_from_str(doc.pop("category_id", None))
    if cat:
        doc["category_id"] = cat
    doc["price"] = float(doc.get("price", 0.0))
    doc["stock_quantity"] = int(doc.get("stock_quantity", 0) or 0)
    doc["is_active"] = bool(doc.get("is_active", True))
    try:
        res = await products_col.insert_one(doc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    inserted = await products_col.find_one({"_id": res.inserted_id})
    return doc_to_dict(inserted)

@app.put(API_PREFIX + "/products/{sku}", status_code=200)
@app.patch(API_PREFIX + "/products/{sku}", status_code=200)
async def update_product(sku: str, payload: ProductUpdate = Body(...)):
    update_data = {k: v for k, v in payload.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "category_id" in update_data:
        cid = oid_from_str(update_data["category_id"])
        if cid:
            update_data["category_id"] = cid
        else:
            update_data.pop("category_id", None)
    if "price" in update_data:
        try:
            update_data["price"] = float(update_data["price"])
        except:
            raise HTTPException(status_code=400, detail="price must be numeric")
    if "stock_quantity" in update_data:
        try:
            update_data["stock_quantity"] = int(update_data["stock_quantity"])
        except:
            raise HTTPException(status_code=400, detail="stock_quantity must be integer")
    res = await products_col.update_one({"sku": sku}, {"$set": update_data})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    doc = await products_col.find_one({"sku": sku})
    return doc_to_dict(doc)

@app.delete(API_PREFIX + "/products/{sku}", status_code=200)
async def delete_product(sku: str):
    res = await products_col.delete_one({"sku": sku})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"deleted": True}

# -------- Endpoints for Categories --------
@app.get(API_PREFIX + "/categories", status_code=200)
async def list_categories(page: int = Query(1, ge=1), pageSize: int = Query(PAGE_SIZE_DEFAULT, ge=1, le=500)):
    skip = (page - 1) * pageSize
    cursor = categories_col.find().skip(skip).limit(pageSize)
    items = []
    async for doc in cursor:
        items.append(doc_to_dict(doc))
    total = await categories_col.count_documents({})
    return {"data": items, "paging": {"total": total, "page": page, "pageSize": pageSize}}

@app.get(API_PREFIX + "/categories/{slug}", status_code=200)
async def get_category(slug: str):
    doc = await categories_col.find_one({"slug": slug})
    if not doc:
        raise HTTPException(status_code=404, detail="Category not found")
    return doc_to_dict(doc)

@app.post(API_PREFIX + "/categories", status_code=201)
async def create_category(payload: CategoryCreate = Body(...)):
    doc = payload.dict()
    doc["is_active"] = bool(doc.get("is_active", True))
    try:
        res = await categories_col.insert_one(doc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    inserted = await categories_col.find_one({"_id": res.inserted_id})
    return doc_to_dict(inserted)

@app.put(API_PREFIX + "/categories/{slug}", status_code=200)
@app.patch(API_PREFIX + "/categories/{slug}", status_code=200)
async def update_category(slug: str, payload: CategoryUpdate = Body(...)):
    update_data = {k: v for k, v in payload.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    res = await categories_col.update_one({"slug": slug}, {"$set": update_data})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    doc = await categories_col.find_one({"slug": slug})
    return doc_to_dict(doc)

@app.delete(API_PREFIX + "/categories/{slug}", status_code=200)
async def delete_category(slug: str):
    res = await categories_col.delete_one({"slug": slug})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"deleted": True}
# ========== USERS ROUTES ==========

@app.get(API_PREFIX + "/users", status_code=200)
async def list_users(page: int = Query(1, ge=1), pageSize: int = Query(PAGE_SIZE_DEFAULT, ge=1, le=500)):
    skip = (page - 1) * pageSize
    cursor = users_col.find().skip(skip).limit(pageSize)
    items = []
    async for doc in cursor:
        items.append(doc_to_dict(doc))
    total = await users_col.count_documents({})
    return {"data": items, "paging": {"total": total, "page": page, "pageSize": pageSize}}


@app.get(API_PREFIX + "/users/{email}", status_code=200)
async def get_user(email: str):
    doc = await users_col.find_one({"email": email})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return doc_to_dict(doc)


@app.get(API_PREFIX + "/users/id/{user_id}", status_code=200)
async def get_user_by_id(user_id: str):
    obj = oid_from_str(user_id)
    if obj is None:
        raise HTTPException(status_code=400, detail="user_id must be a valid 24-hex ObjectId")
    doc = await users_col.find_one({"_id": obj})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return doc_to_dict(doc)


@app.post(API_PREFIX + "/users", status_code=201)
async def create_user(
    full_name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    role: str = Form("customer"),
    password: str = Form(...),   # bắt buộc theo schema
    avatar: UploadFile = File(None)
):
    # 1) validate / check existing
    existing = await users_col.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    # 2) hash password -> đảm bảo password_hash tồn trước insert
    password_hash = bcrypt.hash(password)

    # chuẩn bị folder avatar và giá trị default (luôn phải là string để thỏa schema)
    os.makedirs(AVATAR_DIR, exist_ok=True)
    default_png = os.path.join(AVATAR_DIR, "default.png")
    default_jpg = os.path.join(AVATAR_DIR, "default.jpg")
    if os.path.exists(default_png):
        default_url = "/Figma/admin/images/avatar/default.png"
    elif os.path.exists(default_jpg):
        default_url = "/Figma/admin/images/avatar/default.jpg"
    else:
        # nếu không có file default thì vẫn gán một string rỗng (để qua validation)
        default_url = ""

    # ban đầu gán avatar_url bằng default_url (là string)
    avatar_url = default_url

    now = datetime.datetime.utcnow()
    doc = {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "role": role,
        "status": "active",
        "password_hash": password_hash,   # ← **bắt buộc**
        "avatar_url": avatar_url,
        "created_at": now,
        "updated_at": now
    }

    # insert
    try:
        res = await users_col.insert_one(doc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # nếu có avatar upload -> lưu theo user_id.ext và cập nhật avatar_url
    if avatar and avatar.filename:
        user_id = str(res.inserted_id)
        # xác định ext (như logic trước)
        if "." in avatar.filename:
            ext = avatar.filename.rsplit(".", 1)[1].lower()
            if ext == "jpeg":
                ext = "jpg"
        else:
            ct = getattr(avatar, "content_type", "") or ""
            ext = ct.split("/", 1)[1].lower() if "/" in ct else "png"
            if ext == "jpeg":
                ext = "jpg"
        if ext not in {"png", "jpg", "jpeg", "webp", "gif"}:
            ext = "png"

        out_filename = f"{user_id}.{ext}"
        out_path = os.path.join(AVATAR_DIR, out_filename)
        try:
            contents = await avatar.read()
            # limit check
            if len(contents) > MAX_AVATAR_SIZE:
                # if too large, keep default_url (or handle differently)
                new_avatar_url = default_url
            else:
                with open(out_path, "wb") as f:
                    f.write(contents)
                new_avatar_url = f"/Figma/admin/images/avatar/{out_filename}"
        except Exception:
            # nếu ghi file lỗi thì giữ default_url (đã là string)
            new_avatar_url = default_url

        # cập nhật lại document với avatar_url mới và updated_at
        await users_col.update_one(
            {"_id": res.inserted_id},
            {"$set": {"avatar_url": new_avatar_url, "updated_at": datetime.datetime.utcnow()}}
        )

    inserted = await users_col.find_one({"_id": res.inserted_id})
    return doc_to_dict(inserted)


@app.put(API_PREFIX + "/users/{email}", status_code=200)
@app.patch(API_PREFIX + "/users/{email}", status_code=200)
async def update_user(
    email: str,
    full_name: Optional[str] = Form(None),
    new_email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    avatar: UploadFile = File(None)
):
    user = await users_col.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = {"updated_at": datetime.datetime.utcnow()}

    if full_name is not None:
        update_data["full_name"] = full_name
    if new_email is not None and new_email != email:
        update_data["email"] = new_email
    if phone is not None:
        update_data["phone"] = phone
    if role is not None:
        update_data["role"] = role
    if password:
        update_data["password"] = password

    if avatar and avatar.filename:
        if avatar.content_type not in ["image/png", "image/jpeg"]:
            raise HTTPException(status_code=400, detail="Only PNG or JPG allowed")

        os.makedirs(AVATAR_DIR, exist_ok=True)
        user_id = str(user["_id"])
        ext = "png" if avatar.content_type == "image/png" else "jpg"
        file_path = os.path.join(AVATAR_DIR, f"{user_id}.{ext}")

        contents = await avatar.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        update_data["avatar_url"] = f"/Figma/admin/images/avatar/{user_id}.{ext}"

    if len(update_data) == 1:  # Only updated_at
        raise HTTPException(status_code=400, detail="No fields to update")

    res = await users_col.update_one({"email": email}, {"$set": update_data})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    current_email = update_data.get("email", email)
    doc = await users_col.find_one({"email": current_email})
    return doc_to_dict(doc)


@app.delete(API_PREFIX + "/users/{email}", status_code=200)
async def delete_user(email: str):
    user = await users_col.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await users_col.delete_one({"email": email})
    return {"message": "User deleted successfully"}

# ========== AUTHENTICATION ENDPOINTS ==========
@app.post(API_PREFIX + "/auth/login", status_code=200)
async def login(
    email: str = Form(...),
    password: str = Form(...)
):
    """Login endpoint - verify email and password"""
    # 1. Tìm user theo email
    user = await users_col.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    
    # 2. Verify password với bcrypt
    password_hash = user.get("password_hash", "")
    if not password_hash:
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    
    try:
        # Verify password
        if not bcrypt.verify(password, password_hash):
            raise HTTPException(status_code=401, detail="Email or password is incorrect")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    
    # 3. Kiểm tra status
    if user.get("status") != "active":
        raise HTTPException(status_code=403, detail="Account is not active")
    
    # 4. Trả về user info (không bao gồm password_hash)
    user_dict = doc_to_dict(user)
    user_dict.pop("password_hash", None)  # Xóa password_hash khỏi response
    
    return {
        "success": True,
        "message": "Login successful",
        "user": user_dict
    }

@app.post(API_PREFIX + "/auth/register", status_code=201)
async def register(
    full_name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    password: str = Form(...),
    avatar: UploadFile = File(None)
):
    """Register endpoint - create new user"""
    # 1. Validate email format
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # 2. Validate password length
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    
    # 3. Check if email already exists
    existing = await users_col.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # 4. Hash password
    password_hash = bcrypt.hash(password)
    
    # 5. Prepare avatar URL
    os.makedirs(AVATAR_DIR, exist_ok=True)
    default_url = ""
    avatar_url = default_url
    
    if avatar and avatar.filename:
        if avatar.content_type not in ["image/png", "image/jpeg"]:
            raise HTTPException(status_code=400, detail="Only PNG or JPG allowed")
        
        # Generate unique filename
        user_id = str(ObjectId())
        ext = "png" if avatar.content_type == "image/png" else "jpg"
        file_path = os.path.join(AVATAR_DIR, f"{user_id}.{ext}")
        
        contents = await avatar.read()
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(contents)
        
        avatar_url = f"/Figma/admin/images/avatar/{user_id}.{ext}"
    
    # 6. Create user document
    now = datetime.datetime.utcnow()
    doc = {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "role": "customer",
        "status": "active",
        "password_hash": password_hash,
        "avatar_url": avatar_url,
        "reward_points": 0,
        "marketing_opt_in": False,
        "addresses": [],
        "created_at": now,
        "updated_at": now
    }
    
    # 7. Insert user
    try:
        res = await users_col.insert_one(doc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # 8. Get created user (without password_hash)
    created_user = await users_col.find_one({"_id": res.inserted_id})
    user_dict = doc_to_dict(created_user)
    user_dict.pop("password_hash", None)
    
    return {
        "success": True,
        "message": "Registration successful",
        "user": user_dict
    }

# ========== CART ENDPOINTS ==========
@app.get(API_PREFIX + "/carts", status_code=200)
async def get_cart(
    user_id: Optional[str] = Query(None, description="User ID (from localStorage)"),
    session_id: Optional[str] = Query(None, description="Session ID for guest users")
):
    """Get cart for user or session"""
    query = {}
    
    if user_id:
        try:
            user_obj_id = oid_from_str(user_id)
            if user_obj_id:
                query["user_id"] = user_obj_id
        except:
            pass
    
    if session_id and not query:
        query["session_id"] = session_id
    
    if not query:
        # Tạo session_id mới cho guest
        import uuid
        session_id = str(uuid.uuid4())
        return {
            "data": {
                "session_id": session_id,
                "items": [],
                "subtotal": 0,
                "total": 0
            }
        }
    
    cart = await carts_col.find_one(query)
    
    if not cart:
        return {
            "data": {
                "session_id": session_id or "",
                "items": [],
                "subtotal": 0,
                "total": 0
            }
        }
    
    # Tính toán totals
    items = cart.get("items", [])
    subtotal = sum(item.get("price", 0) * item.get("quantity", 0) for item in items)
    
    cart_dict = doc_to_dict(cart)
    
    # Convert product_id từ ObjectId sang string trong items để frontend dễ xử lý
    if "items" in cart_dict and isinstance(cart_dict["items"], list):
        for item in cart_dict["items"]:
            if "product_id" in item:
                if isinstance(item["product_id"], ObjectId):
                    item["product_id"] = str(item["product_id"])
                # Thêm id field để tương thích với frontend
                item["id"] = item.get("product_id", "")
    
    cart_dict["subtotal"] = subtotal
    cart_dict["total"] = subtotal  # Có thể thêm shipping, tax sau
    
    return {"data": cart_dict}

@app.post(API_PREFIX + "/carts", status_code=200)
async def add_to_cart(
    product_id: str = Form(...),
    product_name: str = Form(...),
    price: str = Form(...),  # Nhận string từ FormData, sẽ convert sau
    quantity: int = Form(1, ge=1),
    image: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None)
):
    """Add item to cart"""
    try:
        # Tìm product_id thật từ database nếu product_id không phải ObjectId
        actual_product_id = product_id
        product_obj_id = oid_from_str(product_id)
        
        if not product_obj_id:
            # product_id không phải ObjectId hợp lệ, tìm product trong database
            # Tìm theo SKU hoặc name
            product = await products_col.find_one({
                "$or": [
                    {"sku": product_id},
                    {"name": product_name}
                ]
            })
            if product:
                actual_product_id = str(product["_id"])
                product_obj_id = product["_id"]
            else:
                # Nếu không tìm thấy, tạo ObjectId mới hoặc dùng product_id như string
                # Nhưng vì schema yêu cầu ObjectId, nên tạo một ObjectId mới
                # Hoặc có thể bỏ qua validation này
                print(f"Warning: Product not found for product_id={product_id}, name={product_name}")
                # Tạo ObjectId mới (tạm thời, nên tìm product thật)
                product_obj_id = ObjectId()
                actual_product_id = str(product_obj_id)
        else:
            actual_product_id = str(product_obj_id)
        
        # Tìm hoặc tạo cart
        query = {}
        cart_doc = None
        
        if user_id:
            try:
                user_obj_id = oid_from_str(user_id)
                if user_obj_id:
                    query["user_id"] = user_obj_id
                    cart_doc = await carts_col.find_one(query)
            except Exception as e:
                print(f"Error converting user_id to ObjectId: {e}")
                pass
        
        if not cart_doc and session_id:
            query = {"session_id": session_id}
            cart_doc = await carts_col.find_one(query)
        
        # Tạo session_id mới nếu chưa có
        if not session_id and not user_id:
            import uuid
            session_id = str(uuid.uuid4())
        
        # Tạo item mới
        # Xử lý price - có thể là string từ FormData
        try:
            price_float = float(price) if price else 0.0
        except (ValueError, TypeError):
            price_float = 0.0
        
        new_item = {
            "product_id": product_obj_id,  # Dùng ObjectId thay vì string
            "name": product_name,
            "price": price_float,
            "quantity": int(quantity),
            "image": image or ""
        }
        
        now = datetime.datetime.utcnow()
        
        if cart_doc:
            # Cập nhật cart hiện có
            items = cart_doc.get("items", [])
            # Tìm item có cùng product_id
            existing_item = None
            for item in items:
                # So sánh product_id (có thể là ObjectId hoặc string)
                item_product_id = item.get("product_id")
                if isinstance(item_product_id, ObjectId):
                    item_product_id = str(item_product_id)
                if item_product_id == actual_product_id or item_product_id == product_id:
                    existing_item = item
                    break
            
            if existing_item:
                # Tăng quantity
                existing_item["quantity"] = existing_item.get("quantity", 0) + quantity
            else:
                # Thêm item mới
                items.append(new_item)
            
            await carts_col.update_one(
                {"_id": cart_doc["_id"]},
                {"$set": {"items": items, "updated_at": now}}
            )
        else:
            # Tạo cart mới
            cart_data = {
                "items": [new_item],
                "created_at": now,
                "updated_at": now
            }
            
            if user_id:
                try:
                    user_obj_id = oid_from_str(user_id)
                    if user_obj_id:
                        cart_data["user_id"] = user_obj_id
                except Exception as e:
                    print(f"Error converting user_id to ObjectId in cart_data: {e}")
                    pass
            
            if session_id:
                cart_data["session_id"] = session_id
            
            await carts_col.insert_one(cart_data)
        
        return {"success": True, "message": "Item added to cart"}
    except Exception as e:
        print(f"Error in add_to_cart: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.put(API_PREFIX + "/carts/item", status_code=200)
async def update_cart_item(
    product_id: str = Form(...),
    quantity: int = Form(..., ge=0),
    user_id: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None)
):
    """Update cart item quantity"""
    try:
        # Tìm product_id thật từ database nếu product_id không phải ObjectId
        product_obj_id = oid_from_str(product_id)
        if not product_obj_id:
            # Tìm product trong database
            product = await products_col.find_one({"sku": product_id})
            if product:
                product_obj_id = product["_id"]
            else:
                raise HTTPException(status_code=404, detail="Product not found")
        
        query = {}
        
        if user_id:
            try:
                user_obj_id = oid_from_str(user_id)
                if user_obj_id:
                    query["user_id"] = user_obj_id
            except:
                pass
        
        if session_id and not query:
            query["session_id"] = session_id
        
        if not query:
            raise HTTPException(status_code=400, detail="user_id or session_id required")
        
        cart = await carts_col.find_one(query)
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")
        
        items = cart.get("items", [])
        updated = False
        
        for item in items:
            item_product_id = item.get("product_id")
            # So sánh ObjectId hoặc string
            if isinstance(item_product_id, ObjectId):
                if item_product_id == product_obj_id:
                    if quantity == 0:
                        items.remove(item)
                    else:
                        item["quantity"] = quantity
                    updated = True
                    break
            elif str(item_product_id) == str(product_obj_id) or item_product_id == product_id:
                if quantity == 0:
                    items.remove(item)
                else:
                    item["quantity"] = quantity
                updated = True
                break
        
        if not updated:
            raise HTTPException(status_code=404, detail="Item not found in cart")
        
        await carts_col.update_one(
            {"_id": cart["_id"]},
            {"$set": {"items": items, "updated_at": datetime.datetime.utcnow()}}
        )
        
        return {"success": True, "message": "Cart updated"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in update_cart_item: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete(API_PREFIX + "/carts/item", status_code=200)
async def remove_cart_item(
    product_id: str = Query(...),
    user_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None)
):
    """Remove item from cart"""
    try:
        # Tìm product_id thật từ database nếu product_id không phải ObjectId
        product_obj_id = oid_from_str(product_id)
        if not product_obj_id:
            # Tìm product trong database
            product = await products_col.find_one({"sku": product_id})
            if product:
                product_obj_id = product["_id"]
            else:
                # Nếu không tìm thấy, vẫn thử xóa bằng string
                product_obj_id = None
        
        query = {}
        
        if user_id:
            try:
                user_obj_id = oid_from_str(user_id)
                if user_obj_id:
                    query["user_id"] = user_obj_id
            except:
                pass
        
        if session_id and not query:
            query["session_id"] = session_id
        
        if not query:
            raise HTTPException(status_code=400, detail="user_id or session_id required")
        
        cart = await carts_col.find_one(query)
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")
        
        items = cart.get("items", [])
        # Lọc items - so sánh cả ObjectId và string
        filtered_items = []
        for item in items:
            item_product_id = item.get("product_id")
            if product_obj_id:
                # So sánh ObjectId
                if isinstance(item_product_id, ObjectId):
                    if item_product_id != product_obj_id:
                        filtered_items.append(item)
                elif str(item_product_id) != str(product_obj_id) and item_product_id != product_id:
                    filtered_items.append(item)
            else:
                # So sánh string
                if str(item_product_id) != product_id and item_product_id != product_id:
                    filtered_items.append(item)
        
        await carts_col.update_one(
            {"_id": cart["_id"]},
            {"$set": {"items": filtered_items, "updated_at": datetime.datetime.utcnow()}}
        )
        
        return {"success": True, "message": "Item removed from cart"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in remove_cart_item: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete(API_PREFIX + "/carts", status_code=200)
async def clear_cart(
    user_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None)
):
    """Clear all items from cart"""
    query = {}
    
    if user_id:
        try:
            user_obj_id = oid_from_str(user_id)
            if user_obj_id:
                query["user_id"] = user_obj_id
        except:
            pass
    
    if session_id and not query:
        query["session_id"] = session_id
    
    if not query:
        raise HTTPException(status_code=400, detail="user_id or session_id required")
    
    await carts_col.update_one(
        query,
        {"$set": {"items": [], "updated_at": datetime.datetime.utcnow()}}
    )
    
    return {"success": True, "message": "Cart cleared"}

# -------- Endpoints for Orders --------
@app.get(API_PREFIX + "/orders", status_code=200)
async def list_orders(
    page: int = Query(1, ge=1),
    pageSize: int = Query(PAGE_SIZE_DEFAULT, ge=1, le=500),
    user_id: Optional[str] = Query(None),
    order_status: Optional[str] = Query(None)
):
    skip = (page - 1) * pageSize
    q: Dict[str, Any] = {}
    if user_id:
        uid = oid_from_str(user_id)
        if not uid:
            raise HTTPException(status_code=400, detail="user_id must be a 24-hex ObjectId")
        q["user_id"] = uid
    if order_status:
        allowed = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]
        if order_status not in allowed:
            raise HTTPException(status_code=400, detail=f"order_status must be one of {allowed}")
        q["order_status"] = order_status
    cursor = orders_col.find(q).skip(skip).limit(pageSize)
    items = []
    async for doc in cursor:
        items.append(order_doc_to_dict(doc))
    total = await orders_col.count_documents(q)
    return {"data": items, "paging": {"total": total, "page": page, "pageSize": pageSize}}

@app.get(API_PREFIX + "/orders/{order_no}", status_code=200)
async def get_order(order_no: str):
    doc = await orders_col.find_one({"order_no": order_no})
    if not doc:
        raise HTTPException(status_code=404, detail="Order not found")
    return order_doc_to_dict(doc)

@app.post(API_PREFIX + "/orders", status_code=201)
async def create_order(payload: OrderCreate = Body(...)):
    doc = payload.dict()
    user_obj = oid_from_str(doc.pop("user_id", None))
    if not user_obj:
        raise HTTPException(status_code=400, detail="user_id must be a valid 24-hex ObjectId")
    doc["user_id"] = user_obj
    items = doc.get("items", []) or []
    cleaned_items = []
    for it in items:
        up = float(it.get("unit_price") or 0.0)
        qty = int(it.get("quantity") or 0)
        lt = it.get("line_total")
        try:
            lt = float(lt) if lt is not None else round(up * qty, 2)
        except Exception:
            lt = round(up * qty, 2)
        cleaned_items.append({
            "product_name": it.get("product_name", "") or "",
            "unit_price": up,
            "quantity": qty,
            "line_total": lt
        })
    doc["items"] = cleaned_items
    subtotal = doc.get("subtotal")
    try:
        subtotal = float(subtotal) if subtotal is not None else round(sum(i["line_total"] for i in cleaned_items), 2)
    except Exception:
        subtotal = round(sum(i.get("line_total", 0) for i in cleaned_items), 2)
    doc["subtotal"] = subtotal
    total_amount = doc.get("total_amount")
    try:
        total_amount = float(total_amount) if total_amount is not None else subtotal
    except Exception:
        total_amount = subtotal
    doc["total_amount"] = total_amount
    doc["shipping_address"] = str(doc.get("shipping_address") or "")
    doc["payment_method"] = str(doc.get("payment_method") or "")
    shipping_fee = doc.get("shipping_fee")
    try:
        shipping_fee = float(shipping_fee) if shipping_fee is not None else 30000.0
    except Exception:
        shipping_fee = 30000.0
    doc["shipping_fee"] = shipping_fee
    status = doc.get("order_status") or "Pending"
    allowed = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]
    if status not in allowed:
        status = "Pending"
    doc["order_status"] = status
    now = datetime.datetime.utcnow()
    doc["created_at"] = extract_date(doc.get("created_at")) or now
    doc["updated_at"] = extract_date(doc.get("updated_at")) or now
    try:
        res = await orders_col.insert_one(doc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    inserted = await orders_col.find_one({"_id": res.inserted_id})
    return order_doc_to_dict(inserted)

@app.put(API_PREFIX + "/orders/{order_no}", status_code=200)
@app.patch(API_PREFIX + "/orders/{order_no}", status_code=200)
async def update_order(order_no: str, payload: OrderUpdate = Body(...)):
    raw = payload.dict(exclude_unset=True)
    if not raw:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_data: Dict[str, Any] = {}
    if "user_id" in raw:
        uid = oid_from_str(raw.get("user_id"))
        if not uid:
            raise HTTPException(status_code=400, detail="user_id must be a valid 24-hex ObjectId")
        update_data["user_id"] = uid
    if "items" in raw:
        items_in = raw.get("items") or []
        cleaned_items = []
        for it in items_in:
            up = float(it.get("unit_price") or 0.0)
            qty = int(it.get("quantity") or 0)
            lt = it.get("line_total")
            try:
                lt = float(lt) if lt is not None else round(up * qty, 2)
            except Exception:
                lt = round(up * qty, 2)
            cleaned_items.append({
                "product_name": it.get("product_name", "") or "",
                "unit_price": up,
                "quantity": qty,
                "line_total": lt
            })
        update_data["items"] = cleaned_items
        if "subtotal" not in raw:
            update_data["subtotal"] = round(sum(i["line_total"] for i in cleaned_items), 2)
    if "shipping_address" in raw:
        update_data["shipping_address"] = str(raw.get("shipping_address") or "")
    if "subtotal" in raw:
        update_data["subtotal"] = float(raw.get("subtotal") or 0.0)
    if "total_amount" in raw:
        update_data["total_amount"] = float(raw.get("total_amount") or raw.get("subtotal", 0.0))
    if "order_status" in raw:
        allowed = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]
        if raw.get("order_status") not in allowed:
            raise HTTPException(status_code=400, detail=f"order_status must be one of {allowed}")
        update_data["order_status"] = raw.get("order_status")
    update_data["updated_at"] = extract_date(raw.get("updated_at")) or datetime.datetime.utcnow()
    try:
        res = await orders_col.update_one({"order_no": order_no}, {"$set": update_data})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    doc = await orders_col.find_one({"order_no": order_no})
    return order_doc_to_dict(doc)

@app.delete(API_PREFIX + "/orders/{order_no}", status_code=200)
async def delete_order(order_no: str):
    res = await orders_col.delete_one({"order_no": order_no})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"deleted": True}

# -------- Endpoints for Order Items (new) --------
class OrderItemCreate(BaseModel):
    order_id: str
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    quantity: int = 1
    unit_price: Optional[float] = 0.0
    line_total: Optional[float] = None

@app.get(API_PREFIX + "/order_items", status_code=200)
async def list_order_items(order_id: Optional[str] = Query(None), page: int = Query(1, ge=1), pageSize: int = Query(PAGE_SIZE_DEFAULT, ge=1, le=500)):
    q = {}
    if order_id:
        oid = oid_from_str(order_id)
        if oid:
            q["order_id"] = oid
        else:
            q["order_id"] = order_id
    skip = (page - 1) * pageSize
    cursor = order_items_col.find(q).skip(skip).limit(pageSize)
    items = []
    async for doc in cursor:
        items.append(doc_to_dict(doc))
    total = await order_items_col.count_documents(q)
    return {"data": items, "paging": {"total": total, "page": page, "pageSize": pageSize}}

@app.post(API_PREFIX + "/order_items", status_code=201)
async def create_order_item(payload: OrderItemCreate = Body(...)):
    doc = payload.dict()
    # convert order_id/product_id if possible
    o = oid_from_str(doc.get("order_id"))
    if o:
        doc["order_id"] = o
    p = oid_from_str(doc.get("product_id"))
    if p:
        doc["product_id"] = p
    # calculate line_total if missing
    try:
        qty = int(doc.get("quantity", 0))
        up = float(doc.get("unit_price") or 0.0)
    except:
        raise HTTPException(status_code=400, detail="Invalid numeric fields")
    doc["line_total"] = float(doc.get("line_total") if doc.get("line_total") is not None else round(qty * up, 2))
    try:
        res = await order_items_col.insert_one(doc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    inserted = await order_items_col.find_one({"_id": res.inserted_id})
    return doc_to_dict(inserted)

# health check
@app.get(API_PREFIX + "/health")
async def health():
    try:
        await client.admin.command("ping")
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------- Run (only when executed directly) --------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)