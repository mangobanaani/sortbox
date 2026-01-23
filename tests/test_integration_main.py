"""Integration tests for src/main.py"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.config import LabelConfig, Settings


def test_get_provider_claude():
    """Test that get_provider returns ClaudeProvider for claude"""
    from src.main import get_provider

    config = LabelConfig(
        labels={},
        settings=Settings(llm_provider="claude")
    )
    provider = get_provider(config)
    assert provider.__class__.__name__ == "ClaudeProvider"


def test_get_provider_openai():
    """Test that get_provider returns OpenAIProvider for openai"""
    import os

    from src.main import get_provider

    # Mock the OpenAI API key
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        config = LabelConfig(
            labels={},
            settings=Settings(llm_provider="openai")
        )
        provider = get_provider(config)
        assert provider.__class__.__name__ == "OpenAIProvider"


def test_get_provider_ollama():
    """Test that get_provider returns OllamaProvider for ollama"""
    from src.main import get_provider

    config = LabelConfig(
        labels={},
        settings=Settings(llm_provider="ollama")
    )
    provider = get_provider(config)
    assert provider.__class__.__name__ == "OllamaProvider"


def test_get_provider_unknown():
    """Test that get_provider raises ValueError for unknown provider"""
    from src.main import get_provider

    config = LabelConfig(
        labels={},
        settings=Settings(llm_provider="unknown")
    )
    with pytest.raises(ValueError, match="Unknown provider: unknown"):
        get_provider(config)


@pytest.mark.asyncio
async def test_app_initialization():
    """Test that app starts and basic routes are registered"""
    # Mock the config loading to avoid needing a real labels.yaml file
    with patch('src.main.load_config') as mock_load_config, \
         patch('src.main.get_provider') as mock_get_provider:

        # Setup mock config
        mock_config = LabelConfig(
            labels={
                "test-label": {
                    "description": "Test label",
                    "rules": []
                }
            },
            settings=Settings(llm_provider="claude")
        )
        mock_load_config.return_value = mock_config

        # Setup mock provider
        mock_provider = MagicMock()
        mock_provider.classify = MagicMock()
        mock_get_provider.return_value = mock_provider

        # Import app after mocking
        from src.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Health endpoint should exist
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

            # Docs endpoint should exist (FastAPI auto-generated)
            response = await client.get("/docs")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_app_classify_endpoint_exists():
    """Test that classify endpoint exists and is accessible"""
    # Mock the config loading
    with patch('src.main.load_config') as mock_load_config, \
         patch('src.main.get_provider') as mock_get_provider:

        # Setup mock config
        mock_config = LabelConfig(
            labels={
                "invoices": {
                    "description": "Bills",
                    "rules": [{"from": "*@stripe.com"}]
                }
            },
            settings=Settings(llm_provider="claude")
        )
        mock_load_config.return_value = mock_config

        # Setup mock provider
        from src.classifier.providers.base import LLMClassification
        mock_provider = MagicMock()

        async def mock_classify(emails, label_definitions):
            return [LLMClassification(label="invoices", confidence=0.9) for _ in emails]

        mock_provider.classify = mock_classify
        mock_get_provider.return_value = mock_provider

        # Import app after mocking
        from src.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/classify",
                json={
                    "emails": [
                        {
                            "email_id": "test001",
                            "sender": "billing@stripe.com",
                            "subject": "Invoice",
                            "body_preview": "Your invoice is ready"
                        }
                    ]
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 1


def test_module_level_initialization():
    """Test that module-level variables are properly initialized"""
    # This test verifies the structure of module-level initialization
    # Note: Cannot easily test module-level code execution during import
    # since the module is already loaded before tests run

    import src.main

    # Verify that expected module-level variables exist
    assert hasattr(src.main, 'config_path')
    assert hasattr(src.main, 'config')
    assert hasattr(src.main, 'provider')
    assert hasattr(src.main, 'app')

    # Verify types
    assert src.main.config_path.name == "labels.yaml"
    assert src.main.config.__class__.__name__ == "LabelConfig"
    assert src.main.provider is not None
    assert src.main.app is not None


def test_uvicorn_main_block():
    """Test that __main__ block would call uvicorn.run"""
    with patch('src.main.load_config'), \
         patch('src.main.get_provider'), \
         patch('src.main.uvicorn.run'):

        # Import the module
        import src.main

        # Simulate running as main
        if src.main.__name__ == "__main__":
            src.main.uvicorn.run(src.main.app, host="127.0.0.1", port=8000)

        # Note: This test verifies the structure exists, not that it executes
        # since __name__ will be 'src.main' during test import
        assert hasattr(src.main, 'app')
        assert hasattr(src.main, 'uvicorn')
