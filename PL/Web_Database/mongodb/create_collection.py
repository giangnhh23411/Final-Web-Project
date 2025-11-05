from pymongo import MongoClient, errors
from pymongo.server_api import ServerApi

# Connection URI from mongodb_connection.py
uri = "mongodb+srv://plwebdatabase123:PLWebsite123@plweb.escgc7n.mongodb.net/?retryWrites=true&w=majority&appName=PLWeb"

# Create client
client = MongoClient(uri, server_api=ServerApi('1'))

# Select database (assuming 'plweb' based on appName and username)
db = client['plweb']

# Function to create or update collection with validator
def update_or_create_collection_with_validator(collection_name, validator):
    try:
        db.create_collection(collection_name, validator=validator)
        print(f"Collection '{collection_name}' created with validator.")
    except errors.CollectionInvalid:
        # Update the validator for existing collection
        db.command({"collMod": collection_name, "validator": validator})
        print(f"Collection '{collection_name}' validator updated.")

# 1. Users collection - Simplified: Keep essentials for login (email, password, name, role, status). Remove phone, addresses, reward_points, marketing_opt_in as not mentioned.
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
update_or_create_collection_with_validator('users', users_validator)
db.users.create_index('email', unique=True)

# 2. Categories collection - Simplified: Keep name, slug, is_active. Remove parent_id, sort_order as not essential for basic add/edit/delete.
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
update_or_create_collection_with_validator('categories', categories_validator)
db.categories.create_index('slug', unique=True)

# 3. Products collection - Simplified: Keep sku, name, category_id, price, stock_quantity, is_active. Add/edit/delete implies description, images might be useful but simplify: remove brand, attributes, currency (assume default), created/updated if not needed for tracking.
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
update_or_create_collection_with_validator('products', products_validator)
db.products.create_index('sku', unique=True)

# 4. Orders collection - Simplified for tracking: Keep order_no, user_id, subtotal, total_amount, order_status, created_at. Remove items (use separate if needed but simplify), shipping_fee, discounts, currency, payment_status, addresses, shipment_id, payment_id, billing_address.
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
update_or_create_collection_with_validator('orders', orders_validator)
db.orders.create_index('order_no', unique=True)

# 5. Order_Items collection - Keep minimal for order tracking: order_id, product_id, qty, unit_price. Remove sku, total_price (can calculate).
order_items_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['order_id', 'product_id', 'qty', 'unit_price'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'order_id': {'bsonType': 'objectId'},
            'product_id': {'bsonType': 'objectId'},
            'qty': {'bsonType': 'int'},
            'unit_price': {'bsonType': 'double'}
        }
    }
}
update_or_create_collection_with_validator('order_items', order_items_validator)

# 6. Vouchers collection - Align to mentioned: Add description, condition (as min_order_value). Keep code (ID), type, value (Sale), start_at (From), end_at (To), usage_limit (Max Usage Limit), status (Action). Remove per_user_limit, applicable_products.
vouchers_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['code', 'type', 'value', 'start_at', 'end_at', 'usage_limit', 'status'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'code': {'bsonType': 'string'},
            'type': {'enum': ['percent', 'fixed']},
            'value': {'bsonType': 'double'},
            'description': {'bsonType': 'string'},  # Added as mentioned
            'start_at': {'bsonType': 'date'},
            'end_at': {'bsonType': 'date'},
            'usage_limit': {'bsonType': 'int'},
            'min_order_value': {'bsonType': 'double'},  # Condition
            'status': {'enum': ['active', 'expired', 'disabled']},
            'applicable_product_ids': {
                'bsonType': ['array', 'null'],
                'items': {'bsonType': ['objectId', 'string']}
            }
        }
    }
}
update_or_create_collection_with_validator('vouchers', vouchers_validator)
db.vouchers.create_index('code', unique=True)

# 7. Blogs collection (renamed from statuses for clarity) - Align to mentioned: title, category (add), content, attached_file (add). Add like_count, comment_count, share_count. Remove slug, author_id, tags, published_at, status if not essential.

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

update_or_create_collection_with_validator('blogs', blogs_validator)  # Renamed collection

# 8. Invoices collection - Added for invoice: serial_no, description, quantity, base_cost, total_cost, action.
invoices_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['serial_no', 'description', 'quantity', 'base_cost', 'total_cost'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'serial_no': {'bsonType': 'string'},
            'description': {'bsonType': 'string'},
            'quantity': {'bsonType': 'int'},
            'base_cost': {'bsonType': 'double'},
            'total_cost': {'bsonType': 'double'},
            'action': {'bsonType': 'string'}
        }
    }
}
update_or_create_collection_with_validator('invoices', invoices_validator)
db.invoices.create_index('serial_no', unique=True)

# Removed unnecessary collections: Carts, Payments, Shipments, Sessions, Notifications, Policies, Admin_Logs as not mentioned in features.

# Close the client
client.close()