import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy import update

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.document import Document
from app.services.document_service import extract_and_save
from app.services.compliance_service import scan_document
from app.pipelines.anomaly_pipeline import run_anomaly_scan

logger = logging.getLogger(__name__)


async def process_document(document_id: str) -> None:
    doc_uuid = uuid.UUID(document_id)

    async with AsyncSessionLocal() as db:
        await db.execute(
            update(Document)
            .where(Document.id == doc_uuid)
            .values(status="processing")
        )
        await db.commit()

        try:
            result = await db.execute(select(Document).where(Document.id == doc_uuid))
            doc = result.scalar_one()

            item_count = await extract_and_save(doc_uuid, db)
            await scan_document(doc_uuid, db)

            if doc.document_type == "procurement":
                await run_anomaly_scan(document_id)

            await db.execute(
                update(Document)
                .where(Document.id == doc_uuid)
                .values(
                    status="complete",
                    item_count=item_count,
                    processed_at=datetime.now(timezone.utc),
                )
            )
            await db.commit()
            logger.info("document %s processed: %d items", document_id, item_count)

        except Exception as exc:
            logger.exception("document %s failed: %s", document_id, exc)
            await db.execute(
                update(Document)
                .where(Document.id == doc_uuid)
                .values(status="error", error_message=str(exc)[:500])
            )
            await db.commit()
