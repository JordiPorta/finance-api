"""Quick end-to-end smoke test. Run: python smoke_test.py (then delete finance.db)."""
from fastapi.testclient import TestClient

from database import create_db_and_tables
from main import app

create_db_and_tables()
client = TestClient(app)

# Health
r = client.get("/")
assert r.status_code == 200, r.text
print("health:", r.json())

# Register + login
r = client.post(
    "/auth/register",
    json={"email": "test@example.com", "password": "secret123", "name": "Test"},
)
assert r.status_code in (201, 400), r.text  # 400 if re-run
r = client.post(
    "/auth/login", json={"email": "test@example.com", "password": "secret123"}
)
assert r.status_code == 200, r.text
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("login: ok")

r = client.get("/auth/me", headers=headers)
assert r.status_code == 200, r.text
print("me:", r.json()["email"])

# Account CRUD
r = client.post(
    "/accounts/", json={"name": "Main Bank", "type": "bank", "currency": "EUR"},
    headers=headers,
)
assert r.status_code == 201, r.text
account_id = r.json()["id"]
print("account created:", account_id)

# Transactions + filters
r = client.post(
    "/transactions/",
    json={
        "account_id": account_id,
        "amount": 2500,
        "type": "income",
        "description": "Salary",
        "date": "2026-07-01",
    },
    headers=headers,
)
assert r.status_code == 201, r.text
r = client.post(
    "/transactions/",
    json={
        "account_id": account_id,
        "amount": 800,
        "type": "expense",
        "description": "Rent",
        "date": "2026-07-01",
    },
    headers=headers,
)
assert r.status_code == 201, r.text
r = client.get(
    "/transactions/",
    params={"type": "expense", "from_date": "2026-07-01"},
    headers=headers,
)
assert r.status_code == 200 and len(r.json()) >= 1, r.text
print("transactions + filters: ok")

# Investments: asset -> buy -> buy (weighted avg) -> sell -> history -> summary
r = client.post(
    "/investments/assets",
    json={"ticker": "VWCE", "name": "Vanguard FTSE All-World", "type": "etf"},
    headers=headers,
)
assert r.status_code in (201, 400), r.text
r = client.get("/investments/assets", headers=headers)
asset_id = r.json()[0]["id"]

r = client.post(
    "/investments/",
    json={
        "account_id": account_id,
        "asset_id": asset_id,
        "shares": 10,
        "price": 100,
        "date": "2026-07-01",
    },
    headers=headers,
)
assert r.status_code == 201, r.text
inv_id = r.json()["id"]
r = client.post(
    "/investments/",
    json={
        "account_id": account_id,
        "asset_id": asset_id,
        "shares": 10,
        "price": 120,
        "date": "2026-07-02",
    },
    headers=headers,
)
assert r.status_code == 201, r.text
assert r.json()["avg_buy_price"] == 110, r.json()  # weighted average
print("buy + weighted avg: ok (avg=110)")

r = client.post(
    f"/investments/{inv_id}/sell",
    json={"shares": 5, "price": 130, "date": "2026-07-02"},
    headers=headers,
)
assert r.status_code == 200 and r.json()["shares"] == 15, r.text
print("sell: ok")

r = client.get(f"/investments/{inv_id}/history", headers=headers)
assert r.status_code == 200 and len(r.json()) == 3, r.text
print("history:", len(r.json()), "operations")

r = client.get("/investments/summary", headers=headers)
assert r.status_code == 200, r.text
print("summary:", r.json()["total_invested"])

# Stats
r = client.get("/stats/cashflow", params={"period": "2026-07"}, headers=headers)
assert r.status_code == 200 and r.json()["net"] == 1700, r.text
print("cashflow:", r.json())

r = client.get("/stats/expenses/by-category", headers=headers)
assert r.status_code == 200, r.text
print("by-category:", r.json())

r = client.post("/stats/networth/snapshot", headers=headers)
assert r.status_code == 201, r.text
print("snapshot:", r.json()["net"])

r = client.get("/stats/networth/history", headers=headers)
assert r.status_code == 200 and len(r.json()) >= 1, r.text

print("\nALL SMOKE TESTS PASSED")
