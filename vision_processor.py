import os
import io
import logging
import re
from typing import Dict, List
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF
from google.cloud import vision
from field_parser import parse_fields  # Externalized field parsing logic

# Set up credentials for Google Cloud Vision API
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/briankaplan/Backup/Desktop/Expenses-py/receipt-processor/gmail_auth/service-account.json"
client = vision.ImageAnnotatorClient()

def is_pdf(file_path: str) -> bool:
    return file_path.lower().endswith(".pdf")

def convert_pdf_to_images(pdf_path: str) -> List[Image.Image]:
    logging.info(f"📄 Converting PDF to images: {pdf_path}")
    images = []
    doc = fitz.open(pdf_path)
    for page in doc:
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    return images

def image_to_text(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    content = buffer.getvalue()
    image_obj = vision.Image(content=content)
    response = client.text_detection(image=image_obj)
    return response.full_text_annotation.text if response.full_text_annotation.text else ""

def process_receipt_image(file_path: str) -> Dict[str, str]:
    logging.info(f"🔍 Processing receipt: {file_path}")
    extracted_text = ""

    try:
        if is_pdf(file_path):
            images = convert_pdf_to_images(file_path)
            extracted_text = "\n".join([image_to_text(img) for img in images])
        else:
            image = Image.open(file_path)
            extracted_text = image_to_text(image)
    except Exception as e:
        logging.error(f"❌ Error processing {file_path}: {e}")
        return {"error": str(e), "file_path": file_path}

    fields = parse_fields(extracted_text)
    fields["file_path"] = file_path
    fields["full_text"] = extracted_text[:10000]  # Optional debug preview
    return fields
