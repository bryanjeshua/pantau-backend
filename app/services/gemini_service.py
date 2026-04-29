import json
import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

_MODEL_NAME = "gemini-2.5-flash-lite"
flash = genai.GenerativeModel(_MODEL_NAME)


def embed_text(text: str, task_type: str = "retrieval_document") -> list[float]:
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type=task_type,
        output_dimensionality=768,
    )
    return result["embedding"]


def extract_document(file_content: bytes | str, mime_type: str, document_type: str) -> dict:
    from app.prompts.extraction import get_extraction_prompt, get_extraction_schema

    prompt = get_extraction_prompt(document_type)
    schema = get_extraction_schema(document_type)

    if isinstance(file_content, str):
        content_parts = [prompt, file_content]
    else:
        content_parts = [prompt, {"mime_type": mime_type, "data": file_content}]

    response = flash.generate_content(
        content_parts,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    return json.loads(response.text)


def classify_risk(item_text: str, regulation_chunks: list[dict]) -> dict:
    from app.prompts.compliance import COMPLIANCE_SYSTEM, get_classify_prompt, CLASSIFY_SCHEMA

    model = genai.GenerativeModel(_MODEL_NAME, system_instruction=COMPLIANCE_SYSTEM)
    response = model.generate_content(
        get_classify_prompt(item_text, regulation_chunks),
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=CLASSIFY_SCHEMA,
        ),
    )
    return json.loads(response.text)


def generate_chat_response(question: str, regulation_chunks: list[dict]) -> dict:
    from app.prompts.chat import CHAT_SYSTEM, get_chat_prompt, CHAT_SCHEMA

    model = genai.GenerativeModel(_MODEL_NAME, system_instruction=CHAT_SYSTEM)
    response = model.generate_content(
        get_chat_prompt(question, regulation_chunks),
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=CHAT_SCHEMA,
        ),
    )
    return json.loads(response.text)


def generate_anomaly_explanation(anomaly_type: str, evidence: dict) -> str:
    from app.prompts.anomaly_explain import get_anomaly_prompt

    response = flash.generate_content(get_anomaly_prompt(anomaly_type, evidence))
    return response.text
