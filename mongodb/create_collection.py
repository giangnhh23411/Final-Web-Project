from pymongo import MongoClient, errors
from pymongo.server_api import ServerApi
from pymongo.read_preferences import ReadPreference
from typing import List, Dict, Any
import argparse
import json
from pathlib import Path

# Connection URI from mongodb_connection.py
uri = "mongodb+srv://plwebdatabase123:PLWebsite123@plweb.escgc7n.mongodb.net/?retryWrites=true&w=majority&appName=PLWeb"

# Create client
client = MongoClient(uri, server_api=ServerApi('1'))
# Read-only client prefers secondary to avoid requiring Primary for simple reads
client_ro = MongoClient(
    uri,
    server_api=ServerApi('1'),
    read_preference=ReadPreference.SECONDARY_PREFERRED,
    retryWrites=False,
)

# Select database (assuming 'plweb' based on appName and username)
db = client['plweb']

# Function to create collection with validator if it doesn't exist
def create_collection_with_validator(collection_name, validator):
    try:
        db.create_collection(collection_name, validator=validator)
        print(f"Collection '{collection_name}' created with validator.")
    except errors.CollectionInvalid:
        print(f"Collection '{collection_name}' already exists.")

# 1. Users collection
users_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['email', 'password_hash', 'full_name', 'status', 'role', 'created_at', 'updated_at'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'email': {'bsonType': 'string'},
            'password_hash': {'bsonType': 'string'},
            'full_name': {'bsonType': 'string'},
            'phone': {'bsonType': 'string'},
            'addresses': {
                'bsonType': 'array',
                'items': {
                    'bsonType': 'object',
                    'properties': {
                        'label': {'bsonType': 'string'},
                        'street': {'bsonType': 'string'},
                        'city': {'bsonType': 'string'},
                        'district': {'bsonType': 'string'},
                        'postal_code': {'bsonType': 'string'},
                        'is_default': {'bsonType': 'bool'}
                    }
                }
            },
            'status': {'enum': ['active', 'unverified', 'disabled']},
            'role': {'enum': ['customer', 'admin', 'staff']},
            'reward_points': {'bsonType': 'int'},
            'created_at': {'bsonType': 'date'},
            'updated_at': {'bsonType': 'date'},
            'marketing_opt_in': {'bsonType': 'bool'}
        }
    }
}
def setup_schema(database):
    # Users
    create_collection_with_validator('users', users_validator)
    database.users.create_index('email', unique=True)

# 2. Categories collection
    categories_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['name', 'slug', 'is_active'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'name': {'bsonType': 'string'},
            'slug': {'bsonType': 'string'},
            'parent_id': {'bsonType': ['objectId', 'null']},
            'sort_order': {'bsonType': 'int'},
            'is_active': {'bsonType': 'bool'}
        }
    }
}
    create_collection_with_validator('categories', categories_validator)
    database.categories.create_index('slug', unique=True)

# 3. Order_Items collection
    order_items_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['order_id', 'product_id', 'sku', 'qty', 'unit_price', 'total_price'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'order_id': {'bsonType': 'objectId'},
            'product_id': {'bsonType': 'objectId'},
            'sku': {'bsonType': 'string'},
            'qty': {'bsonType': 'int'},
            'unit_price': {'bsonType': 'double'},
            'total_price': {'bsonType': 'double'}
        }
    }
}
    create_collection_with_validator('order_items', order_items_validator)

# 4. Products collection
    products_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['sku', 'name', 'category_id', 'price', 'currency', 'stock_quantity', 'is_active', 'created_at', 'updated_at'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'sku': {'bsonType': 'string'},
            'name': {'bsonType': 'string'},
            'description': {'bsonType': 'string'},
            'category_id': {'bsonType': 'objectId'},
            'brand': {'bsonType': 'string'},
            'images': {
                'bsonType': 'array',
                'items': {'bsonType': 'string'}
            },
            'price': {'bsonType': 'double'},
            'currency': {'bsonType': 'string'},
            'stock_quantity': {'bsonType': 'int'},
            'attributes': {'bsonType': 'object'},
            'is_active': {'bsonType': 'bool'},
            'created_at': {'bsonType': 'date'},
            'updated_at': {'bsonType': 'date'}
        }
    }
}
    create_collection_with_validator('products', products_validator)
    database.products.create_index('sku', unique=True)

