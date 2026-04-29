import uuid
from collections import defaultdict
from difflib import SequenceMatcher
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.transaction import ProcurementTransaction
from app.models.vendor import Vendor
from app.models.finding import Finding
from app.services.gemini_service import generate_anomaly_explanation

THRESHOLD_BARANG_JASA = 200_000_000
THRESHOLD_KONSTRUKSI = 300_000_000
VENDOR_CONCENTRATION_THRESHOLD = 0.35
SPJ_LATE_DAYS = 60
MARKUP_THRESHOLD = 1.3


async def detect_split_contracts(document_id: uuid.UUID, db: AsyncSession) -> list[Finding]:
    result = await db.execute(
        select(ProcurementTransaction).where(
            ProcurementTransaction.document_id == document_id,
            ProcurementTransaction.vendor_id.is_not(None),
            ProcurementTransaction.contract_date.is_not(None),
        )
    )
    transactions = result.scalars().all()

    groups: dict[tuple, list] = defaultdict(list)
    for tx in transactions:
        key = (str(tx.vendor_id), tx.category or "", str(tx.opd_id) if tx.opd_id else "")
        groups[key].append(tx)

    findings = []
    seen_groups: set[tuple] = set()

    for key, txs in groups.items():
        if key in seen_groups or len(txs) < 3:
            continue
        txs.sort(key=lambda t: t.contract_date)
        for i in range(len(txs)):
            window = [txs[i]]
            for j in range(i + 1, len(txs)):
                if (txs[j].contract_date - txs[i].contract_date).days <= 30:
                    window.append(txs[j])
                else:
                    break
            if len(window) < 3:
                continue
            threshold = THRESHOLD_KONSTRUKSI if key[1] == "konstruksi" else THRESHOLD_BARANG_JASA
            below = [t for t in window if t.contract_value and t.contract_value < threshold]
            if len(below) < 3:
                continue
            total = sum(t.contract_value for t in below)
            if total <= threshold:
                continue

            seen_groups.add(key)
            evidence = {
                "jumlah_kontrak": len(below),
                "total_nilai": total,
                "threshold": threshold,
                "rentang_tanggal": f"{below[0].contract_date} s/d {below[-1].contract_date}",
            }
            explanation = generate_anomaly_explanation("split_contract", evidence)
            findings.append(Finding(
                document_id=document_id,
                opd_id=below[0].opd_id,
                transaction_id=below[0].id,
                source="procurement_anomaly",
                finding_type="split_contract",
                risk_level="red",
                title="Indikasi Pemecahan Kontrak",
                description=(
                    f"{len(below)} kontrak dari vendor yang sama dalam 30 hari, "
                    f"total Rp{total:,.0f} (threshold Rp{threshold:,.0f})"
                ),
                evidence=evidence,
                ai_explanation=explanation,
                confidence_score=0.85,
            ))
            break

    return findings


async def detect_markup(document_id: uuid.UUID, db: AsyncSession) -> list[Finding]:
    result = await db.execute(
        select(ProcurementTransaction).where(
            ProcurementTransaction.document_id == document_id,
            ProcurementTransaction.contract_value.is_not(None),
            ProcurementTransaction.shsr_benchmark.is_not(None),
        )
    )
    transactions = result.scalars().all()

    findings = []
    for tx in transactions:
        if not tx.shsr_benchmark or float(tx.shsr_benchmark) <= 0:
            continue
        ratio = float(tx.contract_value) / float(tx.shsr_benchmark)
        if ratio > MARKUP_THRESHOLD:
            markup_pct = (ratio - 1) * 100
            evidence = {
                "item": tx.item_description,
                "nilai_kontrak": float(tx.contract_value),
                "shsr_benchmark": float(tx.shsr_benchmark),
                "markup_persen": f"{markup_pct:.1f}%",
            }
            explanation = generate_anomaly_explanation("price_markup", evidence)
            findings.append(Finding(
                document_id=document_id,
                opd_id=tx.opd_id,
                transaction_id=tx.id,
                source="procurement_anomaly",
                finding_type="markup",
                risk_level="red",
                title="Indikasi Markup Harga",
                description=f"Harga kontrak {markup_pct:.1f}% di atas SHSR untuk: {tx.item_description}",
                evidence=evidence,
                ai_explanation=explanation,
                confidence_score=0.9,
            ))

    return findings


