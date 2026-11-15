from google import genai

from app.core.config import get_settings

settings = get_settings()
if not settings.gemini_api_key:
    raise SystemExit("GEMINI_API_KEY is empty in backend/.env")

client = genai.Client(api_key=settings.gemini_api_key)
response = client.models.generate_content(
    model=settings.gemini_model,
    contents="Reply with exactly: Caraxes is online",
)
print(response.text)