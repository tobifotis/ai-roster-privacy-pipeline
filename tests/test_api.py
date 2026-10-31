import os
import time

import jwt


def login(client, client_id, secret, grant_type="client_credentials"):
    return client.post("/oauth/token", data={
        "grant_type": grant_type, "client_id": client_id, "client_secret": secret,
    })


def bearer(client, client_id="app-a", secret="secret-a"):
    token = login(client, client_id, secret).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_token(**overrides):
    now = int(time.time())
    claims = {"sub": "app-a", "tenant": "district_a", "scope": "roster:read",
              "iat": now, "exp": now + 3600}
    claims.update(overrides)
    return jwt.encode(claims, os.environ["ROSTER_JWT_SECRET"], algorithm="HS256")


# ---- the login window ----

def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_login_returns_a_token(client):
    r = login(client, "app-a", "secret-a")
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert body["access_token"]


def test_login_with_wrong_secret_is_401(client):
    assert login(client, "app-a", "wrong").status_code == 401


def test_login_with_unknown_client_is_401(client):
    assert login(client, "nobody", "secret-a").status_code == 401


def test_login_with_unsupported_grant_type_is_400(client):
    assert login(client, "app-a", "secret-a", grant_type="password").status_code == 400


# ---- the bouncer ----

def test_roster_without_token_is_401(client):
    assert client.get("/tenants/district_a/students").status_code == 401


def test_roster_with_garbage_token_is_401(client):
    r = client.get("/tenants/district_a/students", headers={"Authorization": "Bearer abc"})
    assert r.status_code == 401


def test_roster_with_forged_token_is_401(client):
    headers = bearer(client)
    headers["Authorization"] += "x"  # one extra character breaks the signature
    assert client.get("/tenants/district_a/students", headers=headers).status_code == 401


def test_roster_with_expired_token_is_401(client):
    past = int(time.time()) - 10
    headers = {"Authorization": f"Bearer {make_token(iat=past - 3600, exp=past)}"}
    assert client.get("/tenants/district_a/students", headers=headers).status_code == 401


def test_token_with_wrong_scope_is_403(client):
    headers = {"Authorization": f"Bearer {make_token(scope='something:else')}"}
    assert client.get("/tenants/district_a/students", headers=headers).status_code == 403


# ---- district separation ----

def test_app_can_read_its_own_district(client):
    r = client.get("/tenants/district_a/students", headers=bearer(client))
    assert r.status_code == 200
    assert [s["sourced_id"] for s in r.json()] == ["district_a-student-1", "district_a-student-2"]


def test_app_cannot_read_another_district(client):
    r = client.get("/tenants/district_b/students", headers=bearer(client))
    assert r.status_code == 403


def test_unknown_district_is_403_not_404(client):
    # a 404 would let an app discover which districts exist
    r = client.get("/tenants/nope/students", headers=bearer(client))
    assert r.status_code == 403


# ---- privacy ----

def test_roster_never_contains_private_details(client):
    body = client.get("/tenants/district_a/students", headers=bearer(client)).text
    for private in ["Maria", "Lopez", "12 Oak", "Sam", "Cole", "@",
                    "Raw note", "Ana", "Reyes", "district_b"]:
        assert private not in body, f"{private!r} leaked into the roster"


def test_cleaned_note_is_served_instead_of_the_original(client):
    students = client.get("/tenants/district_a/students", headers=bearer(client)).json()
    assert students[0]["notes"][0]["text"] == "[PII] moved to [PII]."


def test_note_without_cleaned_copy_is_not_served(client):
    students = client.get("/tenants/district_a/students", headers=bearer(client)).json()
    assert students[1]["notes"] == []  # Sam's note was never cleaned: fail closed


def test_each_student_has_only_the_allowed_fields(client):
    students = client.get("/tenants/district_a/students", headers=bearer(client)).json()
    for student in students:
        assert set(student) == {"sourced_id", "grades", "class_ids", "notes"}