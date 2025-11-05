from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
import sys

try:
    import certifi
    CA_FILE = certifi.where()
except Exception:
    CA_FILE = None


def main():
    # Prefer env var, fallback to current URI
    uri = os.getenv(
        "MONGODB_URI",
        "mongodb+srv://plwebdatabase123:PLWebsite123@plweb.escgc7n.mongodb.net/?retryWrites=true&w=majority&appName=PLWeb",
    )

    client_kwargs = {"server_api": ServerApi("1")}

    # Use certifi CA bundle if available
    if CA_FILE:
        client_kwargs["tlsCAFile"] = CA_FILE

    client = MongoClient(uri, **client_kwargs)

    try:
        client.admin.command("ping")
        print("Ping OK: Connected to MongoDB")

        # Show basic info
        try:
            db_name = (client.get_default_database().name
                       if client.get_default_database() is not None else "<no-default-db>")
        except Exception:
            db_name = "<no-default-db>"
        print(f"Default DB: {db_name}")

        # Attempt to list databases (may require perm)
        try:
            dbs = [d["name"] for d in client.list_databases()]
            print("Databases:", dbs)
        except Exception as e:
            print("List databases failed:", e)

    except Exception as e:
        print("Connection error:")
        print(e)
        # Diagnostics
        print("\nDiagnostics:")
        print("- Ensure your IP is whitelisted in Atlas (Network Access)")
        print("- Try setting env var MONGODB_URI to your Atlas connection string")
        if not CA_FILE:
            print("- Install certifi: pip install certifi")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()


