"""
Module: auto_真实节点_认知自洽_验证_微小闭环_的_a7fd17

Description:
    This module implements a dynamic cognitive micro-network for decision-making in 
    extremely narrow scenarios. It demonstrates AGI capability to construct temporary 
    cognitive networks without explicit skill nodes, specifically for food recommendation
    that maximizes dopamine release while considering nutritional balance and user preferences.

Key Features:
    - Dynamic node assembly (nutrition, taste history, geolocation, time)
    - Multi-factor decision optimization
    - Real-time constraint validation
    - Self-contained micro-cognitive loop

Author: AGI System
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

# Configure module-level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MealType(Enum):
    """Enumeration of possible meal types based on time of day."""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


@dataclass
class UserProfile:
    """User preference and historical data container."""
    user_id: str
    taste_history: Dict[str, float]  # food_item: preference_score (0-1)
    dietary_restrictions: List[str]
    location: Tuple[float, float]  # (latitude, longitude)
    current_time: datetime
    health_goals: List[str]


@dataclass
class FoodItem:
    """Nutritional and sensory properties of food items."""
    name: str
    nutrition_score: float  # 0-1 (higher is healthier)
    dopamine_potential: float  # 0-1 (estimated pleasure response)
    available_nearby: bool
    prep_time_minutes: int
    suitable_meals: List[MealType]


class CognitiveMicroNetwork:
    """
    A temporary cognitive network that assembles knowledge nodes dynamically
    to solve narrow decision problems.
    """
    
    def __init__(self, user_profile: UserProfile, food_database: List[FoodItem]):
        """
        Initialize the cognitive network with user context and food knowledge.
        
        Args:
            user_profile: Contains user preferences and constraints
            food_database: Available food items with nutritional data
        """
        self.user_profile = user_profile
        self.food_db = food_database
        self.active_nodes: Dict[str, float] = {}  # node_name: relevance_weight
        logger.info("Cognitive micro-network initialized for user %s", user_profile.user_id)
    
    def _determine_meal_type(self) -> MealType:
        """Determine current meal type based on time of day."""
        current_time = self.user_profile.current_time.time()
        
        if time(6, 0) <= current_time <= time(10, 0):
            return MealType.BREAKFAST
        elif time(11, 0) <= current_time <= time(14, 0):
            return MealType.LUNCH
        elif time(17, 0) <= current_time <= time(20, 0):
            return MealType.DINNER
        else:
            return MealType.SNACK
    
    def _activate_cognitive_nodes(self) -> None:
        """
        Dynamically activate relevant cognitive nodes based on current context.
        This simulates the AGI's ability to assemble knowledge components.
        """
        # Core cognitive nodes
        self.active_nodes = {
            'nutrition': 0.3,
            'taste_preference': 0.4,
            'dopamine_prediction': 0.5,
            'time_constraint': 0.2,
            'geolocation': 0.1
        }
        
        # Adjust node weights based on health goals
        if "weight_loss" in self.user_profile.health_goals:
            self.active_nodes['nutrition'] = 0.5
            self.active_nodes['dopamine_prediction'] = 0.3
        elif "muscle_gain" in self.user_profile.health_goals:
            self.active_nodes['nutrition'] = 0.4
        
        logger.debug("Activated cognitive nodes: %s", self.active_nodes)
    
    def _calculate_preference_match(self, food_item: FoodItem) -> float:
        """Calculate how well the food matches user's taste history."""
        if not self.user_profile.taste_history:
            return 0.5  # neutral if no history
        
        # Simple similarity based on name matching (in real system would use embeddings)
        for known_food, score in self.user_profile.taste_history.items():
            if known_food.lower() in food_item.name.lower():
                return score
        
        return 0.5  # default neutral preference
    
    def _validate_constraints(self, food_item: FoodItem) -> bool:
        """Validate food against user's dietary restrictions and current constraints."""
        # Check dietary restrictions
        for restriction in self.user_profile.dietary_restrictions:
            if restriction.lower() in food_item.name.lower():
                logger.warning("Food %s violates dietary restriction: %s", 
                             food_item.name, restriction)
                return False
        
        # Check meal type suitability
        current_meal = self._determine_meal_type()
        if current_meal not in food_item.suitable_meals:
            return False
        
        # Check availability
        if not food_item.available_nearby:
            return False
            
        return True
    
    def evaluate_food_options(self) -> List[Tuple[FoodItem, float]]:
        """
        Core cognitive evaluation function that processes all food options
        through the activated cognitive nodes.
        
        Returns:
            List of tuples containing (food_item, composite_score) sorted by score
        """
        self._activate_cognitive_nodes()
        current_meal = self._determine_meal_type()
        logger.info("Evaluating food options for %s", current_meal.value)
        
        evaluated_options = []
        
        for food in self.food_db:
            if not self._validate_constraints(food):
                continue
                
            # Calculate component scores
            preference_score = self._calculate_preference_match(food)
            
            # Composite score calculation
            composite_score = (
                self.active_nodes['nutrition'] * food.nutrition_score +
                self.active_nodes['taste_preference'] * preference_score +
                self.active_nodes['dopamine_prediction'] * food.dopamine_potential -
                self.active_nodes['time_constraint'] * (food.prep_time_minutes / 60)
            )
            
            evaluated_options.append((food, composite_score))
        
        # Sort by score descending
        evaluated_options.sort(key=lambda x: x[1], reverse=True)
        logger.info("Evaluated %d valid food options", len(evaluated_options))
        
        return evaluated_options
    
    def make_recommendation(self, top_n: int = 3) -> Dict[str, Union[List[Dict], str]]:
        """
        Generate final recommendation with explanations.
        
        Args:
            top_n: Number of recommendations to return
            
        Returns:
            Dictionary containing recommendations and decision explanation
        """
        if top_n < 1:
            raise ValueError("top_n must be at least 1")
            
        evaluated = self.evaluate_food_options()
        
        if not evaluated:
            logger.error("No valid food options found")
            return {
                "recommendations": [],
                "explanation": "No suitable food options found given constraints"
            }
        
        top_recommendations = []
        for food, score in evaluated[:top_n]:
            recommendation = {
                "food": food.name,
                "score": round(score, 3),
                "nutrition_score": food.nutrition_score,
                "dopamine_potential": food.dopamine_potential,
                "prep_time": food.prep_time_minutes
            }
            top_recommendations.append(recommendation)
        
        # Generate explanation
        best_food, best_score = evaluated[0]
        explanation = (
            f"Recommended {best_food.name} (score: {best_score:.2f}) because it balances "
            f"your taste preferences ({self._calculate_preference_match(best_food):.1f}) "
            f"with nutritional needs ({best_food.nutrition_score:.1f}) and expected "
            f"pleasure response ({best_food.dopamine_potential:.1f})."
        )
        
        logger.info("Generated recommendation: %s", best_food.name)
        
        return {
            "recommendations": top_recommendations,
            "explanation": explanation,
            "meal_type": self._determine_meal_type().value,
            "timestamp": self.user_profile.current_time.isoformat()
        }


