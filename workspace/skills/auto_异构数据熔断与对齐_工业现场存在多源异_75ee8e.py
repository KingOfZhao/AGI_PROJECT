"""
Module: auto_heterogeneous_data_fusion_industrial
Description: 【异构数据熔断与对齐】
This module implements a multi-modal mapper designed to fuse heterogeneous industrial data sources.
It specifically addresses the alignment of high-frequency time-series signals (e.g., PLC sensors)
with unstructured text logs (e.g., quality inspector notes) and performs noise reduction
to generate standardized 'Perception Atoms' for cognitive networks.

Key Features:
- Time-series noise cleaning (Drift removal via Savitzky-Golay filter).
- Precise temporal alignment between low-freq logs and high-freq sensors.
- Generation of structured PerceptionAtoms.
"""

import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define standard data structures
@dataclass
class SensorConfig:
    """Configuration for a specific sensor channel."""
    sensor_id: str
    sampling_rate_hz: float
    threshold: float  # For anomaly detection/breaker

@dataclass
class PerceptionAtom:
    """
    Standardized output format representing a unit of perception.
    This is the 'node' ready for the cognitive network.
    """
    atom_id: str
    timestamp: datetime
    duration_seconds: float
    sensor_snapshot: Dict[str, Any]  # Aligned sensor features (mean, max, waveform segment)
    text_context: str                 # Aligned log text
    anomaly_detected: bool            # Fusion result flag

class DataFusionError(Exception):
    """Custom exception for data fusion errors."""
    pass

def _validate_dataframe(df: pd.DataFrame, required_cols: List[str], df_name: str) -> None:
    """
    [Helper Function] Validates if a DataFrame contains required columns and is not empty.
    
    Args:
        df (pd.DataFrame): The dataframe to check.
        required_cols (List[str]): List of column names that must exist.
        df_name (str): Name of the dataframe for error logging.
    
    Raises:
        DataFusionError: If validation fails.
    """
    if df.empty:
        raise DataFusionError(f"{df_name} is empty.")
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise DataFusionError(f"{df_name} missing required columns: {missing_cols}")

def clean_sensor_noise(
    sensor_data: pd.DataFrame, 
    window_size: int = 11, 
    poly_order: int = 3
) -> pd.DataFrame:
    """
    [Core Function 1] Cleans sensor noise and corrects drift using Savitzky-Golay filter.
    
    Args:
        sensor_data (pd.DataFrame): DataFrame with 'timestamp' (datetime) and 'value' (float).
        window_size (int): The length of the filter window (must be odd).
        poly_order (int): The order of the polynomial used to fit the samples.
        
    Returns:
        pd.DataFrame: Cleaned dataframe with an added 'value_cleaned' column.
        
    Raises:
        DataFusionError: If data is insufficient for the window size.
    """
    logger.info("Starting sensor noise cleaning...")
    try:
        _validate_dataframe(sensor_data, ['timestamp', 'value'], "Sensor Data")
        
        if len(sensor_data) < window_size:
            logger.warning(f"Data length {len(sensor_data)} < window size {window_size}. Skipping filtering.")
            sensor_data['value_cleaned'] = sensor_data['value']
            return sensor_data

        # Ensure data is sorted by time
        sensor_data = sensor_data.sort_values('timestamp').reset_index(drop=True)
        
        # Apply Savitzky-Golay filter for smoothing (handles drift better than simple moving avg)
        from scipy.signal import savgol_filter
        sensor_data['value_cleaned'] = savgol_filter(
            sensor_data['value'], 
            window_size, 
            poly_order
        )
        
        logger.info("Sensor noise cleaning completed successfully.")
        return sensor_data
        
    except ImportError:
        logger.error("Scipy not installed. Required for signal processing.")
        raise DataFusionError("Missing dependency: scipy")
    except Exception as e:
        logger.error(f"Error during noise cleaning: {str(e)}")
        raise DataFusionError(f"Signal processing failed: {str(e)}")

