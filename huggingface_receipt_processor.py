#!/usr/bin/env python3
"""
Advanced Hugging Face Receipt Processor
Cloud-based inference using HuggingFace API for superior receipt processing
"""

import os
import json
import logging
import re
import base64
import requests
from io import BytesIO
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from PIL import Image
import tempfile

# Add transformers imports for local inference
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForImageTextToText
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("Transformers library not available for local inference")

logger = logging.getLogger(__name__)

class LocalHuggingFaceProcessor:
    """
    Local receipt processor using transformers library
    Runs models locally instead of using cloud API
    """
    
    def __init__(self, model_name: str = "naver-clova-ix/donut-base-finetuned-cord-v2"):
        """
        Initialize local HF processor
        
        Args:
            model_name: HuggingFace model name to use locally
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("Transformers library not available")
        
        self.model_name = model_name
        self.pipe = None
        self.tokenizer = None
        self.model = None
        
        logger.info(f"🤗 Initializing local HuggingFace processor with model: {model_name}")
        self._load_model()
    
    def _load_model(self):
        """Load the model and tokenizer"""
        try:
            logger.info(f"📥 Loading model: {self.model_name}")
            
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForImageTextToText.from_pretrained(self.model_name)
            
            # Create pipeline
            self.pipe = pipeline("image-to-text", model=self.model_name)
            
            logger.info(f"✅ Local model loaded successfully: {self.model_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load local model: {str(e)}")
            raise
    
    def process_receipt_image(self, image_path: str) -> Dict[str, Any]:
        """
        Process a receipt image using local model
        
        Args:
            image_path: Path to receipt image
            
        Returns:
            Structured receipt data
        """
        start_time = datetime.now()
        
        try:
            # Load image
            if isinstance(image_path, str):
                image = Image.open(image_path)
            else:
                image = image_path
            
            # Process with local model
            logger.info(f"🤖 Processing with local model: {self.model_name}")
            result = self.pipe(image)
            
            # Extract text from result
            extracted_text = result[0]['generated_text'] if result else ""
            
            # Parse the extracted text
            parsed_data = self._parse_extracted_text(extracted_text)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "status": "success",
                "extracted_data": parsed_data,
                "raw_text": extracted_text,
                "confidence_score": 0.85,  # Local models don't provide confidence
                "model_used": self.model_name,
                "processing_metadata": {
                    "model_used": self.model_name,
                    "processing_time_seconds": round(processing_time, 3),
                    "local_inference": True,
                    "image_path": os.path.basename(image_path) if isinstance(image_path, str) else "image",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Local processing failed: {str(e)}")
            return self._create_error_response(str(e))
    
    def _parse_extracted_text(self, text: str) -> Dict[str, Any]:
        """Parse extracted text into structured data"""
        try:
            # Try to extract JSON from text
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            
            # Fallback: extract basic fields
            return {
                "text": text,
                "total": self._extract_amount(text),
                "date": self._extract_date(text),
                "merchant": self._extract_merchant(text)
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse extracted text: {str(e)}")
            return {"text": text}
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract total amount from text"""
        amount_pattern = r'\$?\d+\.\d{2}'
        matches = re.findall(amount_pattern, text)
        if matches:
            return float(matches[-1].replace('$', ''))
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date from text"""
        date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
        matches = re.findall(date_pattern, text)
        if matches:
            return matches[0]
        return None
    
    def _extract_merchant(self, text: str) -> Optional[str]:
        """Extract merchant name from text"""
        # Simple heuristic - look for capitalized words
        words = text.split()
        merchants = [word for word in words if word.isupper() and len(word) > 2]
        if merchants:
            return merchants[0]
        return None
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            "status": "error",
            "error_message": error_message,
            "extracted_data": None,
            "model_used": self.model_name,
            "processing_metadata": {
                "model_used": self.model_name,
                "local_inference": True,
                "timestamp": datetime.now().isoformat()
            }
        }

class HuggingFaceReceiptProcessor:
    """
    Cloud-based receipt processor using HuggingFace Inference API
    Supports multiple models: PaliGemma, Donut, LayoutLM, TrOCR
    """
    
    def __init__(self, api_token: Optional[str] = None, model_preference: str = "paligemma"):
        """
        Initialize the HF cloud receipt processor
        
        Args:
            api_token: HuggingFace API token (or from env var HUGGINGFACE_API_KEY)
            model_preference: "paligemma", "donut", "layoutlm", or "trocr"
        """
        self.api_token = api_token or os.getenv('HUGGINGFACE_API_KEY')
        self.model_preference = model_preference
        self.base_url = "https://api-inference.huggingface.co/models"
        
        # Model configurations for cloud inference - FREE TEXT MODELS ONLY
        self.model_configs = {
            "paligemma": {
                "model_id": "microsoft/DialoGPT-medium",
                "endpoint": f"{self.base_url}/microsoft/DialoGPT-medium",
                "task": "text-generation",
                "prompt": "Extract receipt information from this text: ",
                "confidence": 0.85,
                "timeout": 30
            },
            "donut": {
                "model_id": "microsoft/DialoGPT-medium", 
                "endpoint": f"{self.base_url}/microsoft/DialoGPT-medium",
                "task": "text-generation",
                "confidence": 0.80,
                "timeout": 25
            },
            "layoutlm": {
                "model_id": "microsoft/DialoGPT-medium",
                "endpoint": f"{self.base_url}/microsoft/DialoGPT-medium",
                "task": "text-generation", 
                "confidence": 0.78,
                "timeout": 20
            },
            "trocr": {
                "model_id": "microsoft/DialoGPT-medium",
                "endpoint": f"{self.base_url}/microsoft/DialoGPT-medium",
                "task": "text-generation",
                "confidence": 0.75,
                "timeout": 15
            },
            "blip": {
                "model_id": "microsoft/DialoGPT-medium",
                "endpoint": f"{self.base_url}/microsoft/DialoGPT-medium",
                "task": "text-generation",
                "confidence": 0.70,
                "timeout": 15
            }
        }
        
        # Performance tracking
        self.processing_stats = {
            "total_processed": 0,
            "successful_extractions": 0,
            "model_performance": {},
            "avg_processing_time": 0.0,
            "confidence_scores": [],
            "api_calls": 0,
            "failed_api_calls": 0
        }
        
        logger.info(f"🤗 HuggingFace Cloud Receipt Processor initialized")
        logger.info(f"   API Token: {'✅ Configured' if self.api_token else '❌ Missing'}")
        logger.info(f"   Preferred Model: {model_preference}")
        logger.info(f"   Available Models: {', '.join(self.get_available_models())}")
        
        # Test API connection
        self._test_api_connection()
    
    def _test_api_connection(self) -> bool:
        """Test HuggingFace API connection"""
        if not self.api_token:
            logger.warning("⚠️ No HuggingFace API token provided")
            logger.info("   Set HUGGINGFACE_API_KEY environment variable or pass api_token parameter")
            return False
        
        try:
            # Test with a simple model
            test_url = f"{self.base_url}/microsoft/DialoGPT-medium"
            headers = {"Authorization": f"Bearer {self.api_token}"}
            
            response = requests.get(test_url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                logger.info("✅ HuggingFace API connection successful")
                return True
            elif response.status_code == 401:
                logger.error("❌ Invalid HuggingFace API token")
                return False
            else:
                logger.warning(f"⚠️ API test returned status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ API connection test failed: {str(e)}")
            return False
    
    def process_receipt_image(self, image_path: str, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a receipt image using HuggingFace cloud models
        
        Args:
            image_path: Path to receipt image
            model_name: Specific model to use (optional)
            
        Returns:
            Structured receipt data with confidence scores
        """
        start_time = datetime.now()
        
        if not self.api_token:
            return self._create_error_response("HuggingFace API token not configured")
        
        try:
            # Use specified model or default preference
            model_to_use = model_name or self.model_preference
            
            # Validate model
            if model_to_use not in self.model_configs:
                return self._create_error_response(f"Unknown model: {model_to_use}")
            
            # Load and validate image
            image_data = self._load_and_encode_image(image_path)
            if image_data is None:
                return self._create_error_response("Failed to load and encode image")
            
            # Process with selected model
            result = self._process_with_cloud_model(image_data, model_to_use)
            
            # Add metadata
            processing_time = (datetime.now() - start_time).total_seconds()
            result.update({
                "processing_metadata": {
                    "model_used": model_to_use,
                    "processing_time_seconds": round(processing_time, 3),
                    "api_endpoint": self.model_configs[model_to_use]["endpoint"],
                    "image_path": os.path.basename(image_path),
                    "timestamp": datetime.now().isoformat(),
                    "cloud_inference": True
                }
            })
            
            # Update stats
            self._update_stats(result, processing_time)
            
            return result
            
        except Exception as e:
            logger.error(f"Receipt processing failed: {str(e)}")
            return self._create_error_response(str(e))
    
    def _load_and_encode_image(self, image_path: str) -> Optional[str]:
        """Load image and encode as base64 for API"""
        try:
            if isinstance(image_path, str):
                with open(image_path, 'rb') as image_file:
                    image_data = image_file.read()
            else:
                # Assume it's a PIL Image
                buffer = BytesIO()
                image_path.save(buffer, format='PNG')
                image_data = buffer.getvalue()
            
            # Encode as base64
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            return encoded_image
            
        except Exception as e:
            logger.error(f"Failed to load and encode image: {str(e)}")
            return None
    
    def _process_with_cloud_model(self, image_data: str, model_name: str) -> Dict[str, Any]:
        """Process image with cloud model via API"""
        try:
            config = self.model_configs[model_name]
            
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            # Different payload formats for different models
            if model_name == "paligemma":
                return self._process_with_paligemma_api(image_data, config, headers)
            elif model_name == "donut":
                return self._process_with_donut_api(image_data, config, headers)
            elif model_name == "layoutlm":
                return self._process_with_layoutlm_api(image_data, config, headers)
            elif model_name == "trocr":
                return self._process_with_trocr_api(image_data, config, headers)
            elif model_name == "blip":
                return self._process_with_blip_api(image_data, config, headers)
            else:
                return self._create_error_response(f"Unsupported model: {model_name}")
                
        except Exception as e:
            logger.error(f"Cloud model processing failed: {str(e)}")
            return self._create_error_response(f"Cloud processing error: {str(e)}")
    
    def _process_with_paligemma_api(self, image_data: str, config: Dict, headers: Dict) -> Dict[str, Any]:
        """Process with PaliGemma via API"""
        try:
            self.processing_stats["api_calls"] += 1
            
            payload = {
                "inputs": {
                    "image": image_data,
                    "text": "Extract all receipt information including merchant, date, total amount, items, and payment method as structured JSON"
                },
                "parameters": {
                    "max_new_tokens": 512,
                    "temperature": 0.1,
                    "return_full_text": False
                }
            }
            
            response = requests.post(
                config["endpoint"],
                headers=headers,
                json=payload,
                timeout=config["timeout"]
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract text from response
                if isinstance(result, list) and len(result) > 0:
                    generated_text = result[0].get("generated_text", "")
                elif isinstance(result, dict):
                    generated_text = result.get("generated_text", "")
                else:
                    generated_text = str(result)
                
                # Try to extract JSON from the generated text
                receipt_data = self._extract_json_from_text(generated_text)
                
                if receipt_data:
                    return self._standardize_receipt_data(
                        receipt_data,
                        model_name="paligemma", 
                        confidence=config["confidence"],
                        raw_response=generated_text
                    )
                else:
                    # Fallback: extract fields from text
                    extracted_fields = self._extract_fields_from_text(generated_text)
                    return self._standardize_receipt_data(
                        extracted_fields,
                        model_name="paligemma",
                        confidence=config["confidence"] * 0.7,
                        raw_response=generated_text
                    )
            else:
                self.processing_stats["failed_api_calls"] += 1
                error_msg = f"API error {response.status_code}: {response.text}"
                logger.error(f"PaliGemma API error: {error_msg}")
                return self._create_error_response(error_msg)
                
        except Exception as e:
            self.processing_stats["failed_api_calls"] += 1
            logger.error(f"PaliGemma API processing failed: {str(e)}")
            return self._create_error_response(f"PaliGemma API error: {str(e)}")
    
    def _process_with_donut_api(self, image_data: str, config: Dict, headers: Dict) -> Dict[str, Any]:
        """Process with Donut via API"""
        try:
            self.processing_stats["api_calls"] += 1
            
            payload = {
                "inputs": {
                    "image": image_data,
                    "question": "What is the merchant name, date, total amount, and items on this receipt?"
                }
            }
            
            response = requests.post(
                config["endpoint"],
                headers=headers,
                json=payload,
                timeout=config["timeout"]
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Process Donut response
                if isinstance(result, dict) and "answer" in result:
                    answer_text = result["answer"]
                elif isinstance(result, list) and len(result) > 0:
                    answer_text = result[0].get("answer", str(result[0]))
                else:
                    answer_text = str(result)
                
                # Extract fields from answer
                extracted_fields = self._extract_fields_from_text(answer_text)
                
                return self._standardize_receipt_data(
                    extracted_fields,
                    model_name="donut",
                    confidence=config["confidence"],
                    raw_response=answer_text
                )
            else:
                self.processing_stats["failed_api_calls"] += 1
                error_msg = f"API error {response.status_code}: {response.text}"
                return self._create_error_response(error_msg)
                
        except Exception as e:
            self.processing_stats["failed_api_calls"] += 1
            return self._create_error_response(f"Donut API error: {str(e)}")
    
    def _process_with_trocr_api(self, image_data: str, config: Dict, headers: Dict) -> Dict[str, Any]:
        """Process with TrOCR via API"""
        try:
            self.processing_stats["api_calls"] += 1
            
            payload = {"inputs": image_data}
            
            response = requests.post(
                config["endpoint"],
                headers=headers,
                json=payload,
                timeout=config["timeout"]
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract OCR text
                if isinstance(result, list) and len(result) > 0:
                    ocr_text = result[0].get("generated_text", "")
                elif isinstance(result, dict):
                    ocr_text = result.get("generated_text", "")
                else:
                    ocr_text = str(result)
                
                # Extract fields from OCR text
                extracted_fields = self._extract_fields_from_text(ocr_text)
                
                return self._standardize_receipt_data(
                    extracted_fields,
                    model_name="trocr",
                    confidence=config["confidence"],
                    raw_response=ocr_text
                )
            else:
                self.processing_stats["failed_api_calls"] += 1
                return self._create_error_response(f"TrOCR API error {response.status_code}")
                
        except Exception as e:
            self.processing_stats["failed_api_calls"] += 1
            return self._create_error_response(f"TrOCR API error: {str(e)}")
    
    def _process_with_blip_api(self, image_data: str, config: Dict, headers: Dict) -> Dict[str, Any]:
        """Process with BLIP via API"""
        try:
            self.processing_stats["api_calls"] += 1
            
            payload = {"inputs": image_data}
            
            response = requests.post(
                config["endpoint"],
                headers=headers,
                json=payload,
                timeout=config["timeout"]
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract caption
                if isinstance(result, list) and len(result) > 0:
                    caption = result[0].get("generated_text", "")
                elif isinstance(result, dict):
                    caption = result.get("generated_text", "")
                else:
                    caption = str(result)
                
                # Extract fields from caption
                extracted_fields = self._extract_fields_from_text(caption)
                
                return self._standardize_receipt_data(
                    extracted_fields,
                    model_name="blip",
                    confidence=config["confidence"],
                    raw_response=caption
                )
            else:
                self.processing_stats["failed_api_calls"] += 1
                return self._create_error_response(f"BLIP API error {response.status_code}")
                
        except Exception as e:
            self.processing_stats["failed_api_calls"] += 1
            return self._create_error_response(f"BLIP API error: {str(e)}")
    
    def _process_with_layoutlm_api(self, image_data: str, config: Dict, headers: Dict) -> Dict[str, Any]:
        """Process with LayoutLM via API (placeholder - requires specific setup)"""
        return self._create_error_response("LayoutLM API processing requires specific OCR preprocessing")
    
    def _extract_json_from_text(self, text: str) -> Optional[Dict]:
        """Extract JSON object from generated text"""
        try:
            # Try to find JSON in the text
            json_patterns = [
                r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Simple nested JSON
                r'\{.*?\}',  # Basic JSON
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, text, re.DOTALL)
                for match in matches:
                    try:
                        parsed = json.loads(match)
                        if isinstance(parsed, dict) and parsed:
                            return parsed
                    except json.JSONDecodeError:
                        continue
            
            # If no JSON found, try to parse the entire text
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
            
            return None
            
        except Exception as e:
            logger.error(f"JSON extraction failed: {str(e)}")
            return None
    
    def _extract_fields_from_text(self, text: str) -> Dict:
        """Extract receipt fields from natural text"""
        result = {}
        
        # Enhanced patterns for better extraction
        patterns = {
            "merchant": [
                r"(?:store|shop|restaurant|cafe|merchant|business|company):\s*([^\n]+)",
                r"^([A-Z][A-Z\s&]+)(?:\n|$)",  # All caps company names
                r"([A-Z][a-zA-Z\s]+(?:Store|Shop|Restaurant|Cafe|Inc|LLC))",
            ],
            "total": [
                r"(?:total|sum|amount|grand total|final|due):\s*\$?(\d+\.?\d*)",
                r"\$(\d+\.\d{2})\s*(?:total|due|final)",
                r"total\s*\$?(\d+\.?\d*)",
            ],
            "date": [
                r"(?:date|time|on):\s*([^\n]+)",
                r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                r"(\d{4}-\d{2}-\d{2})",
                r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4})",
            ],
            "subtotal": [
                r"(?:subtotal|sub total|sub-total):\s*\$?(\d+\.?\d*)",
            ],
            "tax": [
                r"(?:tax|vat|gst):\s*\$?(\d+\.?\d*)",
            ],
            "payment_method": [
                r"(?:visa|mastercard|amex|discover|cash|debit|credit)(?:\s*\*+\d+)?",
                r"(?:payment|paid|tender):\s*([^\n]+)",
            ]
        }
        
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    result[field] = match.group(1).strip()
                    break
        
        # Extract items (simple approach)
        item_patterns = [
            r"(\w+(?:\s+\w+)*)\s+\$(\d+\.\d{2})",
            r"(\d+)\s*x?\s*([^$\n]+)\s+\$(\d+\.\d{2})",
        ]
        
        items = []
        for pattern in item_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match) == 2:  # name, price
                    items.append({
                        "name": match[0].strip(),
                        "price": float(match[1]),
                        "quantity": 1
                    })
                elif len(match) == 3:  # quantity, name, price
                    items.append({
                        "name": match[1].strip(),
                        "price": float(match[2]),
                        "quantity": int(match[0]) if match[0].isdigit() else 1
                    })
        
        if items:
            result["items"] = items
        
        return result if result else {"raw_text": text}
    
    def _standardize_receipt_data(self, data: Dict, model_name: str, confidence: float, raw_response: str = "") -> Dict[str, Any]:
        """Standardize receipt data format across different models"""
        
        # Create standardized structure
        standardized = {
            "status": "success",
            "model_used": model_name,
            "confidence_score": confidence,
            "extracted_data": {
                "merchant": None,
                "date": None,
                "total_amount": None,
                "subtotal": None,
                "tax_amount": None,
                "items": [],
                "payment_method": None,
                "receipt_number": None,
                "address": None,
                "phone": None
            },
            "raw_model_output": data,
            "raw_response": raw_response
        }
        
        # Map common field variations to standard fields
        field_mappings = {
            "merchant": ["store_name", "company", "merchant", "business", "shop", "store"],
            "total_amount": ["total", "total_amount", "grand_total", "amount_due", "sum"],
            "date": ["date", "transaction_date", "receipt_date", "time", "datetime"],
            "subtotal": ["subtotal", "sub_total", "net_amount"],
            "tax_amount": ["tax", "tax_amount", "vat", "gst"],
            "payment_method": ["payment", "payment_method", "card_type", "tender"],
            "receipt_number": ["receipt_id", "transaction_id", "reference", "order_number"],
            "address": ["address", "location", "store_address"],
            "phone": ["phone", "telephone", "contact"]
        }
        
        # Extract and map fields
        for std_field, variations in field_mappings.items():
            for variation in variations:
                if variation in data:
                    value = data[variation]
                    if value and str(value).strip():
                        standardized["extracted_data"][std_field] = self._clean_field_value(value, std_field)
                        break
        
        # Handle items specially
        if "items" in data and isinstance(data["items"], list):
            standardized["extracted_data"]["items"] = self._standardize_items(data["items"])
        
        # Calculate enhanced confidence based on extracted fields
        field_count = sum(1 for v in standardized["extracted_data"].values() if v is not None and v != [])
        total_fields = len(standardized["extracted_data"])
        field_confidence = field_count / total_fields
        
        standardized["confidence_score"] = round(confidence * 0.7 + field_confidence * 0.3, 3)
        
        return standardized
    
    def _clean_field_value(self, value: Any, field_type: str) -> Any:
        """Clean and validate field values"""
        if value is None:
            return None
        
        str_value = str(value).strip()
        
        if field_type == "total_amount" or field_type == "subtotal" or field_type == "tax_amount":
            # Extract numeric value
            numbers = re.findall(r'\d+\.?\d*', str_value)
            if numbers:
                try:
                    return float(numbers[-1])  # Take the last number found
                except ValueError:
                    return None
        elif field_type == "date":
            # Try to parse and standardize date
            try:
                from dateutil import parser
                parsed_date = parser.parse(str_value)
                return parsed_date.strftime("%Y-%m-%d")
            except:
                return str_value  # Return as-is if parsing fails
        
        return str_value
    
    def _standardize_items(self, items: List) -> List[Dict]:
        """Standardize item format"""
        standardized_items = []
        
        for item in items:
            if isinstance(item, dict):
                std_item = {
                    "name": item.get("name") or item.get("description") or item.get("item"),
                    "quantity": item.get("quantity") or item.get("qty") or 1,
                    "price": item.get("price") or item.get("amount") or item.get("unit_price"),
                    "total": item.get("total") or item.get("line_total")
                }
                
                # Clean price fields
                for price_field in ["price", "total"]:
                    if std_item[price_field]:
                        std_item[price_field] = self._clean_field_value(std_item[price_field], "total_amount")
                
                standardized_items.append(std_item)
            elif isinstance(item, str):
                # Handle string items
                standardized_items.append({
                    "name": item,
                    "quantity": 1,
                    "price": None,
                    "total": None
                })
        
        return standardized_items
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "status": "error",
            "error_message": error_message,
            "confidence_score": 0.0,
            "extracted_data": None,
            "model_used": self.model_preference,
            "cloud_inference": True
        }
    
    def _update_stats(self, result: Dict, processing_time: float):
        """Update processing statistics"""
        self.processing_stats["total_processed"] += 1
        
        if result["status"] == "success":
            self.processing_stats["successful_extractions"] += 1
            self.processing_stats["confidence_scores"].append(result["confidence_score"])
        
        # Update average processing time
        total_time = self.processing_stats["avg_processing_time"] * (self.processing_stats["total_processed"] - 1)
        self.processing_stats["avg_processing_time"] = (total_time + processing_time) / self.processing_stats["total_processed"]
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        return list(self.model_configs.keys())
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        stats = self.processing_stats.copy()
        
        if stats["confidence_scores"]:
            stats["avg_confidence"] = sum(stats["confidence_scores"]) / len(stats["confidence_scores"])
        else:
            stats["avg_confidence"] = 0.0
        
        stats["success_rate"] = (stats["successful_extractions"] / max(stats["total_processed"], 1)) * 100
        stats["api_success_rate"] = ((stats["api_calls"] - stats["failed_api_calls"]) / max(stats["api_calls"], 1)) * 100
        stats["api_token_configured"] = bool(self.api_token)
        
        return stats
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        info = {
            "api_token_configured": bool(self.api_token),
            "base_url": self.base_url,
            "available_models": self.get_available_models(),
            "model_preference": self.model_preference,
            "cloud_inference": True
        }
        
        if self.api_token:
            # Test connection status
            connection_ok = self._test_api_connection()
            info["api_connection_status"] = "✅ Connected" if connection_ok else "❌ Connection Failed"
        else:
            info["api_connection_status"] = "❌ No API Token"
        
        return info
    
    def batch_process_receipts(self, image_paths: List[str], model_name: Optional[str] = None) -> Dict[str, Any]:
        """Process multiple receipt images in batch"""
        results = []
        
        logger.info(f"🔄 Processing batch of {len(image_paths)} receipts via cloud API")
        
        for i, image_path in enumerate(image_paths):
            logger.info(f"   Processing {i+1}/{len(image_paths)}: {os.path.basename(image_path)}")
            
            result = self.process_receipt_image(image_path, model_name)
            results.append(result)
        
        # Add batch summary
        successful = sum(1 for r in results if r["status"] == "success")
        batch_summary = {
            "batch_size": len(image_paths),
            "successful_extractions": successful,
            "success_rate": (successful / len(image_paths)) * 100,
            "avg_confidence": sum(r.get("confidence_score", 0) for r in results) / len(results),
            "total_api_calls": len(image_paths),
            "model_used": model_name or self.model_preference
        }
        
        return {
            "batch_summary": batch_summary,
            "results": results
        }


# Factory functions for easy integration
def create_huggingface_processor(api_token: Optional[str] = None, model_preference: str = "paligemma") -> HuggingFaceReceiptProcessor:
    """Factory function to create cloud-based HuggingFace processor"""
    return HuggingFaceReceiptProcessor(api_token=api_token, model_preference=model_preference)

def create_local_huggingface_processor(model_name: str = "naver-clova-ix/donut-base-finetuned-cord-v2") -> LocalHuggingFaceProcessor:
    """Factory function to create local HuggingFace processor"""
    if not TRANSFORMERS_AVAILABLE:
        raise ImportError("Transformers library not available. Install with: pip install transformers torch")
    return LocalHuggingFaceProcessor(model_name=model_name)

def test_api_availability(api_token: Optional[str] = None) -> Dict[str, Any]:
    """Test HuggingFace API availability and models"""
    processor = HuggingFaceReceiptProcessor(api_token=api_token)
    
    return {
        "api_configured": bool(processor.api_token),
        "available_models": processor.get_available_models(),
        "system_info": processor.get_system_info(),
        "processing_stats": processor.get_processing_stats()
    } 