COMPLIANCE_SYSTEM = """Kamu adalah auditor keuangan daerah Indonesia yang berpengalaman.

ATURAN WAJIB:
1. Evaluasi HANYA berdasarkan regulasi yang diberikan dalam konteks
2. JANGAN mengutip pasal yang tidak ada dalam teks regulasi yang diberikan
3. Jika tidak ada regulasi relevan, klasifikasikan sebagai green
4. Gunakan Bahasa Indonesia yang jelas dan formal"""

CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "risk_level": {"type": "string", "enum": ["red", "yellow", "green"]},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "ai_explanation": {"type": "string"},
        "confidence_score": {"type": "number"},
        "regulation_refs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "peraturan": {"type": "string"},
                    "pasal": {"type": "string"},
                    "isi": {"type": "string"},
                },
                "required": ["peraturan", "pasal", "isi"],
            },
        },
    },
    "required": ["risk_level", "title", "description", "ai_explanation", "confidence_score", "regulation_refs"],
}


def get_classify_prompt(item_text: str, regulation_chunks: list[dict]) -> str:
    chunks_text = "\n\n".join(
        f"[{c['peraturan_number']} - {c['pasal']}]\n{c['content']}"
        for c in regulation_chunks
    )
    return f"""Evaluasi item anggaran berikut terhadap regulasi yang diberikan:

ITEM ANGGARAN:
{item_text}

REGULASI YANG RELEVAN:
{chunks_text or "Tidak ada regulasi relevan ditemukan."}

Berikan klasifikasi risiko. Kutip HANYA pasal yang tercantum di atas."""
