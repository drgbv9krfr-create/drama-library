
import json
import os
import urllib.request
import urllib.error

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]
EMAIL = os.environ["SUPABASE_EMAIL"]
PASSWORD = os.environ["SUPABASE_PASSWORD"]


def request_json(url, method="GET", data=None, token=None):
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        headers["Authorization"] = f"Bearer {SUPABASE_KEY}"

    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        url, data=body, headers=headers, method=method
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode())


def main():
    # Sign in to the private database
    login = request_json(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        method="POST",
        data={"email": EMAIL, "password": PASSWORD}
    )

    token = login["access_token"]
    print("Database login successful.")

    # Retrieve active source websites
    sources = request_json(
        f"{SUPABASE_URL}/rest/v1/source_sites"
        "?select=name,website_url,active&active=eq.true&order=name",
        token=token
    )

    print(f"Found {len(sources)} active sources.")

    # Check which websites respond
    for source in sources:
        name = source["name"]
        url = source.get("website_url")

        if not url:
            print(f"NEEDS URL: {name}")
            continue

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "DramaLibraryBot/1.0"}
            )
            with urllib.request.urlopen(req, timeout=20) as response:
                print(f"OK ({response.status}): {name}")

        except Exception as error:
            print(f"CHECK: {name} - {error}")


if __name__ == "__main__":
    main()
