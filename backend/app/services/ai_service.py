import json
import re

from groq import Groq

from app.config import settings

_client: Groq | None = None


def _get_client() -> Groq | None:
    global _client
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("your-"):
        return None
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


def _parse_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)


def categorize_ticket(title: str, description: str) -> dict:
    system_prompt = """You are a customer support ticket categorization system.
Analyze the ticket and respond with ONLY a valid JSON object, no explanation.
Response format: {"category": "CATEGORY_NAME", "confidence": 0.95}
Valid categories: Billing, Technical, Account, Shipping, General, Bug_Report, Feature_Request, Complaint
Choose the most appropriate single category."""

    try:
        client = _get_client()
        if not client:
            return {"category": "General", "confidence": 0.0, "error": "API key not configured"}

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Title: {title}\nDescription: {description}"},
            ],
            temperature=0.1,
            max_tokens=150,
        )
        content = response.choices[0].message.content or "{}"
        data = _parse_json(content)
        return {
            "category": data.get("category", "General"),
            "confidence": float(data.get("confidence", 0.0)),
        }
    except Exception as e:
        return {"category": "General", "confidence": 0.0, "error": str(e)}


def analyze_sentiment(text: str) -> dict:
    system_prompt = """You are a sentiment analysis system for customer support tickets.
Analyze the sentiment and respond with ONLY a valid JSON object, no explanation.
Response format: {"sentiment": "SENTIMENT", "score": 0.85, "reasoning": "brief reason"}
Valid sentiments: positive, neutral, negative, frustrated
Use "frustrated" when customer shows anger, urgency, or desperation.
Score is confidence from 0.0 to 1.0."""

    try:
        client = _get_client()
        if not client:
            return {"sentiment": "neutral", "score": 0.0, "error": "API key not configured"}

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.1,
            max_tokens=150,
        )
        content = response.choices[0].message.content or "{}"
        data = _parse_json(content)
        return {
            "sentiment": data.get("sentiment", "neutral"),
            "score": float(data.get("score", 0.0)),
            "reasoning": data.get("reasoning", ""),
        }
    except Exception as e:
        return {"sentiment": "neutral", "score": 0.0, "error": str(e)}


def generate_ticket_summary(
    ticket_title: str, ticket_description: str, comments: list[str]
) -> str:
    system_prompt = """You are a support ticket summarization assistant.
Create a concise 2-3 sentence summary of the support ticket and its resolution.
Focus on: what the problem was, how it was resolved, and any key actions taken.
Be factual and professional."""

    user_message = (
        f"Ticket: {ticket_title}\nDescription: {ticket_description}\nConversation:\n"
        + "\n".join(comments)
    )

    try:
        client = _get_client()
        if not client:
            return "Summary not available."

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        return response.choices[0].message.content or "Summary not available."
    except Exception:
        return "Summary not available."
