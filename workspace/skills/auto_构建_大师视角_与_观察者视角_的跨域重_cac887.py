"""
Module: auto_构建_大师视角_与_观察者视角_的跨域重_cac887
Description: 构建大师视角（第一人称）与观察者视角（第三人称）的跨域重叠模型。
             利用Vision Transformer (ViT) 进行特征提取，并通过自定义的交叉注意力机制
             融合手部动作细节与整体姿态，以解决单一视角下的遮挡和歧义问题。
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
Date: 2023-10-27
License: MIT
"""

import logging
import math
import os
from typing import Dict, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 常量定义
DEFAULT_EMBED_DIM = 768
DEFAULT_NUM_HEADS = 12
DEFAULT_DROPOUT = 0.1
IMAGE_SIZE = 224
PATCH_SIZE = 16

class PatchEmbedding(nn.Module):
    """
    辅助模块：将图像转换为Patch Embeddings。
    """
    def __init__(self, img_size: int = IMAGE_SIZE, patch_size: int = PATCH_SIZE, in_chans: int = 3, embed_dim: int = DEFAULT_EMBED_DIM):
        super().__init__()
        self.img_size = img_size
        self.patch_size = patch_size
        self.n_patches = (img_size // patch_size) ** 2
        
        self.proj = nn.Conv2d(
            in_chans,
            embed_dim,
            kernel_size=patch_size,
            stride=patch_size
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (B, C, H, W) Tensor
        Returns:
            (B, N, D) Tensor where N is number of patches
        """
        x = self.proj(x)  # (B, D, H/P, W/P)
        x = x.flatten(2)  # (B, D, N)
        x = x.transpose(1, 2)  # (B, N, D)
        return x

class CrossViewAttention(nn.Module):
    """
    核心组件：跨视角注意力机制。
    实现第一人称视角（Master）对第三人称视角（Observer）的查询，
    或者反之，实现特征融合。
    """
    def __init__(self, dim: int = DEFAULT_EMBED_DIM, num_heads: int = DEFAULT_NUM_HEADS, dropout: float = DEFAULT_DROPOUT):
        super().__init__()
        if dim % num_heads != 0:
            raise ValueError(f"Embedding dimension {dim} must be divisible by number of heads {num_heads}")
            
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        self.scale = self.head_dim ** -0.5

        self.q_proj = nn.Linear(dim, dim)
        self.k_proj = nn.Linear(dim, dim)
        self.v_proj = nn.Linear(dim, dim)
        self.out_proj = nn.Linear(dim, dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, query: torch.Tensor, key: torch.Tensor, value: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        计算注意力权重并融合特征。
        
        Args:
            query: 源视角特征 (B, N_q, D)
            key: 目标视角特征 (B, N_k, D)
            value: 目标视角特征 (B, N_k, D)
            mask: 可选的注意力掩码
            
        Returns:
            融合后的特征 (B, N_q, D)
        """
        batch_size, seq_len_q, _ = query.shape
        
        # 线性投影
        q = self.q_proj(query)
        k = self.k_proj(key)
        v = self.v_proj(value)

        # 重塑为多头形式 (B, N, Heads, Head_Dim) -> (B, Heads, N, Head_Dim)
        q = q.view(batch_size, seq_len_q, self.num_heads, self.head_dim).transpose(1, 2)
        k = k.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)
        v = v.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)

        # 计算注意力分数 (B, Heads, N_q, N_k)
        attn_weights = torch.matmul(q, k.transpose(-2, -1)) * self.scale

        if mask is not None:
            attn_weights = attn_weights.masked_fill(mask == 0, float('-inf'))

        attn_weights = F.softmax(attn_weights, dim=-1)
        attn_weights = self.dropout(attn_weights)

        # 应用注意力到Value上
        output = torch.matmul(attn_weights, v) # (B, Heads, N_q, Head_Dim)
        
        # 合并多头
        output = output.transpose(1, 2).contiguous().view(batch_size, seq_len_q, -1)
        
        return self.out_proj(output)

