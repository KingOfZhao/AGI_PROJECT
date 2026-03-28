"""
Module: physics_constrained_animation_engine
Description: Implements a physics-based animation engine for CAD kinematics in Flutter.
             Simulates mechanical linkages, gears, and motors with real physics constraints.
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JointType(Enum):
    """Enumeration of supported joint types in the mechanical system."""
    REVOLUTE = "revolute"  # Rotational joint (e.g., hinge)
    PRISMATIC = "prismatic"  # Linear joint (e.g., slider)
    GEAR = "gear"  # Gear meshing joint
    FIXED = "fixed"  # Rigid connection


@dataclass
class Vector2D:
    """2D vector representation with validation."""
    x: float
    y: float
    
    def __post_init__(self):
        """Validate vector components."""
        if not all(isinstance(v, (int, float)) for v in (self.x, self.y)):
            raise ValueError("Vector components must be numeric")
    
    def __add__(self, other: 'Vector2D') -> 'Vector2D':
        return Vector2D(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'Vector2D') -> 'Vector2D':
        return Vector2D(self.x - other.x, self.y - other.y)
    
    def magnitude(self) -> float:
        """Calculate vector magnitude."""
        return math.sqrt(self.x**2 + self.y**2)
    
    def normalize(self) -> 'Vector2D':
        """Return normalized vector."""
        mag = self.magnitude()
        if mag == 0:
            raise ValueError("Cannot normalize zero vector")
        return Vector2D(self.x/mag, self.y/mag)
    
    def rotate(self, angle_rad: float) -> 'Vector2D':
        """Rotate vector by angle in radians."""
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        return Vector2D(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a
        )


@dataclass
class Link:
    """Represents a rigid link in a mechanical system."""
    name: str
    length: float
    mass: float
    anchor_point: Vector2D
    initial_angle: float = 0.0  # In radians
    
    def __post_init__(self):
        """Validate link parameters."""
        if self.length <= 0:
            raise ValueError("Link length must be positive")
        if self.mass <= 0:
            raise ValueError("Link mass must be positive")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Link name must be a non-empty string")
    
    def get_end_point(self, current_angle: float) -> Vector2D:
        """Calculate the end point position based on current angle."""
        direction = Vector2D(math.cos(current_angle), math.sin(current_angle))
        return self.anchor_point + Vector2D(
            direction.x * self.length,
            direction.y * self.length
        )


@dataclass
class Joint:
    """Represents a joint connecting two links."""
    name: str
    joint_type: JointType
    parent_link: Optional[str] = None
    child_link: Optional[str] = None
    angle_limits: Tuple[float, float] = (-math.pi, math.pi)  # In radians
    gear_ratio: Optional[float] = None  # For gear joints
    friction_coefficient: float = 0.1
    
    def __post_init__(self):
        """Validate joint parameters."""
        if self.joint_type == JointType.GEAR and self.gear_ratio is None:
            raise ValueError("Gear joints must specify gear_ratio")
        if not (isinstance(self.angle_limits, tuple) and len(self.angle_limits) == 2):
            raise ValueError("angle_limits must be a tuple of (min, max)")
        if self.angle_limits[0] >= self.angle_limits[1]:
            raise ValueError("angle_limits min must be less than max")
    
    def is_angle_valid(self, angle: float) -> bool:
        """Check if angle is within joint limits."""
        return self.angle_limits[0] <= angle <= self.angle_limits[1]


@dataclass
class Motor:
    """Represents a motor driving a joint."""
    name: str
    joint_name: str
    max_speed: float  # rad/s
    max_torque: float  # N·m
    current_speed: float = 0.0
    current_torque: float = 0.0
    
    def __post_init__(self):
        """Validate motor parameters."""
        if self.max_speed <= 0:
            raise ValueError("Motor max_speed must be positive")
        if self.max_torque <= 0:
            raise ValueError("Motor max_torque must be positive")


class PhysicsConstrainedAnimationEngine:
    """
    Physics-based animation engine for CAD kinematics simulation.
    
    This engine simulates mechanical systems with realistic physics constraints,
    supporting various joint types, linkages, and motor drives.
    
    Example:
        >>> engine = PhysicsConstrainedAnimationEngine()
        >>> engine.add_link("link1", length=100, mass=1.0, anchor_point=Vector2D(0, 0))
        >>> engine.add_joint("joint1", JointType.REVOLUTE, parent_link=None, child_link="link1")
        >>> engine.add_motor("motor1", "joint1", max_speed=2.0, max_torque=10.0)
        >>> state = engine.step_simulation(0.016)  # 16ms time step
    """
    
    def __init__(self, gravity: float = 9.81, time_step: float = 0.016):
        """
        Initialize the physics engine.
        
        Args:
            gravity: Gravitational acceleration (m/s²), default 9.81
            time_step: Simulation time step in seconds, default 0.016 (60 FPS)
        """
        if gravity < 0:
            raise ValueError("Gravity cannot be negative")
        if time_step <= 0:
            raise ValueError("Time step must be positive")
        
        self.gravity = gravity
        self.time_step = time_step
        self.links: Dict[str, Link] = {}
        self.joints: Dict[str, Joint] = {}
        self.motors: Dict[str, Motor] = {}
        self.joint_angles: Dict[str, float] = {}
        self.joint_velocities: Dict[str, float] = {}
        self.joint_accelerations: Dict[str, float] = {}
        self.simulation_time = 0.0
        
        logger.info(f"Physics engine initialized with gravity={gravity}m/s², time_step={time_step}s")
    
    def add_link(self, name: str, length: float, mass: float, 
                 anchor_point: Vector2D, initial_angle: float = 0.0) -> None:
        """
        Add a rigid link to the mechanical system.
        
        Args:
            name: Unique identifier for the link
            length: Length of the link in millimeters
            mass: Mass of the link in kilograms
            anchor_point: Anchor point position as Vector2D
            initial_angle: Initial angle in radians (default 0.0)
        """
        if name in self.links:
            raise ValueError(f"Link '{name}' already exists")
        
        try:
            link = Link(
                name=name,
                length=length,
                mass=mass,
                anchor_point=anchor_point,
                initial_angle=initial_angle
            )
            self.links[name] = link
            logger.info(f"Added link '{name}': length={length}mm, mass={mass}kg")
        except ValueError as e:
            logger.error(f"Failed to add link '{name}': {str(e)}")
            raise
    
    def add_joint(self, name: str, joint_type: JointType, 
                  parent_link: Optional[str], child_link: Optional[str],
                  angle_limits: Tuple[float, float] = (-math.pi, math.pi),
                  gear_ratio: Optional[float] = None,
                  friction_coefficient: float = 0.1) -> None:
        """
        Add a joint to connect two links.
        
        Args:
            name: Unique identifier for the joint
            joint_type: Type of joint (REVOLUTE, PRISMATIC, GEAR, FIXED)
            parent_link: Name of parent link (None for ground)
            child_link: Name of child link (None for ground)
            angle_limits: Tuple of (min, max) angle limits in radians
            gear_ratio: Gear ratio for GEAR type joints
            friction_coefficient: Friction coefficient at the joint
        """
        if name in self.joints:
            raise ValueError(f"Joint '{name}' already exists")
        
        # Validate referenced links exist
        if parent_link and parent_link not in self.links:
            raise ValueError(f"Parent link '{parent_link}' not found")
        if child_link and child_link not in self.links:
            raise ValueError(f"Child link '{child_link}' not found")
        
        try:
            joint = Joint(
                name=name,
                joint_type=joint_type,
                parent_link=parent_link,
                child_link=child_link,
                angle_limits=angle_limits,
                gear_ratio=gear_ratio,
                friction_coefficient=friction_coefficient
            )
            self.joints[name] = joint
            self.joint_angles[name] = 0.0  # Initialize angle
            self.joint_velocities[name] = 0.0  # Initialize velocity
            self.joint_accelerations[name] = 0.0  # Initialize acceleration
            logger.info(f"Added joint '{name}': type={joint_type.value}")
        except ValueError as e:
            logger.error(f"Failed to add joint '{name}': {str(e)}")
            raise
    
    def add_motor(self, name: str, joint_name: str, 
                  max_speed: float, max_torque: float) -> None:
        """
        Add a motor to drive a joint.
        
        Args:
            name: Unique identifier for the motor
            joint_name: Name of the joint to drive
            max_speed: Maximum angular speed in rad/s
            max_torque: Maximum torque in N·m
        """
        if name in self.motors:
            raise ValueError(f"Motor '{name}' already exists")
        if joint_name not in self.joints:
            raise ValueError(f"Joint '{joint_name}' not found")
        
        try:
            motor = Motor(
                name=name,
                joint_name=joint_name,
                max_speed=max_speed,
                max_torque=max_torque
            )
            self.motors[name] = motor
            logger.info(f"Added motor '{name}' to joint '{joint_name}'")
        except ValueError as e:
            logger.error(f"Failed to add motor '{name}': {str(e)}")
            raise
    
    def set_motor_speed(self, motor_name: str, target_speed: float) -> None:
        """
        Set the target speed for a motor.
        
        Args:
            motor_name: Name of the motor
            target_speed: Target angular speed in rad/s
        """
        if motor_name not in self.motors:
            raise ValueError(f"Motor '{motor_name}' not found")
        
        motor = self.motors[motor_name]
        # Clamp to max speed
        clamped_speed = max(-motor.max_speed, min(motor.max_speed, target_speed))
        motor.current_speed = clamped_speed
        logger.debug(f"Motor '{motor_name}' speed set to {clamped_speed} rad/s")
    
    def _calculate_link_forces(self, link_name: str) -> Tuple[Vector2D, float]:
        """
        Calculate forces and torques acting on a link.
        
        Args:
            link_name: Name of the link to analyze
            
        Returns:
            Tuple of (force_vector, net_torque)
        """
        if link_name not in self.links:
            raise ValueError(f"Link '{link_name}' not found")
        
        link = self.links[link_name]
        
        # Gravity force
        gravity_force = Vector2D(0, -self.gravity * link.mass)
        
        # Find connected joints
        connected_joints = [
            joint for joint in self.joints.values()
            if joint.parent_link == link_name or joint.child_link == link_name
        ]
        
        # Initialize net force and torque
        net_force = gravity_force
        net_torque = 0.0
        
        # Calculate forces from connected joints
        for joint in connected_joints:
            if joint.joint_type == JointType.REVOLUTE:
                # Simplified revolute joint model
                friction_torque = -joint.friction_coefficient * self.joint_velocities[joint.name]
                net_torque += friction_torque
            
            elif joint.joint_type == JointType.PRISMATIC:
                # Simplified prismatic joint model
                friction_force = -joint.friction_coefficient * self.joint_velocities[joint.name]
                # Apply friction force along the joint axis
                # This is a simplified model
                pass
            
            elif joint.joint_type == JointType.GEAR and joint.gear_ratio:
                # Gear meshing force (simplified)
                pass
        
        # Motor torque if this link is driven
        for motor in self.motors.values():
            joint = self.joints.get(motor.joint_name)
            if joint and (joint.parent_link == link_name or joint.child_link == link_name):
                # Calculate motor torque based on current speed
                motor.current_torque = motor.max_torque * (motor.current_speed / motor.max_speed)
                net_torque += motor.current_torque
        
        return net_force, net_torque
    
    def _validate_system_integrity(self) -> bool:
        """
        Validate the mechanical system's integrity.
        
        Returns:
            True if system is valid, False otherwise
        """
        # Check for floating links (not connected to ground)
        grounded_joints = [
            joint.name for joint in self.joints.values()
            if joint.parent_link is None or joint.child_link is None
        ]
        
        if not grounded_joints:
            logger.error("System has no grounded joints")
            return False
        
        # Check for kinematic loops (simplified check)
        # In a real implementation, we'd need proper graph analysis
        return True
    
    def step_simulation(self, dt: Optional[float] = None) -> Dict[str, Dict[str, float]]:
        """
        Advance the simulation by one time step.
        
        Args:
            dt: Time step in seconds (uses default if None)
            
        Returns:
            Dictionary containing the current state of all components:
            {
                "links": {link_name: {"x": float, "y": float, "angle": float}},
                "joints": {joint_name: {"angle": float, "velocity": float}},
                "motors": {motor_name: {"speed": float, "torque": float}}
            }
        """
        if dt is None:
            dt = self.time_step
        
        if dt <= 0:
            raise ValueError("Time step must be positive")
        
        # Validate system before simulation step
        if not self._validate_system_integrity():
            raise RuntimeError("System integrity check failed")
        
        # Update physics for each joint
        for joint_name, joint in self.joints.items():
            if joint.joint_type == JointType.FIXED:
                continue
            
            # Get current state
            current_angle = self.joint_angles[joint_name]
            current_velocity = self.joint_velocities[joint_name]
            
            # Calculate forces and torques on connected links
            net_torque = 0.0
            if joint.child_link:
                _, torque = self._calculate_link_forces(joint.child_link)
                net_torque += torque
            
            # Calculate moment of inertia (simplified)
            if joint.child_link:
                child_link = self.links[joint.child_link]
                # I = (1/3) * m * L^2 for a rod rotating about one end
                moment_of_inertia = (1/3) * child_link.mass * (child_link.length/1000)**2
            else:
                moment_of_inertia = 1.0  # Default
            
            # Calculate acceleration (τ = I * α)
            if moment_of_inertia > 0:
                acceleration = net_torque / moment_of_inertia
            else:
                acceleration = 0.0
            
            # Update velocity (v = v0 + a*t)
            new_velocity = current_velocity + acceleration * dt
            
            # Apply joint limits
            new_angle = current_angle + new_velocity * dt
            if not joint.is_angle_valid(new_angle):
                # Bounce back when hitting limit (simplified model)
                new_velocity *= -0.5  # Damped bounce
                new_angle = max(joint.angle_limits[0], min(joint.angle_limits[1], new_angle))
            
            # Update state
            self.joint_velocities[joint_name] = new_velocity
            self.joint_accelerations[joint_name] = acceleration
            self.joint_angles[joint_name] = new_angle
        
        # Update simulation time
        self.simulation_time += dt
        
        # Prepare state for output
        state = {
            "links": {},
            "joints": {},
            "motors": {},
            "time": self.simulation_time
        }
        
        # Calculate link positions
        for link_name, link in self.links.items():
            # Find the joint that connects this link to its parent
            parent_joint = None
            for joint in self.joints.values():
                if joint.child_link == link_name:
                    parent_joint = joint
                    break
            
            if parent_joint:
                angle = link.initial_angle + self.joint_angles[parent_joint.name]
            else:
                angle = link.initial_angle
            
            end_point = link.get_end_point(angle)
            state["links"][link_name] = {
                "anchor_x": link.anchor_point.x,
                "anchor_y": link.anchor_point.y,
                "end_x": end_point.x,
                "end_y": end_point.y,
                "angle": angle
            }
        
        # Add joint states
        for joint_name in self.joints:
            state["joints"][joint_name] = {
                "angle": self.joint_angles[joint_name],
                "velocity": self.joint_velocities[joint_name],
                "acceleration": self.joint_accelerations[joint_name]
            }
        
        # Add motor states
        for motor_name, motor in self.motors.items():
            state["motors"][motor_name] = {
                "speed": motor.current_speed,
                "torque": motor.current_torque
            }
        
        logger.debug(f"Simulation step completed: t={self.simulation_time:.3f}s")
        return state
    
    def run_simulation(self, duration: float) -> List[Dict[str, Dict[str, float]]]:
        """
        Run the simulation for a specified duration.
        
        Args:
            duration: Total simulation time in seconds
            
        Returns:
            List of states at each time step
        """
        if duration <= 0:
            raise ValueError("Duration must be positive")
        
        states = []
        remaining_time = duration
        
        logger.info(f"Starting simulation for {duration}s")
        
        while remaining_time > 0:
            dt = min(self.time_step, remaining_time)
            state = self.step_simulation(dt)
            states.append(state)
            remaining_time -= dt
        
        logger.info(f"Simulation completed: {len(states)} steps")
        return states


# Example usage and demonstration
if __name__ == "__main__":
    try:
        # Create a simple crank-rocker mechanism
        engine = PhysicsConstrainedAnimationEngine(gravity=9.81, time_step=0.016)
        
        # Add links (a 4-bar linkage)
        engine.add_link("ground", length=0, mass=0, anchor_point=Vector2D(0, 0))
        engine.add_link("crank", length=50, mass=0.5, anchor_point=Vector2D(0, 0))
        engine.add_link("coupler", length=120, mass=0.3, anchor_point=Vector2D(50, 0))
        engine.add_link("rocker", length=100, mass=0.4, anchor_point=Vector2D(150, 0))
        
        # Add joints
        engine.add_joint("fixed_ground", JointType.FIXED, None, "ground")
        engine.add_joint("crank_joint", JointType.REVOLUTE, "ground", "crank",
                        angle_limits=(-math.pi, math.pi))
        engine.add_joint("coupler_joint", JointType.REVOLUTE, "crank", "coupler")
        engine.add_joint("rocker_joint", JointType.REVOLUTE, "coupler", "rocker",
                        angle_limits=(-math.pi/2, math.pi/2))
        
        # Add motor to drive the crank
        engine.add_motor("drive_motor", "crank_joint", max_speed=5.0, max_torque=2.0)
        engine.set_motor_speed("drive_motor", 3.0)  # 3 rad/s
        
        # Run simulation for 2 seconds
        results = engine.run_simulation(2.0)
        
        # Print some results
        print(f"\nSimulation completed with {len(results)} steps")
        print("Sample state at t=1.0s:")
        mid_state = results[len(results)//2]
        print(f"  Time: {mid_state['time']:.3f}s")
        print(f"  Crank angle: {math.degrees(mid_state['joints']['crank_joint']['angle']):.1f}°")
        print(f"  Motor speed: {mid_state['motors']['drive_motor']['speed']:.2f} rad/s")
        
    except Exception as e:
        logger.error(f"Simulation failed: {str(e)}")
        raise