async def detect_affiliated_vendors(document_id: uuid.UUID, db: AsyncSession) -> list[Finding]:
    result = await db.execute(
        select(ProcurementTransaction).where(
            ProcurementTransaction.document_id == document_id,
            ProcurementTransaction.vendor_id.is_not(None),
        )
    )
    transactions = result.scalars().all()

    vendor_ids = list({tx.vendor_id for tx in transactions if tx.vendor_id})
    if len(vendor_ids) < 2:
        return []

    vendor_result = await db.execute(select(Vendor).where(Vendor.id.in_(vendor_ids)))
    vendors = vendor_result.scalars().all()

    findings = []
    flagged_pairs: set[tuple] = set()

    for i, v1 in enumerate(vendors):
        for v2 in vendors[i + 1:]:
            pair = tuple(sorted([str(v1.id), str(v2.id)]))
            if pair in flagged_pairs:
                continue

            reason = None
            if v1.npwp and v2.npwp:
                p1 = v1.npwp.replace(".", "").replace("-", "")[:9]
                p2 = v2.npwp.replace(".", "").replace("-", "")[:9]
                if len(p1) == 9 and p1 == p2:
                    reason = f"Prefiks NPWP sama: {p1}"

            if not reason and v1.bank_account and v2.bank_account:
                if v1.bank_account == v2.bank_account:
                    reason = f"Nomor rekening bank sama: {v1.bank_account}"

            if not reason and v1.address and v2.address:
                sim = SequenceMatcher(None, v1.address.lower(), v2.address.lower()).ratio()
                if sim > 0.85:
                    reason = f"Alamat sangat mirip (similarity: {sim:.2f})"

            if reason:
                flagged_pairs.add(pair)
                evidence = {"vendor_1": v1.name, "vendor_2": v2.name, "alasan": reason}
                explanation = generate_anomaly_explanation("affiliated_vendor", evidence)
                tx_ref = next((t for t in transactions if t.vendor_id == v1.id), transactions[0])
                findings.append(Finding(
                    document_id=document_id,
                    opd_id=tx_ref.opd_id,
                    transaction_id=tx_ref.id,
                    source="procurement_anomaly",
                    finding_type="affiliated_vendor",
                    risk_level="red",
                    title="Indikasi Vendor Terafiliasi",
                    description=f"{v1.name} dan {v2.name} terindikasi terafiliasi. {reason}",
                    evidence=evidence,
                    ai_explanation=explanation,
                    confidence_score=0.8,
                ))

    return findings


