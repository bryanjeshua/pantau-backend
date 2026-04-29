import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

TEST_USER_ID = str(uuid.uuid4())


def make_document(**kw):
    d = dict(
        id=uuid.uuid4(), filename="apbd_2024.pdf", document_type="apbd",
        fiscal_year=2024, status="complete", storage_path="x/apbd_2024.pdf",
        page_count=10, item_count=5,
        uploaded_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        processed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        error_message=None,
    )
    d.update(kw)
    return SimpleNamespace(**d)


def make_budget_item(**kw):
    d = dict(
        id=uuid.uuid4(), document_id=uuid.uuid4(),
        item_code="1.02.01.001", item_name="Belanja Obat",
        budget_amount=50_000_000.0, realized_amount=45_000_000.0,
        item_type="belanja", sub_type="barang_jasa",
    )
    d.update(kw)
    return SimpleNamespace(**d)


def make_tx_response(**kw):
    d = dict(
        id=uuid.uuid4(), document_id=uuid.uuid4(),
        vendor_id=uuid.uuid4(), contract_number="KTR-001",
        item_description="Pengadaan ATK", category="barang",
        procurement_method="pengadaan_langsung", contract_value=150_000_000.0,
    )
    d.update(kw)
    return SimpleNamespace(**d)


def make_finding(**kw):
    d = dict(
        id=uuid.uuid4(), document_id=uuid.uuid4(), opd_id=uuid.uuid4(),
        budget_item_id=uuid.uuid4(), transaction_id=None,
        source="compliance_scan", finding_type="regulation_violation",
        risk_level="red", title="Potensi Pelanggaran Regulasi",
        description="Item belanja berpotensi melanggar regulasi",
        regulation_refs=[{"peraturan": "Perpres 12/2021", "pasal": "Pasal 38", "isi": "isi"}],
        evidence=None, ai_explanation="Penjelasan AI",
        confidence_score=0.85, status="pending",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        confirmed_at=None,
    )
    d.update(kw)
    return SimpleNamespace(**d)


def make_opd(**kw):
    d = dict(
        id=uuid.uuid4(), opd_code="1.02.01", name="Dinas Kesehatan",
        kabupaten="Kabupaten Nusantara Jaya",
        total_budget=120_000_000_000.0, fiscal_year=2024,
    )
    d.update(kw)
    return SimpleNamespace(**d)


def make_session(**kw):
    d = dict(
        id=uuid.uuid4(), title="Sesi Konsultasi",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    d.update(kw)
    return SimpleNamespace(**d)


def make_message(**kw):
    d = dict(
        id=uuid.uuid4(), session_id=uuid.uuid4(),
        role="assistant", content="Berdasarkan regulasi...",
        regulation_refs=[{"peraturan": "Perpres 12/2021", "pasal": "Pasal 38", "isi": "isi"}],
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    d.update(kw)
    return SimpleNamespace(**d)


def make_memo(**kw):
    d = dict(
        id=uuid.uuid4(), opd_id=uuid.uuid4(), fiscal_year=2024,
        finding_ids=[], format="docx",
        memo_number="PANTAU/2024/01010101",
        storage_path="memo/test.docx",
        generated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    d.update(kw)
    return SimpleNamespace(**d)


def db_result(items=None, scalar=None):
    r = MagicMock()
    s = MagicMock()
    s.all.return_value = items if items is not None else []
    r.scalars.return_value = s
    r.scalar_one_or_none.return_value = scalar
    return r
