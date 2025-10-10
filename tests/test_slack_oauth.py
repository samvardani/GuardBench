"""Tests for Slack OAuth integration."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from service.api import app
    return TestClient(app)


def test_slack_oauth_config_not_configured():
    """Test SlackOAuthConfig when not configured."""
    with patch.dict("os.environ", {}, clear=True):
        from integrations.slack_oauth import SlackOAuthConfig
        
        config = SlackOAuthConfig()
        assert not config.is_configured()


def test_slack_oauth_config_configured():
    """Test SlackOAuthConfig when configured."""
    with patch.dict("os.environ", {
        "SLACK_CLIENT_ID": "123.456",
        "SLACK_CLIENT_SECRET": "secret123",
    }):
        from integrations.slack_oauth import SlackOAuthConfig
        
        config = SlackOAuthConfig()
        assert config.is_configured()
        assert config.client_id == "123.456"


def test_slack_oauth_get_install_url():
    """Test OAuth install URL generation."""
    from integrations.slack_oauth import SlackOAuthConfig
    
    config = SlackOAuthConfig(
        client_id="123.456",
        client_secret="secret",
    )
    
    url = config.get_install_url(state="test-state")
    
    assert "slack.com/oauth/v2/authorize" in url
    assert "client_id=123.456" in url
    assert "state=test-state" in url


def test_slack_installation_from_oauth_response():
    """Test creating SlackInstallation from OAuth response."""
    from integrations.slack_oauth import SlackInstallation
    
    oauth_data = {
        "ok": True,
        "access_token": "xoxb-test-token",
        "team": {
            "id": "T123456",
            "name": "Test Workspace"
        },
        "authed_user": {
            "id": "U123456"
        },
        "scope": "commands,chat:write",
        "app_id": "A123456",
    }
    
    installation = SlackInstallation.from_oauth_response(oauth_data)
    
    assert installation.team_id == "T123456"
    assert installation.team_name == "Test Workspace"
    assert installation.access_token == "xoxb-test-token"
    assert installation.bot_user_id == "U123456"


def test_slack_installation_to_dict_no_token():
    """Test SlackInstallation to_dict doesn't include access token."""
    from integrations.slack_oauth import SlackInstallation
    
    installation = SlackInstallation(
        team_id="T123",
        team_name="Test",
        access_token="xoxb-secret",
        bot_user_id="U123",
        scope="commands",
        app_id="A123"
    )
    
    d = installation.to_dict()
    
    assert "access_token" not in d
    assert d["team_id"] == "T123"


