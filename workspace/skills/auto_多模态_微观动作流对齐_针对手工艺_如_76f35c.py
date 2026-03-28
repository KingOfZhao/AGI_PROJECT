"""
Module: auto_多模态_微观动作流对齐_针对手工艺_如_76f35c
Description: [Multi-modal Micro-action Stream Alignment]
             Focuses on aligning visual streams (hand deformation) with high-frequency
             IMU sensor data (acceleration/angular velocity) for handicraft scenarios
             (e.g., pottery throwing). This module constructs a spatiotemporal feature
             extraction model to map unstructured physical actions into a computable
             'Gesture-Force' joint embedding space.
Author: AGI System Core
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Tuple, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Attempt to import torch, handle case if not available for pure numpy fallback logic
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch not found. Neural network components will be disabled.")

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Constants and Configuration ---
DEFAULT_IMU_SAMPLE_RATE = 200  # Hz
DEFAULT_VIDEO_FPS = 30
WINDOW_SIZE_MS = 100  # Milliseconds
EMBEDDING_DIM = 128

class ModalityType(Enum):
    """Enumeration for different data modalities."""
    VISUAL = "visual"
    IMU = "imu"

@dataclass
class SensorCalibration:
    """Calibration parameters for sensors."""
    acc_bias: np.ndarray
    gyro_bias: np.ndarray
    time_offset_ms: float = 0.0

class DataValidationError(ValueError):
    """Custom exception for invalid data formats."""
    pass

class AlignmentEngine:
    """
    Handles the temporal alignment and feature extraction for multi-modal craft data.
    """

    def __init__(self, 
                 imu_sample_rate: int = DEFAULT_IMU_SAMPLE_RATE, 
                 video_fps: int = DEFAULT_VIDEO_FPS,
                 device: str = 'cpu'):
        """
        Initialize the AlignmentEngine.

        Args:
            imu_sample_rate (int): Sampling rate of the IMU sensor.
            video_fps (int): Frames per second of the video stream.
            device (str): Computation device ('cpu' or 'cuda').
        """
        self.imu_sample_rate = imu_sample_rate
        self.video_fps = video_fps
        self.device = device
        self._calibration: Optional[SensorCalibration] = None
        
        # Calculate window sizes in discrete units
        self.imu_window_size = int((WINDOW_SIZE_MS / 1000.0) * imu_sample_rate)
        self.video_window_size = int((WINDOW_SIZE_MS / 1000.0) * video_fps)
        
        if TORCH_AVAILABLE:
            self.visual_encoder = self._build_visual_encoder().to(device)
            self.imu_encoder = self._build_imu_encoder().to(device)
            logger.info("PyTorch encoders initialized successfully.")
        else:
            self.visual_encoder = None
            self.imu_encoder = None
            logger.info("Running in NumPy-only mode (Encoders disabled).")

    def _build_visual_encoder(self) -> 'nn.Module':
        """Builds a dummy CNN for visual feature extraction."""
        if not TORCH_AVAILABLE: return None
        # Input: (Batch, Channels=3, Time=Frames, H, W) -> Simplified here to (Batch, Features)
        # In a real scenario, this would be a 3D-ResNet or similar
        return nn.Sequential(
            nn.Linear(512, 256), # Assuming pre-extracted features from a vision model
            nn.ReLU(),
            nn.Linear(256, EMBEDDING_DIM)
        )

    def _build_imu_encoder(self) -> 'nn.Module':
        """Builds a 1D CNN for IMU time-series feature extraction."""
        if not TORCH_AVAILABLE: return None
        # Input: (Batch, Channels=6, Length=imu_window_size)
        return nn.Sequential(
            nn.Conv1d(6, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.AdaptiveAvgPool1d(1), # Global pooling
            nn.Flatten(),
            nn.Linear(128, EMBEDDING_DIM)
        )

    def calibrate(self, calibration_data: SensorCalibration) -> None:
        """
        Set calibration parameters for the sensors.
        
        Args:
            calibration_data (SensorCalibration): Dataclass containing bias and offsets.
        """
        if not isinstance(calibration_data, SensorCalibration):
            raise TypeError("Invalid calibration data type.")
        self._calibration = calibration_data
        logger.info(f"Calibration applied. Time offset: {calibration_data.time_offset_ms}ms")

    def _validate_inputs(self, 
                         video_frames: np.ndarray, 
                         imu_data: np.ndarray, 
                         timestamps_video: np.ndarray, 
                         timestamps_imu: np.ndarray) -> None:
        """
        Validates the shape and consistency of input data streams.
        
        Input Formats:
            video_frames: (N, D) where N is frames, D is feature dimension (or flattened image dims).
            imu_data: (M, 6) where M is samples, 6 corresponds to [ax, ay, az, gx, gy, gz].
            timestamps_video: (N,) in milliseconds.
            timestamps_imu: (M,) in milliseconds.
        """
        if video_frames.shape[0] != timestamps_video.shape[0]:
            raise DataValidationError("Video frames and timestamps length mismatch.")
        if imu_data.shape[0] != timestamps_imu.shape[0]:
            raise DataValidationError("IMU data and timestamps length mismatch.")
        if imu_data.shape[1] != 6:
            raise DataValidationError("IMU data must have 6 channels (Accel X,Y,Z, Gyro X,Y,Z).")
        
        # Check for empty data
        if video_frames.size == 0 or imu_data.size == 0:
            raise DataValidationError("Input streams cannot be empty.")

    def align_streams_millisecond(self,
                                  video_frames: np.ndarray,
                                  imu_data: np.ndarray,
                                  timestamps_video: np.ndarray,
                                  timestamps_imu: np.ndarray
                                 ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Core Function 1: Temporal Alignment.
        Aligns high-freq IMU data with lower-freq video frames using nearest-neighbor 
        interpolation within sliding windows.
        
        Args:
            video_frames (np.ndarray): Visual features or frames.
            imu_data (np.ndarray): Raw IMU data.
            timestamps_video (np.ndarray): Video timestamps in ms.
            timestamps_imu (np.ndarray): IMU timestamps in ms.
            
        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray]: 
                - aligned_visual (N, D)
                - aligned_imu (N, 6, L) (L is padded window length)
                - aligned_masks (N,) (validity flags)
        """
        self._validate_inputs(video_frames, imu_data, timestamps_video, timestamps_imu)
        
        # Apply calibration offset if exists
        if self._calibration:
            imu_data = imu_data - np.concatenate([self._calibration.acc_bias, self._calibration.gyro_bias])
            timestamps_imu = timestamps_imu - self._calibration.time_offset_ms

        logger.info(f"Starting alignment. Video points: {len(timestamps_video)}, IMU points: {len(timestamps_imu)}")
        
        aligned_visual = []
        aligned_imu_windows = []
        valid_masks = []
        
        # Determine padding length based on window size
        target_imu_len = self.imu_window_size
        
        for i, t_video in enumerate(timestamps_video):
            # Define window center
            start_t = t_video - WINDOW_SIZE_MS / 2
            end_t = t_video + WINDOW_SIZE_MS / 2
            
            # Extract IMU slice
            mask = (timestamps_imu >= start_t) & (timestamps_imu <= end_t)
            imu_slice = imu_data[mask]
            
            if len(imu_slice) == 0:
                # Handle missing data: Zero padding or skipping
                # Here we append zeros and mark as invalid for the loss function later
                imu_padded = np.zeros((target_imu_len, 6))
                valid_masks.append(0)
            else:
                # Resample/Padding to fixed length
                # Simple truncation or zero-padding
                if len(imu_slice) >= target_imu_len:
                    imu_padded = imu_slice[:target_imu_len]
                else:
                    pad_width = target_imu_len - len(imu_slice)
                    imu_padded = np.pad(imu_slice, ((0, pad_width), (0, 0)), mode='constant')
                valid_masks.append(1)
            
            aligned_imu_windows.append(imu_padded)
            aligned_visual.append(video_frames[i])
            
        logger.info(f"Alignment complete. Generated {len(aligned_visual)} aligned pairs.")
        # Transpose IMU for PyTorch Conv1d (Batch, Channels, Length)
        return np.array(aligned_visual), np.transpose(np.array(aligned_imu_windows), (0, 2, 1)), np.array(valid_masks)

    def map_to_joint_embedding(self, 
                               visual_features: np.ndarray, 
                               imu_features: np.ndarray
                              ) -> Dict[str, Any]:
        """
        Core Function 2: Feature Mapping.
        Maps aligned features into the 'Gesture-Force' joint embedding space.
        
        Args:
            visual_features (np.ndarray): Aligned visual features.
            imu_features (np.ndarray): Aligned IMU features (Batch, 6, Length).
            
        Returns:
            Dict[str, Any]: Dictionary containing 'joint_vector', 'force_magnitude', 'gesture_class'.
        """
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch is required for embedding mapping.")
            
        self.visual_encoder.eval()
        self.imu_encoder.eval()
        
        with torch.no_grad():
            # Convert to tensors
            v_tensor = torch.tensor(visual_features, dtype=torch.float32).to(self.device)
            i_tensor = torch.tensor(imu_features, dtype=torch.float32).to(self.device)
            
            # Extract embeddings
            v_emb = self.visual_encoder(v_tensor) # (Batch, 128)
            i_emb = self.imu_encoder(i_tensor)    # (Batch, 128)
            
            # Fusion Strategy: Concatenation + Weighted Sum (Simplified)
            # Here we calculate a joint embedding and a 'force' scalar
            joint_embedding = (v_emb + i_emb) / 2.0
            
            # Normalize
            joint_embedding = F.normalize(joint_embedding, p=2, dim=1)
            
            # Calculate synthetic force metric (Euclidean norm of IMU embedding)
            force_metric = torch.norm(i_emb, p=2, dim=1, keepdim=True)
            
        logger.info(f"Mapped {visual_features.shape[0]} samples to joint embedding space.")
        
        return {
            "joint_vector": joint_embedding.cpu().numpy(),
            "force_magnitude": force_metric.cpu().numpy(),
            "raw_visual_emb": v_emb.cpu().numpy(),
            "raw_imu_emb": i_emb.cpu().numpy()
        }

    def visualize_alignment(self, 
                            aligned_imu: np.ndarray, 
                            save_path: str = "alignment_debug.png") -> None:
        """
        Helper Function: Visualization.
        Generates a heatmap of the aligned IMU data for debugging.
        
        Args:
            aligned_imu (np.ndarray): The aligned IMU data (Batch, 6, Length).
            save_path (str): Path to save the plot.
        """
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            # Average over batch to see typical signal
            avg_signal = np.mean(aligned_imu, axis=0) # (6, Length)
            
            plt.figure(figsize=(10, 6))
            sns.heatmap(avg_signal, cmap='coolwarm', yticklabels=['AccX', 'AccY', 'AccZ', 'GyroX', 'GyroY', 'GyroZ'])
            plt.title("Average Aligned IMU Signal Heatmap")
            plt.xlabel("Time Steps (Milliseconds resolution)")
            plt.ylabel("Sensor Channels")
            plt.savefig(save_path)
            plt.close()
            logger.info(f"Alignment visualization saved to {save_path}")
        except ImportError:
            logger.error("Matplotlib/Seaborn not installed. Cannot visualize.")
        except Exception as e:
            logger.error(f"Visualization failed: {str(e)}")

