"""
Module: auto_针对_左右跨域重叠_能力的验证_测试ai_9d6ea3
Description: This module demonstrates the cross-domain application of biological immune system 
principles (specifically T-cell Negative Selection) to cybersecurity Intrusion Detection Systems (IDS).
It generates pseudo-code and a functional simulation to verify if an AI can map biological 
mechanisms to computational algorithms for optimizing anomaly detection.

Domain: Cognitive Science / Artificial General Intelligence (AGI) Testing
"""

import logging
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CrossDomain_Immune_IDS")

@dataclass
class NetworkPacket:
    """
    Represents a simplified network packet or system call trace.
    
    Attributes:
        source_ip (str): Origin of the packet.
        payload_signature (str): A string representing the content or behavior signature.
        is_malicious (bool): Ground truth label (unknown to the detector in real scenarios).
    """
    source_ip: str
    payload_signature: str
    is_malicious: bool = False

class NegativeSelectionIDS:
    """
    An Intrusion Detection System model based on the Negative Selection algorithm 
    found in the biological immune system.
    
    Biological Analogy:
    1. Self Set: Normal network traffic (Healthy host cells).
    2. Detectors: Randomly generated patterns (T-cells).
    3. Negative Selection: Discarding detectors that match 'Self' (Preventing autoimmunity).
    4. Monitoring: Detecting non-self patterns (Pathogens).
    """
    
    def __init__(self, self_tolerance_threshold: float = 0.8):
        """
        Initialize the IDS model.
        
        Args:
            self_tolerance_threshold (float): The similarity ratio required to consider 
                                              a detector 'self-reactive'.
        """
        if not 0.0 <= self_tolerance_threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
            
        self.self_set: List[str] = []
        self.detector_set: List[str] = []
        self.tolerance = self_tolerance_threshold
        logger.info("Initialized NegativeSelectionIDS with tolerance: %.2f", self_tolerance_threshold)

    def _calculate_affinity(self, seq1: str, seq2: str) -> float:
        """
        Helper function: Calculate the similarity (affinity) between two signatures.
        Uses a simple overlap/co-occurrence logic for pseudo-code demonstration.
        
        Args:
            seq1 (str): First signature (Detector).
            seq2 (str): Second signature (Self/Antigen).
            
        Returns:
            float: Similarity score between 0.0 and 1.0.
        """
        if not seq1 or not seq2:
            return 0.0
        
        # Simple character-level overlap calculation
        matches = 0
        min_len = min(len(seq1), len(seq2))
        
        # Use a subset for comparison to simulate partial binding
        window = 3
        for i in range(min_len - window + 1):
            if seq1[i:i+window] in seq2:
                matches += 1
                
        max_possible = max(len(seq1), len(seq2)) - window + 1
        return matches / max_possible if max_possible > 0 else 0.0

    def train_model(self, normal_traffic: List[NetworkPacket], population_size: int = 100) -> None:
        """
        Core Function 1: Generates and selects detectors via Negative Selection.
        
        Process:
        1. Define 'Self' (Normal behavior).
        2. Generate random candidates (Detectors).
        3. If candidate matches 'Self', delete it (Negative Selection).
        4. Retain candidates that do not match 'Self'.
        
        Args:
            normal_traffic (List[NetworkPacket]): Historical data of benign traffic.
            population_size (int): Number of detector candidates to generate.
        """
        logger.info("Starting training phase: Defining 'Self' and generating detectors...")
        
        # 1. Define Self Set
        self.self_set = [p.payload_signature for p in normal_traffic]
        
        # 2. Generate and Filter Detectors
        valid_detectors = []
        chars = "abcdef0123456789" # Simulating hex signatures
        
        attempts = 0
        max_attempts = population_size * 10 # Prevent infinite loops
        
        while len(valid_detectors) < population_size and attempts < max_attempts:
            attempts += 1
            # Generate random candidate (simulating genetic recombination)
            candidate = "".join(random.choice(chars) for _ in range(10))
            
            # Negative Selection Check
            is_self_reactive = False
            for self_sig in self.self_set:
                affinity = self._calculate_affinity(candidate, self_sig)
                if affinity >= self.tolerance:
                    is_self_reactive = True
                    break
            
            if not is_self_reactive:
                valid_detectors.append(candidate)
                
        self.detector_set = valid_detectors
        logger.info("Training complete. Generated %d non-self reactive detectors.", len(self.detector_set))

    def detect_intrusion(self, live_traffic: List[NetworkPacket]) -> List[Tuple[NetworkPacket, str]]:
        """
        Core Function 2: Scans live traffic using the mature detector set.
        
        Process:
        1. For each packet, check if any detector binds to it.
        2. If binding occurs, flag as an anomaly.
        
        Args:
            live_traffic (List[NetworkPacket]): Incoming network packets to monitor.
            
        Returns:
            List[Tuple[NetworkPacket, str]]: A list of detected anomalies with the matching detector.
        """
        if not self.detector_set:
            logger.error("Model has not been trained or no detectors survived selection.")
            return []

        logger.info("Starting intrusion detection monitoring...")
        anomalies = []
        
        for packet in live_traffic:
            for detector in self.detector_set:
                affinity = self._calculate_affinity(detector, packet.payload_signature)
                
                # If affinity is high, it matches the detector (Non-Self detected)
                if affinity >= self.tolerance:
                    alert_msg = f"Anomaly detected by detector {detector} (Score: {affinity:.2f})"
                    logger.warning("Alert: %s from %s", alert_msg, packet.source_ip)
                    anomalies.append((packet, alert_msg))
                    break # One detection is enough for this packet
        
        return anomalies