# 5. Carts collection
    carts_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['items', 'created_at', 'updated_at'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'user_id': {'bsonType': ['objectId', 'null']},
            'session_id': {'bsonType': 'string'},
            'items': {
                'bsonType': 'array',
                'items': {
                    'bsonType': 'object',
                    'properties': {
                        'product_id': {'bsonType': 'objectId'},
                        'sku': {'bsonType': 'string'},
                        'qty': {'bsonType': 'int'},
                        'price_at_add': {'bsonType': 'double'},
                        'attributes': {'bsonType': 'object'}
                    }
                }
            },
            'created_at': {'bsonType': 'date'},
            'updated_at': {'bsonType': 'date'}
        }
    }
}
    create_collection_with_validator('carts', carts_validator)

# 6. Payments collection
    payments_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['order_id', 'method', 'status', 'amount', 'created_at'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'order_id': {'bsonType': 'objectId'},
            'method': {'enum': ['COD', 'Card', 'Ewallet']},
            'provider': {'bsonType': 'string'},
            'status': {'enum': ['Pending', 'Paid', 'Failed', 'Refunded']},
            'amount': {'bsonType': 'double'},
            'transaction_id': {'bsonType': 'string'},
            'paid_at': {'bsonType': 'date'},
            'created_at': {'bsonType': 'date'}
        }
    }
}
    create_collection_with_validator('payments', payments_validator)
    database.payments.create_index('transaction_id', unique=True)

# 7. Orders collection
    orders_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['order_no', 'user_id', 'items', 'subtotal', 'total_amount', 'currency', 'payment_status', 'order_status', 'shipping_address', 'created_at', 'updated_at'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'order_no': {'bsonType': 'string'},
            'user_id': {'bsonType': 'objectId'},
            'items': {
                'bsonType': 'array',
                'items': {
                    'bsonType': 'object',
                    'properties': {
                        'product_id': {'bsonType': 'objectId'},
                        'sku': {'bsonType': 'string'},
                        'qty': {'bsonType': 'int'},
                        'price': {'bsonType': 'double'},
                        'attributes': {'bsonType': 'object'}
                    }
                }
            },
            'subtotal': {'bsonType': 'double'},
            'shipping_fee': {'bsonType': 'double'},
            'discounts': {'bsonType': 'array'},
            'total_amount': {'bsonType': 'double'},
            'currency': {'bsonType': 'string'},
            'payment_status': {'enum': ['Pending', 'Paid', 'Failed', 'Refunded']},
            'order_status': {'enum': ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled', 'Refunded']},
            'shipping_address': {'bsonType': 'object'},
            'billing_address': {'bsonType': 'object'},
            'shipment_id': {'bsonType': 'objectId'},
            'payment_id': {'bsonType': 'objectId'},
            'created_at': {'bsonType': 'date'},
            'updated_at': {'bsonType': 'date'}
        }
    }
}
    create_collection_with_validator('orders', orders_validator)
    database.orders.create_index('order_no', unique=True)

# 8. Vouchers collection
    vouchers_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['code', 'type', 'value', 'start_at', 'end_at', 'status'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'code': {'bsonType': 'string'},
            'type': {'enum': ['percent', 'fixed']},
            'value': {'bsonType': 'double'},
            'start_at': {'bsonType': 'date'},
            'end_at': {'bsonType': 'date'},
            'usage_limit': {'bsonType': 'int'},
            'per_user_limit': {'bsonType': 'int'},
            'min_order_value': {'bsonType': 'double'},
            'applicable_products': {'bsonType': ['array', 'null'], 'items': {'bsonType': 'objectId'}},
            'status': {'enum': ['active', 'expired', 'disabled']}
        }
    }
}
    create_collection_with_validator('vouchers', vouchers_validator)
    database.vouchers.create_index('code', unique=True)

