
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.read_preferences import ReadPreference
from typing import Dict, Any, Set

uri = "mongodb+srv://plwebdatabase123:PLWebsite123@plweb.escgc7n.mongodb.net/?retryWrites=false&w=majority&appName=PLWeb"

# Create a new client and connect to the server (prefer secondary for read-only checks)
client = MongoClient(
    uri,
    server_api=ServerApi('1'),
    read_preference=ReadPreference.SECONDARY_PREFERRED,
)

def get_fields_from_validator(validator: Dict[str, Any]) -> Set[str]:
    fields: Set[str] = set()
    try:
        schema = validator.get('$jsonSchema') or {}
        props = schema.get('properties') or {}
        fields.update(props.keys())
    except Exception:
        pass
    return fields

def get_fields_from_samples(coll, sample_size: int = 50) -> Set[str]:
    fields: Set[str] = set()
    try:
        # Prefer $sample when possible; fall back to find().limit()
        try:
            cursor = coll.aggregate([{ '$sample': { 'size': sample_size } }])
        except Exception:
            cursor = coll.find({}, { '_id': 0 }).limit(sample_size)
        for doc in cursor:
            if isinstance(doc, dict):
                fields.update(doc.keys())
    except Exception:
        pass
    return fields

def list_collections_and_fields(db_name: str) -> None:
    try:
        admin_ro = client.get_database('admin', read_preference=ReadPreference.SECONDARY_PREFERRED)
        admin_ro.command({'ping': 1})
        print("Ping OK (secondaryPreferred).")
    except Exception as e:
        print(f"Ping failed: {e}")
        return

    db = client.get_database(db_name, read_preference=ReadPreference.SECONDARY_PREFERRED)

    try:
        # List collections with options (to read validators if set)
        coll_info = db.command({'listCollections': 1})
        infos = coll_info.get('cursor', {}).get('firstBatch', [])
    except Exception as e:
        print(f"Failed to list collections: {e}")
        return

    if not infos:
        print(f"No collections found in database '{db_name}'.")
        return

    print(f"Database: {db_name}")
    for info in infos:
        name = info.get('name')
        options = info.get('options') or {}
        validator = options.get('validator') or {}

        fields_from_validator = get_fields_from_validator(validator)
        fields_from_data = get_fields_from_samples(db[name])

        # Prefer validator-defined fields; merge with sample-derived for completeness
        all_fields = sorted(fields_from_validator.union(fields_from_data))

        print(f"\n- Collection: {name}")
        if fields_from_validator:
            print(f"  Fields (from validator): {sorted(fields_from_validator)}")
        if fields_from_data:
            print(f"  Fields (from data samples): {sorted(fields_from_data)}")
        print(f"  Fields (union): {all_fields}")

def list_all_dbs_and_fields(skip_system: bool = True) -> None:
    try:
        admin_ro = client.get_database('admin', read_preference=ReadPreference.SECONDARY_PREFERRED)
        admin_ro.command({'ping': 1})
        print("Ping OK (secondaryPreferred). Listing databases...")
        dbs_res = admin_ro.command({'listDatabases': 1, 'nameOnly': True})
        db_names = [d['name'] for d in dbs_res.get('databases', [])]
    except Exception as e:
        print(f"Failed to list databases: {e}")
        return

    system_dbs = {"admin", "local", "config"}
    for db_name in db_names:
        if skip_system and db_name in system_dbs:
            continue
        print("\n===============================")
        list_collections_and_fields(db_name)

if __name__ == "__main__":
    list_all_dbs_and_fields(skip_system=True)