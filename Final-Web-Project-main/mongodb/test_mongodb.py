
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://plwebdatabase123:PLWebsite123@plweb.escgc7n.mongodb.net/?retryWrites=true&w=majority&appName=PLWeb"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("=" * 60)
    print("✓ Kết nối MongoDB thành công!")
    print("=" * 60)
    
    # Select database
    db = client['plweb']
    
    # Get all collections (bảng)
    collections = db.list_collection_names()
    print(f"\n📊 Tổng số bảng (collections): {len(collections)}")
    print("-" * 60)
    
    # Lấy thông tin từng collection
    for idx, collection_name in enumerate(sorted(collections), 1):
        collection = db[collection_name]
        
        # Đếm số documents
        count = collection.count_documents({})
        
        print(f"\n{idx}. Bảng: {collection_name}")
        print(f"   Số lượng documents: {count}")
        
        # Lấy một document mẫu để xem các trường (columns)
        sample_doc = collection.find_one()
        
        if sample_doc:
            # Lấy tất cả các keys (columns) từ document
            columns = list(sample_doc.keys())
            print(f"   Số lượng cột (fields): {len(columns)}")
            print(f"   Các cột:")
            
            for col in columns:
                # Lấy kiểu dữ liệu của giá trị
                value = sample_doc[col]
                value_type = type(value).__name__
                
                # Hiển thị thông tin cột
                if isinstance(value, list):
                    if len(value) > 0:
                        item_type = type(value[0]).__name__
                        print(f"      - {col}: Array[{item_type}]")
                    else:
                        print(f"      - {col}: Array")
                elif isinstance(value, dict):
                    print(f"      - {col}: Object (có {len(value)} trường con)")
                else:
                    print(f"      - {col}: {value_type}")
        else:
            print(f"   ⚠ Bảng trống (chưa có documents)")
        
        print("-" * 60)
    
    print(f"\n✓ Hoàn tất! Đã kiểm tra {len(collections)} bảng.")
    print("=" * 60)
    
    # Lấy các SKU unique từ collection products
    print("\n" + "=" * 60)
    print("📦 DANH SÁCH SKU UNIQUE TRONG PRODUCTS")
    print("=" * 60)
    
    products_col = db['products']
    # Lấy tất cả các SKU unique
    unique_skus = products_col.distinct('sku')
    
    if unique_skus:
        print(f"\nTổng số SKU unique: {len(unique_skus)}")
        print("\nDanh sách SKU:")
        print("-" * 60)
        for idx, sku in enumerate(sorted(unique_skus), 1):
            # Lấy thông tin product với SKU này
            product = products_col.find_one({'sku': sku})
            if product:
                name = product.get('name', 'N/A')
                category_id = product.get('category_id', 'N/A')
                # Nếu category_id là ObjectId, convert sang string
                if category_id != 'N/A' and hasattr(category_id, '__str__'):
                    category_id = str(category_id)
                print(f"{idx:3d}. SKU: {sku:<20} | Tên: {name:<30} | Category ID: {category_id}")
            else:
                print(f"{idx:3d}. SKU: {sku}")
        print("-" * 60)
    else:
        print("\n⚠ Collection 'products' trống hoặc không có SKU nào.")
    
    # Lấy danh sách categories với id và name
    print("\n" + "=" * 60)
    print("📂 DANH SÁCH CATEGORIES")
    print("=" * 60)
    
    categories_col = db['categories']
    categories = list(categories_col.find({}))
    
    if categories:
        print(f"\nTổng số categories: {len(categories)}")
        print("\nDanh sách Categories:")
        print("-" * 60)
        for idx, category in enumerate(sorted(categories, key=lambda x: x.get('name', '')), 1):
            cat_id = str(category.get('_id', 'N/A'))
            cat_name = category.get('name', 'N/A')
            cat_slug = category.get('slug', 'N/A')
            is_active = category.get('is_active', 'N/A')
            print(f"{idx:3d}. ID: {cat_id:<25} | Name: {cat_name:<30} | Slug: {cat_slug:<20} | Active: {is_active}")
        print("-" * 60)
    else:
        print("\n⚠ Collection 'categories' trống hoặc không có category nào.")
    
    # Lấy danh sách users từ collection "users"
    print("\n" + "=" * 60)
    print("👥 DANH SÁCH USERS (từ bảng 'users')")
    print("=" * 60)
    
    # Lấy từ collection "users"
    if 'users' in collections:
        users_col = db['users']
        users = list(users_col.find({}))
        
        if users:
            print(f"\nTổng số users: {len(users)}")
            print("\nDanh sách Users:")
            print("-" * 60)
            # Sort by email hoặc full_name
            sort_key = lambda x: x.get('email', '') or x.get('full_name', '')
            for idx, user in enumerate(sorted(users, key=sort_key), 1):
                user_id = str(user.get('_id', 'N/A'))
                email = user.get('email', 'N/A')
                full_name = user.get('full_name', 'N/A')
                phone = user.get('phone', 'N/A')
                password_hash = user.get('password_hash', 'N/A')
                role = user.get('role', 'N/A')
                status = user.get('status', 'N/A')
                reward_points = user.get('reward_points', 0)
                marketing_opt_in = user.get('marketing_opt_in', False)
                addresses = user.get('addresses', [])
                created_at = user.get('created_at', 'N/A')
                updated_at = user.get('updated_at', 'N/A')
                
                # Format datetime nếu có
                if hasattr(created_at, 'strftime'):
                    created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')
                if hasattr(updated_at, 'strftime'):
                    updated_at = updated_at.strftime('%Y-%m-%d %H:%M:%S')
                
                # Truncate password_hash nếu quá dài
                if password_hash != 'N/A' and len(str(password_hash)) > 50:
                    password_hash_display = str(password_hash)[:50] + "..."
                else:
                    password_hash_display = password_hash
                
                print(f"{idx:3d}. ID: {user_id}")
                print(f"     Email: {email:<35} | Full Name: {full_name:<30}")
                print(f"     Phone: {phone:<20} | Role: {role:<15} | Status: {status:<15}")
                print(f"     Password Hash: {password_hash_display}")
                print(f"     Reward Points: {reward_points:<10} | Marketing Opt-in: {marketing_opt_in}")
                print(f"     Addresses: {len(addresses)} địa chỉ")
                print(f"     Created At: {created_at}")
                if updated_at != 'N/A':
                    print(f"     Updated At: {updated_at}")
                print("-" * 60)
        else:
            print("\n⚠ Collection 'users' trống hoặc không có user nào.")
    else:
        print("\n⚠ Collection 'users' không tồn tại trong database.")
    
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Lỗi kết nối MongoDB: {e}")