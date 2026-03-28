"""
Module: cross_domain_geometry_transfer
Description: Implements a skill for AGI systems to demonstrate cross-domain knowledge transfer.
             It abstracts the core logic of a collision detection algorithm (Game Development, Domain A)
             and applies it to a Geofencing alert system (GIS, Domain B), maintaining the O(N^2) logic
             but adapting for spherical geometry and domain-specific data structures.
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Type Aliases for clarity ---
Vector2D = Tuple[float, float]
Vector3D = Tuple[float, float, float]

# --- Domain A: Game Development (2D Euclidean Space) ---

@dataclass
class GameObject:
    """
    Represents an entity in a 2D Game world.
    Attributes:
        id: Unique identifier.
        position: (x, y) coordinates.
        radius: Collision radius.
    """
    id: str
    position: Vector2D
    radius: float

    def __post_init__(self):
        if self.radius < 0:
            raise ValueError("Radius cannot be negative")

def euclidean_distance(p1: Union[Vector2D, Vector3D], p2: Union[Vector2D, Vector3D]) -> float:
    """
    Helper function: Calculates Euclidean distance between two points.
    
    Args:
        p1: First point coordinates.
        p2: Second point coordinates.
        
    Returns:
        float: The distance between points.
    """
    if len(p1) != len(p2):
        raise ValueError("Points must have the same dimensions")
    
    sum_sq = sum((a - b) ** 2 for a, b in zip(p1, p2))
    return math.sqrt(sum_sq)

def detect_game_collisions(objects: List[GameObject]) -> List[Tuple[str, str]]:
    """
    Core Algorithm (Domain A): Detects collisions between circular game objects.
    Uses a pairwise comparison approach (O(N^2)).
    
    Args:
        objects: List of GameObjects.
        
    Returns:
        List of tuples representing IDs of colliding pairs.
        
    Example:
        >>> objs = [GameObject('p1', (0,0), 1), GameObject('p2', (1.5, 0), 1)]
        >>> detect_game_collisions(objs)
        [('p1', 'p2')]
    """
    logger.info(f"Starting collision detection for {len(objects)} game objects.")
    collisions = []
    
    for i in range(len(objects)):
        for j in range(i + 1, len(objects)):
            obj_a = objects[i]
            obj_b = objects[j]
            
            dist = euclidean_distance(obj_a.position, obj_b.position)
            threshold = obj_a.radius + obj_b.radius
            
            if dist < threshold:
                logger.debug(f"Collision detected: {obj_a.id} <-> {obj_b.id}")
                collisions.append((obj_a.id, obj_b.id))
                
    return collisions

# --- Domain B: GIS System (Spherical Space) ---

@dataclass
class GeoEntity:
    """
    Represents a tracked entity in a GIS system.
    Attributes:
        id: Unique identifier (e.g., asset ID).
        lat_lon: (Latitude, Longitude) in degrees.
        radius_meters: Proximity radius in meters.
    """
    id: str
    lat_lon: Tuple[float, float]
    radius_meters: float

    def __post_init__(self):
        lat, lon = self.lat_lon
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise ValueError(f"Invalid coordinates for entity {self.id}")
        if self.radius_meters < 0:
            raise ValueError("Radius cannot be negative")

def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    Helper function: Calculates the great-circle distance between two points 
    on a sphere given their longitudes and latitudes (Haversine formula).
    
    Args:
        coord1: (lat, lon) in degrees.
        coord2: (lat, lon) in degrees.
        
    Returns:
        float: Distance in meters.
    """
    R = 6371000  # Earth radius in meters
    
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def detect_geo_intrusions(entities: List[GeoEntity], zone_entity_id: str) -> List[str]:
    """
    Transferred Logic (Domain B): Detects intrusions into a specific geofence zone.
    
    This function represents the AGI "Skill" of Cross-Domain Transfer. 
    It recognizes that Geofencing is mathematically isomorphic to Collision Detection:
    - Logic: Distance(P1, P2) < Radius(P1) + Radius(P2)
    - Difference: Euclidean geometry vs Spherical geometry.
    
    Args:
        entities: List of GeoEntities (vehicles, assets, etc.).
        zone_entity_id: The ID of the entity acting as the 'Zone' center.
        
    Returns:
        List of entity IDs that have breached the zone radius.
    """
    logger.info(f"Starting geofence check for zone '{zone_entity_id}'.")
    
    # Identify the zone object
    zone = next((e for e in entities if e.id == zone_entity_id), None)
    if not zone:
        logger.error(f"Zone entity {zone_entity_id} not found.")
        raise ValueError(f"Zone entity {zone_entity_id} not found in entity list.")
    
    intruders = []
    
    for entity in entities:
        if entity.id == zone_entity_id:
            continue # Skip self-check
            
        # Abstracted Logic: Distance Check
        # Here we swap euclidean_distance for haversine_distance
        dist = haversine_distance(zone.lat_lon, entity.lat_lon)
        threshold = zone.radius_meters + entity.radius_meters
        
        if dist < threshold:
            logger.warning(f"INTRUSION DETECTED: {entity.id} is {dist:.2f}m from zone {zone.id}")
            intruders.append(entity.id)
            
    return intruders

# --- System Orchestration ---

def run_cross_domain_demo():
    """
    Demonstrates the AGI capability to transfer the collision algorithm 
    from Game Dev (A) to GIS (B).
    """
    print("--- [AGI Skill Execution: Cross-Domain Transfer] ---")
    
    # 1. Domain A Context
    print("\n[Domain A: Game Physics]")
    game_objs = [
        GameObject('player', (0, 0), 5),
        GameObject('enemy', (7, 0), 3),
        GameObject('npc', (20, 20), 2)
    ]
    collisions = detect_game_collisions(game_objs)
    print(f"Detected Game Collisions: {collisions}")

    # 2. Domain B Context (Transfer Target)
    print("\n[Domain B: GIS Geofencing]")
    # Simulating a sensitive area and a moving asset
    # sensitive_area: New York (approx), 1000m radius
    # drone_1: Inside zone
    # drone_2: Outside zone
    geo_entities = [
        GeoEntity('sensitive_area', (40.7128, -74.0060), 1000),
        GeoEntity('drone_1', (40.7200, -74.0060), 10),  # ~800m North -> Inside
        GeoEntity('drone_2', (40.7500, -74.0060), 10)   # Too far -> Outside
    ]
    
    try:
        intrusions = detect_geo_intrusions(geo_entities, 'sensitive_area')
        print(f"Detected Geofence Intruders: {intrusions}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_cross_domain_demo()