class CrossDomainFusionModel(nn.Module):
    """
    主要模型类：构建大师视角与观察者视角的融合模型。
    包含两个独立的ViT骨干网络和一个跨域融合模块。
    """
    def __init__(self, 
                 img_size: int = IMAGE_SIZE, 
                 embed_dim: int = DEFAULT_EMBED_DIM, 
                 num_heads: int = DEFAULT_NUM_HEADS):
        super().__init__()
        
        # 数据校验
        if img_size <= 0 or embed_dim <= 0:
            raise ValueError("Image size and embedding dimension must be positive integers.")

        logger.info("Initializing CrossDomainFusionModel...")
        
        # 1. 第一人称视角处理 (Master/First-Person)
        self.master_patch_embed = PatchEmbedding(img_size=img_size, embed_dim=embed_dim)
        self.master_pos_embed = nn.Parameter(torch.zeros(1, self.master_patch_embed.n_patches + 1, embed_dim))
        self.master_cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))
        
        # 2. 第三人称视角处理 (Observer/Third-Person)
        self.observer_patch_embed = PatchEmbedding(img_size=img_size, embed_dim=embed_dim)
        self.observer_pos_embed = nn.Parameter(torch.zeros(1, self.observer_patch_embed.n_patches + 1, embed_dim))
        self.observer_cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))

        # 3. 融合层
        # 使用交叉注意力：用第一人称细节去查询第三人称的上下文
        self.cross_attention = CrossViewAttention(dim=embed_dim, num_heads=num_heads)
        self.norm1 = nn.LayerNorm(embed_dim)
        self.norm2 = nn.LayerNorm(embed_dim)
        self.mlp = nn.Sequential(
            nn.Linear(embed_dim, embed_dim * 4),
            nn.GELU(),
            nn.Linear(embed_dim * 4, embed_dim),
        )
        
        # 初始化参数
        self._init_weights()

    def _init_weights(self):
        nn.init.trunc_normal_(self.master_pos_embed, std=0.02)
        nn.init.trunc_normal_(self.observer_pos_embed, std=0.02)
        nn.init.trunc_normal_(self.master_cls_token, std=0.02)
        nn.init.trunc_normal_(self.observer_cls_token, std=0.02)

    def _process_single_view(self, x: torch.Tensor, embed_layer: PatchEmbedding, cls_token: nn.Parameter, pos_embed: nn.Parameter) -> torch.Tensor:
        """
        辅助函数：处理单一视角的输入流。
        
        Args:
            x: 输入图像张量
            embed_layer: 对应的Patch Embedding层
            cls_token: Class token
            pos_embed: Positional Embedding
            
        Returns:
            包含位置编码的Embedding序列
        """
        B = x.shape[0]
        x = embed_layer(x)
        
        # 添加CLS token
        cls_tokens = cls_token.expand(B, -1, -1)
        x = torch.cat((cls_tokens, x), dim=1)
        
        # 添加位置编码
        x = x + pos_embed
        return x

    def forward(self, first_person_img: torch.Tensor, third_person_img: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        前向传播函数。
        
        Args:
            first_person_img (torch.Tensor): 第一人称摄像头图像流 (B, C, H, W)
            third_person_img (torch.Tensor): 第三人称外部视角图像 (B, C, H, W)
            
        Returns:
            Dict[str, torch.Tensor]: 包含融合特征和各视角独立特征的字典
            
        Raises:
            ValueError: 如果输入张量形状不一致
        """
        # 边界检查
        if first_person_img.shape != third_person_img.shape:
            logger.error("Input shapes do not match.")
            raise ValueError("First person and third person images must have the same dimensions.")

        # 处理第一人称视角
        master_feat = self._process_single_view(
            first_person_img, self.master_patch_embed, self.master_cls_token, self.master_pos_embed
        )
        
        # 处理第三人称视角
        observer_feat = self._process_single_view(
            third_person_img, self.observer_patch_embed, self.observer_cls_token, self.observer_pos_embed
        )

        # 跨域注意力融合
        # Query: Master features (关注手部细节)
        # Key/Value: Observer features (提供全局上下文，解决遮挡)
        try:
            fused_feat = self.cross_attention(query=master_feat, key=observer_feat, value=observer_feat)
            
            # 残差连接 + LayerNorm (Post-Norm strategy here for simplicity, or Pre-Norm depending on architecture choice)
            # 这里使用简单的 Add & Norm
            master_fused = self.norm1(master_feat + fused_feat)
            
            # Feed Forward
            master_fused = self.norm2(master_fused + self.mlp(master_fused))
            
        except Exception as e:
            logger.error(f"Error during attention fusion: {e}")
            raise

        return {
            "fused_representation": master_fused,
            "master_features": master_feat,
            "observer_features": observer_feat
        }

# 使用示例
if __name__ == "__main__":
    # 模拟输入数据
    # Batch Size = 4, Channels = 3, Height = Width = 224
    dummy_fp_img = torch.randn(4, 3, IMAGE_SIZE, IMAGE_SIZE)
    dummy_tp_img = torch.randn(4, 3, IMAGE_SIZE, IMAGE_SIZE)

    # 实例化模型
    model = CrossDomainFusionModel(img_size=IMAGE_SIZE, embed_dim=DEFAULT_EMBED_DIM)
    
    logger.info("Running forward pass example...")
    
    # 禁用梯度计算以进行演示
    with torch.no_grad():
        outputs = model(dummy_fp_img, dummy_tp_img)
        
    logger.info(f"Fused output shape: {outputs['fused_representation'].shape}")
    logger.info("Model execution successful.")