import pytest
from unittest.mock import MagicMock, patch

# Mock the encoder to avoid downloading models during tests
@pytest.fixture
def mock_encoder():
    with patch("app.services.semantic_router.HuggingFaceEncoder") as mock:
        yield mock

def test_semantic_router_routing(mock_encoder):
    from app.services.semantic_router import SemanticRouterService
    
    # Setup mock layer behavior
    with patch("app.services.semantic_router.RouteLayer") as mock_layer_cls:
        mock_layer = mock_layer_cls.return_value
        
        # Test 1: Internal Knowledge Match
        mock_layer.return_value = MagicMock(name="internal_knowledge")
        mock_layer.return_value.name = "internal_knowledge"
        
        router = SemanticRouterService()
        route, conf = router.route("What is the holiday policy?")
        
        assert route == "internal_knowledge"
        
        # Test 2: Codebase Match
        mock_layer.return_value.name = "codebase"
        route, conf = router.route("Fix bugs in main.py")
        assert route == "codebase"
        
        # Test 3: Fallback (None name)
        mock_layer.return_value.name = None
        route, conf = router.route("Random chitchat")
        assert route == "general_chat"
        
    assert True
