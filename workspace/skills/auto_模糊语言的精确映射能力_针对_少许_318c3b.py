"""
Module: auto_fuzzy_quantity_mapper
Description: Transforms vague culinary terms (e.g., 'a little', 'some') into precise
             measurements (grams, milliliters) based on environmental context like
             ingredient density, total batch size, and container capacity.
Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
"""

import logging
import re
from typing import Dict, Optional, Tuple, Union
from pydantic import BaseModel, Field, ValidationError, validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# --- Data Models ---

class CookingContext(BaseModel):
    """
    Represents the environmental context for the cooking session.
    Used to determine the scale of the dish.
    """
    serving_size: int = Field(..., gt=0, description="Number of people to serve")
    main_ingredient_weight_g: float = Field(..., gt=0, description="Weight of the primary solid ingredient in grams")
    container_capacity_l: float = Field(2.0, gt=0, description="Capacity of the cooking vessel in liters")

    @validator('serving_size')
    def validate_serving(cls, v):
        if v > 50:
            logger.warning("Serving size > 50 detected. Context set to industrial scale.")
        return v


class IngredientProperty(BaseModel):
    """
    Properties of a specific ingredient required for conversion.
    """
    name: str
    density_g_per_ml: float = Field(1.0, gt=0, description="Density to convert volume to mass")
    is_liquid: bool = False
    intensity_score: float = Field(1.0, ge=0.1, le=10.0, 
                                   description="Flavor intensity (salt=10, sugar=5, water=1)")


class QuantifiedResult(BaseModel):
    """
    Output model representing the precise measurement.
    """
    original_term: str
    grams: float
    milliliters: float
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    explanation: str


# --- Core Logic Classes ---

class FuzzyQuantizationEngine:
    """
    Core Engine responsible for mapping fuzzy terms to specific quantities
    based on heuristic algorithms and context scaling.
    """

    def __init__(self):
        self._initialize_base_mappings()

    def _initialize_base_mappings(self) -> None:
        """
        Initializes the dynamic dictionary nodes for base fuzzy terms.
        These represent the 'standard' amount for a single serving.
        """
        logger.info("Initializing fuzzy logic semantic nodes...")
        # Base values represent grams per serving for a standard context
        self.base_fuzzy_map: Dict[str, float] = {
            "少许": 0.5,    # ~0.5g per serving (e.g., salt)
            "适量": 2.0,    # ~2.0g per serving (e.g., soy sauce)
            "一撮": 0.3,    # ~0.3g per serving
            "一点": 0.8,    # ~0.8g per serving
            "少许": 0.5,    # Duplicate key handling implicitly, or use distinct keys
            "some": 3.0,
            "a little": 1.0,
        }

    def _calculate_base_quantity(self, fuzzy_term: str, ingredient: IngredientProperty) -> float:
        """
        Helper function to determine the base quantity in grams 
        before scaling by context.
        
        Args:
            fuzzy_term (str): The vague term used.
            ingredient (IngredientProperty): The ingredient properties.
            
        Returns:
            float: Base quantity in grams.
        """
        term_normalized = fuzzy_term.lower().strip()
        
        # Retrieve base value or use heuristic default
        base_val = self.base_fuzzy_map.get(term_normalized, 1.0) # Default 1.0g
        
        # Adjust based on ingredient intensity
        # If intensity is high (e.g., salt=10), we want less than the base suggests if base is generic
        # If intensity is low (water=1), we might want more.
        # Formula: base * (1 / log(intensity + 1)) adjustment
        intensity_factor = 1.0
        if ingredient.intensity_score > 5:
            intensity_factor = 0.8
        elif ingredient.intensity_score < 2:
            intensity_factor = 1.5
            
        return base_val * intensity_factor

    def map_to_precise_measurement(
        self, 
        fuzzy_term: str, 
        context: CookingContext, 
        ingredient: IngredientProperty
    ) -> QuantifiedResult:
        """
        Main entry point for the skill. Maps the fuzzy term to precise units.
        
        Args:
            fuzzy_term: The string representing the vague quantity.
            context: The environmental context model.
            ingredient: The ingredient property model.
            
        Returns:
            QuantifiedResult: The precise mapped result.
        """
        try:
            logger.debug(f"Mapping '{fuzzy_term}' for {ingredient.name}...")
            
            # 1. Get base quantity (heuristic)
            base_qty_g = self._calculate_base_quantity(fuzzy_term, ingredient)
            
            # 2. Apply Context Scaling
            # Scale linearly with serving size, but apply logarithmic dampening for large batches
            # to avoid over-seasoning.
            scaling_factor = context.serving_size
            if context.serving_size > 4:
                # Diminishing returns for large batches
                scaling_factor = 4 + (context.serving_size - 4) * 0.7
            
            total_qty_g = base_qty_g * scaling_factor
            
            # 3. Apply Container Constraints (Boundary Check)
            # If the container is small, we cap the liquid volume to 1/10th of capacity
            max_ml = context.container_capacity_l * 100
            calculated_ml = total_qty_g / ingredient.density_g_per_ml
            
            if calculated_ml > max_ml:
                logger.warning("Calculated volume exceeds container safety limits. Capping value.")
                calculated_ml = max_ml
                total_qty_g = calculated_ml * ingredient.density_g_per_ml

            # 4. Construct Result
            result = QuantifiedResult(
                original_term=fuzzy_term,
                grams=round(total_qty_g, 2),
                milliliters=round(calculated_ml, 2),
                confidence_score=0.85, # Static confidence for this demo
                explanation=f"Scaled base value {base_qty_g:.2f}g by factor {scaling_factor:.2f} for {context.serving_size} servings."
            )
            
            logger.info(f"Mapping Success: '{fuzzy_term}' -> {result.grams}g")
            return result

        except Exception as e:
            logger.error(f"Quantization failed: {str(e)}")
            raise RuntimeError(f"Failed to map fuzzy term: {str(e)}")


