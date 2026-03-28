"""
Module: street_vendor_knowledge_digitalizer.py

Description:
    Validates the digitalization precision of unstructured 'street vendor knowledge'
    (specifically the 'Bargaining/Haggling' skill).

    This module implements a simulation framework where:
    1. A Decision Tree model is constructed to represent the bargaining logic.
    2. A text-based adventure game engine simulates the interaction between a Buyer and a Seller.
    3. The AI Seller analyzes unstructured inputs (text descriptions of tone/micro-expressions)
       to adjust pricing strategies, aiming to maximize the deal closure rate.

Domain: Behavioral Economics / AGI Skill Verification
Author: Senior Python Engineer
Date: 2023-10-27
"""

import logging
import random
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Tuple, Optional

# --- Configuration & Setup ---

# Setting up robust logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Enums and Data Structures ---

class BuyerTone(Enum):
    """Represents the detected tone/micro-expression of the buyer."""
    NEUTRAL = auto()
    HESITANT = auto()
    AGGRESSIVE = auto()
    FRIENDLY = auto()
    WALKING_AWAY = auto()

class ActionType(Enum):
    """Actions the Seller AI can take."""
    HOLD_PRICE = "Hold Price"
    SMALL_DISCOUNT = "Offer Small Discount (5-10%)"
    LARGE_DISCOUNT = "Offer Large Discount (15-20%)"
    ADD_VALUE = "Add Freebie/Service"
    CLOSE_DEAL = "Accept Current Offer"

@dataclass
class Product:
    """Represents the item being sold."""
    name: str
    base_cost: float  # The absolute minimum the seller can accept
    initial_price: float
    current_price: float = field(init=False)
    
    def __post_init__(self):
        self.current_price = self.initial_price

    def apply_discount(self, percentage: float) -> float:
        """Applies a discount percentage and returns the new price."""
        if not (0 <= percentage <= 1):
            raise ValueError("Discount percentage must be between 0 and 1")
        
        new_price = self.current_price * (1 - percentage)
        # Boundary check: Price cannot go below base cost
        self.current_price = max(self.base_cost, new_price)
        logger.debug(f"Price updated: {self.current_price:.2f}")
        return self.current_price

@dataclass
class BuyerState:
    """Simulates the internal state of the buyer."""
    budget: float
    patience: int  # 0 to 100
    interest_level: int  # 0 to 100
    current_offer: float = 0.0
    
    def update_state(self, tone: BuyerTone, price_diff: float):
        """Updates buyer state based on interaction."""
        # Simple simulation logic
        if tone == BuyerTone.AGGRESSIVE:
            self.patience -= 10
        elif tone == BuyerTone.HESITANT:
            self.patience -= 5
        
        if price_diff > 0: # Seller price is higher than offer
            self.interest_level -= int(price_diff * 2)
        else:
            self.interest_level += 10 # Seller accepted or went lower

        # Clamp values
        self.patience = max(0, min(100, self.patience))
        self.interest_level = max(0, min(100, self.interest_level))

# --- Core Components ---

