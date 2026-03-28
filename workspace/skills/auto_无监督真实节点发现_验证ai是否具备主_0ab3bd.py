"""
Module: auto_无监督真实节点发现_验证ai是否具备主_0ab3bd

This module is designed to validate an AGI system's ability to proactively discover
'true nodes' (latent patterns or entities) within noisy, unstructured data without
explicit instructions.

It simulates an E-commerce anomaly traffic log scenario. The system must identify
a hidden 'Brushing Order' (Fake Traffic) pattern amidst legitimate traffic and random noise,
treating this pattern as a newly discovered 'node' in the knowledge graph.

Key Capabilities Demonstrated:
1. Unsupervised Pattern Recognition (Isolation Forest / Statistical Analysis).
2. Anomaly Scoring and Filtering.
3. Proactive Labeling of unknown clusters.
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Any
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Constants and Configuration ---
RANDOM_STATE = 42
CONTAMINATION_RATE = 0.05  # Expected proportion of outliers in the dataset

class NoPatternFoundError(Exception):
    """Custom exception raised when no distinct pattern can be isolated."""
    pass

def _validate_and_preprocess_data(
    raw_data: List[Dict[str, Any]]
) -> Tuple[pd.DataFrame, StandardScaler]:
    """
    [Helper Function]
    Validates the input data structure, handles missing values, and normalizes features.
    
    Args:
        raw_data (List[Dict]): A list of dictionaries representing log entries.
            Expected keys: 'user_id', 'click_rate', 'session_duration', 'purchase_amount', 'device_age_days'.
    
    Returns:
        Tuple[pd.DataFrame, StandardScaler]: The cleaned DataFrame and the fitted Scaler object.
    
    Raises:
        ValueError: If data is empty or missing critical keys.
    """
    logger.info("Starting data validation and preprocessing...")
    
    if not raw_data:
        logger.error("Input data list is empty.")
        raise ValueError("Input data cannot be empty.")
        
    try:
        df = pd.DataFrame(raw_data)
    except Exception as e:
        logger.error(f"Failed to create DataFrame: {e}")
        raise ValueError(f"Invalid data format: {e}")

    # Check required columns (flexible check)
    required_cols = ['click_rate', 'session_duration', 'purchase_amount']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.error(f"Missing required feature columns: {missing_cols}")
        raise ValueError(f"Data missing required columns: {missing_cols}")

    # Handle missing values (Imputation)
    if df.isnull().values.any():
        logger.warning("Missing values detected. Filling with column medians.")
        df = df.fillna(df.median(numeric_only=True))

    # Feature Selection & Scaling
    features = df[required_cols]
    
    # Boundary Check: Ensure no negative values where not physically possible
    if (features < 0).any().any():
        logger.warning("Negative values found in features. Clipping to 0.")
        features = features.clip(lower=0)

    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)
    
    # Create a clean dataframe for processing
    processed_df = df.copy()
    processed_df[['click_rate_scaled', 'duration_scaled', 'amount_scaled']] = scaled_features
    
    logger.info(f"Preprocessing complete. Processed {len(processed_df)} records.")
    return processed_df, scaler

def discover_latent_nodes(
    traffic_logs: List[Dict[str, Any]], 
    sensitivity: float = 0.1
) -> Dict[str, Any]:
    """
    [Core Function 1]
    Analyzes traffic logs to proactively discover hidden 'Brushing Order' nodes.
    
    This function uses an unsupervised approach (Isolation Forest) to detect anomalies,
    then clusters these anomalies to identify specific patterns (e.g., high click rate,
    zero purchase amount, specific duration).
    
    Args:
        traffic_logs (List[Dict]): Raw log data.
        sensitivity (float): The contamination factor for the anomaly detection model.
    
    Returns:
        Dict[str, Any]: A discovery report containing:
            - 'total_samples': int
            - 'discovered_nodes': List[Dict] - Description of the found patterns.
            - 'anomaly_indices': List[int] - Indices of logs classified as the new node.
    
    Example:
        >>> logs = [{'click_rate': 0.5, 'session_duration': 100, 'purchase_amount': 20}, ...]
        >>> result = discover_latent_nodes(logs)
        >>> print(result['discovered_nodes'])
    """
    logger.info("Initializing Unsupervised Node Discovery Engine...")
    
    # Step 1: Preprocessing
    try:
        df, scaler = _validate_and_preprocess_data(traffic_logs)
    except ValueError as e:
        return {"error": str(e), "status": "failed"}

    feature_cols = ['click_rate_scaled', 'duration_scaled', 'amount_scaled']
    X = df[feature_cols].values

    # Step 2: Anomaly Detection (Isolation Forest)
    # The AI proactively looks for data points that "don't belong" to the majority distribution.
    logger.info("Training Isolation Forest for anomaly detection...")
    iso_forest = IsolationForest(
        n_estimators=100, 
        contamination=sensitivity, 
        random_state=RANDOM_STATE,
        n_jobs=-1
    )
    
    try:
        df['anomaly_score'] = iso_forest.fit_predict(X)
        # -1 is outlier, 1 is inlier
        outliers = df[df['anomaly_score'] == -1]
        inliers = df[df['anomaly_score'] == 1]
        
        logger.info(f"Detected {len(outliers)} potential anomalies out of {len(df)} total logs.")
        
        if len(outliers) < 5:
            logger.warning("Insufficient anomalies detected to form a pattern cluster.")
            return {
                "status": "success",
                "message": "No significant new nodes discovered.",
                "discovered_nodes": []
            }
            
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        raise RuntimeError("Model training failed.") from e

    # Step 3: Cluster the Outliers to define specific "Nodes"
    # We try to see if the anomalies are random noise or a cohesive new pattern.
    discovered_patterns = _characterize_anomaly_clusters(outliers, feature_cols)
    
    return {
        "status": "success",
        "total_samples": len(df),
        "anomaly_indices": outliers.index.tolist(),
        "discovered_nodes": discovered_patterns
    }

def _characterize_anomaly_clusters(
    outlier_df: pd.DataFrame, 
    feature_cols: List[str]
) -> List[Dict[str, Any]]:
    """
    [Core Function 2 - Internal Logic]
    Clusters the detected anomalies and characterizes them to define a 'Node'.
    
    Args:
        outlier_df (pd.DataFrame): Dataframe containing only the anomalies.
        feature_cols (List[str]): Columns used for clustering.
    
    Returns:
        List[Dict]: A list of discovered 'Node' definitions.
    """
    logger.info("Characterizing anomaly clusters...")
    
    # Use K-Means to group similar anomalies (e.g., one group might be bots, another DDoS)
    # Assuming we want to find at most 3 distinct patterns in the noise
    n_clusters = min(3, len(outlier_df) // 2) 
    if n_clusters == 0:
        return []

    kmeans = KMeans(n_clusters=n_clusters, random_state=RANDOM_STATE, n_init=10)
    outlier_df['cluster'] = kmeans.fit_predict(outlier_df[feature_cols])
    
    nodes = []
    
    # Analyze each cluster to create a semantic label
    for cluster_id in range(n_clusters):
        cluster_data = outlier_df[outlier_df['cluster'] == cluster_id]
        
        # Calculate statistical properties of this specific anomaly group
        stats = cluster_data[['click_rate', 'session_duration', 'purchase_amount']].describe()
        
        # Heuristic Logic to define the "Node" (The AGI "Insight")
        node_type = "Unknown Anomaly"
        insight = ""
        
        avg_click = stats.loc['mean', 'click_rate']
        avg_purchase = stats.loc['mean', 'purchase_amount']
        avg_duration = stats.loc['mean', 'session_duration']
        
        # Pattern Recognition Logic
        if avg_click > 50 and avg_purchase < 1:
            node_type = "New Node: High-Frequency Crawler / Brushing Bot"
            insight = "Extremely high click rate with near-zero conversion."
        elif avg_duration < 5 and avg_purchase > 100:
            node_type = "New Node: Automated Bulk Buyer / Script"
            insight = "Extremely short sessions with high purchase value."
        elif avg_duration > 1000 and avg_click < 1:
            node_type = "New Node: Connection Holder / Idle Bot"
            insight = "Long idle sessions with no activity."
        else:
            node_type = "New Node: Unspecified Behavioral Pattern"
            insight = "Requires further investigation."
            
        node_info = {
            "node_id": f"pattern_cluster_{cluster_id}",
            "label": node_type,
            "insight": insight,
            "statistics": {
                "avg_click_rate": float(avg_click),
                "avg_purchase": float(avg_purchase),
                "avg_duration": float(avg_duration),
                "sample_count": len(cluster_data)
            }
        }
        nodes.append(node_info)
        logger.info(f"Discovered Node: {node_type} | Samples: {len(cluster_data)}")
        
    return nodes

# --- Main Execution Block (Usage Example) ---
if __name__ == "__main__":
    # 1. Generate Synthetic Data (Simulating E-commerce Logs)
    # Normal users: moderate clicks, varied duration, varied purchase
    np.random.seed(42)
    n_normal = 1000
    normal_data = {
        'user_id': range(n_normal),
        'click_rate': np.random.normal(10, 5, n_normal).clip(0), # Avg 10 clicks
        'session_duration': np.random.normal(300, 100, n_normal), # 5 mins
        'purchase_amount': np.random.normal(50, 20, n_normal).clip(0),
        'device_age_days': np.random.randint(1, 365, n_normal)
    }
    
    # Noise/Anomalies (The "Hidden Truth"): Brushing Bots
    # High clicks, very short duration, 0 purchase (or very high fake purchase)
    n_bots = 50
    bot_data = {
        'user_id': range(n_normal, n_normal + n_bots),
        'click_rate': np.random.normal(120, 10, n_bots), # Abnormally high
        'session_duration': np.random.normal(2, 1, n_bots), # Abnormally short
        'purchase_amount': np.zeros(n_bots), # Zero real purchase
        'device_age_days': np.random.randint(1, 5, n_bots) # New devices
    }
    
    # Mix them up
    df_normal = pd.DataFrame(normal_data)
    df_bots = pd.DataFrame(bot_data)
    full_data_df = pd.concat([df_normal, df_bots]).sample(frac=1, random_state=42).reset_index(drop=True)
    
    # Convert to list of dicts for the function input
    input_logs = full_data_df.to_dict('records')
    
    print(f"Generated {len(input_logs)} log entries. Starting analysis...\n")
    
    # 2. Run the Discovery System
    try:
        result_report = discover_latent_nodes(input_logs, sensitivity=0.1)
        
        # 3. Display Results
        if "error" not in result_report:
            print("="*50)
            print("DISCOVERY REPORT")
            print("="*50)
            print(f"Total Logs Analyzed: {result_report['total_samples']}")
            print(f"Anomalies Detected: {len(result_report['anomaly_indices'])}")
            print("\n[Discovered Nodes]")
            for node in result_report['discovered_nodes']:
                print(f"- Label: {node['label']}")
                print(f"  Insight: {node['insight']}")
                print(f"  Sample Count: {node['statistics']['sample_count']}")
                print(f"  Avg Click Rate: {node['statistics']['avg_click_rate']:.2f}")
                print("-" * 30)
        else:
            print(f"Execution failed: {result_report['error']}")
            
    except Exception as e:
        logger.critical(f"System crashed: {e}")