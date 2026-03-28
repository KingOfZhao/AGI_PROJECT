"""
Module: tacit_skill_digitalizer.py

This module is designed to bridge the gap between human expert tacit knowledge
(technician's "feel") and robotic executable parameters. It focuses on processing
sensor data (force/torque, position) collected during expert demonstrations to
extract quantitative parameters for trajectory planning.

Author: Senior Python Engineer (AGI System)
Domain: robotics_hri
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ProcessParameters:
    """
    Data class representing the quantified parameters for robotic execution.
    
    Attributes:
        avg_feed_rate (float): Average movement speed in m/s.
        contact_force_target (float): Target normal force in Newtons.
        force_damping_factor (float): Coefficient for force feedback control loop.
        oscillation_amplitude (float): Amplitude for rhythmic movements (e.g., polishing).
        oscillation_freq (float): Frequency for rhythmic movements in Hz.
        stiffness_matrix (np.ndarray): 6x6 Cartesian stiffness matrix.
    """
    avg_feed_rate: float
    contact_force_target: float
    force_damping_factor: float
    oscillation_amplitude: float
    oscillation_freq: float
    stiffness_matrix: np.ndarray = field(default_factory=lambda: np.eye(6))

    def to_dict(self) -> Dict:
        """Converts parameters to a dictionary for JSON serialization."""
        return {
            "avg_feed_rate": self.avg_feed_rate,
            "contact_force_target": self.contact_force_target,
            "force_damping_factor": self.force_damping_factor,
            "oscillation_amplitude": self.oscillation_amplitude,
            "oscillation_freq": self.oscillation_freq,
            "stiffness_matrix": self.stiffness_matrix.tolist()
        }

def validate_sensor_data(timestamps: np.ndarray, forces: np.ndarray, positions: np.ndarray) -> None:
    """
    Helper function to validate input data integrity and shapes.
    
    Args:
        timestamps: 1D array of time values.
        forces: 2D array of force values (N, 3) or (N, 6).
        positions: 2D array of Cartesian positions (N, 3).
        
    Raises:
        ValueError: If data shapes mismatch or contain invalid values.
    """
    if not (len(timestamps) == len(forces) == len(positions)):
        raise ValueError(f"Shape mismatch: Time({len(timestamps)}), Forces({len(forces)}), Pos({len(positions)})")
    
    if len(timestamps) < 10:
        raise ValueError("Insufficient data points for statistical analysis (min 10).")
    
    if np.any(np.diff(timestamps) <= 0):
        logger.warning("Timestamps are not strictly increasing. Sorting might be required.")
    
    if np.any(np.isnan(forces)) or np.any(np.isnan(positions)):
        raise ValueError("Input data contains NaN values.")

def calculate_adaptive_damping(force_profile: np.ndarray, velocity_profile: np.ndarray) -> float:
    """
    Helper function to calculate damping coefficient based on force/velocity correlation.
    Simulates the human ability to soften contact at high speeds.
    
    Args:
        force_profile: Array of normal forces.
        velocity_profile: Array of feed velocities.
        
    Returns:
        Calculated damping coefficient.
    """
    # Simple linear regression proxy for damping: Force = Damping * Velocity
    # Using least squares: D = (V.T * F) / (V.T * V)
    v_safe = velocity_profile.reshape(-1, 1)
    f_safe = force_profile.reshape(-1, 1)
    
    dot_vv = np.dot(v_safe.T, v_safe)
    if dot_vv[0, 0] < 1e-6:
        return 0.5 # Default safe value
        
    damping = np.dot(v_safe.T, f_safe)[0, 0] / dot_vv[0, 0]
    return float(np.clip(damping, 0.0, 5.0))

def extract_tactile_parameters(
    timestamps: np.ndarray,
    force_torque_data: np.ndarray,
    cartesian_positions: np.ndarray,
    tool_axis: str = 'z'
) -> ProcessParameters:
    """
    Core Function 1: Analyzes raw sensor data from a technician's demonstration.
    
    Processes force/position data to extract rhythmic patterns (polishing rhythm),
    average resistance, and adaptive compliance parameters.
    
    Args:
        timestamps (np.ndarray): 1D array of time in seconds.
        force_torque_data (np.ndarray): 2D array (N, 6) containing [Fx, Fy, Fz, Mx, My, Mz].
        cartesian_positions (np.ndarray): 2D array (N, 3) containing [X, Y, Z].
        tool_axis (str): The axis along which the tool works ('x', 'y', or 'z').
        
    Returns:
        ProcessParameters: A dataclass containing the quantified skill parameters.
        
    Raises:
        ValueError: If inputs are invalid or processing fails.
        
    Example:
        >>> t = np.linspace(0, 10, 1000)
        >>> # Simulate a sine wave movement with constant force
        >>> pos = np.array([np.zeros(1000), np.zeros(1000), np.sin(2 * np.pi * 0.5 * t)]).T
        >>> ft = np.random.normal(10, 0.5, (1000, 6)) # 10N force
        >>> params = extract_tactile_parameters(t, ft, pos, tool_axis='z')
    """
    logger.info("Starting tactile parameter extraction...")
    
    try:
        validate_sensor_data(timestamps, force_torque_data, cartesian_positions)
    except ValueError as e:
        logger.error(f"Data validation failed: {e}")
        raise

    # Map axis to index
    axis_map = {'x': 0, 'y': 1, 'z': 2}
    ax_idx = axis_map.get(tool_axis.lower(), 2)
    
    # 1. Calculate Feed Rate (Velocity magnitude)
    dt = np.diff(timestamps)
    dt[dt == 0] = 1e-6 # prevent division by zero
    deltas = np.diff(cartesian_positions, axis=0)
    velocities = np.linalg.norm(deltas, axis=1) / dt
    avg_feed_rate = float(np.median(velocities))
    
    # 2. Analyze Force Profile (Resistance)
    # Assuming force sensor reads positive when pushing INTO surface
    normal_forces = force_torque_data[:-1, ax_idx]
    target_force = float(np.mean(normal_forces))
    force_std = float(np.std(normal_forces))
    
    logger.info(f"Analyzed Force: Mean={target_force:.2f}N, StdDev={force_std:.2f}N")

    # 3. Detect Rhythm (Frequency Analysis)
    # Using FFT on position data along the tool axis to find oscillation (polishing rhythm)
    signal = cartesian_positions[:, ax_idx]
    signal = signal - np.mean(signal) # Remove DC component
    
    n = len(signal)
    freq = np.fft.fftfreq(n, d=np.median(dt))
    fft_vals = np.abs(np.fft.fft(signal))
    
    # Find peak frequency (ignore 0 Hz)
    peak_idx = np.argmax(fft_vals[1:n//2]) + 1
    dominant_freq = abs(freq[peak_idx])
    
    # Calculate amplitude (half of peak-to-peak)
    amplitude = (np.max(signal) - np.min(signal)) / 2.0
    
    logger.info(f"Detected Rhythm: Freq={dominant_freq:.2f}Hz, Amp={amplitude:.4f}m")

    # 4. Calculate Compliance/Damping
    damping = calculate_adaptive_damping(normal_forces, velocities)
    
    # 5. Construct Stiffness Matrix (Simplified: High lateral stiffness, lower axial)
    stiffness = np.eye(6) * 2000 # Default stiff
    stiffness[ax_idx, ax_idx] = 500 # Softer along approach axis
    
    return ProcessParameters(
        avg_feed_rate=avg_feed_rate,
        contact_force_target=target_force,
        force_damping_factor=damping,
        oscillation_amplitude=amplitude,
        oscillation_freq=dominant_freq,
        stiffness_matrix=stiffness
    )

def generate_robot_trajectory(
    params: ProcessParameters,
    start_point: Tuple[float, float, float],
    end_point: Tuple[float, float, float],
    duration: float
) -> Dict[str, np.ndarray]:
    """
    Core Function 2: Generates executable trajectory based on extracted parameters.
    
    Takes the quantified parameters and generates a time-series of poses and
    force control setpoints that mimic the technician's rhythm and pressure.
    
    Args:
        params (ProcessParameters): The quantified skill parameters.
        start_point (Tuple): (x, y, z) start coordinates.
        end_point (Tuple): (x, y, z) end coordinates.
        duration (float): Desired execution time in seconds.
        
    Returns:
        Dict[str, np.ndarray]: Dictionary containing 'positions', 'velocities', 
                               and 'force_setpoints' arrays.
                               
    Example:
        >>> params = ProcessParameters(avg_feed_rate=0.1, contact_force_target=10.0, 
        >>>                            force_damping_factor=0.8, oscillation_amplitude=0.01,
        >>>                            oscillation_freq=2.0)
        >>> traj = generate_robot_trajectory(params, (0,0,0), (0.1,0,0), 5.0)
    """
    logger.info("Generating robot trajectory with skill parameters...")
    
    if duration <= 0:
        raise ValueError("Duration must be positive.")
    
    # Time resolution: aim for 100Hz or adapt to frequency
    dt = min(0.01, 1.0 / (params.oscillation_freq * 10)) if params.oscillation_freq > 0 else 0.01
    t = np.arange(0, duration, dt)
    n_steps = len(t)
    
    # 1. Base Linear Path (Interpolation)
    start_np = np.array(start_point)
    end_np = np.array(end_point)
    path_vector = end_np - start_np
    path_length = np.linalg.norm(path_vector)
    path_unit = path_vector / path_length if path_length > 1e-6 else np.zeros(3)
    
    # Linear progression [0..1]
    s = t / duration 
    
    # 2. Superimpose Oscillation (The "Rhythm")
    # Oscillation is perpendicular to the path direction for polishing/sanding
    # Assuming Z is the primary polishing normal for simplicity, or using cross product
    normal_vec = np.array([0, 0, 1]) # Default surface normal assumption
    osc_dir = np.cross(path_unit, normal_vec)
    if np.linalg.norm(osc_dir) < 1e-6:
        osc_dir = np.array([0, 1, 0]) # Fallback
        
    osc_offset = params.oscillation_amplitude * np.sin(2 * np.pi * params.oscillation_freq * t)
    osc_matrix = np.outer(osc_offset, osc_dir)
    
    # 3. Construct Position Trajectory
    linear_positions = start_np + np.outer(s, path_vector)
    final_positions = linear_positions + osc_matrix
    
    # 4. Construct Velocity Profile
    base_velocity = path_length / duration
    # Velocity of the oscillator
    osc_velocity = params.oscillation_amplitude * 2 * np.pi * params.oscillation_freq * np.cos(2 * np.pi * params.oscillation_freq * t)
    
    # Combine speeds (approximate magnitude for feed rate control)
    final_speeds = np.sqrt((base_velocity**2) + (osc_velocity**2))
    
    # 5. Force Setpoints
    # Constant target force with potential modulation based on velocity (optional)
    force_setpoints = np.full((n_steps, 3), [0, 0, params.contact_force_target])
    
    logger.info(f"Generated {n_steps} waypoints. Avg Speed: {np.mean(final_speeds):.3f} m/s")
    
    return {
        "timestamps": t,
        "positions": final_positions,
        "velocities": final_speeds,
        "force_setpoints": force_setpoints,
        "parameters_used": params.to_dict()
    }

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Generate Mock Data representing a Technician's Polishing Action
    # 5 seconds of data, 100Hz
    time_data = np.linspace(0, 5, 500)
    
    # Movement: X changes linearly, Z oscillates (polishing motion)
    x_pos = 0.1 * time_data  # 0.1 m/s feed
    y_pos = np.zeros_like(time_data)
    z_pos = 0.005 * np.sin(2 * np.pi * 2.0 * time_data) # 2Hz rhythm, 5mm amp
    pos_data = np.vstack([x_pos, y_pos, z_pos]).T
    
    # Force: Fz is roughly 15N with some noise
    fz = 15.0 + np.random.normal(0, 0.5, 500)
    ft_data = np.zeros((500, 6))
    ft_data[:, 2] = fz
    
    # 2. Run Parameter Extraction
    try:
        skill_params = extract_tactile_parameters(time_data, ft_data, pos_data, tool_axis='z')
        print("\n--- Extracted Parameters ---")
        print(f"Target Force: {skill_params.contact_force_target:.2f} N")
        print(f"Rhythm Freq: {skill_params.oscillation_freq:.2f} Hz")
        print(f"Feed Rate: {skill_params.avg_feed_rate:.4f} m/s")
        
        # 3. Generate Robot Trajectory based on learned skill
        trajectory = generate_robot_trajectory(
            skill_params, 
            start_point=(0, 0, 0), 
            end_point=(0.5, 0, 0), 
            duration=5.0
        )
        
        print("\n--- Trajectory Generation Success ---")
        print(f"Waypoints generated: {len(trajectory['positions'])}")
        
    except ValueError as e:
        print(f"Error: {e}")