class BargainingDecisionModel:
    """
    A Decision Tree implementation to digitize vendor experience.
    It maps unstructured inputs (Tone, Price Gap) to structured Actions.
    """

    @staticmethod
    def analyze_input(text_input: str) -> BuyerTone:
        """
        Helper function to parse unstructured text into structured data.
        Simulates NLP/Micro-expression analysis.
        """
        text = text_input.lower()
        if any(word in text for word in ["frown", "hesitant", "maybe", "expensive"]):
            return BuyerTone.HESITANT
        elif any(word in text for word in ["angry", "ridiculous", "rip-off", "storming"]):
            return BuyerTone.AGGRESSIVE
        elif any(word in text for word in ["smile", "love it", "deal", "nice"]):
            return BuyerTone.FRIENDLY
        elif any(word in text for word in ["leave", "walking away", "elsewhere"]):
            return BuyerTone.WALKING_AWAY
        else:
            return BuyerTone.NEUTRAL

    def decide_action(self, buyer_tone: BuyerTone, price_gap_ratio: float) -> ActionType:
        """
        The core decision tree logic.
        
        Args:
            buyer_tone (BuyerTone): The perceived state of the buyer.
            price_gap_ratio (float): (SellerPrice - BuyerOffer) / SellerPrice. 
                                     Positive means seller wants more.
        
        Returns:
            ActionType: The suggested action for the seller.
        """
        logger.info(f"Decision Node: Tone={buyer_tone.name}, Gap Ratio={price_gap_ratio:.2f}")

        # Decision Logic based on 'Street Knowledge'
        if buyer_tone == BuyerTone.WALKING_AWAY:
            # Panic mode: Try to keep them
            return ActionType.LARGE_DISCOUNT
        
        if buyer_tone == BuyerTone.AGGRESSIVE:
            if price_gap_ratio > 0.3:
                return ActionType.SMALL_DISCOUNT # Don't yield too much to aggression
            else:
                return ActionType.HOLD_PRICE # Hold ground if close

        if buyer_tone == BuyerTone.HESITANT:
            return ActionType.ADD_VALUE # Sweeten the deal without lowering price much
        
        if buyer_tone == BuyerTone.FRIENDLY:
            if price_gap_ratio < 0.1:
                return ActionType.CLOSE_DEAL # Close while vibes are good
            return ActionType.SMALL_DISCOUNT

        # Default Neutral logic
        if price_gap_ratio > 0.5:
            return ActionType.LARGE_DISCOUNT
        elif price_gap_ratio > 0.1:
            return ActionType.SMALL_DISCOUNT
        else:
            return ActionType.CLOSE_DEAL


