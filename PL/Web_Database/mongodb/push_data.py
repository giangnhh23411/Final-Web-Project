# push_to_mongo_using_existing_client.py
import os
import json
from bson import ObjectId
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError
import hashlib
from datetime import datetime

# ----------------------------
# SỬ DỤNG KẾT NỐI MONGODB BẠN ĐÃ TẠO
# (mình dùng chính xác snippet bạn gửi)
from pymongo import MongoClient, errors
from pymongo.server_api import ServerApi

uri = "mongodb+srv://plwebdatabase123:PLWebsite123@plweb.escgc7n.mongodb.net/?retryWrites=true&w=majority&appName=PLWeb"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['plweb']
# ----------------------------

# FILES (từ bước trước)
DATA_DIR = "../data_scraper/processed_data"
CATEGORIES_FILE = os.path.join(DATA_DIR, "categories.json")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
USERS_FILE=os.path.join(DATA_DIR, "users.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
BLOGS_FILE = os.path.join(DATA_DIR, "blogs.json")

# DRY_RUN = True => không ghi DB, chỉ log. Đặt biến môi trường DRY_RUN=1 để bật.
DRY_RUN = os.getenv("DRY_RUN", "0") in ("1", "true", "True", "yes")

# Validator (giữ theo bạn đã đưa)
categories_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['name', 'slug', 'is_active'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'name': {'bsonType': 'string'},
            'slug': {'bsonType': 'string'},
            'is_active': {'bsonType': 'bool'}
        }
    }
}
products_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['sku', 'name', 'category_id', 'price', 'is_active'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'sku': {'bsonType': 'string'},
            'name': {'bsonType': 'string'},
            'description': {'bsonType': 'string'},
            'category_id': {'bsonType': 'objectId'},
            'images': {
                'bsonType': 'array',
                'items': {'bsonType': 'string'}
            },
            'price': {'bsonType': 'double'},
            'is_active': {'bsonType': 'bool'}
        }
    }
}
orders_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['order_no', 'user_id', 'subtotal', 'total_amount', 'order_status', 'created_at', 'updated_at'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'order_no': {'bsonType': 'string'},
            'user_id': {'bsonType': 'objectId'},
            'subtotal': {'bsonType': 'double'},
            'total_amount': {'bsonType': 'double'},
            'shipping_address': {'bsonType': 'string'},
            'order_status': {'enum': ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']},  # Simplified statuses
            'created_at': {'bsonType': 'date'},
            'updated_at': {'bsonType': 'date'}
        }
    }
}
users_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['email', 'password_hash', 'full_name', 'status', 'role', 'created_at', 'updated_at'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'email': {'bsonType': 'string'},
            'password_hash': {'bsonType': 'string'},
            'full_name': {'bsonType': 'string'},
            'status': {'enum': ['active', 'unverified', 'disabled']},
            'role': {'enum': ['customer', 'admin']},
            'avatar_url': {'bsonType': 'string'},  # Simplified roles: only admin/customer as mentioned
            'created_at': {'bsonType': 'date'},
            'updated_at': {'bsonType': 'date'}
        }
    }
}

blogs_validator={
  "$jsonSchema": {
    "bsonType": "object",
    "required": ["title", "category", "content"],
    "properties": {
      "_id": { "bsonType": "objectId" },
      "title": { "bsonType": "string" },
      "category": { "bsonType": "string" },
      "content": { "bsonType": "string" },
      "lead": { "bsonType": ["string", "null"] },
      "date_display": { "bsonType": ["string", "null"] },
      "tags": {
        "bsonType": ["array", "null"],
        "items": { "bsonType": "string" }
      },
      "cta": {
        "bsonType": ["array", "null"],
        "items": {
          "bsonType": "object",
          "required": ["label", "href"],
          "properties": {
            "label": { "bsonType": "string" },
            "href": { "bsonType": "string" },
            "kind": { "bsonType": ["string", "null"] }
          }
        }
      }
    }
  }
}
# ----------------------------
# Helper: load JSON
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# Ensure collection & validator (try collMod or create)
def ensure_collection_with_validator(db, name, validator):
    if name in db.list_collection_names():
        try:
            db.command("collMod", name, validator=validator)
            print(f"✅ Updated validator for '{name}'")
        except Exception as e:
            print(f"⚠️ collMod failed for '{name}': {e}  (continuing)")
    else:
        try:
            db.create_collection(name, validator=validator)
            print(f"✅ Created collection '{name}' with validator")
        except Exception as e:
            print(f"⚠️ Create collection '{name}' failed: {e}  (continuing)")

