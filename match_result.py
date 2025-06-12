from typing import Optional, Dict, Any

class MatchResult:
    def __init__(
        self,
        receipt_id: str,
        transaction_id: str,
        confidence: float,
        reasoning: str,
        match_type: str = "automatic",
        receipt: Optional[Dict[str, Any]] = None,
        transaction: Optional[Dict[str, Any]] = None
    ):
        self.receipt_id = receipt_id
        self.transaction_id = transaction_id
        self.confidence = confidence
        self.reasoning = reasoning
        self.match_type = match_type
        self.receipt = receipt
        self.transaction = transaction

    def to_dict(self) -> dict:
        return {
            "receipt_id": self.receipt_id,
            "transaction_id": self.transaction_id,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "match_type": self.match_type,
            "score": self.confidence,  # for backward compatibility
            "match_reason": self.reasoning,  # for backward compatibility
            "receipt": self.receipt,
            "transaction": self.transaction
        }

def standardize_match_data(matches):
    """Convert any match format to standardized format (dicts with required fields)."""
    standardized = []
    for match in matches:
        if isinstance(match, dict):
            std_match = {
                "receipt_id": match.get("receipt_id") or match.get("receipt", {}).get("id") or match.get("receipt", {}).get("message_id"),
                "transaction_id": match.get("transaction_id") or match.get("transaction", {}).get("id"),
                "confidence": match.get("confidence") or match.get("score", 0),
                "reasoning": match.get("reasoning") or match.get("match_reason", ""),
                "match_type": match.get("match_type", "automatic"),
                "receipt": match.get("receipt"),
                "transaction": match.get("transaction")
            }
        else:
            std_match = match.to_dict() if hasattr(match, 'to_dict') else match
        standardized.append(std_match)
    return standardized 