def create_sample_food_database() -> List[FoodItem]:
    """Helper function to create a sample food database for demonstration."""
    return [
        FoodItem(
            name="Grilled Salmon with Quinoa",
            nutrition_score=0.9,
            dopamine_potential=0.7,
            available_nearby=True,
            prep_time_minutes=25,
            suitable_meals=[MealType.LUNCH, MealType.DINNER]
        ),
        FoodItem(
            name="Dark Chocolate Avocado Smoothie",
            nutrition_score=0.8,
            dopamine_potential=0.9,
            available_nearby=True,
            prep_time_minutes=5,
            suitable_meals=[MealType.BREAKFAST, MealType.SNACK]
        ),
        FoodItem(
            name="Spicy Tuna Roll",
            nutrition_score=0.75,
            dopamine_potential=0.85,
            available_nearby=True,
            prep_time_minutes=15,
            suitable_meals=[MealType.LUNCH, MealType.DINNER]
        ),
        FoodItem(
            name="Caesar Salad with Chicken",
            nutrition_score=0.7,
            dopamine_potential=0.6,
            available_nearby=True,
            prep_time_minutes=10,
            suitable_meals=[MealType.LUNCH, MealType.DINNER]
        ),
        FoodItem(
            name="Pepperoni Pizza",
            nutrition_score=0.3,
            dopamine_potential=0.95,
            available_nearby=True,
            prep_time_minutes=30,
            suitable_meals=[MealType.LUNCH, MealType.DINNER]
        )
    ]


def main():
    """Demonstration of the cognitive micro-network in action."""
    # Create sample user profile
    user_profile = UserProfile(
        user_id="user_123",
        taste_history={
            "salmon": 0.9,
            "chocolate": 0.85,
            "spicy": 0.8,
            "salad": 0.4
        },
        dietary_restrictions=["peanuts"],
        location=(37.7749, -122.4194),  # San Francisco
        current_time=datetime(2023, 6, 15, 12, 30),  # Lunch time
        health_goals=["weight_loss"]
    )
    
    # Initialize cognitive network
    food_db = create_sample_food_database()
    cognitive_net = CognitiveMicroNetwork(user_profile, food_db)
    
    # Generate and display recommendation
    result = cognitive_net.make_recommendation(top_n=3)
    
    print("\n=== RECOMMENDATION RESULT ===")
    print(f"Meal Type: {result['meal_type'].upper()}")
    print(f"Time: {result['timestamp']}")
    print("\nTop Recommendations:")
    for i, rec in enumerate(result['recommendations'], 1):
        print(f"{i}. {rec['food']} (Score: {rec['score']})")
        print(f"   Nutrition: {rec['nutrition_score']} | Dopamine: {rec['dopamine_potential']} | Prep: {rec['prep_time']}min")
    
    print("\nExplanation:")
    print(result['explanation'])


if __name__ == "__main__":
    main()