def parse_date(v):
    """Parse ISO date string or numeric epoch to datetime. Fallback -> now."""
    if v is None:
        return datetime.utcnow()
    if isinstance(v, datetime):
        return v
    if isinstance(v, (int, float)):
        try:
            return datetime.fromtimestamp(int(v))
        except Exception:
            return datetime.utcnow()
    if isinstance(v, str):
        # try ISO first
        try:
            # Python's fromisoformat handles "YYYY-MM-DDTHH:MM:SS" (may need slight adjustments)
            return datetime.fromisoformat(v)
        except Exception:
            # try parse as integer string epoch
            try:
                return datetime.fromtimestamp(int(v))
            except Exception:
                return datetime.utcnow()
    return datetime.utcnow()

def extract_objectid(val):
    """Convert {'$oid': '...'} or string -> ObjectId, else return None"""
    if val is None:
        return None
    if isinstance(val, dict) and "$oid" in val:
        try:
            return ObjectId(val["$oid"])
        except Exception:
            return None
    # nếu người dùng đã để string id
    if isinstance(val, str):
        try:
            return ObjectId(val)
        except Exception:
            return None
    return None

def extract_date(val):
    """Convert {'$date': 'iso' or epoch} or iso string -> datetime using parse_date"""
    if val is None:
        return parse_date(None)
    if isinstance(val, dict) and "$date" in val:
        v = val["$date"]
        # v có thể là ISO string hoặc epoch (int)
        if isinstance(v, str):
            # datetime.fromisoformat không chấp nhận 'Z' -> thay bằng +00:00
            if v.endswith("Z"):
                v2 = v.replace("Z", "+00:00")
            else:
                v2 = v
            try:
                return datetime.fromisoformat(v2)
            except Exception:
                try:
                    return parse_date(v)
                except Exception:
                    return parse_date(None)
        else:
            return parse_date(v)
    # nếu truyền thẳng chuỗi
    if isinstance(val, str):
        if val.endswith("Z"):
            val2 = val.replace("Z", "+00:00")
        else:
            val2 = val
        try:
            return datetime.fromisoformat(val2)
        except Exception:
            return parse_date(val)
    # nếu số epoch
    return parse_date(val)

def hash_password_sha256(pw):
    if not pw:
        return ""
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