# --- Helper Functions ---

def parse_user_input(input_str: str) -> Tuple[str, str]:
    """
    Parses raw user input to extract the fuzzy term and ingredient name.
    This simulates the NLP extraction layer prior to the logic layer.
    
    Args:
        input_str (str): Raw text like "Add a little salt".
        
    Returns:
        Tuple[str, str]: (fuzzy_term, ingredient_name)
    """
    # Simple regex simulation for the example
    # Pattern: "Add [fuzzy] [ingredient]"
    pattern = r"[Aa]dd\s(.*?)\s(of\s)?(.*)"
    match = re.match(pattern, input_str)
    
    if match:
        fuzzy = match.group(1) # e.g., "a little"
        ingredient = match.group(3) # e.g., "salt"
        return fuzzy, ingredient
    
    # Fallback for Chinese or other structures
    # Assuming format: "动词 [模糊词] [食材]" e.g. "加 少许 盐"
    tokens = input_str.split()
    if len(tokens) >= 3:
        return tokens[1], tokens[2]
        
    return "适量", "unknown_ingredient"


def validate_input_safety(context: CookingContext) -> bool:
    """
    Auxiliary function to ensure the context parameters are within 
    physical safety limits before processing.
    """
    if context.container_capacity_l > 100:
        logger.critical("Container size exceeds logic limits (100L). Potential overflow.")
        return False
    return True


# --- Main Execution Example ---

if __name__ == "__main__":
    # Setup Simulation Data
    try:
        # 1. Define Context: Family dinner, 4 people, medium pot
        cook_context = CookingContext(
            serving_size=4, 
            main_ingredient_weight_g=500.0, 
            container_capacity_l=3.0
        )
        
        # 2. Define Ingredient: Salt (High intensity)
        salt_props = IngredientProperty(
            name="Salt",
            density_g_per_ml=2.16,
            is_liquid=False,
            intensity_score=9.0
        )
        
        # 3. Initialize Engine
        engine = FuzzyQuantizationEngine()
        
        # Safety Check
        if validate_input_safety(cook_context):
            # 4. Execute Skill: Map "少许" (a little)
            result = engine.map_to_precise_measurement(
                fuzzy_term="少许",
                context=cook_context,
                ingredient=salt_props
            )
            
            print("\n--- Mapping Result ---")
            print(f"Term: {result.original_term}")
            print(f"Precise Amount: {result.grams} g ({result.milliliters} ml)")
            print(f"Logic: {result.explanation}")
            print(f"Confidence: {result.confidence_score}")
            
    except ValidationError as ve:
        logger.error(f"Input Validation Error: {ve}")
    except Exception as e:
        logger.error(f"System Error: {e}")