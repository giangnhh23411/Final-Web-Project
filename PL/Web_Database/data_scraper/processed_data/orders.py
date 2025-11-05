#!/usr/bin/env python3
# generate_orders.py
import json, random, datetime

# --- Dữ liệu user_id ---
USER_IDS = [
'690303e90cf9c0351ba8f7c5', '6907314c0cf9c0351ba8f970','6907314c0cf9c0351ba8f971','6907314c0cf9c0351ba8f972',
'6907314c0cf9c0351ba8f973','6907314c0cf9c0351ba8f974','6907314c0cf9c0351ba8f975','6907314c0cf9c0351ba8f976',
'6907314c0cf9c0351ba8f977','6907314c0cf9c0351ba8f978','6907314c0cf9c0351ba8f979','6907314c0cf9c0351ba8f97a',
'6907314c0cf9c0351ba8f97b','6907314c0cf9c0351ba8f97c','6907314c0cf9c0351ba8f97d','6907314c0cf9c0351ba8f97e',
'6907314c0cf9c0351ba8f97f','6907314c0cf9c0351ba8f980','6907314c0cf9c0351ba8f981','690303e90cf9c0351ba8f7c4'
]

# --- Danh sách sản phẩm ---
PRODUCTS = [
    'Trà đen Phúc Long 200g','Trà đen Phúc Long 500g','Trà lài hộp giấy 150g','Trà lài 15 - 200g','Trà lài 15 - 500g',
    'Trà nõn tôm ủ lạnh túi tgiác CC 2gx12gói','Trà lài ủ lạnh túi tgiac CC 2gx12 gói','Trà lài túi tam giác (3g x 10 gói)',
    'Trà lài đặc biệt (100g/ gói)','Trà ô long 80-150g','Trà Sữa Matcha (L)','Trà Ô Long Dâu (L)',
    'Matcha Latte Oatside Nguyên Vị (L)','Matcha Dừa Thanh Yên (L)','Matcha Dừa Đảo Phô Mai Mặn (L)',
    'Matcha Oatside Tuyết Lạnh (L)','Bà Kẹ','Ông Kẹ','Trà Vải Lài (M)','Trà Vải Sen (M)','Trà Vải Lài (L)',
    'Trà Lucky Tea (L)','Trà Lucky Tea (M)','Trà Vải Sen (L)','Trà Nhãn Sen (M)','Topping Nhãn (4 trái)',
    'Trà Nhãn Sen (L)','Trà Nhãn Lài (M)','Trà Nhãn Lài (L)','Trà Lài Đác Thơm (M)','Hồng Trà Đác Cam Đá Xay',
    'Topping Đác Cam','Trà Lài Đác Thơm (L)','Topping Đác Thơm','Cà Phê Đen Đá (L)','Cà Phê Sữa Đá (L)',
    'Cà phê Latte (M)','Cà phê Latte (L)','Cà phê Cappuccino (M)','Trà Phúc Long (M)','Trà Ô Long (M)',
    'Trà Phúc Long (L)','Trà Ô Long (L)','Hồng Trà (Nóng)','Trà Lài (Nóng)','Cà phê Cappuccino (L)',
    'Hồng Trà (M)','Trà Lài (M)','Hồng Trà (L)','Trà Sen (Nóng)','Trà Lài (L)','Trà Sữa Nhãn Sen (M)',
    'Trà Lài Kem Silky (M)','Topping thạch konjac','Trà Sữa Ô Long Quế Hoa (L)',
    'Trà Ô Long Cam Đào Thạch Konjac(M)','Trà Ô Long Kem Silky (L)',
    'Trà Lài Mãng Cầu Thạch Dừa Sợi (M)','Trà Phúc Long Kem Silky (M)',
    'Cà Phê Sữa Kem Silky (L)','Bánh Thập Cẩm Lạp Xưởng Sốt Nấm Truffle',
    'Trà Sữa Phúc Long (M)','Hồng Trà Đào (L)','Hồng Trà Đào (M)',
    'Trà Sữa Ô Long (L)','Trà Sữa Phúc Long (L)','Đá xay Matcha',
    'Hồng Trà Sữa (L)','Đào (3 miếng)','Hồng Trà Chanh (L)',
    'Hồng Trà Đào Sữa Thạch Konjac (L)'
]

# --- Bảng giá ---
PRICE_BUCKETS = [
    15000,20000,22000,25000,30000,35000,36000,37000,38000,39000,40000,45000,
    49000,50000,55000,58000,59000,60000,65000,69000,70000,75000,80000,85000,
    220000,250000,380000,436000
]
PRICE_WEIGHTS = [20 if p < 40000 else 5 if p < 100000 else 1 for p in PRICE_BUCKETS]
ORDER_STATUSES = ['Pending','Processing','Shipped','Delivered','Cancelled']

