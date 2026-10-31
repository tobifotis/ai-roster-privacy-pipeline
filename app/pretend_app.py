"""A pretend learning app: logs in with OAuth, then asks the API for its district's roster."""
import os
import sys

import httpx

BASE_URL = os.getenv("ROSTER_API_URL", "http://localhost:8000")
CLIENT_ID = "pretend-learning-app"
DISTRICT = "district_a"


def main():
    secret = os.getenv("PRETEND_APP_SECRET")
    if not secret:
        print("PRETEND_APP_SECRET is not set in this terminal tab.")
        sys.exit(1)

    # Step 1: trade the client ID and secret for a one-hour token
    login = httpx.post(f"{BASE_URL}/oauth/token", data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": secret,
    })
    if login.status_code != 200:
        print(f"Login failed ({login.status_code}): {login.text}")
        sys.exit(1)
    token = login.json()["access_token"]
    print(f"Logged in as {CLIENT_ID}. Token received (valid for 1 hour).\n")

    # Step 2: show the token with the request for our district's roster
    response = httpx.get(
        f"{BASE_URL}/tenants/{DISTRICT}/students",
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(f"Roster request failed ({response.status_code}): {response.text}")
        sys.exit(1)
    students = response.json()
    print(f"Received {len(students)} students for {DISTRICT}. First three:\n")
    for s in students[:3]:
        print(f"  {s['sourced_id']}  grades={s['grades']}  classes={len(s['class_ids'])}")
        for note in s["notes"]:
            print(f"      note: {note['text']}")


if __name__ == "__main__":
    main()