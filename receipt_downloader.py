import os
import base64
import tempfile
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ReceiptDownloader:
    def __init__(self, ocr_processor=None):
        """
        :param ocr_processor: any object with a .process(file_path) -> dict method
                              (e.g. HuggingFaceClient, MindeeClient, VisionClient)
        """
        self.ocr_processor = ocr_processor

    def download_and_process_attachments_parallel(self, service, messages: List[Dict], max_workers=5) -> List[Dict]:
        """
        Downloads and optionally OCR-processes attachments from Gmail messages in parallel.
        :param service: Gmail service for an account
        :param messages: List of Gmail metadata (must include 'id')
        :param max_workers: Thread pool size
        :return: List of structured receipt data (from OCR or raw file info)
        """
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._download_and_process, service, msg["id"]) for msg in messages]
            for future in as_completed(futures):
                data = future.result()
                if data:
                    results.append(data)
        return results

    def _download_and_process(self, service, msg_id) -> Optional[Dict]:
        try:
            msg = service.users().messages().get(userId='me', id=msg_id).execute()
            parts = msg.get("payload", {}).get("parts", [])
            for part in parts:
                filename = part.get("filename", "")
                body = part.get("body", {})
                attachment_id = body.get("attachmentId")

                if filename and attachment_id:
                    attachment = service.users().messages().attachments().get(
                        userId='me', messageId=msg_id, id=attachment_id
                    ).execute()

                    file_data = base64.urlsafe_b64decode(attachment["data"].encode("UTF-8"))
                    ext = filename.split(".")[-1] or "pdf"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as temp_file:
                        temp_file.write(file_data)
                        temp_path = temp_file.name

                    logger.info(f"✅ Downloaded {filename} to {temp_path}")

                    if self.ocr_processor:
                        try:
                            ocr_result = self.ocr_processor.process(temp_path)
                            os.remove(temp_path)
                            return ocr_result
                        except Exception as ocr_error:
                            logger.warning(f"OCR failed: {ocr_error}")
                            return None
                    else:
                        return {"path": temp_path, "filename": filename, "raw_bytes": file_data}

        except Exception as e:
            logger.error(f"❌ Failed to process Gmail msg {msg_id}: {e}")
            return None