import uuid
import logging

from app.core.database import AsyncSessionLocal
from app.services.anomaly_service import (
    detect_affiliated_vendors,
    detect_markup,
    detect_split_contracts,
    detect_timing_anomalies,
    detect_vendor_concentration,
)

logger = logging.getLogger(__name__)


async def run_anomaly_scan(document_id: str) -> None:
    doc_uuid = uuid.UUID(document_id)

    async with AsyncSessionLocal() as db:
        try:
            findings = []
            findings += await detect_split_contracts(doc_uuid, db)
            findings += await detect_markup(doc_uuid, db)
            findings += await detect_affiliated_vendors(doc_uuid, db)
            findings += await detect_vendor_concentration(doc_uuid, db)
            findings += await detect_timing_anomalies(doc_uuid, db)

            for f in findings:
                db.add(f)
            await db.commit()

            logger.info("anomaly scan %s: %d findings", document_id, len(findings))

        except Exception as exc:
            logger.exception("anomaly scan %s failed: %s", document_id, exc)