def generate_mock_traffic(num_samples: int, include_anomalies: bool = True) -> List[NetworkPacket]:
    """
    Utility function to generate synthetic data for testing.
    
    Args:
        num_samples (int): Number of packets to generate.
        include_anomalies (bool): Whether to inject malicious packets.
        
    Returns:
        List[NetworkPacket]: List of synthetic packets.
    """
    traffic = []
    normal_patterns = ["aaaa", "bbbb", "cccc", "1234", "safe"]
    anomaly_patterns = ["xyz", "mal", "hack", "virus", "999"]
    
    for i in range(num_samples):
        is_malicious = include_anomalies and random.random() < 0.1
        
        if is_malicious:
            payload = f"hdr_{random.choice(anomaly_patterns)}_{random.randint(1000, 9999)}"
        else:
            payload = f"hdr_{random.choice(normal_patterns)}_{random.randint(1000, 9999)}"
            
        traffic.append(NetworkPacket(
            source_ip=f"192.168.1.{random.randint(1, 50)}",
            payload_signature=payload,
            is_malicious=is_malicious
        ))
    return traffic

if __name__ == "__main__":
    # Example Usage demonstrating the Cross-Domain Logic
    
    print("--- Cross-Domain Capability Verification: Immune System -> Cyber Security ---")
    
    # 1. Prepare Data
    training_data = generate_mock_traffic(50, include_anomalies=False)
    test_data = generate_mock_traffic(20, include_anomalies=True)
    
    # 2. Initialize the 'Artificial Immune System'
    try:
        ids_system = NegativeSelectionIDS(self_tolerance_threshold=0.6)
        
        # 3. Train (Negative Selection Process)
        # Biological concept: T-cells that bind to self-peptides are apoptosed (killed).
        # Computational equivalent: Rules that match normal traffic are discarded.
        ids_system.train_model(training_data, population_size=50)
        
        # 4. Test (Intrusion Detection)
        # Biological concept: Remaining T-cells circulate to find non-self pathogens.
        # Computational equivalent: Detectors scan traffic for unknown patterns.
        alerts = ids_system.detect_intrusion(test_data)
        
        # 5. Validation Output
        print(f"\nDetection Results:")
        print(f"Total Test Packets: {len(test_data)}")
        print(f"Detected Anomalies: {len(alerts)}")
        
        # Calculate basic stats
        true_positives = sum(1 for p, _ in alerts if p.is_malicious)
        false_positives = sum(1 for p, _ in alerts if not p.is_malicious)
        actual_malicious = sum(1 for p in test_data if p.is_malicious)
        
        print(f"Actual Malicious: {actual_malicious}")
        print(f"True Positives: {true_positives}")
        print(f"False Positives: {false_positives}")
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
    except Exception as e:
        logger.critical(f"Unexpected system failure: {e}", exc_info=True)