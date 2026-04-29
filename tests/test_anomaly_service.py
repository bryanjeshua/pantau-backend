import uuid
import pytest
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


# --- helpers ---
def tx(**kw):
    d = dict(
        id=uuid.uuid4(), document_id=uuid.uuid4(),
        vendor_id=uuid.uuid4(), opd_id=uuid.uuid4(),
        category="barang", procurement_method="pengadaan_langsung",
        contract_value=None, shsr_benchmark=None,
        contract_date=None, work_start_date=None, work_end_date=None,
        spj_date=None, payment_date=None,
        item_description="Test item",
    )
    d.update(kw)
    return SimpleNamespace(**d)


def vendor(**kw):
    d = dict(id=uuid.uuid4(), name="PT Test", npwp=None, address=None, bank_account=None)
    d.update(kw)
    return SimpleNamespace(**d)


def make_db(first_result, second_result=None):
    db = AsyncMock()
    results = [first_result]
    if second_result is not None:
        results.append(second_result)

    def _result(items=None, scalar=None):
        r = MagicMock()
        s = MagicMock()
        s.all.return_value = items or []
        r.scalars.return_value = s
        r.scalar_one_or_none.return_value = scalar
        return r

    call = [0]
    async def execute_side(*a, **kw):
        idx = min(call[0], len(results) - 1)
        call[0] += 1
        return results[idx]
    db.execute.side_effect = execute_side
    db.add = MagicMock()
    return db, _result


# ═══════════════════════════════════════════
# Rule 1 — Split Contract
# ═══════════════════════════════════════════
@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_split_contract_detected(mock_exp):
    from app.services.anomaly_service import detect_split_contracts
    doc_id = uuid.uuid4()
    vid = uuid.uuid4()
    oid = uuid.uuid4()
    # 4 contracts, same vendor+category+opd, within 30 days, each < 200M, total > 200M
    txs = [
        tx(vendor_id=vid, opd_id=oid, category="barang",
           contract_date=date(2024, 3, 1), contract_value=198_000_000),
        tx(vendor_id=vid, opd_id=oid, category="barang",
           contract_date=date(2024, 3, 8), contract_value=198_000_000),
        tx(vendor_id=vid, opd_id=oid, category="barang",
           contract_date=date(2024, 3, 15), contract_value=198_000_000),
        tx(vendor_id=vid, opd_id=oid, category="barang",
           contract_date=date(2024, 3, 22), contract_value=198_000_000),
    ]
    db = AsyncMock()
    r = MagicMock(); s = MagicMock(); s.all.return_value = txs; r.scalars.return_value = s
    db.execute.return_value = r

    findings = await detect_split_contracts(doc_id, db)
    assert len(findings) == 1
    assert findings[0].finding_type == "split_contract"
    assert findings[0].risk_level == "red"


@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_split_contract_different_vendors_no_finding(mock_exp):
    from app.services.anomaly_service import detect_split_contracts
    doc_id = uuid.uuid4()
    oid = uuid.uuid4()
    txs = [
        tx(vendor_id=uuid.uuid4(), opd_id=oid, category="barang",
           contract_date=date(2024, 3, 1), contract_value=198_000_000),
        tx(vendor_id=uuid.uuid4(), opd_id=oid, category="barang",
           contract_date=date(2024, 3, 8), contract_value=198_000_000),
        tx(vendor_id=uuid.uuid4(), opd_id=oid, category="barang",
           contract_date=date(2024, 3, 15), contract_value=198_000_000),
    ]
    db = AsyncMock()
    r = MagicMock(); s = MagicMock(); s.all.return_value = txs; r.scalars.return_value = s
    db.execute.return_value = r
    findings = await detect_split_contracts(doc_id, db)
    assert len(findings) == 0