# --- Danh sách địa chỉ ---
LOCATIONS = [
    "Đường Quảng Trường Sáng Tạo, Linh Trung, Thủ Đức, TP.HCM",
    "Khu phố 6, Linh Trung, Thủ Đức, TP.HCM",
    "45/6A Đường Tân Lập, Phường Hiệp Phú, Thủ Đức, TP.HCM",
    "Số 200 Đường Thống Nhất, Phường Bình Thọ, Thủ Đức, TP.HCM",
    "Đường Dân Chủ, Phường Bình Thọ, Thủ Đức, TP.HCM",
    "13 Khổng Tử, Phường Bình Thọ, Thủ Đức, TP.HCM",
    "783 Kha Vạn Cân, Phường Linh Chiểu, Thủ Đức, TP.HCM",
    "6 Chu Mạnh Trinh, Phường Bình Thọ, Thủ Đức, TP.HCM",
    "103 Hoàng Diệu 2, Phường Linh Trung, Thủ Đức, TP.HCM",
    "20 Đoàn Kết, Phường Bình Thọ, Thủ Đức, TP.HCM",
    "14 Einstein, Phường Bình Thọ, Thủ Đức, TP.HCM",
    "88 Đường số 26, Phường Hiệp Bình Chánh, Thủ Đức, TP.HCM",
    "60 Đinh Thị Thi, Khu đô thị Vạn Phúc, Thủ Đức, TP.HCM",
    "254 Đặng Văn Bi, Phường Bình Thọ, Thủ Đức, TP.HCM",
    "2 Đường số 9, Khu Phố 5, Thủ Đức, TP.HCM",
    "55/18 Đường số 48, Khu phố 6, Thủ Đức, TP.HCM",
    "102 Đặng Văn Bi, Phường Bình Thọ, Thủ Đức, TP.HCM",
    "Đường số 23, Khu phố 5, Thủ Đức, TP.HCM",
    "5 Hoàng Diệu 2, Phường Linh Trung, Thủ Đức, TP.HCM",
    "120 Xa Lộ Hà Nội, Phường Tân Phú, Thủ Đức, TP.HCM"
]

def random_date(start, end):
    delta = end - start
    sec = random.randint(0, int(delta.total_seconds()))
    return start + datetime.timedelta(seconds=sec)

def gen_order(i, start_date, end_date):
    created = random_date(start_date, end_date)
    order_no = f"ORD{created.strftime('%Y%m%d')}-{i:04d}"
    user = random.choice(USER_IDS)
    n_items = random.randint(1, 5)
    items = []
    subtotal = 0.0
    for _ in range(n_items):
        prod = random.choice(PRODUCTS)
        unit_price = float(random.choices(PRICE_BUCKETS, weights=PRICE_WEIGHTS, k=1)[0])
        qty = random.randint(1, 3)
        line_total = round(unit_price * qty, 2)
        items.append({
            "product_name": prod,
            "unit_price": unit_price,
            "quantity": qty,
            "line_total": line_total
        })
        subtotal += line_total
    subtotal = round(subtotal, 2)
    total_amount = subtotal
    updated = created + datetime.timedelta(seconds=random.randint(0, 86400))
    order_status = random.choices(ORDER_STATUSES, weights=[10,30,20,30,5], k=1)[0]
    address = random.choice(LOCATIONS)
    return {
        "order_no": order_no,
        "user_id": {"$oid": user},
        "items": items,
        "subtotal": subtotal,
        "total_amount": total_amount,
        "order_status": order_status,
        "address": address,
        "created_at": {"$date": created.strftime("%Y-%m-%dT%H:%M:%SZ")},
        "updated_at": {"$date": updated.strftime("%Y-%m-%dT%H:%M:%SZ")}
    }

def main():
    random.seed(42)
    start_date = datetime.datetime(2025,8,1,0,0,0)
    end_date = datetime.datetime(2025,11,1,23,59,59)
    n_orders = 300
    orders = [gen_order(i+1, start_date, end_date) for i in range(n_orders)]

    # --- In ra console ---
    print(json.dumps(orders, ensure_ascii=False, indent=2))

    # --- Xuất ra file ---
    with open("orders.json", "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)
    print("\n✅ File 'orders.json' đã được tạo thành công!")

if __name__ == "__main__":
    main()