@pytest.mark.asyncio
async def test_oauth_exchange_code_mock():
    """Test OAuth code exchange with mock."""
    from integrations.slack_oauth import SlackOAuthConfig
    
    config = SlackOAuthConfig(
        client_id="123.456",
        client_secret="secret"
    )
    
    mock_response = {
        "ok": True,
        "access_token": "xoxb-token",
        "team": {"id": "T123", "name": "Test"},
        "authed_user": {"id": "U123"},
        "scope": "commands",
        "app_id": "A123",
    }
    
    with patch("integrations.slack_oauth.httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock()
        mock_post.json.return_value = mock_response
        mock_post.raise_for_status = MagicMock()
        
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_post
        
        result = await config.exchange_code("temp-code")
        
        assert result["ok"] is True
        assert result["access_token"] == "xoxb-token"


@pytest.mark.asyncio
async def test_oauth_exchange_code_error():
    """Test OAuth code exchange with error."""
    from integrations.slack_oauth import SlackOAuthConfig
    
    config = SlackOAuthConfig(
        client_id="123.456",
        client_secret="secret"
    )
    
    mock_response = {
        "ok": False,
        "error": "invalid_code"
    }
    
    with patch("integrations.slack_oauth.httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock()
        mock_post.json.return_value = mock_response
        mock_post.raise_for_status = MagicMock()
        
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_post
        
        with pytest.raises(ValueError, match="invalid_code"):
            await config.exchange_code("invalid-code")


def test_slack_install_endpoint_not_configured(client):
    """Test /slack/install when not configured."""
    with patch.dict("os.environ", {}, clear=True):
        # Reset global config
        import integrations.slack_oauth as slack_oauth_module
        slack_oauth_module._global_oauth_config = None
        
        response = client.get("/slack/install")
        
        assert response.status_code == 503


def test_slack_install_endpoint_redirects(client):
    """Test /slack/install redirects to Slack."""
    with patch("integrations.slack_routes.get_slack_oauth_config") as mock_config:
        mock_oauth = MagicMock()
        mock_oauth.is_configured.return_value = True
        mock_oauth.get_install_url.return_value = "https://slack.com/oauth/authorize?..."
        mock_config.return_value = mock_oauth
        
        response = client.get("/slack/install", follow_redirects=False)
        
        assert response.status_code == 307  # Redirect
        assert "slack.com" in response.headers["location"]


def test_slack_oauth_callback_missing_code(client):
    """Test OAuth callback without code."""
    response = client.get("/slack/oauth_callback")
    
    assert response.status_code == 400


def test_slack_oauth_callback_with_error(client):
    """Test OAuth callback with error from Slack."""
    response = client.get("/slack/oauth_callback?error=access_denied")
    
    assert response.status_code == 400
    assert "Installation Failed" in response.text


@pytest.mark.asyncio
async def test_slack_oauth_callback_success(client):
    """Test successful OAuth callback."""
    with patch("integrations.slack_routes.get_slack_oauth_config") as mock_get_config:
        from integrations.slack_oauth import SlackOAuthConfig
        
        mock_config = SlackOAuthConfig(
            client_id="123.456",
            client_secret="secret"
        )
        
        mock_oauth_response = {
            "ok": True,
            "access_token": "xoxb-token",
            "team": {"id": "T123", "name": "Test Workspace"},
            "authed_user": {"id": "U123"},
            "scope": "commands",
            "app_id": "A123",
        }
        
        mock_config.exchange_code = AsyncMock(return_value=mock_oauth_response)
        mock_get_config.return_value = mock_config
        
        response = client.get("/slack/oauth_callback?code=temp-code&state=test-state")
        
        # Should show success page
        assert response.status_code == 200
        assert "Installation Successful" in response.text


def test_add_to_slack_page_loads(client):
    """Test /slack/add-to-slack page loads."""
    with patch("integrations.slack_routes.get_slack_oauth_config") as mock_config:
        mock_oauth = MagicMock()
        mock_oauth.is_configured.return_value = True
        mock_config.return_value = mock_oauth
        
        response = client.get("/slack/add-to-slack")
        
        assert response.status_code == 200
        assert "Add to Slack" in response.text


def test_add_to_slack_page_not_configured(client):
    """Test /slack/add-to-slack when not configured."""
    with patch.dict("os.environ", {}, clear=True):
        import integrations.slack_oauth as slack_oauth_module
        slack_oauth_module._global_oauth_config = None
        
        response = client.get("/slack/add-to-slack")
        
        assert response.status_code == 503


def test_db_slack_init_tables():
    """Test Slack database table initialization."""
    import sqlite3
    from service.db_slack import init_slack_tables
    
    conn = sqlite3.connect(":memory:")
    init_slack_tables(conn)
    
    # Verify table exists
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='slack_installations'")
    assert cur.fetchone() is not None


def test_db_slack_store_installation():
    """Test storing Slack installation."""
    import sqlite3
    from service.db_slack import init_slack_tables, store_slack_installation
    
    conn = sqlite3.connect(":memory:")
    init_slack_tables(conn)
    
    success = store_slack_installation(
        conn,
        team_id="T123",
        team_name="Test",
        access_token="xoxb-token",
        bot_user_id="U123",
        scope="commands",
        app_id="A123"
    )
    
    assert success is True


def test_db_slack_get_installation():
    """Test retrieving Slack installation."""
    import sqlite3
    from service.db_slack import init_slack_tables, store_slack_installation, get_slack_installation
    
    conn = sqlite3.connect(":memory:")
    init_slack_tables(conn)
    store_slack_installation(
        conn, "T123", "Test", "xoxb-token", "U123", "commands", "A123"
    )
    
    installation = get_slack_installation(conn, "T123")
    
    assert installation is not None
    assert installation["team_id"] == "T123"
    assert installation["access_token"] == "xoxb-token"


def test_db_slack_get_nonexistent_installation():
    """Test getting non-existent installation returns None."""
    import sqlite3
    from service.db_slack import init_slack_tables, get_slack_installation
    
    conn = sqlite3.connect(":memory:")
    init_slack_tables(conn)
    
    installation = get_slack_installation(conn, "T999")
    
    assert installation is None


def test_slack_oauth_scopes():
    """Test default OAuth scopes."""
    from integrations.slack_oauth import SlackOAuthConfig
    
    config = SlackOAuthConfig()
    
    assert "commands" in config.scopes
    assert "chat:write" in config.scopes

