def get_anomaly_prompt(anomaly_type: str, evidence: dict) -> str:
    evidence_text = "\n".join(f"- {k}: {v}" for k, v in evidence.items())
    return f"""Kamu adalah auditor pengadaan pemerintah daerah Indonesia.
Jelaskan anomali berikut dalam 2-3 kalimat Bahasa Indonesia yang padat.
Fokus pada MENGAPA ini mencurigakan dan APA yang perlu diperiksa.

Jenis anomali: {anomaly_type}
Data:
{evidence_text}"""
