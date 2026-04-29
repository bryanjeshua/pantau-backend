"""
Integration tests — hit real Gemini + Supabase APIs.

Run with:
    py -m pytest -m integration -v

Skipped automatically during normal `py -m pytest` runs.
Each test cleans up any data it creates.
"""
import os
import time
import uuid
import pytest

# Skip entire module if credentials are missing
pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="module")]

REQUIRED_VARS = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "GEMINI_API_KEY", "DATABASE_URL"]


def _missing_vars():
    from app.core.config import settings
    missing = []
    for v in REQUIRED_VARS:
        val = getattr(settings, v, None)
        if not val or val.startswith("https://xxxx") or val.startswith("AIzaSy..."):
            missing.append(v)
    return missing


# ─── Supabase Connection ──────────────────────────────────────

def _ensure_bucket(supabase_client, bucket_name: str):
    """Create bucket if it doesn't exist (idempotent)."""
    try:
        supabase_client.storage.create_bucket(bucket_name, options={"public": False})
    except Exception:
        pass  # already exists


def test_supabase_storage_upload_and_delete():
    """Verify Supabase Storage is reachable and credentials are valid."""
    missing = _missing_vars()
    if missing:
        pytest.skip(f"Missing env vars: {missing}")

    from app.core.database import supabase

    _ensure_bucket(supabase, "documents")

    test_path = f"integration-test/{uuid.uuid4()}.txt"
    content = b"pantau integration test"

    # Upload
    result = supabase.storage.from_("documents").upload(
        path=test_path,
        file=content,
        file_options={"content-type": "text/plain"},
    )
    assert result is not None, "Upload returned None"

    # Download and verify
    downloaded = supabase.storage.from_("documents").download(test_path)
    assert downloaded == content, "Downloaded content does not match uploaded content"

    # Cleanup
    supabase.storage.from_("documents").remove([test_path])


def test_supabase_storage_signed_url():
    """Verify signed URL generation works."""
    missing = _missing_vars()
    if missing:
        pytest.skip(f"Missing env vars: {missing}")

    from app.core.database import supabase

    _ensure_bucket(supabase, "memos")

    test_path = f"integration-test/{uuid.uuid4()}.txt"
    supabase.storage.from_("memos").upload(
        path=test_path, file=b"test memo",
        file_options={"content-type": "text/plain"},
    )

    signed = supabase.storage.from_("memos").create_signed_url(test_path, expires_in=60)
    url = signed.get("signedURL") or signed.get("signedUrl")
    assert url and url.startswith("https://"), f"Expected HTTPS signed URL, got: {url}"

    # Cleanup
    supabase.storage.from_("memos").remove([test_path])


# ─── Database Connection ──────────────────────────────────────

async def test_database_connection():
    """Verify async DB connection and basic query."""
    missing = _missing_vars()
    if missing:
        pytest.skip(f"Missing env vars: {missing}")

    from sqlalchemy import text
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(text("SELECT 1 AS ok"))
        row = result.fetchone()
        assert row.ok == 1


async def test_database_tables_exist():
    """Verify all required tables exist in the schema."""
    missing = _missing_vars()
    if missing:
        pytest.skip(f"Missing env vars: {missing}")

    from sqlalchemy import text
    from app.core.database import AsyncSessionLocal

    required_tables = [
        "documents", "budget_items", "procurement_transactions",
        "findings", "vendors", "opd_units", "audit_memos",
        "regulations", "regulation_chunks", "chat_sessions", "chat_messages",
    ]

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public'"
            )
        )
        existing = {row.tablename for row in result.fetchall()}

    missing_tables = [t for t in required_tables if t not in existing]
    assert not missing_tables, f"Missing tables in DB: {missing_tables}"


# ─── Gemini API ───────────────────────────────────────────────

def test_gemini_embedding():
    """Verify Gemini text-embedding-004 returns a 768-dim vector."""
    missing = _missing_vars()
    if missing:
        pytest.skip(f"Missing env vars: {missing}")

    from app.services.gemini_service import embed_text

    embedding = embed_text("Batas uang muka pengadaan barang jasa pemerintah")
    assert isinstance(embedding, list), "Embedding should be a list"
    assert len(embedding) == 768, f"Expected 768 dims, got {len(embedding)}"
    assert all(isinstance(x, float) for x in embedding), "All values should be float"


