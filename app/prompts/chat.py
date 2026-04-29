CHAT_SYSTEM = """Kamu adalah AI Budget Compliance Assistant untuk pejabat keuangan pemerintah daerah Indonesia.
Jawab HANYA berdasarkan regulasi yang diberikan dalam konteks.
JANGAN mengutip pasal yang tidak ada dalam teks yang diberikan.
Gunakan Bahasa Indonesia yang jelas, formal, dan mudah dipahami."""

CHAT_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
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
    "required": ["answer", "regulation_refs"],
}


def get_chat_prompt(question: str, regulation_chunks: list[dict]) -> str:
    chunks_text = "\n\n".join(
        f"[{c['peraturan_number']} - {c['pasal']}]\n{c['content']}"
        for c in regulation_chunks
    )
    return f"""Pertanyaan: {question}

Regulasi yang relevan:
{chunks_text or "Tidak ada regulasi relevan ditemukan dalam knowledge base."}

Jawab berdasarkan regulasi di atas. Kutip HANYA pasal yang tercantum."""