# 9. Shipments collection
    shipments_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['_id', 'order_id', 'carrier', 'status'],  # Add the required fields here
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'order_id': {'bsonType': 'objectId'},
            'carrier': {'bsonType': 'string'},
            'tracking_no': {'bsonType': 'string'},
            'status': {'enum': ['Preparing', 'Shipped', 'In Transit', 'Delivered', 'Returned']},
            'shipped_at': {'bsonType': 'date'},
            'expected_delivery': {'bsonType': 'date'},
            'delivered_at': {'bsonType': 'date'},
            'events': {
                'bsonType': 'array',
                'items': {
                    'bsonType': 'object',
                    'properties': {
                        'location': {'bsonType': 'string'},
                        'status': {'bsonType': 'string'},
                        'timestamp': {'bsonType': 'date'}
                    }
                }
            }
        }
    }
}
    create_collection_with_validator('shipments', shipments_validator)

# 10. Statuses collection (assuming for blog posts based on attributes)
    statuses_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['title', 'slug', 'content', 'author_id', 'status'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'title': {'bsonType': 'string'},
            'slug': {'bsonType': 'string'},
            'content': {'bsonType': 'string'},
            'author_id': {'bsonType': 'objectId'},
            'tags': {'bsonType': 'array', 'items': {'bsonType': 'string'}},
            'published_at': {'bsonType': 'date'},
            'status': {'enum': ['draft', 'published', 'archived']}
        }
    }
}
    create_collection_with_validator('statuses', statuses_validator)
    database.statuses.create_index('slug', unique=True)

# 11. Sessions collection
    sessions_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['user_id', 'token_hash', 'expires_at'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'user_id': {'bsonType': 'objectId'},
            'token_hash': {'bsonType': 'string'},
            'last_seen': {'bsonType': 'date'},
            'expires_at': {'bsonType': 'date'}
        }
    }
}
    create_collection_with_validator('sessions', sessions_validator)
    database.sessions.create_index('token_hash', unique=True)

# 12. Notifications collection
    notifications_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['to_user', 'type', 'payload', 'sent_status'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'to_user': {'bsonType': 'objectId'},
            'type': {'enum': ['in_app', 'email', 'sms']},
            'payload': {'bsonType': 'object'},
            'sent_status': {'enum': ['pending', 'sent', 'failed']},
            'sent_at': {'bsonType': 'date'}
        }
    }
}
    create_collection_with_validator('notifications', notifications_validator)

# 13. Policies collection
    policies_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['key', 'title', 'content', 'last_updated', 'is_active'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'key': {'bsonType': 'string'},
            'title': {'bsonType': 'string'},
            'content': {'bsonType': 'string'},
            'last_updated': {'bsonType': 'date'},
            'is_active': {'bsonType': 'bool'}
        }
    }
}
    create_collection_with_validator('policies', policies_validator)
    database.policies.create_index('key', unique=True)

# 14. Admin_Logs collection
    admin_logs_validator = {
    '$jsonSchema': {
        'bsonType': 'object',
        'required': ['actor_id', 'action', 'entity_type', 'timestamp'],
        'properties': {
            '_id': {'bsonType': 'objectId'},
            'actor_id': {'bsonType': 'objectId'},
            'action': {'bsonType': 'string'},
            'entity_type': {'bsonType': 'string'},
            'entity_id': {'bsonType': 'string'},
            'details': {'bsonType': ['string', 'object']},
            'timestamp': {'bsonType': 'date'}
        }
    }
}
    create_collection_with_validator('admin_logs', admin_logs_validator)

def list_databases(mongo_client: MongoClient) -> List[str]:
    # Use explicit secondaryPreferred on admin DB to avoid Primary requirement
    admin_db = mongo_client.get_database("admin", read_preference=ReadPreference.SECONDARY_PREFERRED)
    res = admin_db.command({"listDatabases": 1, "nameOnly": True})
    return sorted([d.get("name", "") for d in res.get("databases", [])])