# ----------------------------
def main():
    # 1. Check files
    if not os.path.exists(CATEGORIES_FILE):
        print("❌ Không tìm thấy:", CATEGORIES_FILE); return
    if not os.path.exists(PRODUCTS_FILE):
        print("❌ Không tìm thấy:", PRODUCTS_FILE); return
    if not os.path.exists(USERS_FILE):
        print("❌ Không tìm thấy:", USERS_FILE); return
    if not os.path.exists(BLOGS_FILE):
        print("❌ Không tìm thấy:", BLOGS_FILE); return

    categories_list = load_json(CATEGORIES_FILE)
    products_list = load_json(PRODUCTS_FILE)
    users_list = load_json(USERS_FILE)
    blogs_list = load_json(BLOGS_FILE)
    print(f"🔎 Đọc {len(categories_list)} categories, {len(products_list)} products and {len(users_list)} users {len(blogs_list)} blogs")

    if DRY_RUN:
        print("ℹ️ DRY_RUN = True (chỉ log, không ghi DB)")

    # 2. Ensure collections + validators
    ensure_collection_with_validator(db, "categories", categories_validator)
    ensure_collection_with_validator(db, "products", products_validator)
    ensure_collection_with_validator(db, "users", users_validator)
    ensure_collection_with_validator(db, "blogs", blogs_validator)

    # 3. Ensure unique indexes (skip in DRY run)
    if not DRY_RUN:
        try:
            db.categories.create_index([("slug", ASCENDING)], unique=True)
            db.products.create_index([("sku", ASCENDING)], unique=True)
            db.users.create_index([("_id", ASCENDING)], unique=True)
            db.blogs.create_index([("_id", ASCENDING)], unique=True)
            print("🔧 Indexes ensured: categories.slug (unique), products.sku (unique)")
        except Exception as e:
            print("⚠️ Lỗi khi tạo index:", e)
    else:
        print("🔧 (DRY) Skip creating indexes")

    # 4. Upsert categories: map old_id_str -> new ObjectId
    oldid_to_newid = {}
    slug_to_newid = {}

    for c in categories_list:
        slug = c.get("slug")
        name = c.get("name")
        is_active = bool(c.get("is_active", True))
        old_id = c.get("_id")

        if not slug:
            print("⚠️ Category missing slug, skip:", c)
            continue

        set_doc = {"name": name, "slug": slug, "is_active": is_active}

        if DRY_RUN:
            print(f"(DRY) Upsert category slug={slug} -> {set_doc}")
            new_id = ObjectId()  # simulated
        else:
            res = db.categories.update_one({"slug": slug}, {"$set": set_doc}, upsert=True)
            if res.upserted_id:
                new_id = res.upserted_id
            else:
                doc = db.categories.find_one({"slug": slug})
                new_id = doc["_id"]
            print(f"✅ Category upserted/existed slug={slug} -> _id={new_id}")

        # store mapping (string key)
        if old_id is not None:
            oldid_to_newid[str(old_id)] = new_id
        slug_to_newid[str(slug)] = new_id

    # 5. Upsert products
    upserted = 0
    skipped = 0
    for p in products_list:
        sku = str(p.get("sku") or "").strip()
        if not sku:
            print("⚠️ Skip product missing sku:", p.get("name", "")[:50])
            skipped += 1
            continue

        # prepare product doc for DB
        prod_doc = {
            "sku": sku,
            "name": p.get("name", ""),
            "price": float(p.get("price", 0) or 0),
            "stock_quantity": int(p.get("stock_quantity", 0) or 0),
            "is_active": bool(p.get("is_active", True)),
            "description": p.get("description", "") or "",
            "images": p.get("images", []) or []
        }

        # Resolve category_id -> ObjectId
        cat_objid = None
        cat_old = p.get("category_id")
        if cat_old is not None:
            cat_objid = oldid_to_newid.get(str(cat_old))
        if cat_objid is None:
            # try if product contains 'category_slug'
            cat_slug = p.get("category_slug")
            if cat_slug:
                cat_objid = slug_to_newid.get(str(cat_slug))
        if cat_objid is None:
            # final fallback: try to get category 'Thức uống' or first category
            try:
                fallback = db.categories.find_one({"slug": {"$regex": "thuc-uong|thuc-uong", "$options": "i"}})
            except Exception:
                fallback = None
            if fallback:
                cat_objid = fallback["_id"]
            else:
                any_cat = db.categories.find_one({})
                if any_cat:
                    cat_objid = any_cat["_id"]
        prod_doc["category_id"] = cat_objid

        if DRY_RUN:
            print(f"(DRY) Upsert product sku={sku}, cat_id={cat_objid}, price={prod_doc['price']}")
            upserted += 1
        else:
            try:
                res = db.products.update_one({"sku": sku}, {"$set": prod_doc}, upsert=True)
                upserted += 1
                if res.upserted_id:
                    print(f"🔸 Inserted product sku={sku} (_id={res.upserted_id})")
                else:
                    print(f"🔸 Updated product sku={sku}")
            except DuplicateKeyError as e:
                print(f"⚠️ DuplicateKeyError sku={sku}: {e}")
            except Exception as e:
                print(f"❌ Lỗi upsert sku={sku}: {e}")

    #Users insert
    upserted_u = 0
    skipped_u = 0

    # ensure unique index on email (important)
    if not DRY_RUN:
        try:
            db.users.create_index([("email", ASCENDING)], unique=True)
            print("🔧 Index ensured: users.email (unique)")
        except Exception as e:
            print("⚠️ Lỗi khi tạo index users.email:", e)
    else:
        print("🔧 (DRY) Skip ensuring users.email index")

    for u in users_list:
        email = (u.get("email") or "").strip().lower()
        if not email:
            print("⚠️ Skip user missing email:", u.get("full_name", "")[:40])
            skipped_u += 1
            continue

        # prepare user doc
        pwd_hash = u.get("password_hash")
        if not pwd_hash:
            # nếu có password plain, hash nó; nếu không có, set default empty hash
            pwd_hash = hash_password_sha256(u.get("password", ""))
        full_name = u.get("full_name") or ""
        status = u.get("status") or "unverified"
        role = u.get("role") or "customer"
        avatar_url = u.get("avatar_url") or ""
        created_at = parse_date(u.get("created_at"))
        updated_at = parse_date(u.get("updated_at"))

        user_doc = {
            "email": email,
            "password_hash": pwd_hash,
            "full_name": full_name,
            "status": status,
            "role": role,
            "avatar_url": avatar_url,
            "created_at": created_at,
            "updated_at": updated_at
        }

        # nếu file users.json có _id (string) và bạn muốn dùng luôn _id cũ:
        if u.get("_id"):
            try:
                user_doc["_id"] = ObjectId(u["_id"])
            except Exception:
                # nếu không convert được, bỏ qua _id để Mongo tạo mới
                pass

        if DRY_RUN:
            print(f"(DRY) Upsert user email={email}, name={full_name}, role={role}")
            upserted_u += 1
        else:
            try:
                res = db.users.update_one({"email": email}, {"$set": user_doc}, upsert=True)
                upserted_u += 1
                if res.upserted_id:
                    print(f"🔸 Inserted user email={email} (_id={res.upserted_id})")
                else:
                    print(f"🔸 Updated user email={email}")
            except DuplicateKeyError as e:
                print(f"⚠️ DuplicateKeyError user email={email}: {e}")
            except Exception as e:
                print(f"❌ Lỗi upsert user email={email}: {e}")
     # 7. Upsert orders
    if not os.path.exists(ORDERS_FILE):
        print("❌ Không tìm thấy:", ORDERS_FILE)
    else:
        orders_list = load_json(ORDERS_FILE)
        print(f"🔎 Đọc {len(orders_list)} orders từ {ORDERS_FILE}")

        # ensure collection + validator
        ensure_collection_with_validator(db, "orders", orders_validator)

        # ensure unique index on order_no
        if not DRY_RUN:
            try:
                db.orders.create_index([("order_no", ASCENDING)], unique=True)
                print("🔧 Index ensured: orders.order_no (unique)")
            except Exception as e:
                print("⚠️ Lỗi khi tạo index orders.order_no:", e)
        else:
            print("🔧 (DRY) Skip ensuring orders.order_no index")

        upserted_o = 0
        skipped_o = 0

        for ord_raw in orders_list:
            # basic validation
            order_no = (ord_raw.get("order_no") or "").strip()
            if not order_no:
                print("⚠️ Skip order missing order_no:", ord_raw)
                skipped_o += 1
                continue

            # convert user_id
            user_id_val = ord_raw.get("user_id")
            user_objid = extract_objectid(user_id_val)
            if user_objid is None:
                # nếu user_id không hợp lệ, log và skip (bảo toàn ràng buộc validator)
                print(f"⚠️ order {order_no} missing/invalid user_id -> skip")
                skipped_o += 1
                continue

            # items: đảm bảo số liệu numeric
            items = ord_raw.get("items", [])
            cleaned_items = []
            for it in items:
                unit_price = float(it.get("unit_price") or 0)
                quantity = int(it.get("quantity") or 0)
                line_total = float(it.get("line_total") or (unit_price * quantity))
                cleaned_items.append({
                    "product_name": it.get("product_name", ""),
                    "unit_price": unit_price,
                    "quantity": quantity,
                    "line_total": line_total
                })

            # subtotal / total
            try:
                subtotal = float(ord_raw.get("subtotal") or 0)
            except Exception:
                subtotal = float(0)
            try:
                total_amount = float(ord_raw.get("total_amount") or subtotal)
            except Exception:
                total_amount = subtotal

            # order_status: ép về 1 trong enum nếu không hợp lệ -> chuyển sang 'Pending' và log
            status = ord_raw.get("order_status") or "Pending"
            allowed_status = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]
            if status not in allowed_status:
                print(f"⚠️ order {order_no} has invalid status '{status}', coercing to 'Pending'")
                status = "Pending"

            # created_at / updated_at (giữ extract_date nhưng fallback nếu None)
            created_at = extract_date(ord_raw.get("created_at")) or datetime.datetime.utcnow()
            updated_at = extract_date(ord_raw.get("updated_at")) or created_at

            # shipping_address: lấy từ keys có khả năng có trong file (shipping_address, address)
            shipping_address = ord_raw.get("shipping_address") or ord_raw.get("address") or ""

            # build document (không gán _id để Mongo tự tạo)
            order_doc = {
                "order_no": order_no,
                "user_id": user_objid,
                "items": cleaned_items,
                "subtotal": float(subtotal),
                "total_amount": float(total_amount),
                "shipping_address": str(shipping_address),
                "order_status": status,
                "created_at": created_at,
                "updated_at": updated_at
            }

            if DRY_RUN:
                print(f"(DRY) Upsert order {order_no} user_id={user_objid}")
                upserted_o += 1
            else:
                try:
                    res = db.orders.update_one({"order_no": order_no}, {"$set": order_doc}, upsert=True)
                    upserted_o += 1
                    if res.upserted_id:
                        print(f"🔸 Inserted order {order_no} (_id={res.upserted_id})")
                    else:
                        print(f"🔸 Updated order {order_no}")
                except DuplicateKeyError as e:
                    print(f"⚠️ DuplicateKeyError order_no={order_no}: {e}")
                    skipped_o += 1
                except Exception as e:
                    print(f"❌ Lỗi upsert order {order_no}: {e}")
                    skipped_o += 1

    # Assumes `blogs_list`, `db`, `DRY_RUN`, `ensure_collection_with_validator`,
    # `oldid_to_newid`, `slug_to_newid`, `extract_date`, `extract_objectid` are available.
    print("\n🔎 Upserting blogs...")

    # ensure collection + validator (safe to call again)

    # ensure helpful index for listing/filtering (non-unique)
    if not DRY_RUN:
        try:
            db.blogs.create_index([("title", ASCENDING), ("date_display", ASCENDING)])
            db.blogs.create_index([("created_at", ASCENDING)])
            print("🔧 Indexes ensured on blogs.title,date_display,created_at")
        except Exception as e:
            print("⚠️ Could not ensure blogs indexes:", e)
    else:
        print("🔧 (DRY) Skip creating blogs indexes")

    upserted_b = 0
    skipped_b = 0

    for b in blogs_list:
        title = (b.get("title") or "").strip()
        if not title:
            print("⚠️ Skip blog missing title:", b)
            skipped_b += 1
            continue

        # category: prefer explicit string name, fallback from category_id or category_slug
        category_val = None
        if isinstance(b.get("category"), str) and b.get("category").strip():
            category_val = b.get("category").strip()
        else:
            # try category_slug
            if b.get("category_slug"):
                category_val = str(b.get("category_slug"))
            else:
                # try map from category_id -> slug/name
                cat_old = b.get("category_id")
                if cat_old is not None:
                    mapped = oldid_to_newid.get(str(cat_old)) or extract_objectid(cat_old)
                    if mapped:
                        try:
                            cat_doc = db.categories.find_one({"_id": mapped})
                            if cat_doc:
                                category_val = cat_doc.get("slug") or cat_doc.get("name")
                        except Exception:
                            category_val = None
        # ensure fallback to empty string if still None
        if category_val is None:
            category_val = ""

        # build document
        created_at = extract_date(b.get("created_at"))
        updated_at = extract_date(b.get("updated_at")) if b.get("updated_at") else created_at

        # prepare numeric counts safely
        def to_int_safe(v):
            try:
                return int(v or 0)
            except Exception:
                return 0

        blog_doc = {
            "title": title,
            "category": category_val,
            "content": b.get("content") or "",
            "lead": b.get("lead") or None,
            "date_display": b.get("date_display") or None,
            "attached_file": b.get("attached_file") or None,
            "like_count": to_int_safe(b.get("like_count")),
            "comment_count": to_int_safe(b.get("comment_count")),
            "share_count": to_int_safe(b.get("share_count")),
            "tags": b.get("tags") or [],
            "cta": b.get("cta") or None,
            "created_at": created_at,
            "updated_at": updated_at
        }

        # preserve provided _id if present and valid
        filter_q = None
        if b.get("_id"):
            try:
                oid = extract_objectid(b.get("_id"))
                if oid:
                    filter_q = {"_id": oid}
                    # set _id into doc so upsert with _id uses same id
                    blog_doc["_id"] = oid
            except Exception:
                filter_q = None

        # fallback filter: title + date_display (best-effort)
        if filter_q is None:
            key = {"title": title}
            if blog_doc.get("date_display"):
                key["date_display"] = blog_doc["date_display"]
            filter_q = key

        if DRY_RUN:
            print(f"(DRY) Upsert blog filter={filter_q} -> title='{title[:60]}'")
            upserted_b += 1
        else:
            try:
                res = db.blogs.update_one(filter_q, {"$set": blog_doc}, upsert=True)
                upserted_b += 1
                if getattr(res, "upserted_id", None):
                    print(f"🔸 Inserted blog title='{title[:60]}' (_id={res.upserted_id})")
                else:
                    # could not easily tell whether updated vs no-op; assume updated
                    print(f"🔸 Updated blog title='{title[:60]}'")
            except DuplicateKeyError as e:
                print(f"⚠️ DuplicateKeyError upserting blog title='{title}': {e}")
                skipped_b += 1
            except Exception as e:
                print(f"❌ Error upserting blog title='{title}': {e}")
                skipped_b += 1

    print(f"\nHoàn tất blogs: upserted ~{upserted_b}, skipped {skipped_b}")
    print(f"\nHoàn tất orders: upserted ~{upserted_o}, skipped {skipped_o}")
    print(f"\nHoàn tất users: upserted ~{upserted_u}, skipped {skipped_u}")
    print(f"\nHoàn tất: upserted ~{upserted} products, skipped {skipped}")

if __name__ == "__main__":
    main()
