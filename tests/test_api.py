from datetime import datetime, timedelta, timezone

def signup_and_login(client, email="amrish@example.com"):
    r = client.post("/auth/signup", json={"name": "Amrish Kumar", "email": email, "password": "StrongPass123"})
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", json={"email": email, "password": "StrongPass123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

def create_centre(client):
    r = client.post("/centres/", json={"name": "City Diagnostic Centre", "location": "Kurukshetra, Haryana", "tests": [
        {"test_name": "CBC", "description": "Complete blood count", "price": "450.00"},
        {"test_name": "Lipid Profile", "description": "Cholesterol test", "price": "800.00"}]})
    assert r.status_code == 201, r.text
    return r.json()

def create_booking(client, headers, centre):
    test = next(t for t in centre["tests"] if t["test_name"] == "CBC")
    r = client.post("/bookings/", headers=headers, json={"centre_id": centre["id"], "test_id": test["test_id"], "appointment_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()})
    assert r.status_code == 201, r.text
    return r.json()

def test_signup_login_and_duplicate_email(client):
    headers = signup_and_login(client)
    assert headers["Authorization"].startswith("Bearer ")
    r = client.post("/auth/signup", json={"name": "Another User", "email": "amrish@example.com", "password": "StrongPass123"})
    assert r.status_code == 409

def test_booking_requires_authentication(client):
    centre = create_centre(client)
    test = centre["tests"][0]
    r = client.post("/bookings/", json={"centre_id": centre["id"], "test_id": test["test_id"], "appointment_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()})
    assert r.status_code == 401

def test_booking_and_successful_payment(client):
    headers = signup_and_login(client)
    booking = create_booking(client, headers, create_centre(client))
    assert booking["status"] == "PENDING"
    r = client.post("/payments/", headers=headers, json={"booking_id": booking["id"], "simulate_status": "SUCCESS"})
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "SUCCESS"
    updated = client.get(f"/bookings/{booking['id']}", headers=headers)
    assert updated.json()["status"] == "CONFIRMED"

def test_webhook_is_idempotent(client):
    headers = signup_and_login(client)
    booking = create_booking(client, headers, create_centre(client))
    payload = {"event_id": "provider-event-123", "booking_id": booking["id"], "status": "SUCCESS", "amount": str(booking["amount"])}
    secret = {"X-Webhook-Secret": "test-secret-key"}
    first = client.post("/payments/webhook/", json=payload, headers=secret)
    second = client.post("/payments/webhook/", json=payload, headers=secret)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["id"] == second.json()["id"]

def test_webhook_rejects_wrong_amount(client):
    headers = signup_and_login(client)
    booking = create_booking(client, headers, create_centre(client))
    r = client.post("/payments/webhook/", headers={"X-Webhook-Secret": "test-secret-key"}, json={"event_id": "wrong-amount-event", "booking_id": booking["id"], "status": "SUCCESS", "amount": "1.00"})
    assert r.status_code == 400

def test_user_cannot_read_another_users_booking(client):
    headers1 = signup_and_login(client, "one@example.com")
    headers2 = signup_and_login(client, "two@example.com")
    booking = create_booking(client, headers1, create_centre(client))
    r = client.get(f"/bookings/{booking['id']}", headers=headers2)
    assert r.status_code == 404

def test_failed_payment_updates_booking(client):
    headers = signup_and_login(client)
    booking = create_booking(client, headers, create_centre(client))
    r = client.post("/payments/", headers=headers, json={"booking_id": booking["id"], "simulate_status": "FAILED"})
    assert r.status_code == 201
    updated = client.get(f"/bookings/{booking['id']}", headers=headers)
    assert updated.json()["status"] == "FAILED"