class SimulationEngine:
    """
    Manages the Text Adventure Game simulation loop.
    """
    
    def __init__(self, product: Product, buyer: BuyerState):
        self.product = product
        self.buyer = buyer
        self.decision_model = BargainingDecisionModel()
        self.turn_count = 0
        self.max_turns = 10
        self.deal_closed = False

    def _generate_buyer_behavior(self) -> Tuple[str, float]:
        """
        Simulates the buyer generating an unstructured text input and an offer.
        """
        # Simulate dynamic buyer offer generation
        # Buyer tries to offer slightly lower than current price
        offer = self.product.current_price * random.uniform(0.7, 0.95)
        
        # Ensure offer is not higher than budget
        offer = min(offer, self.buyer.budget)
        
        behaviors = [
            (f"I don't know... {self.product.name} looks a bit worn. {offer:.2f}?", BuyerTone.HESITANT),
            (f"That's a rip-off! I'm walking away if you don't go lower.", BuyerTone.WALKING_AWAY),
            (f"Hmm, I really like it. How about {offer:.2f}?", BuyerTone.FRIENDLY),
            (f"Come on, give me a break. {offer:.2f} is fair.", BuyerTone.AGGRESSIVE),
            (f"I see. The price is {self.product.current_price:.2f}. I offer {offer:.2f}.", BuyerTone.NEUTRAL)
        ]
        
        # Weighted choice based on patience
        if self.buyer.patience < 20:
            text, tone = "I'm done here. Bye.", BuyerTone.WALKING_AWAY
        else:
            text, tone = random.choice(behaviors)
        
        # Inject tone into text (simulation imperfection)
        logger.debug(f"Buyer Internal Tone: {tone.name}")
        return text, offer

    def step(self) -> bool:
        """
        Executes a single turn of the simulation.
        
        Returns:
            bool: True if simulation should continue, False if ended.
        """
        if self.turn_count >= self.max_turns:
            logger.info("Max turns reached. Deal failed.")
            return False
        
        if self.buyer.patience <= 0:
            logger.info("Buyer ran out of patience. Deal failed.")
            return False

        self.turn_count += 1
        print(f"\n--- Turn {self.turn_count} ---")
        print(f"Seller Price: {self.product.current_price:.2f} | Buyer Budget: {self.buyer.budget:.2f}")
        
        # 1. Buyer acts (Generates unstructured text)
        text_input, buyer_offer = self._generate_buyer_behavior()
        print(f"Buyer says: \"{text_input}\" (Offers {buyer_offer:.2f})")
        
        # 2. AI Model processes
        detected_tone = self.decision_model.analyze_input(text_input)
        gap_ratio = (self.product.current_price - buyer_offer) / self.product.current_price if self.product.current_price > 0 else 0
        
        action = self.decision_model.decide_action(detected_tone, gap_ratio)
        print(f"AI Analysis: Tone={detected_tone.name}, Gap={gap_ratio:.2f} -> Action={action.value}")
        
        # 3. Execute Action
        if action == ActionType.CLOSE_DEAL:
            if buyer_offer >= self.product.base_cost:
                print(f"SUCCESS! Deal closed at {buyer_offer:.2f}")
                self.deal_closed = True
                return False
            else:
                print("Seller: I can't go that low!")
                self.buyer.patience -= 10
                
        elif action == ActionType.SMALL_DISCOUNT:
            self.product.apply_discount(0.08)
            print(f"Seller: Okay, I can drop the price to {self.product.current_price:.2f} for you.")
            
        elif action == ActionType.LARGE_DISCOUNT:
            self.product.apply_discount(0.18)
            print(f"Seller: Wait! Special price just for you: {self.product.current_price:.2f}!")
            
        elif action == ActionType.ADD_VALUE:
            print("Seller: If you buy now, I'll throw in a free carrying case!")
            self.buyer.interest_level += 15 # Simulate value adding effect
            
        elif action == ActionType.HOLD_PRICE:
            print(f"Seller: The price is firm at {self.product.current_price:.2f}. Quality costs money.")
            self.buyer.patience -= 5

        # 4. Update internal states
        self.buyer.update_state(detected_tone, self.product.current_price - buyer_offer)
        
        return True

    def run_simulation(self) -> bool:
        """Runs the full loop."""
        logger.info(f"Starting Simulation for {self.product.name}")
        running = True
        while running:
            running = self.step()
        
        if self.deal_closed:
            logger.info(f"Result: SUCCESS. Final Price: {self.product.current_price:.2f}")
        else:
            logger.info("Result: FAILED.")
            
        return self.deal_closed

# --- Helper Functions ---

def validate_parameters(product_cost: float, initial_price: float, buyer_budget: float) -> bool:
    """
    Validates input data to ensure simulation stability.
    """
    if product_cost <= 0 or initial_price <= 0 or buyer_budget <= 0:
        logger.error("Financial values must be positive.")
        return False
    if initial_price < product_cost:
        logger.error("Initial price cannot be lower than base cost.")
        return False
    if buyer_budget < product_cost:
        logger.warning("Buyer has no budget to afford the item even at cost.")
        # Not returning False, as this is a valid edge case for testing rejection logic
    return True

# --- Main Execution ---

if __name__ == "__main__":
    # Example Usage
    
    # 1. Define Scenario Data
    item_name = "Vintage Ceramic Vase"
    cost = 50.0
    list_price = 100.0
    buyer_starting_budget = 95.0
    
    # 2. Validate
    if validate_parameters(cost, list_price, buyer_starting_budget):
        
        # 3. Initialize Objects
        item = Product(name=item_name, base_cost=cost, initial_price=list_price)
        buyer_agent = BuyerState(budget=buyer_starting_budget, patience=80, interest_level=60)
        
        # 4. Run Simulation
        engine = SimulationEngine(product=item, buyer=buyer_agent)
        result = engine.run_simulation()
        
        print("\n" + "="*30)
        print(f"Simulation Finished. Deal Success: {result}")
        print("="*30)