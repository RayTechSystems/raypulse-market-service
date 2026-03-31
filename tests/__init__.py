import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from freeapp import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    """Test health endpoint returns 200"""
    response = client.get('/health')
    assert response.status_code == 200

def test_health_returns_ok(client):
    """Test health endpoint returns ok status"""
    response = client.get('/health')
    data = response.get_json()
    assert data['status'] == 'ok'

def test_market_endpoint(client):
    """Test market endpoint returns 200"""
    response = client.get('/market')
    assert response.status_code == 200

def test_market_returns_json(client):
    """Test market endpoint returns JSON"""
    response = client.get('/market')
    assert response.content_type == 'application/json'

def test_quote_invalid_symbol(client):
    """Test invalid symbol returns 404"""
    response = client.get('/quote/INVALID')
    assert response.status_code == 404 
