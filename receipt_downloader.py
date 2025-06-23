import os
import base64
import tempfile
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
import mimetypes

logger = logging.getLogger(__name__)

class ReceiptDownloader:
    def __init__(self, ocr_processor=None, r2_client=None):
        """
        :param ocr_processor: any object with a .process(file_path) -> dict method
                              (e.g. HuggingFaceClient, MindeeClient, VisionClient)
        :param r2_client: R2Client instance for cloud storage
        """
        self.ocr_processor = ocr_processor
        self.r2_client = r2_client
        self.supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
        self.receipt_keywords = ['receipt', 'invoice', 'bill', 'order', 'payment', 'confirmation']

    def download_and_process_attachments_parallel(self, service, messages: List[Dict], max_workers=10) -> List[Dict]:
        """
        OPTIMIZED: Downloads and processes attachments from Gmail messages in parallel.
        - Increased max_workers for better concurrency
        - Pre-filters messages for likely receipts
        - Batch processing for better performance
        """
        if not messages:
            return []
        
        logger.info(f"🚀 Starting parallel processing of {len(messages)} messages with {max_workers} workers")
        start_time = time.time()
        
        # Pre-filter messages that likely contain receipts
        filtered_messages = self._filter_receipt_messages(messages)
        logger.info(f"📧 Filtered to {len(filtered_messages)} likely receipt messages")
        
        results = []
        processed_count = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_msg = {
                executor.submit(self._download_and_process_optimized, service, msg): msg 
                for msg in filtered_messages
            }
            
            # Process completed tasks as they finish
            for future in as_completed(future_to_msg):
                try:
                    data = future.result(timeout=30)  # 30-second timeout per message
                    if data:
                        results.append(data)
                    processed_count += 1
                    
                    # Log progress every 10 messages
                    if processed_count % 10 == 0:
                        logger.info(f"⏳ Processed {processed_count}/{len(filtered_messages)} messages")
                        
                except Exception as e:
                    msg = future_to_msg[future]
                    logger.error(f"❌ Failed to process message {msg.get('id', 'unknown')}: {e}")
        
        elapsed_time = time.time() - start_time
        logger.info(f"✅ Completed processing in {elapsed_time:.2f} seconds. Found {len(results)} receipts.")
        return results

    def _filter_receipt_messages(self, messages: List[Dict]) -> List[Dict]:
        """Pre-filter messages that likely contain receipts based on subject and sender"""
        filtered = []
        for msg in messages:
            subject = msg.get('subject', '').lower()
            sender = msg.get('from', '').lower()
            
            # Check for receipt keywords in subject or sender
            if any(keyword in subject or keyword in sender for keyword in self.receipt_keywords):
                filtered.append(msg)
            # Check for common receipt senders
            elif any(domain in sender for domain in ['paypal', 'stripe', 'square', 'amazon', 'walmart', 'target']):
                filtered.append(msg)
        
        return filtered if filtered else messages  # Return all if no filtering matches

    def _download_and_process_optimized(self, service, msg_data) -> Optional[Dict]:
        """OPTIMIZED: Download and process with better performance and error handling"""
        msg_id = msg_data.get('id')
        if not msg_id:
            return None
            
        try:
            # Get message with minimal data first (faster API call)
            msg = service.users().messages().get(
                userId='me', 
                id=msg_id, 
                format='full'
            ).execute()
            
            # Extract message metadata
            headers = msg.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Process all parts of the message
            all_parts = self._get_all_message_parts(msg.get("payload", {}))
            
            for part in all_parts:
                filename = part.get("filename", "")
                body = part.get("body", {})
                attachment_id = body.get("attachmentId")
                
                # Skip if no attachment or not a supported file type
                if not filename or not attachment_id:
                    continue
                    
                file_ext = os.path.splitext(filename.lower())[1]
                if file_ext not in self.supported_extensions:
                    continue
                
                try:
                    # Download attachment
                    attachment = service.users().messages().attachments().get(
                        userId='me', 
                        messageId=msg_id, 
                        id=attachment_id
                    ).execute()
                    
                    file_data = base64.urlsafe_b64decode(attachment["data"].encode("UTF-8"))
                    
                    # Create temporary file with proper extension
                    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                        temp_file.write(file_data)
                        temp_path = temp_file.name
                    
                    logger.info(f"📎 Downloaded {filename} ({len(file_data)} bytes)")
                    
                    # Upload to R2 storage if available
                    r2_key = None
                    r2_url = None
                    if self.r2_client and self.r2_client.is_connected():
                        try:
                            # Extract email account from sender for organized storage
                            email_account = msg_data.get('account', 'unknown')
                            
                            # Upload to R2 with organized path structure
                            attachment_info = {
                                'size': len(file_data),
                                'mime_type': mimetypes.guess_type(filename)[0] or 'application/octet-stream',
                                'message_id': msg_id
                            }
                            
                            r2_key = self.r2_client.upload_receipt_attachment(
                                temp_path, 
                                msg_id, 
                                email_account, 
                                attachment_info
                            )
                            
                            if r2_key:
                                # Generate public URL for the uploaded file
                                r2_public_url = os.getenv('R2_PUBLIC_URL', '')
                                if r2_public_url:
                                    r2_url = f"{r2_public_url}/{r2_key}"
                                    logger.info(f"☁️ Uploaded {filename} to R2: {r2_key}")
                                
                        except Exception as r2_error:
                            logger.warning(f"⚠️ R2 upload failed for {filename}: {r2_error}")
                    
                    # Process with OCR if available
                    if self.ocr_processor:
                        try:
                            ocr_result = self.ocr_processor.process(temp_path)
                            os.remove(temp_path)  # Clean up temp file
                            
                            # Add metadata to result including R2 info
                            if ocr_result:
                                ocr_result.update({
                                    'email_id': msg_id,
                                    'subject': subject,
                                    'sender': sender,
                                    'date': date,
                                    'filename': filename,
                                    'file_size': len(file_data),
                                    'email_account': msg_data.get('account', 'unknown'),
                                    'r2_key': r2_key,
                                    'r2_url': r2_url,
                                    'attachment_id': attachment_id
                                })
                            return ocr_result
                            
                        except Exception as ocr_error:
                            logger.warning(f"⚠️ OCR failed for {filename}: {ocr_error}")
                            os.remove(temp_path)  # Clean up on failure
                            continue
                    else:
                        # Return file info without OCR
                        return {
                            "path": temp_path,
                            "filename": filename,
                            "raw_bytes": file_data,
                            'email_id': msg_id,
                            'subject': subject,
                            'sender': sender,
                            'date': date,
                            'file_size': len(file_data)
                        }
                        
                except Exception as attachment_error:
                    logger.error(f"❌ Failed to download attachment {filename}: {attachment_error}")
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Failed to process Gmail message {msg_id}: {e}")
            return None
        
        return None
    
    def _get_all_message_parts(self, payload):
        """Recursively extract all parts from a message payload"""
        parts = []
        
        if 'parts' in payload:
            for part in payload['parts']:
                parts.extend(self._get_all_message_parts(part))
        else:
            parts.append(payload)
            
        return parts

    def _download_and_process(self, service, msg_id) -> Optional[Dict]:
        """Legacy method - kept for backward compatibility"""
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