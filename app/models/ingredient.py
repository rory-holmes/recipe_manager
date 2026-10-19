from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field

class RecipeIngredient(BaseModel):
    original_text: str
    canonical_ingredient_id: Optional[str] = None  # e.g., "onion_yellow"
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None                     # e.g., "g", "ml", "cup", "clove"
    ingredient_form: Optional[str] = None          # e.g., "fresh", "frozen", "canned", "dried"
    preparation: Optional[str] = None              # e.g., "diced", "thinly_sliced", "caramelized"
    is_quantity_estimated: bool = False            # Flagged if derived from vague quantities
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

class CanonicalIngredient(BaseModel):
    id: str                                        # e.g., "onion_yellow"
    default_slug: str
    category: str                                  # e.g., "produce", "pantry", "dairy"
    storage_life_days: int                         # Perishability baseline
    aliases: List[str] = Field(default_factory=list)

class FeedbackEvent(BaseModel):
    event_id: str
    recipe_id: str
    event_type: str  # "EXPLICIT_RATING", "THUMBS_UP", "ACCEPTED_FOR_WEEK", "SKIPPED", "DISCARDED"
    rating_value: Optional[float] = None  # 1.0 to 5.0 for explicit ratings; +1/-1 for thumbs
    context_tags: List[str] = Field(default_factory=list)
    timestamp_utc: str