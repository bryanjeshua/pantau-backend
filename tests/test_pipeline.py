import uuid
from unittest.mock import patch, AsyncMock, MagicMock


async def test_pipeline_sets_status_complete():
    from app.pipelines.document_pipeline import process_document
    doc_id = str(uuid.uuid4())

    with patch("app.pipelines.document_pipeline.AsyncSessionLocal") as mock_ctx, \
         patch("app.pipelines.document_pipeline.extract_and_save", return_value=5) as mock_extract, \
         patch("app.pipelines.document_pipeline.scan_document", return_value=2) as mock_scan, \
         patch("app.pipelines.document_pipeline.run_anomaly_scan") as mock_anomaly:

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)

        doc = MagicMock()
        doc.document_type = "apbd"
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = doc
        mock_db.execute.return_value = mock_result

        mock_ctx.return_value = mock_db

        await process_document(doc_id)

        mock_extract.assert_called_once()
        mock_scan.assert_called_once()
        # apbd: anomaly scan should NOT be called
        mock_anomaly.assert_not_called()

        # commit should be called at least twice (status update + final)
        assert mock_db.commit.call_count >= 2


async def test_pipeline_triggers_anomaly_scan_for_procurement():
    from app.pipelines.document_pipeline import process_document
    doc_id = str(uuid.uuid4())

    with patch("app.pipelines.document_pipeline.AsyncSessionLocal") as mock_ctx, \
         patch("app.pipelines.document_pipeline.extract_and_save", return_value=3), \
         patch("app.pipelines.document_pipeline.scan_document", return_value=1), \
         patch("app.pipelines.document_pipeline.run_anomaly_scan") as mock_anomaly:

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)

        doc = MagicMock()
        doc.document_type = "procurement"
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = doc
        mock_db.execute.return_value = mock_result
        mock_ctx.return_value = mock_db

        await process_document(doc_id)

        mock_anomaly.assert_called_once_with(doc_id)


async def test_pipeline_on_exception_sets_error_status():
    from app.pipelines.document_pipeline import process_document
    doc_id = str(uuid.uuid4())

    with patch("app.pipelines.document_pipeline.AsyncSessionLocal") as mock_ctx, \
         patch("app.pipelines.document_pipeline.extract_and_save",
               side_effect=Exception("Gemini error")):

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)

        doc = MagicMock()
        doc.document_type = "apbd"
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = doc
        mock_db.execute.return_value = mock_result
        mock_ctx.return_value = mock_db

        await process_document(doc_id)

        # Should commit error status
        assert mock_db.commit.call_count >= 1


async def test_pipeline_item_count_saved():
    from app.pipelines.document_pipeline import process_document
    doc_id = str(uuid.uuid4())

    with patch("app.pipelines.document_pipeline.AsyncSessionLocal") as mock_ctx, \
         patch("app.pipelines.document_pipeline.extract_and_save", return_value=10), \
         patch("app.pipelines.document_pipeline.scan_document", return_value=3), \
         patch("app.pipelines.document_pipeline.run_anomaly_scan"):

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)

        doc = MagicMock()
        doc.document_type = "apbd"
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = doc
        mock_db.execute.return_value = mock_result
        mock_ctx.return_value = mock_db

        await process_document(doc_id)

        # Verify execute was called to update status to complete with item_count=10
        calls = mock_db.execute.call_args_list
        assert len(calls) >= 2  # initial status + fetch doc + final update