# --- Usage Example ---
if __name__ == "__main__":
    # 1. Setup dummy data
    N_VIDEO = 100  # 100 frames
    N_IMU = 2000   # 2000 IMU samples (20x density)
    D_FEATURE = 512
    
    # Video: Timestamps in ms (0 to 3300ms approx)
    t_vid = np.linspace(0, 3300, N_VIDEO)
    vid_data = np.random.rand(N_VIDEO, D_FEATURE)
    
    # IMU: Timestamps in ms (0 to 3300ms)
    t_imu = np.linspace(0, 3300, N_IMU)
    # Simulate IMU data: [ax, ay, az, gx, gy, gz]
    imu_data = np.random.randn(N_IMU, 6) * 0.1
    
    # Add a bias for calibration test
    calibration = SensorCalibration(
        acc_bias=np.array([0.01, 0.01, 0.02]),
        gyro_bias=np.array([0.001, 0.001, -0.001]),
        time_offset_ms=5.0
    )
    
    # 2. Initialize Engine
    engine = AlignmentEngine(imu_sample_rate=200, video_fps=30)
    engine.calibrate(calibration)
    
    # 3. Align Streams
    try:
        a_vid, a_imu, masks = engine.align_streams_millisecond(vid_data, imu_data, t_vid, t_imu)
        print(f"Aligned Visual Shape: {a_vid.shape}") # (100, 512)
        print(f"Aligned IMU Shape: {a_imu.shape}")    # (100, 6, 20)
        
        # 4. Map to Joint Space (if PyTorch available)
        if TORCH_AVAILABLE:
            embeddings = engine.map_to_joint_embedding(a_vid, a_imu)
            print(f"Joint Embedding Shape: {embeddings['joint_vector'].shape}") # (100, 128)
            
            # 5. Visualize
            engine.visualize_alignment(a_imu, save_path="skill_debug_output.png")
            
    except DataValidationError as e:
        logger.error(f"Data Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")