def test_gemini_chat_response():
    """Verify Gemini generates a valid structured chat response."""
    missing = _missing_vars()
    if missing:
        pytest.skip(f"Missing env vars: {missing}")
    time.sleep(5)  # avoid Gemini free-tier rate limit (15 RPM)

    from app.services.gemini_service import generate_chat_response

    # Provide a dummy regulation chunk so Gemini has context
    chunks = [{
        "peraturan_number": "Perpres 12/2021",
        "pasal": "Pasal 38",
        "content": "Pemilihan penyedia barang/jasa dilakukan melalui tender "
                   "apabila nilai pengadaan di atas Rp 200.000.000.",
        "similarity": 0.9,
    }]

    result = generate_chat_response(
        "Kapan pengadaan harus menggunakan tender?", chunks
    )

    assert "answer" in result, "Response must have 'answer' key"
    assert isinstance(result["answer"], str), "Answer must be a string"
    assert len(result["answer"]) > 10, "Answer seems too short"
    assert "regulation_refs" in result, "Response must have 'regulation_refs'"


def test_gemini_extraction_from_text():
    """Verify Gemini can extract budget items from a simple text document."""
    missing = _missing_vars()
    if missing:
        pytest.skip(f"Missing env vars: {missing}")
    time.sleep(5)  # avoid Gemini free-tier rate limit (15 RPM)

    from app.services.gemini_service import extract_document

    # Minimal APBD-like text content
    sample_text = """
    APBD Kabupaten Nusantara Jaya Tahun 2024
    
    5.1.01 Belanja Pegawai           Rp 10.000.000.000
    5.2.01 Belanja Barang dan Jasa   Rp  5.000.000.000
    5.2.02 Belanja Modal             Rp  2.500.000.000
    """

    result = extract_document(sample_text, "text/plain", "apbd")
    assert "items" in result, "Extraction must return 'items'"
    assert isinstance(result["items"], list), "'items' must be a list"
    assert len(result["items"]) > 0, "No items extracted from sample document"

    first = result["items"][0]
    assert "item_name" in first, "Each item must have 'item_name'"


# ─── Full Stack: Upload → Extract → Find ─────────────────────

async def test_full_document_pipeline_with_real_apis():
    """
    End-to-end: upload a text document → Gemini extracts items →
    compliance scan runs → findings saved to DB.

    This test creates real records and cleans them up after.
    """
    missing = _missing_vars()
    if missing:
        pytest.skip(f"Missing env vars: {missing}")
    time.sleep(5)  # avoid Gemini free-tier rate limit (15 RPM)

    # Skip if regulation_chunks is empty (RAG won't work without seeded data)
    from sqlalchemy import text
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        r = await db.execute(text("SELECT COUNT(*) FROM regulation_chunks"))
        count = r.scalar()
        if count == 0:
            pytest.skip("regulation_chunks table is empty — seed regulations first")

    from app.core.database import supabase, AsyncSessionLocal
    from app.services.document_service import extract_and_save
    from app.services.compliance_service import scan_document
    from app.models.document import Document
    from sqlalchemy import select, delete

    _ensure_bucket(supabase, "documents")

    sample_content = (
        "APBD Kabupaten Test 2024\n"
        "5.2.01 Pengadaan Alat Tulis Kantor via penunjukan langsung Rp 250.000.000\n"
    )

    doc_id = None
    storage_path = None

    try:
        async with AsyncSessionLocal() as db:
            doc = Document(
                filename="integration_test.txt",
                document_type="apbd",
                fiscal_year=2024,
                status="pending",
            )
            db.add(doc)
            await db.flush()
            doc_id = doc.id

            storage_path = f"{doc_id}/integration_test.txt"
            supabase.storage.from_("documents").upload(
                path=storage_path,
                file=sample_content.encode(),
                file_options={"content-type": "text/plain"},
            )
            doc.storage_path = storage_path
            await db.commit()

            item_count = await extract_and_save(doc_id, db)
            assert item_count >= 0, "extract_and_save should return a non-negative count"

            finding_count = await scan_document(doc_id, db)
            assert finding_count >= 0

    finally:
        # Always clean up
        if doc_id:
            async with AsyncSessionLocal() as db:
                await db.execute(delete(Document).where(Document.id == doc_id))
                await db.commit()
        if storage_path:
            try:
                supabase.storage.from_("documents").remove([storage_path])
            except Exception:
                pass