def list_collections(database) -> List[str]:
    # Ensure read preference is secondaryPreferred
    db_ro = database.client.get_database(database.name, read_preference=ReadPreference.SECONDARY_PREFERRED)
    return sorted(db_ro.list_collection_names())


def infer_top_level_fields(database, collection_name: str, sample_limit: int = 10000) -> List[str]:
    pipeline = [
        {"$limit": sample_limit},
        {"$project": {"pairs": {"$objectToArray": "$$ROOT"}}},
        {"$unwind": "$pairs"},
        {"$group": {"_id": "$pairs.k"}},
        {"$sort": {"_id": 1}},
    ]
    return [d["_id"] for d in database[collection_name].aggregate(pipeline, allowDiskUse=True)]


def infer_array_fields(database, collection_name: str, array_path: str, sample_limit: int = 10000) -> List[str]:
    # array_path like "sizes"
    pipeline = [
        {"$limit": sample_limit},
        {"$unwind": f"${array_path}"},
        {"$project": {"pairs": {"$objectToArray": f"${array_path}"}}},
        {"$unwind": "$pairs"},
        {"$group": {"_id": "$pairs.k"}},
        {"$sort": {"_id": 1}},
    ]
    return [d["_id"] for d in database[collection_name].aggregate(pipeline, allowDiskUse=True)]


def import_json_array(database, collection_name: str, file_path: str) -> Dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # support either { items: [...] } or [...] at root
    docs = data.get("items") if isinstance(data, dict) else data
    if not isinstance(docs, list):
        raise ValueError("JSON must be an array or have 'items' array.")
    if not docs:
        return {"inserted": 0}
    try:
        result = database[collection_name].insert_many(docs, ordered=False)
        return {"inserted": len(result.inserted_ids)}
    except errors.BulkWriteError as bwe:
        inserted = sum(1 for w in bwe.details.get("writeErrors", []) if w.get("code") == 11000)
        # Even on bulk errors, some may be inserted
        return {"inserted": bwe.details.get("nInserted", 0), "duplicates": inserted}


def main() -> None:
    parser = argparse.ArgumentParser(description="Mongo utilities: list DB/collections, infer fields, import JSON")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list-dbs")

    p_list_col = sub.add_parser("list-cols")
    p_list_col.add_argument("db", nargs="?", default="plweb")

    p_fields = sub.add_parser("fields")
    p_fields.add_argument("collection")
    p_fields.add_argument("--db", default="plweb")
    p_fields.add_argument("--limit", type=int, default=10000)

    p_sizes = sub.add_parser("fields-sizes")
    p_sizes.add_argument("collection")
    p_sizes.add_argument("--db", default="plweb")
    p_sizes.add_argument("--array", default="sizes")
    p_sizes.add_argument("--limit", type=int, default=10000)

    p_import = sub.add_parser("import-json")
    p_import.add_argument("collection")
    p_import.add_argument("file")
    p_import.add_argument("--db", default="plweb")

    sub.add_parser("init-schema")

    args = parser.parse_args()

    if args.cmd == "list-dbs":
        print("\n".join(list_databases(client_ro)))
    elif args.cmd == "list-cols":
        database = client_ro[args.db]
        print("\n".join(list_collections(database)))
    elif args.cmd == "fields":
        database = client_ro[args.db]
        fields = infer_top_level_fields(database, args.collection, args.limit)
        print("\n".join(fields))
    elif args.cmd == "fields-sizes":
        database = client_ro[args.db]
        fields = infer_array_fields(database, args.collection, args.array, args.limit)
        print("\n".join(fields))
    elif args.cmd == "import-json":
        database = client[args.db]
        result = import_json_array(database, args.collection, args.file)
        print(json.dumps(result))
    elif args.cmd == "init-schema":
        setup_schema(client["plweb"])  # or choose args for DB if needed
        print("Schema initialization completed.")
    else:
        parser.print_help()

    client.close()


if __name__ == "__main__":
    main()