async def detect_vendor_concentration(document_id: uuid.UUID, db: AsyncSession) -> list[Finding]:
    result = await db.execute(
        select(ProcurementTransaction).where(
            ProcurementTransaction.document_id == document_id,
            ProcurementTransaction.vendor_id.is_not(None),
            ProcurementTransaction.contract_value.is_not(None),
            ProcurementTransaction.opd_id.is_not(None),
        )
    )
    transactions = result.scalars().all()
    if not transactions:
        return []

    opd_txs: dict[str, list] = defaultdict(list)
    for tx in transactions:
        opd_txs[str(tx.opd_id)].append(tx)

    findings = []
    for opd_id_str, txs in opd_txs.items():
        total_opd = sum(float(t.contract_value) for t in txs if t.contract_value)
        if total_opd <= 0:
            continue

        vendor_totals: dict[str, float] = defaultdict(float)
        vendor_methods: dict[str, set] = defaultdict(set)
        for tx in txs:
            vid = str(tx.vendor_id)
            vendor_totals[vid] += float(tx.contract_value)
            if tx.procurement_method:
                vendor_methods[vid].add(tx.procurement_method)

        for vid, vendor_total in vendor_totals.items():
            pct = vendor_total / total_opd
            if pct > VENDOR_CONCENTRATION_THRESHOLD and "penunjukan_langsung" in vendor_methods[vid]:
                vr = await db.execute(select(Vendor).where(Vendor.id == uuid.UUID(vid)))
                vendor = vr.scalar_one_or_none()
                vendor_name = vendor.name if vendor else vid

                evidence = {
                    "vendor": vendor_name,
                    "nilai_vendor": vendor_total,
                    "total_opd": total_opd,
                    "persentase": f"{pct * 100:.1f}%",
                }
                explanation = generate_anomaly_explanation("vendor_concentration", evidence)
                tx_ref = next(t for t in txs if str(t.vendor_id) == vid)
                findings.append(Finding(
                    document_id=document_id,
                    opd_id=tx_ref.opd_id,
                    transaction_id=tx_ref.id,
                    source="procurement_anomaly",
                    finding_type="vendor_concentration",
                    risk_level="yellow",
                    title="Indikasi Konsentrasi Vendor",
                    description=(
                        f"{vendor_name} menerima {pct * 100:.1f}% dari total pengadaan OPD "
                        f"melalui penunjukan langsung"
                    ),
                    evidence=evidence,
                    ai_explanation=explanation,
                    confidence_score=0.75,
                ))

    return findings


async def detect_timing_anomalies(document_id: uuid.UUID, db: AsyncSession) -> list[Finding]:
    result = await db.execute(
        select(ProcurementTransaction).where(
            ProcurementTransaction.document_id == document_id,
        )
    )
    transactions = result.scalars().all()

    findings = []
    for tx in transactions:
        if tx.spj_date and tx.work_end_date:
            late_days = (tx.spj_date - tx.work_end_date).days
            if late_days > SPJ_LATE_DAYS:
                evidence = {
                    "item": tx.item_description,
                    "tanggal_selesai": str(tx.work_end_date),
                    "tanggal_spj": str(tx.spj_date),
                    "keterlambatan_hari": late_days,
                }
                explanation = generate_anomaly_explanation("spj_late", evidence)
                findings.append(Finding(
                    document_id=document_id,
                    opd_id=tx.opd_id,
                    transaction_id=tx.id,
                    source="procurement_anomaly",
                    finding_type="timing_anomaly",
                    risk_level="yellow",
                    title="SPJ Terlambat",
                    description=f"SPJ diajukan {late_days} hari setelah pekerjaan selesai (batas: {SPJ_LATE_DAYS} hari)",
                    evidence=evidence,
                    ai_explanation=explanation,
                    confidence_score=0.95,
                ))

        if tx.payment_date and tx.work_end_date and tx.payment_date < tx.work_end_date:
            premature_days = (tx.work_end_date - tx.payment_date).days
            evidence = {
                "item": tx.item_description,
                "tanggal_bayar": str(tx.payment_date),
                "tanggal_selesai": str(tx.work_end_date),
                "selisih_hari": premature_days,
                "nilai_kontrak": float(tx.contract_value) if tx.contract_value else None,
            }
            explanation = generate_anomaly_explanation("premature_payment", evidence)
            findings.append(Finding(
                document_id=document_id,
                opd_id=tx.opd_id,
                transaction_id=tx.id,
                source="procurement_anomaly",
                finding_type="timing_anomaly",
                risk_level="red",
                title="Pembayaran Sebelum Pekerjaan Selesai",
                description=f"Pembayaran dilakukan {premature_days} hari sebelum pekerjaan selesai",
                evidence=evidence,
                ai_explanation=explanation,
                confidence_score=0.95,
            ))

    return findings
