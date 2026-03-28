"""
Module: auto_cognitive_atomization.py
Description: Implements a cognitive atomization algorithm to extract Minimum Reusable Units (MRUs)
             from existing skill nodes using Graph Neural Networks (GNN) and clustering techniques.
"""

import logging
from typing import List, Tuple, Dict, Optional
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score
from sklearn.neighbors import kneighbors_graph
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
from torch_geometric.data import Data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cognitive_atomization.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GCNEncoder(nn.Module):
    """
    Graph Convolutional Network (GCN) based encoder for generating skill node embeddings.
    """
    def __init__(self, input_dim: int, hidden_dim: int = 64, output_dim: int = 32):
        super(GCNEncoder, self).__init__()
        self.conv1 = GCNConv(input_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, output_dim)

    def forward(self, data: Data) -> torch.Tensor:
        x, edge_index = data.x, data.edge_index
        x = F.relu(self.conv1(x, edge_index))
        x = F.dropout(x, training=self.training)
        embeddings = self.conv2(x, edge_index)
        return embeddings


class CognitiveAtomizer:
    """
    Extracts Minimum Reusable Units (MRUs) from a graph of skill nodes by analyzing
    structural and semantic overlaps using GNN and clustering.
    """

    def __init__(self, n_skills: int = 451, skill_dim: int = 128, device: str = 'cpu'):
        """
        Initialize the CognitiveAtomizer.

        Args:
            n_skills (int): Number of initial skill nodes (e.g., 322 or 451).
            skill_dim (int): Dimension of raw skill feature vectors.
            device (str): Computation device ('cpu' or 'cuda').
        """
        self.n_skills = n_skills
        self.skill_dim = skill_dim
        self.device = torch.device(device)
        self.model = GCNEncoder(input_dim=skill_dim).to(self.device)
        logger.info(f"CognitiveAtomizer initialized with {n_skills} nodes on {device}.")

    def construct_skill_graph(self, skill_features: np.ndarray, k_neighbors: int = 5) -> Data:
        """
        Constructs a graph data object from skill features using k-NN connectivity.

        Args:
            skill_features (np.ndarray): Matrix of shape (n_skills, skill_dim).
            k_neighbors (int): Number of neighbors for graph connectivity.

        Returns:
            Data: PyTorch Geometric Data object containing node features and edges.

        Raises:
            ValueError: If input dimensions do not match initialized parameters.
        """
        if skill_features.shape[0] != self.n_skills or skill_features.shape[1] != self.skill_dim:
            msg = (f"Expected features shape ({self.n_skills}, {self.skill_dim}), "
                   f"got {skill_features.shape}")
            logger.error(msg)
            raise ValueError(msg)

        logger.info("Constructing skill graph using k-NN...")
        # Generate adjacency matrix using k-NN
        adjacency = kneighbors_graph(skill_features, k_neighbors, mode='connectivity', include_self=False)
        # Convert to edge_index (COO format)
        edge_index = torch.tensor(np.array(adjacency.nonzero()), dtype=torch.long)
        x = torch.tensor(skill_features, dtype=torch.float32)

        data = Data(x=x, edge_index=edge_index).to(self.device)
        return data

    def train_gnn_embeddings(self, data: Data, epochs: int = 50, lr: float = 0.01) -> np.ndarray:
        """
        Trains the GCN model to generate structural embeddings. 
        Uses a reconstruction-like self-supervision approach (simplified for demo).

        Args:
            data (Data): Graph data object.
            epochs (int): Training epochs.
            lr (float): Learning rate.

        Returns:
            np.ndarray: Node embeddings of shape (n_skills, embedding_dim).
        """
        logger.info("Starting GNN training for structural embeddings...")
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        
        # For demonstration, we use a simplified unsupervised objective: 
        # minimizing distance between connected nodes (contrastive-like).
        self.model.train()
        
        for epoch in range(epochs):
            optimizer.zero_grad()
            embeddings = self.model(data)
            
            # Positive pairs (edges)
            pos_src, pos_dst = data.edge_index
            pos_sim = F.cosine_similarity(embeddings[pos_src], embeddings[pos_dst])
            
            # Negative sampling (random nodes not connected)
            neg_dst = torch.randint(0, self.n_skills, (pos_src.shape[0],), device=self.device)
            neg_sim = F.cosine_similarity(embeddings[pos_src], embeddings[neg_dst])
            
            # Margin loss
            loss = F.margin_ranking_loss(
                pos_sim, neg_sim, torch.ones_like(pos_sim), margin=0.5
            )
            
            loss.backward()
            optimizer.step()
            
            if epoch % 10 == 0:
                logger.debug(f"Epoch {epoch}, Loss: {loss.item():.4f}")

        logger.info("GNN training complete.")
        self.model.eval()
        with torch.no_grad():
            final_embeddings = self.model(data).cpu().numpy()
        return final_embeddings

    def extract_mrus(self, embeddings: np.ndarray, max_clusters: int = 50) -> Tuple[Dict[int, List[int]], float]:
        """
        Identifies MRUs (clusters of skills) using hierarchical clustering on embeddings.

        Args:
            embeddings (np.ndarray): Node embeddings.
            max_clusters (int): Maximum number of atomic units to extract.

        Returns:
            Tuple[Dict[int, List[int]], float]: 
                - Mapping of cluster_id to list of skill indices.
                - Silhouette score for quality evaluation.
        """
        if embeddings.shape[0] == 0:
            raise ValueError("Embeddings cannot be empty.")

        logger.info("Extracting MRUs via hierarchical clustering...")
        
        # Determine optimal number of clusters using Silhouette score
        best_score = -1.0
        best_labels = None
        
        # Search range: compress 322/451 nodes into fewer primitives
        min_k = max(2, int(self.n_skills / 20))  # e.g., at least 5% compression
        max_k = min(max_clusters, self.n_skills - 1)
        
        # Simple search loop (could be optimized)
        for n_clusters in range(min_k, max_k, 2):
            clusterer = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward')
            labels = clusterer.fit_predict(embeddings)
            
            if len(set(labels)) > 1:
                score = silhouette_score(embeddings, labels)
                if score > best_score:
                    best_score = score
                    best_labels = labels

        if best_labels is None:
            # Fallback if range was too small
            best_labels = np.zeros(self.n_skills, dtype=int)
            best_score = 0.0

        # Group skills by cluster
        mru_map = {}
        for idx, label in enumerate(best_labels):
            if label not in mru_map:
                mru_map[label] = []
            mru_map[label].append(idx)

        logger.info(f"Extracted {len(mru_map)} MRUs with Silhouette Score: {best_score:.4f}")
        return mru_map, best_score

    def analyze_overlap(self, mru_map: Dict[int, List[int]], skill_names: List[str]) -> List[str]:
        """
        Helper function to describe the logic of extracted MRUs.
        
        Args:
            mru_map (Dict): The clustered MRUs.
            skill_names (List[str]): List of original skill names corresponding to indices.
            
        Returns:
            List[str]: Descriptions of overlapping logic.
        """
        descriptions = []
        for mru_id, indices in mru_map.items():
            if len(indices) > 1:  # Only interested in merged skills
                combined_skills = [skill_names[i] for i in indices if i < len(skill_names)]
                # In a real AGI system, an LLM would summarize this.
                # Here we just list them as sharing "atomic logic".
                desc = f"MRU {mru_id}: Potential shared logic between {', '.join(combined_skills)}"
                descriptions.append(desc)
        return descriptions


