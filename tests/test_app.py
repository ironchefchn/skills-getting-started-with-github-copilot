import copy
import pytest
from fastapi.testclient import TestClient

from src.app import app, activities


@pytest.fixture(autouse=True)
def reset_activities():
    """Arrange: back up and restore the in-memory `activities` to keep tests isolated."""
    original = copy.deepcopy(activities)
    yield
    activities.clear()
    activities.update(copy.deepcopy(original))


@pytest.fixture
def client():
    """Arrange: provide a TestClient for the app."""
    return TestClient(app)


def test_get_activities(client):
    # Arrange
    # client fixture provided, activities seeded by app

    # Act
    resp = client.get("/activities")

    # Assert
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    # expected top-level activities
    assert "Chess Club" in data
    assert "Programming Class" in data
    assert "Gym Class" in data
    # check structure of one activity
    chess = data["Chess Club"]
    assert set(chess.keys()) >= {"description", "schedule", "max_participants", "participants"}


def test_signup_success(client):
    # Arrange
    activity = "Chess Club"
    email = "teststudent@example.com"
    assert email not in activities[activity]["participants"]

    # Act
    resp = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert resp.status_code == 200
    body = resp.json()
    assert "Signed up" in body.get("message", "")
    assert email in activities[activity]["participants"]


def test_signup_activity_not_found(client):
    # Arrange
    activity = "Nonexistent Club"
    email = "nobody@example.com"

    # Act
    resp = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert resp.status_code == 404
    data = resp.json()
    assert data.get("detail") == "Activity not found"


def test_duplicate_signup_prevented(client):
    # Arrange
    activity = "Programming Class"
    email = "emma@mergington.edu"
    original_count = activities[activity]["participants"].count(email)

    # Act
    resp = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert resp.status_code == 409
    data = resp.json()
    assert data.get("detail") == "Already signed up"
    assert activities[activity]["participants"].count(email) == original_count


def test_capacity_enforced(client):
    # Arrange
    activity = "Gym Class"
    # Temporarily set max to current participants to simulate full activity
    activities[activity]["max_participants"] = len(activities[activity]["participants"])
    email = "latecomer@example.com"

    # Act
    resp = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert resp.status_code == 400
    data = resp.json()
    assert data.get("detail") == "Activity is full"
    assert email not in activities[activity]["participants"]


def test_signup_empty_email_rejected(client):
    # Arrange
    activity = "Chess Club"
    email = "   "

    # Act
    resp = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert resp.status_code == 400
    data = resp.json()
    assert data.get("detail") == "Email must not be empty"
    assert email.strip() not in activities[activity]["participants"]
