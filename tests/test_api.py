
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.config import settings


def create_user(client, email=None, password="StrongPass123"):
    email = email or f"user-{uuid4().hex[:8]}@example.com"

    response = client.post(
        "/auth/signup/",
        json={
            "name": "Test User",
            "email": email,
            "password": password,
        },
    )
    assert response.status_code in (200, 201), response.text

    login_response = client.post(
        "/auth/login/",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200, login_response.text

    token = login_response.json()["access_token"]

    return {
        "email": email,
        "password": password,
        "headers": {
            "Authorization": f"Bearer {token}"
        },
    }


def create_centre(client, headers):
    response = client.post(
        "/centres/",
        headers=headers,
        json={
            "name": "City Diagnostic Centre",
            "location": "Kurukshetra, Haryana",
            "tests": [
                {
                    "test_name": "CBC",
                    "description": "Complete blood count",
                    "price": "450.00",
                },
                {
                    "test_name": "Lipid Profile",
                    "description": "Cholesterol test",
                    "price": "800.00",
                },
            ],
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_booking(client, headers, centre):
    response = client.post(
        "/bookings/",
        headers=headers,
        json={
            "centre_id": centre["id"],
            "test_id": centre["tests"][0]["test_id"],
            "appointment_at": (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat(),
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def test_signup_and_login(client):
    user = create_user(client)

    assert user["email"].endswith("@example.com")
    assert user["headers"]["Authorization"].startswith("Bearer ")


def test_duplicate_signup_is_rejected(client):
    email = f"duplicate-{uuid4().hex[:8]}@example.com"

    payload = {
        "name": "Test User",
        "email": email,
        "password": "StrongPass123",
    }

    first = client.post("/auth/signup/", json=payload)
    assert first.status_code in (200, 201), first.text

    second = client.post("/auth/signup/", json=payload)
    assert second.status_code in (400, 409, 422), second.text


def test_booking_requires_authentication(client):
    response = client.post(
        "/bookings/",
        json={
            "centre_id": 1,
            "test_id": 1,
            "appointment_at": (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat(),
        },
    )

    assert response.status_code in (401, 403), response.text


def test_create_and_get_booking(client):
    user = create_user(client)
    centre = create_centre(client, user["headers"])
    booking = create_booking(client, user["headers"], centre)

    assert Decimal(str(booking["amount"])) == Decimal("450.00")

    response = client.get(
        f"/bookings/{booking['id']}/",
        headers=user["headers"],
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == booking["id"]


def test_user_cannot_access_another_users_booking(client):
    user1 = create_user(client)
    user2 = create_user(client)

    centre = create_centre(client, user1["headers"])
    booking = create_booking(client, user1["headers"], centre)

    response = client.get(
        f"/bookings/{booking['id']}/",
        headers=user2["headers"],
    )

    assert response.status_code in (403, 404), response.text


def test_successful_payment_confirms_booking(client):
    user = create_user(client)
    centre = create_centre(client, user["headers"])
    booking = create_booking(client, user["headers"], centre)

    response = client.post(
        "/payments/",
        headers=user["headers"],
        json={
            "booking_id": booking["id"],
            "simulate_status": "SUCCESS",
        },
    )

    assert response.status_code in (200, 201), response.text

    booking_response = client.get(
        f"/bookings/{booking['id']}/",
        headers=user["headers"],
    )

    assert booking_response.status_code == 200, booking_response.text
    assert booking_response.json()["status"] == "CONFIRMED"


def test_failed_payment_updates_booking(client):
    user = create_user(client)
    centre = create_centre(client, user["headers"])
    booking = create_booking(client, user["headers"], centre)

    response = client.post(
        "/payments/",
        headers=user["headers"],
        json={
            "booking_id": booking["id"],
            "simulate_status": "FAILED",
        },
    )

    assert response.status_code in (200, 201), response.text

    booking_response = client.get(
        f"/bookings/{booking['id']}/",
        headers=user["headers"],
    )

    assert booking_response.status_code == 200, booking_response.text
    assert booking_response.json()["status"] == "FAILED"


def test_webhook_is_idempotent(client):
    user = create_user(client)
    centre = create_centre(client, user["headers"])
    booking = create_booking(client, user["headers"], centre)

    payload = {
        "event_id": f"test-event-{uuid4().hex}",
        "booking_id": booking["id"],
        "status": "SUCCESS",
        "amount": str(booking["amount"]),
    }

    headers = {
        "X-Webhook-Secret": settings.jwt_secret_key
    }

    first = client.post(
        "/payments/webhook/",
        headers=headers,
        json=payload,
    )

    assert first.status_code in (200, 201), first.text

    second = client.post(
        "/payments/webhook/",
        headers=headers,
        json=payload,
    )

    assert second.status_code == first.status_code, second.text
    assert second.json() == first.json()


def test_webhook_rejects_wrong_amount(client):
    user = create_user(client)
    centre = create_centre(client, user["headers"])
    booking = create_booking(client, user["headers"], centre)

    response = client.post(
        "/payments/webhook/",
        headers={
            "X-Webhook-Secret": settings.jwt_secret_key
        },
        json={
            "event_id": f"wrong-amount-{uuid4().hex}",
            "booking_id": booking["id"],
            "status": "SUCCESS",
            "amount": "1.00",
        },
    )

    assert response.status_code in (400, 409, 422), response.text
