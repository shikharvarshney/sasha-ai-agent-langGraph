"""Pytest configuration and fixtures"""

import os
import pytest
from unittest.mock import MagicMock, patch

# Disable LangSmith tracing during tests
os.environ["LANGSMITH_TRACING"] = "false"


@pytest.fixture
def mock_openai():
    """Mock OpenAI API calls"""
    with patch("langchain_openai.ChatOpenAI") as mock:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = MagicMock(content="Test response")
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def sample_email_data():
    """Sample email data for testing"""
    return {
        "lead_id": "test-lead-001",
        "email_from": "customer@example.com",
        "email_subject": "Quote Request",
        "email_body": "I need 100 custom widgets with logo printing. Timeline: 2 weeks.",
    }


@pytest.fixture
def sample_flow_state(sample_email_data):
    """Sample flow state for testing"""
    return {
        **sample_email_data,
        "status": "new",
        "email_type": "new",
        "thread_history": "",
    }

