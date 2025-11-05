import os
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.server_api import ServerApi


URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://plwebdatabase123:PLWebsite123@plweb.escgc7n.mongodb.net/?retryWrites=true&w=majority&appName=PLWeb",
)
DB_NAME = os.getenv("MONGODB_DB", "plweb")


def upsert_vouchers():
    client = MongoClient(URI, server_api=ServerApi("1"))
    db = client[DB_NAME]
    col = db["vouchers"]
    products = list(db["products"].find({}, {"_id": 1}).limit(5))
    product_ids = [p["_id"] for p in products]

    now = datetime.utcnow()
    start = now - timedelta(days=7)
    end = now + timedelta(days=365)

    samples = [
        {"code": f"SALE{i:02d}", "type": "percent", "value": float(i), "description": f"Giảm {i}%", "usage_limit": 100 + i, "min_order_value": 0.0, "status": "active"}
        for i in range(5, 15)
    ]

    # Alternate a few fixed amounts
    for j, s in enumerate(samples):
        if j % 3 == 0:
            s["type"] = "fixed"
            s["value"] = float((j + 1) * 10)

        # spread dates a bit
        s["start_at"] = start + timedelta(days=j)
        s["end_at"] = end + timedelta(days=j)
        # attach a couple of product ids if available
        if product_ids:
            s["applicable_product_ids"] = [pid for idx, pid in enumerate(product_ids) if idx <= (j % len(product_ids))]

    upserted = 0
    for s in samples:
        res = col.update_one({"code": s["code"]}, {"$set": s}, upsert=True)
        upserted += 1
    print(f"Seeded/updated {upserted} vouchers.")


if __name__ == "__main__":
    upsert_vouchers()


