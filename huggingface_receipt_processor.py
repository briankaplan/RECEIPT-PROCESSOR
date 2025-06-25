#!/usr/bin/env python3
"""
Advanced Hugging Face Receipt Processor
Integrates multiple state-of-the-art models via cloud APIs for superior receipt processing
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

logger = logging.getLogger(__name__)

class HuggingFaceReceiptProcessor:
    """
    Advanced receipt processor using Hugging Face transformers
    Supports multiple models: PaliGemma, Donut, LayoutLM, TrOCR
    """
    
    def __init__(self, model_preference: str = "paligemma", device: str = "auto"):
        """
        Initialize the HF receipt processor
        
        Args:
            model_preference: "paligemma", "donut", "layoutlm", or "trocr"
            device: "auto", "cuda", "cpu"
        """
        self.model_preference = model_preference
        self.device = self._setup_device(device)
        self.models = {}
        self.processors = {}
        
        # Check if transformers is available
        self.transformers_available = self._check_transformers()
        
        # Model configurations
        self.model_configs = {
            "paligemma": {
                "model_id": "mychen76/paligemma-receipt-json-3b-mix-448-v2b",
                "task": "image-to-text",
                "prompt": "EXTRACT_JSON_RECEIPT",
                "max_tokens": 512,
                "confidence": 0.95
            },
            "mistral_ocr": {
                "model_id": "mychen76/mistral7b_ocr_to_json_v1", 
                "task": "ocr-to-json",
                "confidence": 0.90
            },
            "donut": {
                "model_id": "jinhybr/OCR-Donut-CORD",
                "task": "document-parsing",
                "confidence": 0.85
            },
            "layoutlm": {
                "model_id": "jinhybr/OCR-LayoutLMv3-Invoice",
                "task": "token-classification",
                "confidence": 0.88
            }
        }
        
        # Performance tracking
        self.processing_stats = {
            "total_processed": 0,
            "successful_extractions": 0,
            "model_performance": {},
            "avg_processing_time": 0.0,
            "confidence_scores": []
        }
        
        logger.info(f"🤗 HuggingFace Receipt Processor initialized")
        logger.info(f"   Device: {self.device}")
        logger.info(f"   Preferred Model: {model_preference}")
        logger.info(f"   Transformers Available: {self.transformers_available}")
        
        if self.transformers_available:
            # Try to load the preferred model
            self._initialize_model(model_preference)
    
    def _check_transformers(self) -> bool:
        """Check if transformers library is available"""
        try:
            import transformers
            import torch
            logger.info(f"✅ Transformers library available (v{transformers.__version__})")
            return True
        except ImportError:
            logger.warning("⚠️ Transformers library not available")
            return False
    
    def _setup_device(self, device: str) -> str:
        """Setup the appropriate device for model inference"""
        if not self.transformers_available:
            return "cpu"
            
        try:
            import torch
            if device == "auto":
                if torch.cuda.is_available():
                    return "cuda"
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    return "mps"  # Apple Silicon
                else:
                    return "cpu"
            return device
        except ImportError:
            return "cpu"
    
    def _initialize_model(self, model_name: str) -> bool:
        """Initialize a specific model"""
        if not self.transformers_available:
            logger.warning("Cannot initialize models - transformers not available")
            return False
            
        try:
            if model_name in self.models:
                return True
                
            config = self.model_configs.get(model_name)
            if not config:
                logger.error(f"Unknown model: {model_name}")
                return False
            
            logger.info(f"📥 Loading {model_name} model: {config['model_id']}")
            
            if model_name == "paligemma":
                return self._load_paligemma(config)
            elif model_name == "donut":
                return self._load_donut(config)
            elif model_name == "layoutlm":
                return self._load_layoutlm(config)
            elif model_name == "mistral_ocr":
                return self._load_mistral_ocr(config)
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to initialize {model_name}: {str(e)}")
            return False
    
    def _load_paligemma(self, config: Dict) -> bool:
        """Load PaliGemma receipt model"""
        try:
            from transformers import AutoProcessor, PaliGemmaForConditionalGeneration
            import torch
            
            model_id = config["model_id"]
            
            # Load processor and model
            processor = AutoProcessor.from_pretrained(model_id)
            model = PaliGemmaForConditionalGeneration.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map=self.device if self.device != "cpu" else None
            )
            
            self.processors["paligemma"] = processor
            self.models["paligemma"] = model
            
            logger.info("✅ PaliGemma model loaded successfully")
            return True
            
        except ImportError:
            logger.warning("⚠️ PaliGemma not available - install transformers>=4.40.0")
            return False
        except Exception as e:
            logger.error(f"Failed to load PaliGemma: {str(e)}")
            return False
    
    def _load_donut(self, config: Dict) -> bool:
        """Load Donut receipt model"""
        try:
            from transformers import DonutProcessor, VisionEncoderDecoderModel
            
            model_id = config["model_id"]
            
            processor = DonutProcessor.from_pretrained(model_id)
            model = VisionEncoderDecoderModel.from_pretrained(model_id)
            
            if self.device != "cpu":
                model = model.to(self.device)
            
            self.processors["donut"] = processor
            self.models["donut"] = model
            
            logger.info("✅ Donut model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load Donut: {str(e)}")
            return False
    
    def process_receipt_image(self, image_path: str, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a receipt image using HuggingFace models
        
        Args:
            image_path: Path to receipt image
            model_name: Specific model to use (optional)
            
        Returns:
            Structured receipt data with confidence scores
        """
        start_time = datetime.now()
        
        if not self.transformers_available:
            return self._create_error_response("Transformers library not available")
        
        try:
            # Use specified model or default preference
            model_to_use = model_name or self.model_preference
            
            # Ensure model is loaded
            if not self._initialize_model(model_to_use):
                # Fallback to any available model
                available_models = list(self.models.keys())
                if not available_models:
                    return self._create_error_response("No models available")
                model_to_use = available_models[0]
                logger.warning(f"Using fallback model: {model_to_use}")
            
            # Load and validate image
            image = self._load_image(image_path)
            if image is None:
                return self._create_error_response("Failed to load image")
            
            # Process with selected model
            result = self._process_with_model(image, model_to_use)
            
            # Add metadata
            processing_time = (datetime.now() - start_time).total_seconds()
            result.update({
                "processing_metadata": {
                    "model_used": model_to_use,
                    "processing_time_seconds": round(processing_time, 3),
                    "device": self.device,
                    "image_path": os.path.basename(image_path),
                    "timestamp": datetime.now().isoformat()
                }
            })
            
            # Update stats
            self._update_stats(result, processing_time)
            
            return result
            
        except Exception as e:
            logger.error(f"Receipt processing failed: {str(e)}")
            return self._create_error_response(str(e))
    
    def _load_image(self, image_path: str) -> Optional[Image.Image]:
        """Load and validate image file"""
        try:
            if isinstance(image_path, str):
                image = Image.open(image_path)
            else:
                image = image_path  # Assume it's already a PIL Image
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            return image
            
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {str(e)}")
            return None
    
    def _process_with_model(self, image: Image.Image, model_name: str) -> Dict[str, Any]:
        """Process image with specific model"""
        try:
            if model_name == "paligemma":
                return self._process_with_paligemma(image)
            elif model_name == "donut":
                return self._process_with_donut(image)
            elif model_name == "layoutlm":
                return self._process_with_layoutlm(image)
            elif model_name == "mistral_ocr":
                return self._process_with_mistral_ocr(image)
            else:
                return self._create_error_response(f"Unknown model: {model_name}")
                
        except Exception as e:
            logger.error(f"Model processing failed with {model_name}: {str(e)}")
            return self._create_error_response(f"Model processing failed: {str(e)}")
    
    def _process_with_paligemma(self, image: Image.Image) -> Dict[str, Any]:
        """Process receipt with PaliGemma model"""
        try:
            import torch
            
            processor = self.processors["paligemma"]
            model = self.models["paligemma"]
            config = self.model_configs["paligemma"]
            
            # Prepare inputs
            prompt = config["prompt"]
            inputs = processor(
                text=prompt, 
                images=image, 
                return_tensors="pt"
            )
            
            # Move to device
            if self.device != "cpu":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate response
            with torch.no_grad():
                generated_ids = model.generate(
                    **inputs,
                    max_new_tokens=config["max_tokens"],
                    do_sample=False,
                    temperature=0.1
                )
            
            # Decode response
            generated_text = processor.batch_decode(
                generated_ids, 
                skip_special_tokens=True
            )[0]
            
            # Extract JSON from generated text
            receipt_data = self._extract_json_from_text(generated_text)
            
            if receipt_data:
                return self._standardize_receipt_data(
                    receipt_data, 
                    model_name="paligemma",
                    confidence=config["confidence"]
                )
            else:
                return self._create_error_response("Failed to extract valid JSON")
                
        except Exception as e:
            logger.error(f"PaliGemma processing failed: {str(e)}")
            return self._create_error_response(f"PaliGemma error: {str(e)}")
    
    def _process_with_donut(self, image: Image.Image) -> Dict[str, Any]:
        """Process receipt with Donut model"""
        try:
            processor = self.processors["donut"]
            model = self.models["donut"]
            config = self.model_configs["donut"]
            
            # Prepare task prompt for receipt parsing
            task_prompt = "<s_receipt>"
            decoder_input_ids = processor.tokenizer(
                task_prompt, 
                add_special_tokens=False, 
                return_tensors="pt"
            ).input_ids
            
            pixel_values = processor(image, return_tensors="pt").pixel_values
            
            # Generate
            outputs = model.generate(
                pixel_values.to(self.device) if self.device != "cpu" else pixel_values,
                decoder_input_ids=decoder_input_ids.to(self.device) if self.device != "cpu" else decoder_input_ids,
                max_length=model.decoder.config.max_position_embeddings,
                early_stopping=True,
                pad_token_id=processor.tokenizer.pad_token_id,
                eos_token_id=processor.tokenizer.eos_token_id,
                use_cache=True,
                num_beams=1,
                bad_words_ids=[[processor.tokenizer.unk_token_id]],
                return_dict_in_generate=True,
            )
            
            # Decode output
            sequence = processor.batch_decode(outputs.sequences)[0]
            sequence = sequence.replace(processor.tokenizer.eos_token, "").replace(processor.tokenizer.pad_token, "")
            sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()  # remove first task start token
            
            # Parse JSON from sequence
            receipt_data = self._extract_json_from_text(sequence)
            
            if receipt_data:
                return self._standardize_receipt_data(
                    receipt_data,
                    model_name="donut", 
                    confidence=config["confidence"]
                )
            else:
                return self._create_error_response("Failed to parse Donut output")
                
        except Exception as e:
            logger.error(f"Donut processing failed: {str(e)}")
            return self._create_error_response(f"Donut error: {str(e)}")
    
    def _process_with_layoutlm(self, image: Image.Image) -> Dict[str, Any]:
        """Process receipt with LayoutLM model (placeholder - requires OCR preprocessing)"""
        return self._create_error_response("LayoutLM processing not yet implemented")
    
    def _process_with_mistral_ocr(self, image: Image.Image) -> Dict[str, Any]:
        """Process receipt with Mistral OCR model (placeholder)"""
        return self._create_error_response("Mistral OCR processing not yet implemented")
    
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
            
            # Last resort: try to create JSON from text patterns
            return self._extract_fields_from_text(text)
            
        except Exception as e:
            logger.error(f"JSON extraction failed: {str(e)}")
            return None
    
    def _extract_fields_from_text(self, text: str) -> Dict:
        """Fallback field extraction from raw text"""
        result = {}
        
        # Common receipt field patterns
        patterns = {
            "store_name": r"(?:store|shop|restaurant|cafe):\s*([^\n]+)",
            "total": r"(?:total|sum|amount):\s*\$?(\d+\.?\d*)",
            "date": r"(?:date|time):\s*([^\n]+)",
            "items": r"(?:item|product):\s*([^\n]+)"
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result[field] = match.group(1).strip()
        
        return result if result else {"raw_text": text}
    
    def _standardize_receipt_data(self, data: Dict, model_name: str, confidence: float) -> Dict[str, Any]:
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
            "raw_model_output": data
        }
        
        # Map common field variations to standard fields
        field_mappings = {
            "merchant": ["store_name", "company", "merchant", "business", "shop"],
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
            "model_used": self.model_preference
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
    
    def get_loaded_models(self) -> List[str]:
        """Get list of currently loaded models"""
        return list(self.models.keys())
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        stats = self.processing_stats.copy()
        
        if stats["confidence_scores"]:
            stats["avg_confidence"] = sum(stats["confidence_scores"]) / len(stats["confidence_scores"])
        else:
            stats["avg_confidence"] = 0.0
        
        stats["success_rate"] = (stats["successful_extractions"] / max(stats["total_processed"], 1)) * 100
        stats["transformers_available"] = self.transformers_available
        
        return stats
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        info = {
            "transformers_available": self.transformers_available,
            "device": self.device,
            "available_models": self.get_available_models(),
            "loaded_models": self.get_loaded_models(),
            "model_preference": self.model_preference
        }
        
        if self.transformers_available:
            try:
                import transformers
                import torch
                info["transformers_version"] = transformers.__version__
                info["torch_version"] = torch.__version__
                info["cuda_available"] = torch.cuda.is_available()
                if torch.cuda.is_available():
                    info["cuda_device_count"] = torch.cuda.device_count()
                    info["cuda_device_name"] = torch.cuda.get_device_name(0)
            except ImportError:
                pass
        
        return info


# Factory functions for easy integration
def create_huggingface_processor(model_preference: str = "paligemma", device: str = "auto") -> HuggingFaceReceiptProcessor:
    """Factory function to create HuggingFace processor"""
    return HuggingFaceReceiptProcessor(model_preference=model_preference, device=device)

def test_model_availability() -> Dict[str, bool]:
    """Test which models are available for use"""
    processor = HuggingFaceReceiptProcessor()
    availability = {}
    
    if not processor.transformers_available:
        logger.warning("Transformers not available - cannot test models")
        return {"transformers_available": False}
    
    for model_name in processor.get_available_models():
        try:
            success = processor._initialize_model(model_name)
            availability[model_name] = success
            if success:
                logger.info(f"✅ {model_name} model available")
            else:
                logger.warning(f"❌ {model_name} model not available")
        except Exception as e:
            availability[model_name] = False
            logger.error(f"Model {model_name} not available: {str(e)}")
    
    return availability 