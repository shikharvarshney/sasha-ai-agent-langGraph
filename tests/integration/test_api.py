"""Integration tests for API endpoints"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client"""
    # Disable LangSmith for tests
    import os
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    from sasha_sales_ai.main import app
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint"""
    
    def test_health_check(self, client):
        """Test health endpoint returns OK"""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestRootEndpoint:
    """Tests for root endpoint"""
    
    def test_root(self, client):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Sasha Sales AI"
        assert "version" in data


class TestLeadsEndpoint:
    """Tests for leads listing endpoint"""
    
    def test_list_leads_empty(self, client):
        """Test listing leads when empty"""
        response = client.get("/api/v1/leads")
        
        assert response.status_code == 200
        data = response.json()
        assert "leads" in data
        assert "total" in data


class TestPendingApprovalsEndpoint:
    """Tests for pending approvals endpoint"""
    
    def test_get_pending_approvals(self, client):
        """Test getting pending approvals"""
        response = client.get("/api/v1/approvals/pending")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestLeadNotFound:
    """Tests for lead not found scenarios"""
    
    def test_get_nonexistent_lead(self, client):
        """Test getting a lead that doesn't exist"""
        response = client.get("/api/v1/lead/nonexistent-lead-id")
        
        assert response.status_code == 404
    
    def test_approve_nonexistent_lead(self, client):
        """Test approving a lead that doesn't exist"""
        response = client.post(
            "/api/v1/approve/nonexistent-lead-id",
            json={"approved_by": "test", "notes": "test"}
        )
        
        assert response.status_code in [400, 404, 500]


class TestEmailWebhookValidation:
    """Tests for email webhook validation"""
    
    def test_webhook_missing_fields(self, client):
        """Test webhook with missing required fields"""
        response = client.post(
            "/api/v1/webhook/email",
            json={"from_email": "test@example.com"}  # missing subject and body
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_webhook_invalid_email(self, client):
        """Test webhook with invalid email format"""
        response = client.post(
            "/api/v1/webhook/email",
            json={
                "from_email": "not-an-email",
                "subject": "Test",
                "body": "Test body",
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestReplyWebhookValidation:
    """Tests for reply webhook validation"""
    
    def test_reply_webhook_missing_lead_id(self, client):
        """Test reply webhook without lead_id"""
        response = client.post(
            "/api/v1/webhook/reply",
            json={
                "from_email": "test@example.com",
                "subject": "Re: Quote",
                "body": "I accept",
            }
        )
        
        assert response.status_code == 400
        assert "lead_id" in response.json()["detail"].lower()

