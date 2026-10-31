"""Register an app that may log in to the API.

Prints the secret once. Only its hash is stored, so it cannot be shown again.
Running it again for the same client_id issues a new secret (rotation).
"""
import secrets
import sys

from app.db import SessionLocal
from app.models import ApiClient
from app.security import hash_secret


def register(client_id, tenant_id, name):
    secret = secrets.token_urlsafe(32)
    with SessionLocal() as session:
        client = session.get(ApiClient, client_id)
        if client is None:
            client = ApiClient(client_id=client_id)
            session.add(client)
        client.tenant_id = tenant_id
        client.name = name
        client.secret_hash = hash_secret(secret)
        session.commit()
    return secret


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print('Usage: python -m app.register_client CLIENT_ID TENANT_ID "App name"')
        sys.exit(1)
    new_secret = register(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"client_id:     {sys.argv[1]}")
    print(f"client_secret: {new_secret}")
    print("Copy the secret now. It cannot be shown again.")