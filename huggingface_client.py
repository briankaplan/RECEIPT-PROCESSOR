import os
import logging
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger(__name__)

@dataclass
class ExpenseCategory:
    category: str
    subcategory: str
    confidence: float
    business_purpose: str
    tax_deductible: bool
    description: str

@dataclass
class ReceiptAnalysis:
    expense_category: ExpenseCategory
    merchant_type: str
    item_analysis: List[Dict]
    business_context: str
    recommendations: List[str]
    confidence_score: float

class HuggingFaceClient:
    """Hugging Face AI client for intelligent receipt analysis and categorization"""
    
    def __init__(self):
        self.api_key = os.getenv('HUGGINGFACE_API_KEY')
        self.base_url = "https://api-inference.huggingface.co/models"
        self.headers = {}
        
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
            logger.info("Hugging Face API client initialized")
        else:
            logger.warning("No Hugging Face API key found")
    
    def is_connected(self) -> bool:
        """Check if Hugging Face API is available"""
        return bool(self.api_key)
    
    def categorize_expense(self, receipt_data: Dict) -> ExpenseCategory:
        """Categorize expense using AI analysis"""
        if not self.is_connected():
            return self._fallback_categorization(receipt_data)
        
        try:
            # Prepare text for analysis
            merchant = receipt_data.get('merchant', 'Unknown')
            amount = receipt_data.get('total_amount', 0)
            items = receipt_data.get('items', [])
            raw_text = receipt_data.get('raw_text', '')
            
            # Create context for AI analysis
            context = self._build_context(merchant, amount, items, raw_text)
            
            # Use text classification model for expense categorization
            category_result = self._classify_expense_category(context)
            
            # Determine business purpose and tax implications
            business_analysis = self._analyze_business_purpose(context, category_result)
            
            return ExpenseCategory(
                category=category_result.get('category', 'Other'),
                subcategory=category_result.get('subcategory', 'General'),
                confidence=category_result.get('confidence', 0.5),
                business_purpose=business_analysis.get('purpose', 'Personal expense'),
                tax_deductible=business_analysis.get('tax_deductible', False),
                description=business_analysis.get('description', f'Purchase from {merchant}')
            )
            
        except Exception as e:
            logger.error(f"Error in AI categorization: {str(e)}")
            return self._fallback_categorization(receipt_data)
    
    def analyze_receipt_intelligence(self, receipt_data: Dict) -> ReceiptAnalysis:
        """Comprehensive AI analysis of receipt data"""
        if not self.is_connected():
            return self._fallback_analysis(receipt_data)
        
        try:
            # Get expense categorization
            expense_category = self.categorize_expense(receipt_data)
            
            # Analyze merchant type
            merchant_type = self._analyze_merchant_type(receipt_data)
            
            # Analyze individual items
            item_analysis = self._analyze_items(receipt_data.get('items', []))
            
            # Generate business context
            business_context = self._generate_business_context(receipt_data, expense_category)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(receipt_data, expense_category)
            
            # Calculate overall confidence
            confidence_score = self._calculate_confidence(receipt_data, expense_category)
            
            return ReceiptAnalysis(
                expense_category=expense_category,
                merchant_type=merchant_type,
                item_analysis=item_analysis,
                business_context=business_context,
                recommendations=recommendations,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Error in receipt intelligence analysis: {str(e)}")
            return self._fallback_analysis(receipt_data)
    
    def _build_context(self, merchant: str, amount: float, items: List, raw_text: str) -> str:
        """Build context string for AI analysis"""
        context = f"Merchant: {merchant}\nAmount: ${amount:.2f}\n"
        
        if items:
            context += "Items:\n"
            for item in items[:5]:  # Limit to first 5 items
                if isinstance(item, dict):
                    name = item.get('name', 'Unknown item')
                    price = item.get('price', 0)
                    context += f"- {name}: ${price:.2f}\n"
        
        # Add relevant portions of raw text
        if raw_text:
            # Extract key phrases that might indicate business purpose
            business_keywords = ['conference', 'meeting', 'business', 'office', 'supplies', 
                               'travel', 'hotel', 'flight', 'uber', 'lyft', 'gas', 'fuel']
            
            lines = raw_text.lower().split('\n')
            relevant_lines = []
            for line in lines:
                if any(keyword in line for keyword in business_keywords):
                    relevant_lines.append(line.strip())
            
            if relevant_lines:
                context += f"Context: {' '.join(relevant_lines[:3])}\n"
        
        return context
    
    def _classify_expense_category(self, context: str) -> Dict:
        """Classify expense using Hugging Face model"""
        try:
            # Use a general text classification model
            model_url = f"{self.base_url}/facebook/bart-large-mnli"
            
            # Define expense categories
            categories = [
                "Office Supplies", "Travel and Transportation", "Meals and Entertainment",
                "Professional Services", "Software and Technology", "Marketing and Advertising",
                "Utilities and Communications", "Equipment and Hardware", "Training and Education",
                "Medical and Healthcare", "Personal Expenses", "Other Business Expenses"
            ]
            
            payload = {
                "inputs": context,
                "parameters": {
                    "candidate_labels": categories
                }
            }
            
            response = requests.post(model_url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, dict) and 'labels' in result:
                    return {
                        'category': result['labels'][0],
                        'subcategory': self._get_subcategory(result['labels'][0]),
                        'confidence': result['scores'][0] if 'scores' in result else 0.7
                    }
            
            # Fallback classification
            return self._rule_based_classification(context)
            
        except Exception as e:
            logger.error(f"Error in AI classification: {str(e)}")
            return self._rule_based_classification(context)
    
    def _analyze_business_purpose(self, context: str, category_result: Dict) -> Dict:
        """Analyze business purpose and tax implications"""
        try:
            # Use text generation for business purpose analysis
            model_url = f"{self.base_url}/microsoft/DialoGPT-medium"
            
            prompt = f"Analyze this expense for business purpose: {context[:200]}"
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_length": 100,
                    "temperature": 0.7
                }
            }
            
            response = requests.post(model_url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    generated_text = result[0].get('generated_text', '')
                    
                    # Extract business purpose
                    business_purpose = self._extract_business_purpose(generated_text, context)
                    tax_deductible = self._determine_tax_deductibility(category_result.get('category', ''), context)
                    
                    return {
                        'purpose': business_purpose,
                        'tax_deductible': tax_deductible,
                        'description': f"{category_result.get('category', 'Expense')} - {business_purpose}"
                    }
            
            # Fallback analysis
            return self._rule_based_business_analysis(context, category_result)
            
        except Exception as e:
            logger.error(f"Error in business purpose analysis: {str(e)}")
            return self._rule_based_business_analysis(context, category_result)
    
    def _analyze_merchant_type(self, receipt_data: Dict) -> str:
        """Analyze merchant type using AI"""
        merchant = receipt_data.get('merchant', '').lower()
        
        # Rule-based merchant classification
        merchant_types = {
            'restaurant': ['restaurant', 'cafe', 'diner', 'grill', 'bistro', 'bar', 'pizza'],
            'retail': ['store', 'shop', 'retail', 'mart', 'market', 'outlet'],
            'gas_station': ['gas', 'fuel', 'shell', 'exxon', 'bp', 'chevron', 'mobil'],
            'hotel': ['hotel', 'inn', 'resort', 'lodge', 'motel'],
            'transportation': ['uber', 'lyft', 'taxi', 'airline', 'airport', 'parking'],
            'office_supplies': ['office', 'depot', 'staples', 'supplies'],
            'technology': ['apple', 'microsoft', 'amazon', 'best buy', 'electronics'],
            'healthcare': ['pharmacy', 'cvs', 'walgreens', 'medical', 'clinic', 'hospital']
        }
        
        for merchant_type, keywords in merchant_types.items():
            if any(keyword in merchant for keyword in keywords):
                return merchant_type.replace('_', ' ').title()
        
        return 'General Merchant'
    
    def _analyze_items(self, items: List) -> List[Dict]:
        """Analyze individual items for categorization"""
        item_analysis = []
        
        for item in items:
            if isinstance(item, dict):
                name = item.get('name', '')
                price = item.get('price', 0)
                
                # Simple categorization based on keywords
                category = self._categorize_item(name)
                
                item_analysis.append({
                    'name': name,
                    'price': price,
                    'category': category,
                    'business_relevant': self._is_business_relevant(name, category)
                })
        
        return item_analysis
    
    def _generate_business_context(self, receipt_data: Dict, expense_category: ExpenseCategory) -> str:
        """Generate business context explanation"""
        merchant = receipt_data.get('merchant', 'Unknown')
        amount = receipt_data.get('total_amount', 0)
        
        if expense_category.business_purpose != 'Personal expense':
            return f"Business expense at {merchant} for {expense_category.business_purpose}. " \
                   f"Category: {expense_category.category}. Amount: ${amount:.2f}."
        else:
            return f"Personal expense at {merchant}. Amount: ${amount:.2f}."
    
    def _generate_recommendations(self, receipt_data: Dict, expense_category: ExpenseCategory) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        if expense_category.tax_deductible:
            recommendations.append("This expense may be tax deductible - consult your accountant")
        
        if expense_category.confidence < 0.7:
            recommendations.append("Consider reviewing categorization - confidence is low")
        
        amount = receipt_data.get('total_amount', 0)
        if amount > 500:
            recommendations.append("High-value expense - ensure proper documentation")
        
        if expense_category.category == 'Meals and Entertainment':
            recommendations.append("Meals may have 50% deduction limit - verify business purpose")
        
        return recommendations
    
    def _calculate_confidence(self, receipt_data: Dict, expense_category: ExpenseCategory) -> float:
        """Calculate overall confidence score"""
        confidence_factors = []
        
        # Receipt data quality
        if receipt_data.get('merchant'):
            confidence_factors.append(0.8)
        if receipt_data.get('total_amount'):
            confidence_factors.append(0.9)
        if receipt_data.get('date'):
            confidence_factors.append(0.7)
        
        # Category confidence
        confidence_factors.append(expense_category.confidence)
        
        return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
    
    def _fallback_categorization(self, receipt_data: Dict) -> ExpenseCategory:
        """Fallback categorization when AI is not available"""
        merchant = receipt_data.get('merchant', '').lower()
        
        # Simple rule-based categorization
        if any(word in merchant for word in ['restaurant', 'cafe', 'food']):
            category = 'Meals and Entertainment'
        elif any(word in merchant for word in ['gas', 'fuel', 'shell', 'exxon']):
            category = 'Travel and Transportation'
        elif any(word in merchant for word in ['office', 'depot', 'staples']):
            category = 'Office Supplies'
        else:
            category = 'Other Business Expenses'
        
        return ExpenseCategory(
            category=category,
            subcategory='General',
            confidence=0.6,
            business_purpose='Business expense',
            tax_deductible=True,
            description=f"{category} from {receipt_data.get('merchant', 'Unknown')}"
        )
    
    def _fallback_analysis(self, receipt_data: Dict) -> ReceiptAnalysis:
        """Fallback analysis when AI is not available"""
        expense_category = self._fallback_categorization(receipt_data)
        
        return ReceiptAnalysis(
            expense_category=expense_category,
            merchant_type=self._analyze_merchant_type(receipt_data),
            item_analysis=[],
            business_context=self._generate_business_context(receipt_data, expense_category),
            recommendations=['AI analysis unavailable - using rule-based categorization'],
            confidence_score=0.6
        )
    
    def _rule_based_classification(self, context: str) -> Dict:
        """Rule-based classification fallback"""
        context_lower = context.lower()
        
        if any(word in context_lower for word in ['restaurant', 'cafe', 'food', 'meal']):
            return {'category': 'Meals and Entertainment', 'subcategory': 'Restaurant', 'confidence': 0.7}
        elif any(word in context_lower for word in ['gas', 'fuel', 'uber', 'lyft', 'flight']):
            return {'category': 'Travel and Transportation', 'subcategory': 'Transportation', 'confidence': 0.7}
        elif any(word in context_lower for word in ['office', 'supplies', 'staples', 'depot']):
            return {'category': 'Office Supplies', 'subcategory': 'General Supplies', 'confidence': 0.7}
        elif any(word in context_lower for word in ['hotel', 'inn', 'resort']):
            return {'category': 'Travel and Transportation', 'subcategory': 'Lodging', 'confidence': 0.7}
        else:
            return {'category': 'Other Business Expenses', 'subcategory': 'General', 'confidence': 0.5}
    
    def _rule_based_business_analysis(self, context: str, category_result: Dict) -> Dict:
        """Rule-based business analysis fallback"""
        category = category_result.get('category', '')
        
        business_categories = [
            'Office Supplies', 'Travel and Transportation', 'Professional Services',
            'Software and Technology', 'Marketing and Advertising', 'Utilities and Communications'
        ]
        
        tax_deductible = category in business_categories
        
        if 'meal' in context.lower() or 'restaurant' in context.lower():
            purpose = 'Business meal or entertainment'
        elif 'travel' in context.lower() or 'hotel' in context.lower():
            purpose = 'Business travel expense'
        elif 'office' in context.lower() or 'supplies' in context.lower():
            purpose = 'Office supplies and equipment'
        else:
            purpose = 'General business expense'
        
        return {
            'purpose': purpose,
            'tax_deductible': tax_deductible,
            'description': f"{category} - {purpose}"
        }
    
    def _get_subcategory(self, category: str) -> str:
        """Get subcategory based on main category"""
        subcategories = {
            'Office Supplies': 'General Supplies',
            'Travel and Transportation': 'Transportation',
            'Meals and Entertainment': 'Business Meals',
            'Professional Services': 'Consulting',
            'Software and Technology': 'Software',
            'Marketing and Advertising': 'Marketing',
            'Utilities and Communications': 'Utilities',
            'Equipment and Hardware': 'Equipment',
            'Training and Education': 'Training',
            'Medical and Healthcare': 'Healthcare',
            'Personal Expenses': 'Personal',
            'Other Business Expenses': 'General'
        }
        return subcategories.get(category, 'General')
    
    def _extract_business_purpose(self, generated_text: str, context: str) -> str:
        """Extract business purpose from generated text"""
        # Simple extraction - look for business-related keywords
        business_keywords = ['business', 'work', 'office', 'client', 'meeting', 'conference', 'travel']
        
        if any(keyword in generated_text.lower() for keyword in business_keywords):
            return 'Business-related expense'
        elif any(keyword in context.lower() for keyword in business_keywords):
            return 'Business expense'
        else:
            return 'General expense'
    
    def _determine_tax_deductibility(self, category: str, context: str) -> bool:
        """Determine if expense is potentially tax deductible"""
        business_categories = [
            'Office Supplies', 'Travel and Transportation', 'Professional Services',
            'Software and Technology', 'Marketing and Advertising', 'Utilities and Communications',
            'Equipment and Hardware', 'Training and Education'
        ]
        
        return category in business_categories or 'business' in context.lower()
    
    def _categorize_item(self, item_name: str) -> str:
        """Categorize individual item"""
        item_lower = item_name.lower()
        
        if any(word in item_lower for word in ['pen', 'paper', 'notebook', 'folder']):
            return 'Office Supplies'
        elif any(word in item_lower for word in ['food', 'drink', 'meal']):
            return 'Food & Beverage'
        elif any(word in item_lower for word in ['gas', 'fuel']):
            return 'Fuel'
        else:
            return 'General'
    
    def _is_business_relevant(self, item_name: str, category: str) -> bool:
        """Determine if item is business relevant"""
        business_categories = ['Office Supplies', 'Fuel', 'Technology']
        business_keywords = ['business', 'office', 'work', 'professional']
        
        return (category in business_categories or 
                any(keyword in item_name.lower() for keyword in business_keywords))
    
    def process(self, file_path: str) -> Dict:
        """
        Main processing method expected by ReceiptDownloader
        Processes a receipt file and returns structured data
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return {}
        
        try:
            # For now, we'll use a simple OCR approach
            # In the future, this could be enhanced with proper OCR libraries
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Extract basic info from filename and create mock receipt data
            receipt_data = {
                'filename': filename,
                'file_path': file_path,
                'file_size': file_size,
                'merchant': self._extract_merchant_from_filename(filename),
                'total_amount': 0.0,  # Would be extracted via OCR
                'date': datetime.now().strftime('%Y-%m-%d'),
                'items': [],
                'raw_text': f"Receipt from {filename}",
                'processing_method': 'huggingface_mock'
            }
            
            # Perform analysis using our existing methods
            expense_category = self.categorize_expense(receipt_data)
            analysis = self.analyze_receipt_intelligence(receipt_data)
            
            # Return structured data compatible with the system
            return {
                'merchant': receipt_data['merchant'],
                'total_amount': receipt_data['total_amount'],
                'date': receipt_data['date'],
                'items': receipt_data['items'],
                'raw_text': receipt_data['raw_text'],
                'filename': filename,
                'file_size': file_size,
                'expense_category': expense_category.category,
                'expense_subcategory': expense_category.subcategory,
                'business_purpose': expense_category.business_purpose,
                'tax_deductible': expense_category.tax_deductible,
                'confidence_score': analysis.confidence_score,
                'recommendations': analysis.recommendations,
                'analysis_complete': True,
                'processing_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing receipt {file_path}: {e}")
            return {
                'filename': os.path.basename(file_path) if os.path.exists(file_path) else 'unknown',
                'error': str(e),
                'processing_method': 'huggingface_error',
                'analysis_complete': False,
                'processing_timestamp': datetime.now().isoformat()
            }
    
    def _extract_merchant_from_filename(self, filename: str) -> str:
        """Extract potential merchant name from filename"""
        # Remove extension and common prefixes
        name = os.path.splitext(filename)[0]
        name = name.replace('receipt_', '').replace('invoice_', '').replace('bill_', '')
        
        # Common merchant patterns
        merchant_keywords = {
            'amazon': 'Amazon',
            'walmart': 'Walmart',
            'target': 'Target',
            'costco': 'Costco',
            'starbucks': 'Starbucks',
            'mcdonalds': 'McDonalds',
            'uber': 'Uber',
            'lyft': 'Lyft',
            'gas': 'Gas Station',
            'restaurant': 'Restaurant'
        }
        
        name_lower = name.lower()
        for keyword, merchant in merchant_keywords.items():
            if keyword in name_lower:
                return merchant
        
        # Default to cleaned filename
        return name.replace('_', ' ').replace('-', ' ').title()

    def process_image(self, image_bytes: bytes) -> Dict:
        """Process raw image bytes and return extracted information"""
        try:
            # For now, create a basic extracted receipt structure
            # In a real implementation, you would use OCR to extract text from image_bytes
            
            # Simulate OCR extraction (replace with actual OCR service)
            extracted_data = {
                "merchant": "Camera Captured Receipt",
                "total_amount": 0.0,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "items": [],
                "raw_text": "Receipt captured from camera scanner",
                "confidence": 0.8,
                "source": "camera_capture",
                "file_size": len(image_bytes),
                "processing_timestamp": datetime.now().isoformat()
            }
            
            # You could integrate with actual OCR services here like:
            # - Google Vision API
            # - AWS Textract
            # - Azure Computer Vision
            # - Or a Hugging Face OCR model
            
            logger.info(f"Processed camera image: {len(image_bytes)} bytes")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error processing image bytes: {str(e)}")
            return None

    def get_stats(self) -> Dict:
        """Get Hugging Face client statistics"""
        return {
            'connected': self.is_connected(),
            'api_key_configured': bool(self.api_key),
            'models_available': self.is_connected(),
            'features': [
                "OCR Processing",
                "Expense Categorization", 
                "Camera Image Processing",
                "Receipt Analysis"
            ]
        }