@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_split_contract_spread_over_30_days_no_finding(mock_exp):
    from app.services.anomaly_service import detect_split_contracts
    doc_id = uuid.uuid4()
    vid = uuid.uuid4(); oid = uuid.uuid4()
    txs = [
        tx(vendor_id=vid, opd_id=oid, category="barang",
           contract_date=date(2024, 1, 1), contract_value=198_000_000),
        tx(vendor_id=vid, opd_id=oid, category="barang",
           contract_date=date(2024, 3, 1), contract_value=198_000_000),
        tx(vendor_id=vid, opd_id=oid, category="barang",
           contract_date=date(2024, 5, 1), contract_value=198_000_000),
    ]
    db = AsyncMock()
    r = MagicMock(); s = MagicMock(); s.all.return_value = txs; r.scalars.return_value = s
    db.execute.return_value = r
    findings = await detect_split_contracts(doc_id, db)
    assert len(findings) == 0


# ═══════════════════════════════════════════
# Rule 2 — Price Markup
# ═══════════════════════════════════════════
@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_markup_detected(mock_exp):
    from app.services.anomaly_service import detect_markup
    doc_id = uuid.uuid4()
    txs = [tx(contract_value=850_000 * 200, shsr_benchmark=450_000 * 200)]  # 89% markup
    db = AsyncMock()
    r = MagicMock(); s = MagicMock(); s.all.return_value = txs; r.scalars.return_value = s
    db.execute.return_value = r
    findings = await detect_markup(doc_id, db)
    assert len(findings) == 1
    assert findings[0].finding_type == "markup"
    assert findings[0].risk_level == "red"


@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_markup_at_threshold_no_finding(mock_exp):
    from app.services.anomaly_service import detect_markup
    doc_id = uuid.uuid4()
    txs = [tx(contract_value=130_000_000, shsr_benchmark=100_000_000)]  # exactly 30%
    db = AsyncMock()
    r = MagicMock(); s = MagicMock(); s.all.return_value = txs; r.scalars.return_value = s
    db.execute.return_value = r
    findings = await detect_markup(doc_id, db)
    assert len(findings) == 0


@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_markup_no_benchmark_skipped(mock_exp):
    from app.services.anomaly_service import detect_markup
    doc_id = uuid.uuid4()
    txs = [tx(contract_value=500_000_000, shsr_benchmark=None)]
    db = AsyncMock()
    r = MagicMock(); s = MagicMock(); s.all.return_value = txs; r.scalars.return_value = s
    db.execute.return_value = r
    findings = await detect_markup(doc_id, db)
    assert len(findings) == 0


# ═══════════════════════════════════════════
# Rule 3 — Affiliated Vendor
# ═══════════════════════════════════════════
@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_affiliated_vendor_same_npwp_prefix(mock_exp):
    from app.services.anomaly_service import detect_affiliated_vendors
    doc_id = uuid.uuid4()
    v1 = vendor(npwp="12.345.678.9-123.000")
    v2 = vendor(npwp="12.345.678.9-124.000")
    txs = [tx(vendor_id=v1.id), tx(vendor_id=v2.id)]
    db = AsyncMock()
    def _r(items=None, scalar=None):
        r = MagicMock(); s = MagicMock()
        s.all.return_value = items or []; r.scalars.return_value = s
        r.scalar_one_or_none.return_value = scalar; return r
    db.execute.side_effect = [_r(txs), _r([v1, v2])]
    findings = await detect_affiliated_vendors(doc_id, db)
    assert len(findings) == 1
    assert findings[0].finding_type == "affiliated_vendor"


@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_affiliated_vendor_same_bank_account(mock_exp):
    from app.services.anomaly_service import detect_affiliated_vendors
    doc_id = uuid.uuid4()
    v1 = vendor(bank_account="1234567890")
    v2 = vendor(bank_account="1234567890")
    txs = [tx(vendor_id=v1.id), tx(vendor_id=v2.id)]
    db = AsyncMock()
    def _r(items=None):
        r = MagicMock(); s = MagicMock()
        s.all.return_value = items or []; r.scalars.return_value = s; return r
    db.execute.side_effect = [_r(txs), _r([v1, v2])]
    findings = await detect_affiliated_vendors(doc_id, db)
    assert len(findings) == 1