# --- Usage Example ---
if __name__ == "__main__":
    # Setup mock data
    NUM_NODES = 322
    DIM = 128
    
    # 1. Generate dummy skill embeddings (e.g., from some previous semantic encoding)
    # In reality, these would be loaded from a database.
    mock_features = np.random.rand(NUM_NODES, DIM).astype(np.float32)
    mock_skill_names = [f"Skill_{i}" for i in range(NUM_NODES)]
    # Inject some correlation to simulate "Code Refactoring" and "Article Rewriting"
    # Let's say Skill_0 and Skill_1 are highly correlated
    mock_features[1] = mock_features[0] + np.random.normal(0, 0.1, DIM) 

    try:
        atomizer = CognitiveAtomizer(n_skills=NUM_NODES, skill_dim=DIM)
        
        # 2. Build Graph
        graph_data = atomizer.construct_skill_graph(mock_features, k_neighbors=5)
        
        # 3. Train GNN to get structural embeddings
        node_embeddings = atomizer.train_gnn_embeddings(graph_data, epochs=30)
        
        # 4. Extract MRUs
        mru_clusters, score = atomizer.extract_mrus(node_embeddings, max_clusters=30)
        
        # 5. Analyze Results
        insights = atomizer.analyze_overlap(mru_clusters, mock_skill_names)
        
        print("\n--- Extracted Cognitive Atoms (MRUs) ---")
        for insight in insights[:5]:  # Print first 5 findings
            print(insight)
            
        print(f"\nTotal Nodes: {NUM_NODES} -> Compressed into {len(mru_clusters)} Atoms")
        
    except Exception as e:
        logger.error(f"Critical failure in execution: {str(e)}", exc_info=True)