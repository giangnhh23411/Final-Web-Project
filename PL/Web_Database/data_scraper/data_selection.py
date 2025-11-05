# classify_and_export.py
import os
import json
import glob
import re
from uuid import uuid4

RAW_DIR = "raw_data"               # nơi chứa các file JSON nguồn
OUT_DIR = "Web_Database/data_scraper/processed_data"     # nơi lưu kết quả
os.makedirs(OUT_DIR, exist_ok=True)

# Optional: use real ObjectId if bson available
try:
    from bson.objectid import ObjectId
    def make_id():
        return ObjectId()
    OBJECTID_AVAILABLE = True
except Exception:
    OBJECTID_AVAILABLE = False
    def make_id():
        return uuid4().hex

def slugify(s):
    s = (s or "").strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "-", s, flags=re.UNICODE)
    s = re.sub(r"-+", "-", s, flags=re.UNICODE)
    return s.strip("-")

# Regex để phát hiện trọng lượng (ví dụ: 500g, 200 g, 15-500g, 250ml, 1kg)
weight_re = re.compile(r"\b\d{1,4}(?:\s*[-–]\s*\d{1,4})?\s*(?:g|gram|grams|kg|ml|l)\b", flags=re.IGNORECASE)

# Keyword sets (có thể mở rộng)
tea_keywords = ["trà", "tra", "tea"]
coffee_keywords = ["cà phê", "ca phe", "cafe", "coffee"]
cake_keywords = ["bánh", "cake", "cookie", "biscuit", "muffin", "pastry"]
drink_keywords = ["nước", "juice", "soda", "pepsi", "coca", "nước ép", "drink", "nước hoa quả", "nước tăng lực"]

# Setup category templates (the ones you requested)
category_templates = [
    {"name": "Bánh", "slug": slugify("Bánh"), "is_active": True, "_id": make_id()},
    {"name": "Thức uống", "slug": slugify("Thức uống"), "is_active": True, "_id": make_id()},
    {"name": "Sản phẩm đóng gói - Trà", "slug": slugify("Sản phẩm đóng gói - Trà"), "is_active": True, "_id": make_id()},
    {"name": "Sản phẩm đóng gói - Cà phê", "slug": slugify("Sản phẩm đóng gói - Cà phê"), "is_active": True, "_id": make_id()},
    {"name": "Sản phẩm đóng gói - Khác", "slug": slugify("Sản phẩm đóng gói - Khác"), "is_active": True, "_id": make_id()},
]

# Map name -> doc for quick access
categories_by_name = {c["name"]: c for c in category_templates}

files = glob.glob(os.path.join(RAW_DIR, "*.json"))
if not files:
    print("Không tìm thấy file trong", RAW_DIR)
else:
    print(f"Tìm thấy {len(files)} file trong {RAW_DIR}")

products = []

def contains_any(text, keywords):
    if not text:
        return False
    t = text.lower()
    return any(k.lower() in t for k in keywords)

for fpath in files:
    with open(fpath, "r", encoding="utf-8") as f:
        try:
            payload = json.load(f)
        except Exception as e:
            print(f"⚠️ Bỏ qua file {fpath} (không parse được): {e}")
            continue

    items = payload.get("data", {}).get("items") or []
    for it in items:
        name = (it.get("name") or it.get("seoName") or "").strip()
        sku = it.get("itemNo") or it.get("basicItemNo") or None

        # 1) Kiểm tra trọng lượng -> Sản phẩm đóng gói
        is_packaged = bool(weight_re.search(name))

        category_choice = None
        if is_packaged:
            # kiểm tra trà / cà phê
            if contains_any(name, tea_keywords):
                category_choice = categories_by_name["Sản phẩm đóng gói - Trà"]
            elif contains_any(name, coffee_keywords):
                category_choice = categories_by_name["Sản phẩm đóng gói - Cà phê"]
            else:
                category_choice = categories_by_name["Sản phẩm đóng gói - Khác"]
        else:
            # 2) Không có trọng lượng -> check bánh vs thức uống vs mặc định
            if contains_any(name, cake_keywords):
                category_choice = categories_by_name["Bánh"]
            elif contains_any(name, drink_keywords) or contains_any(name, tea_keywords) or contains_any(name, coffee_keywords):
                # chú ý: trà/cà phê ở đây coi như Thức uống nếu không có trọng lượng
                category_choice = categories_by_name["Thức uống"]
            else:
                # fallback (mặc định)
                category_choice = categories_by_name["Thức uống"]

        # Price
        price = it.get("salePrice") if it.get("salePrice") is not None else it.get("price")
        try:
            price = float(price) if price is not None else 0.0
        except Exception:
            price = 0.0

        # images
        images = []
        for m in it.get("mediaItems") or []:
            url = m.get("mediaUrl")
            if url:
                images.append(url)
        if not images:
            mu = it.get("mediaUrl")
            if mu:
                images = [mu]

        product_doc = {
            "sku": str(sku) if sku is not None else uuid4().hex,
            "name": name or "no-name",
            "category_id": category_choice["_id"],
            "price": price,
            "stock_quantity": 0,
            "is_active": True,
            "description": it.get("shortDesc") or it.get("subName") or "",
            "images": images,
            # helpful metadata:
            "raw_itemNo": it.get("itemNo"),
            "raw_id": it.get("id"),
            "detected_packaged": is_packaged
        }
        products.append(product_doc)

# Export categories and products
cats_out = os.path.join(OUT_DIR, "categories.json")
prods_out = os.path.join(OUT_DIR, "products.json")

# Ensure serializable IDs (ObjectId -> str) for JSON
def serial_id(x):
    try:
        return str(x)
    except Exception:
        return x

cats_serial = []
for c in category_templates:
    c_copy = {k: v for k, v in c.items() if k != "_id"}  # we'll include _id as string
    c_copy["_id"] = serial_id(c["_id"])
    cats_serial.append(c_copy)

prods_serial = []
for p in products:
    p_copy = p.copy()
    p_copy["category_id"] = serial_id(p_copy["category_id"])
    prods_serial.append(p_copy)

with open(cats_out, "w", encoding="utf-8") as f:
    json.dump(cats_serial, f, ensure_ascii=False, indent=2)

with open(prods_out, "w", encoding="utf-8") as f:
    json.dump(prods_serial, f, ensure_ascii=False, indent=2)

print("✅ Hoàn tất phân loại và lưu file:")
print(" - Categories:", cats_out)
print(" - Products:", prods_out)
if OBJECTID_AVAILABLE:
    print("ℹ️ category._id là bson.ObjectId (thực).")
else:
    print("⚠️ category._id là chuỗi UUID hex; nếu bạn muốn ObjectId thực khi insert vào Mongo, cài pymongo và convert trước khi insert.")