@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_affiliated_vendor_high_address_similarity(mock_exp):
    from app.services.anomaly_service import detect_affiliated_vendors
    doc_id = uuid.uuid4()
    addr = "Jl. Industri No. 45, Kel. Menteng, Kota Palangkaraya"
    v1 = vendor(address=addr)
    v2 = vendor(address=addr + " Lt.2")
    txs = [tx(vendor_id=v1.id), tx(vendor_id=v2.id)]
    db = AsyncMock()
    def _r(items=None):
        r = MagicMock(); s = MagicMock()
        s.all.return_value = items or []; r.scalars.return_value = s; return r
    db.execute.side_effect = [_r(txs), _r([v1, v2])]
    findings = await detect_affiliated_vendors(doc_id, db)
    assert len(findings) == 1


@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_affiliated_vendor_unrelated_no_finding(mock_exp):
    from app.services.anomaly_service import detect_affiliated_vendors
    doc_id = uuid.uuid4()
    v1 = vendor(npwp="12.345.678.9-001.000", address="Jl. A No.1", bank_account="111")
    v2 = vendor(npwp="99.999.999.9-999.000", address="Jl. Z No.99", bank_account="999")
    txs = [tx(vendor_id=v1.id), tx(vendor_id=v2.id)]
    db = AsyncMock()
    def _r(items=None):
        r = MagicMock(); s = MagicMock()
        s.all.return_value = items or []; r.scalars.return_value = s; return r
    db.execute.side_effect = [_r(txs), _r([v1, v2])]
    findings = await detect_affiliated_vendors(doc_id, db)
    assert len(findings) == 0


# ═══════════════════════════════════════════
# Rule 4 — Vendor Concentration
# ═══════════════════════════════════════════
@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_vendor_concentration_detected(mock_exp):
    from app.services.anomaly_service import detect_vendor_concentration
    doc_id = uuid.uuid4()
    vid = uuid.uuid4(); oid = uuid.uuid4()
    # vendor gets 40% of OPD total via penunjukan_langsung
    txs = [
        tx(vendor_id=vid, opd_id=oid, contract_value=40_000_000_000,
           procurement_method="penunjukan_langsung"),
        tx(vendor_id=uuid.uuid4(), opd_id=oid, contract_value=60_000_000_000,
           procurement_method="tender"),
    ]
    mock_vendor = vendor(id=vid, name="PT Agro Mandiri")
    db = AsyncMock()
    def _r(items=None, scalar=None):
        r = MagicMock(); s = MagicMock()
        s.all.return_value = items or []; r.scalars.return_value = s
        r.scalar_one_or_none.return_value = scalar; return r
    db.execute.side_effect = [_r(txs), _r(scalar=mock_vendor)]
    findings = await detect_vendor_concentration(doc_id, db)
    assert len(findings) == 1
    assert findings[0].finding_type == "vendor_concentration"


@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_vendor_concentration_below_threshold_no_finding(mock_exp):
    from app.services.anomaly_service import detect_vendor_concentration
    doc_id = uuid.uuid4()
    vid = uuid.uuid4(); oid = uuid.uuid4()
    txs = [
        tx(vendor_id=vid, opd_id=oid, contract_value=34_000_000_000,
           procurement_method="penunjukan_langsung"),
        tx(vendor_id=uuid.uuid4(), opd_id=oid, contract_value=66_000_000_000,
           procurement_method="tender"),
    ]
    db = AsyncMock()
    r = MagicMock(); s = MagicMock(); s.all.return_value = txs; r.scalars.return_value = s
    db.execute.return_value = r
    findings = await detect_vendor_concentration(doc_id, db)
    assert len(findings) == 0


