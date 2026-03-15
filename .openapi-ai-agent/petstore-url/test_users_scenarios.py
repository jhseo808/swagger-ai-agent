import os
import uuid

import requests

BASE_URL = os.environ.get("OPENAPI_BASE_URL", "https://petstore.swagger.io/v2")


def unique_email():
    return f"agent-{uuid.uuid4().hex[:8]}@example.com"

def test_get_pet_findbystatus_happy_path():
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": ["available"]}, timeout=30)
    assert response.status_code in (200, 204)

def test_get_store_inventory_happy_path():
    response = requests.get(f"{BASE_URL}/store/inventory", timeout=30)
    assert response.status_code in (200, 204)

def test_get_user_login_happy_path():
    response = requests.get(f"{BASE_URL}/user/login", params={"username": "user1", "password": "password123"}, timeout=30)
    assert response.status_code in (200, 204)

def test_get_pet_petid_resource_lookup():
    response = requests.get(f"{BASE_URL}/pet/1", timeout=30)
    assert response.status_code in (200, 404)

def test_get_pet_petid_not_found():
    response = requests.get(f"{BASE_URL}/pet/999999", timeout=30)
    assert response.status_code == 404

def test_get_store_order_orderid_resource_lookup():
    response = requests.get(f"{BASE_URL}/store/order/1", timeout=30)
    assert response.status_code in (200, 404)

def test_get_store_order_orderid_not_found():
    response = requests.get(f"{BASE_URL}/store/order/999999", timeout=30)
    assert response.status_code == 404

def test_get_user_username_resource_lookup():
    response = requests.get(f"{BASE_URL}/user/user1", timeout=30)
    assert response.status_code in (200, 404)

def test_get_user_username_not_found():
    response = requests.get(f"{BASE_URL}/user/999999", timeout=30)
    assert response.status_code == 404
