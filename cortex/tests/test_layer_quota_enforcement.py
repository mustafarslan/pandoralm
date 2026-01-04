import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timedelta

from app.models.layer import Layer, LayerType, QuotaTier, AccessLevel
from app.services.security.layer_manager import LayerManager

# Mock DB Session
@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session

@pytest.fixture
def layer_manager():
    return LayerManager()

@pytest.mark.asyncio
async def test_create_private_layer_for_user(layer_manager, mock_db):
    user_id = "user-123"
    username = "testuser"
    
    # Mock no existing layer
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    
    # We need to mock assigns_permission too as it uses db
    with patch.object(layer_manager, 'assign_permission', new_callable=AsyncMock) as mock_assign:
        layer = await layer_manager.create_private_layer_for_user(user_id, username, mock_db)
        
        assert layer.name == f"user-{username}"
        assert layer.type == LayerType.USER
        assert layer.owner_user_id == user_id
        assert layer.quota_tier == QuotaTier.FREE
        assert layer.storage_quota_bytes == 104857600
        
        # Verify DB calls
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
        mock_assign.assert_called_with(layer.id, f"user:{user_id}", AccessLevel.ADMIN, mock_db)

@pytest.mark.asyncio
async def test_create_private_layer_returns_existing(layer_manager, mock_db):
    user_id = "user-123"
    username = "testuser"
    
    existing_layer = Layer(id="existing", name="user-testuser")
    mock_db.execute.return_value.scalar_one_or_none.return_value = existing_layer
    
    layer = await layer_manager.create_private_layer_for_user(user_id, username, mock_db)
    
    assert layer == existing_layer
    mock_db.add.assert_not_called()

@pytest.mark.asyncio
async def test_check_quota_exceeded(layer_manager, mock_db):
    layer_id = str(uuid4())
    
    # Mock layer with quota exceeded
    mock_layer = Layer(
        id=layer_id, 
        storage_quota_bytes=100, 
        storage_used_bytes=150
    )
    # Configure mock for get_layer
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_layer
    
    is_exceeded = await layer_manager.check_quota_exceeded(layer_id, mock_db)
    assert is_exceeded is True

    # Mock layer within quota
    mock_layer.storage_used_bytes = 50
    is_exceeded = await layer_manager.check_quota_exceeded(layer_id, mock_db)
    assert is_exceeded is False

@pytest.mark.asyncio
async def test_update_storage_used(layer_manager, mock_db):
    layer_id = str(uuid4())
    mock_layer = Layer(id=layer_id, storage_used_bytes=100)
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_layer
    
    # Add 50 bytes
    new_usage = await layer_manager.update_storage_used(layer_id, 50, mock_db)
    assert new_usage == 150
    assert mock_layer.storage_used_bytes == 150
    
    # Remove 200 bytes (floor at 0)
    new_usage = await layer_manager.update_storage_used(layer_id, -200, mock_db)
    assert new_usage == 0
    assert mock_layer.storage_used_bytes == 0

@pytest.mark.asyncio
async def test_cleanup_soft_deleted_layers(layer_manager, mock_db):
    # Mock return value for delete execution
    mock_result = MagicMock()
    mock_result.rowcount = 5
    mock_db.execute.return_value = mock_result
    
    deleted_count = await layer_manager.cleanup_soft_deleted_layers(mock_db, retention_days=30)
    
    assert deleted_count == 5
    mock_db.execute.assert_called()
    mock_db.commit.assert_called()