@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_vendor_concentration_tender_method_no_finding(mock_exp):
    from app.services.anomaly_service import detect_vendor_concentration
    doc_id = uuid.uuid4()
    vid = uuid.uuid4(); oid = uuid.uuid4()
    # vendor gets 40% but via tender (not penunjukan_langsung)
    txs = [
        tx(vendor_id=vid, opd_id=oid, contract_value=40_000_000_000, procurement_method="tender"),
        tx(vendor_id=uuid.uuid4(), opd_id=oid, contract_value=60_000_000_000, procurement_method="tender"),
    ]
    db = AsyncMock()
    r = MagicMock(); s = MagicMock(); s.all.return_value = txs; r.scalars.return_value = s
    db.execute.return_value = r
    findings = await detect_vendor_concentration(doc_id, db)
    assert len(findings) == 0


# ═══════════════════════════════════════════
# Rule 5 — Timing Anomaly
# ═══════════════════════════════════════════
@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_spj_late_detected(mock_exp):
    from app.services.anomaly_service import detect_timing_anomalies
    doc_id = uuid.uuid4()
    txs = [tx(work_end_date=date(2024, 6, 30), spj_date=date(2024, 9, 15))]  # 77 days late
    db = AsyncMock()
    r = MagicMock(); s = MagicMock(); s.all.return_value = txs; r.scalars.return_value = s
    db.execute.return_value = r
    findings = await detect_timing_anomalies(doc_id, db)
    spj_findings = [f for f in findings if "SPJ" in f.title]
    assert len(spj_findings) == 1
    assert spj_findings[0].risk_level == "yellow"


@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_spj_exactly_60_days_no_finding(mock_exp):
    from app.services.anomaly_service import detect_timing_anomalies
    doc_id = uuid.uuid4()
    txs = [tx(work_end_date=date(2024, 6, 30), spj_date=date(2024, 8, 29))]  # exactly 60 days
    db = AsyncMock()
    r = MagicMock(); s = MagicMock(); s.all.return_value = txs; r.scalars.return_value = s
    db.execute.return_value = r
    findings = await detect_timing_anomalies(doc_id, db)
    spj_findings = [f for f in findings if "SPJ" in f.title]
    assert len(spj_findings) == 0


@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_premature_payment_detected(mock_exp):
    from app.services.anomaly_service import detect_timing_anomalies
    doc_id = uuid.uuid4()
    txs = [tx(work_end_date=date(2024, 11, 30), payment_date=date(2024, 9, 15))]  # 76 days early
    db = AsyncMock()
    r = MagicMock(); s = MagicMock(); s.all.return_value = txs; r.scalars.return_value = s
    db.execute.return_value = r
    findings = await detect_timing_anomalies(doc_id, db)
    pay_findings = [f for f in findings if "Pembayaran" in f.title]
    assert len(pay_findings) == 1
    assert pay_findings[0].risk_level == "red"


@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_payment_on_completion_date_no_finding(mock_exp):
    from app.services.anomaly_service import detect_timing_anomalies
    doc_id = uuid.uuid4()
    txs = [tx(work_end_date=date(2024, 11, 30), payment_date=date(2024, 11, 30))]
    db = AsyncMock()
    r = MagicMock(); s = MagicMock(); s.all.return_value = txs; r.scalars.return_value = s
    db.execute.return_value = r
    findings = await detect_timing_anomalies(doc_id, db)
    pay_findings = [f for f in findings if "Pembayaran" in f.title]
    assert len(pay_findings) == 0


@patch("app.services.anomaly_service.generate_anomaly_explanation", return_value="exp")
async def test_both_spj_late_and_premature_payment_detected(mock_exp):
    from app.services.anomaly_service import detect_timing_anomalies
    doc_id = uuid.uuid4()
    txs = [tx(
        work_end_date=date(2024, 6, 30),
        spj_date=date(2024, 9, 15),       # 77 days late
        payment_date=date(2024, 4, 1),    # 90 days premature
    )]
    db = AsyncMock()
    r = MagicMock(); s = MagicMock(); s.all.return_value = txs; r.scalars.return_value = s
    db.execute.return_value = r
    findings = await detect_timing_anomalies(doc_id, db)
    assert len(findings) == 2
