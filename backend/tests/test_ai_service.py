from unittest.mock import MagicMock, patch

from app.services import ai_service


def test_categorize_ticket_success():
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"category": "Billing", "confidence": 0.95}'))
    ]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch.object(ai_service, "_get_client", return_value=mock_client):
        result = ai_service.categorize_ticket("Double charge", "I was charged twice")
    assert result["category"] == "Billing"
    assert result["confidence"] == 0.95


def test_categorize_ticket_api_error():
    with patch.object(ai_service, "_get_client", side_effect=Exception("API down")):
        result = ai_service.categorize_ticket("title", "desc")
    assert result["category"] == "General"


def test_analyze_sentiment_success():
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='{"sentiment": "frustrated", "score": 0.9, "reasoning": "angry"}'
            )
        )
    ]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch.object(ai_service, "_get_client", return_value=mock_client):
        result = ai_service.analyze_sentiment("No one is helping me!!!")
    assert result["sentiment"] == "frustrated"


def test_analyze_sentiment_fallback():
    with patch.object(ai_service, "_get_client", return_value=None):
        result = ai_service.analyze_sentiment("hello")
    assert result["sentiment"] == "neutral"