def align_and_fuse(
    cleaned_sensor_data: pd.DataFrame,
    text_logs: pd.DataFrame,
    fusion_window_seconds: int = 5
) -> List[PerceptionAtom]:
    """
    [Core Function 2] Aligns text logs with sensor data segments and generates Perception Atoms.
    
    It maps each log entry to a time window of sensor data, extracts statistical features,
    and fuses them into a single object.
    
    Args:
        cleaned_sensor_data (pd.DataFrame): Output from `clean_sensor_noise`.
        text_logs (pd.DataFrame): DataFrame with 'timestamp' and 'content'.
        fusion_window_seconds (int): Time window (seconds) to look back for sensor context.
        
    Returns:
        List[PerceptionAtom]: List of fused data nodes.
    """
    logger.info(f"Starting fusion of {len(text_logs)} log entries with sensor stream...")
    
    try:
        _validate_dataframe(cleaned_sensor_data, ['timestamp', 'value_cleaned'], "Cleaned Sensor Data")
        _validate_dataframe(text_logs, ['timestamp', 'content'], "Text Logs")
    except DataFusionError as e:
        logger.error(f"Validation failed: {e}")
        return []

    atoms: List[PerceptionAtom] = []
    
    # Ensure timestamps are datetime objects
    cleaned_sensor_data['timestamp'] = pd.to_datetime(cleaned_sensor_data['timestamp'])
    text_logs['timestamp'] = pd.to_datetime(text_logs['timestamp'])
    
    # Set index for efficient searching (slicing)
    sensor_indexed = cleaned_sensor_data.set_index('timestamp').sort_index()

    for idx, row in text_logs.iterrows():
        log_time = row['timestamp']
        window_start = log_time - timedelta(seconds=fusion_window_seconds)
        
        try:
            # Extract sensor segment within the time window
            # Using slice for fast indexing on sorted data
            segment = sensor_indexed.loc[window_start:log_time]
            
            if segment.empty:
                logger.warning(f"No sensor data found for log at {log_time}. Skipping atom generation.")
                continue
                
            # Feature Extraction from Segment
            sensor_values = segment['value_cleaned']
            features = {
                "mean": float(np.mean(sensor_values)),
                "max": float(np.max(sensor_values)),
                "min": float(np.min(sensor_values)),
                "std": float(np.std(sensor_values)),
                "trend": float(sensor_values.iloc[-1] - sensor_values.iloc[0]) if len(sensor_values) > 1 else 0.0
            }
            
            # Simple Anomaly Detection Logic (Fusion Rule)
            # If text contains keywords OR sensor variance is high, mark as anomaly
            is_anomaly = False
            if "error" in str(row['content']).lower() or features['std'] > 5.0:
                is_anomaly = True
            
            # Create Atom
            atom = PerceptionAtom(
                atom_id=f"atom_{idx}_{int(log_time.timestamp())}",
                timestamp=log_time,
                duration_seconds=fusion_window_seconds,
                sensor_snapshot=features,
                text_context=str(row['content']),
                anomaly_detected=is_anomaly
            )
            atoms.append(atom)
            
        except Exception as e:
            logger.warning(f"Failed to process log entry at {log_time}: {e}")
            continue

    logger.info(f"Fusion complete. Generated {len(atoms)} Perception Atoms.")
    return atoms

# =========================================================
# Usage Example
# =========================================================
if __name__ == "__main__":
    # 1. Generate Mock Data
    # Sensor Data: 100Hz sampling for 10 seconds
    time_steps = 1000
    end_time = datetime.now()
    start_time = end_time - timedelta(seconds=10)
    timestamps = pd.date_range(start=start_time, end=end_time, periods=time_steps)
    
    # Add some noise and drift to sensor values
    values = np.sin(np.linspace(0, 20, time_steps)) + np.random.normal(0, 0.5, time_steps) + (np.linspace(0, 5, time_steps))
    mock_sensor_df = pd.DataFrame({'timestamp': timestamps, 'value': values})
    
    # Text Logs: 3 entries
    mock_logs_df = pd.DataFrame({
        'timestamp': [
            start_time + timedelta(seconds=2), 
            start_time + timedelta(seconds=5), 
            start_time + timedelta(seconds=8)
        ],
        'content': [
            "System nominal.", 
            "Detected vibration in sector 4.", 
            "Error: Temperature spike."
        ]
    })

    print("--- Step 1: Cleaning Sensor Data ---")
    try:
        cleaned_data = clean_sensor_noise(mock_sensor_df, window_size=21)
        print(f"Cleaned Data Sample:\n{cleaned_data.head()}")
        
        print("\n--- Step 2: Aligning and Fusing Data ---")
        perception_atoms = align_and_fuse(cleaned_data, mock_logs_df, fusion_window_seconds=3)
        
        print(f"\n--- Generated {len(perception_atoms)} Atoms ---")
        for atom in perception_atoms:
            print(f"ID: {atom.atom_id}")
            print(f"Time: {atom.timestamp}")
            print(f"Text: {atom.text_context}")
            print(f"Sensor Stats: Mean={atom.sensor_snapshot['mean']:.2f}, Std={atom.sensor_snapshot['std']:.2f}")
            print(f"Anomaly: {atom.anomaly_detected}")
            print("-" * 30)
            
    except DataFusionError as e:
        print(f"Pipeline Error: {e}")