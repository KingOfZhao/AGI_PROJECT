"""
模块名称: industrial_perceptual_atom_builder
功能描述: 将工业现场的多模态异构数据（PLC时序、音频事件、震动频谱）融合为统一的“感知原子”。

核心逻辑:
1. 数据清洗与标准化。
2. 基于时间戳的多模态数据对齐。
3. 因果窗口内的特征聚合，生成Perceptual Atom (PA)。
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义数据结构
@dataclass
class PerceptualAtom:
    """
    感知原子数据结构。
    代表了在特定时间窗口内，多模态数据融合后的最小逻辑单元。
    """
    atom_id: str
    start_time: datetime
    end_time: datetime
    modality_features: Dict[str, Any]  # 存储各模态的特征，如plc_status, audio_transcript
    is_anomaly: bool = False
    confidence: float = 0.0
    metadata: Dict[str, str] = field(default_factory=dict)

def _validate_timestamp(data: Dict[str, Any], key: str = 'timestamp') -> datetime:
    """
    辅助函数: 验证并转换时间戳字段。
    
    Args:
        data: 包含时间戳的字典。
        key: 时间戳键名。
        
    Returns:
        datetime: 转换后的时间对象。
        
    Raises:
        ValueError: 如果时间戳缺失或格式无效。
    """
    if key not in data:
        raise ValueError(f"Missing required field: {key}")
    
    ts = data[key]
    if isinstance(ts, datetime):
        return ts
    try:
        # 尝试解析常见格式
        return pd.to_datetime(ts).to_pydatetime()
    except Exception as e:
        logger.error(f"Timestamp parsing error for value {ts}: {e}")
        raise ValueError(f"Invalid timestamp format: {ts}")

def clean_plc_data(plc_logs: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    核心函数1: 清洗与标准化PLC时序数据。
    
    处理缺失值、去噪，并将状态码转换为布尔标记（如is_running）。
    
    Args:
        plc_logs: 原始PLC日志列表，每个字典包含 'timestamp', 'status_code', 'voltage'等。
        
    Returns:
        pd.DataFrame: 标准化后的DataFrame，包含时间索引。
        
    Example:
        >>> logs = [{'timestamp': '2023-10-01 10:00:00', 'status_code': 1, 'voltage': 380}]
        >>> df = clean_plc_data(logs)
    """
    if not plc_logs:
        logger.warning("Empty PLC logs provided.")
        return pd.DataFrame()

    cleaned_data = []
    for log in plc_logs:
        try:
            # 数据验证
            ts = _validate_timestamp(log)
            status = log.get('status_code')
            voltage = log.get('voltage')
            
            # 边界检查
            if voltage is not None and voltage < 0:
                logger.warning(f"Negative voltage detected at {ts}, capping to 0.")
                voltage = 0
            
            # 业务逻辑转换: 假设 status=1 为运行，其他为停机或故障
            is_running = (status == 1)
            is_stopping = not is_running
            
            cleaned_data.append({
                'timestamp': ts,
                'is_running': is_running,
                'is_stopping': is_stopping,
                'voltage': voltage if voltage is not None else np.nan
            })
        except ValueError as ve:
            logger.warning(f"Skipping invalid PLC log entry: {ve}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error processing PLC log: {e}")
            continue

    df = pd.DataFrame(cleaned_data)
    if not df.empty:
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        # 填充缺失电压为前向填充
        df['voltage'].fillna(method='ffill', inplace=True)
        
    logger.info(f"Cleaned PLC data: {len(df)} valid records.")
    return df

def align_multimodal_data(
    plc_df: pd.DataFrame,
    audio_events: List[Dict[str, Any]],
    spectrum_data: List[Dict[str, Any]],
    time_window_ms: int = 2000
) -> List[PerceptualAtom]:
    """
    核心函数2: 对齐多模态数据并构建感知原子。
    
    寻找因果重叠窗口：
    1. PLC显示停机(is_stopping=True)作为主触发器。
    2. 在停机前后 time_window_ms 毫秒内查找音频(异响)和震动(频谱异常)特征。
    3. 融合为PerceptualAtom。
    
    Args:
        plc_df: 清洗后的PLC数据框。
        audio_events: 音频事件列表，含 'timestamp', 'description', 'db_level'。
        spectrum_data: 震动频谱列表，含 'timestamp', 'peak_freq', 'amplitude'。
        time_window_ms: 搜索关联数据的时间窗口大小（毫秒）。
        
    Returns:
        List[PerceptualAtom]: 生成的感知原子列表。
    """
    if plc_df.empty:
        logger.error("PLC DataFrame is empty, cannot align modalities.")
        return []

    atoms: List[PerceptualAtom] = []
    
    # 预处理其他模态数据为DataFrame以便高效搜索
    audio_df = pd.DataFrame([{
        'timestamp': _validate_timestamp(e), 
        'desc': e.get('description'), 
        'db': e.get('db_level')
    } for e in audio_events if e]).set_index('timestamp').sort_index() if audio_events else pd.DataFrame()
    
    spectrum_df = pd.DataFrame([{
        'timestamp': _validate_timestamp(s), 
        'freq': s.get('peak_freq'), 
        'amp': s.get('amplitude')
    } for s in spectrum_data if s]).set_index('timestamp').sort_index() if spectrum_data else pd.DataFrame()

    # 筛选出停机事件
    stop_events = plc_df[plc_df['is_stopping'] == True]
    
    logger.info(f"Processing {len(stop_events)} potential stop events for alignment.")
    
    for ts, row in stop_events.iterrows():
        try:
            # 定义搜索窗口
            start_window = ts - pd.Timedelta(milliseconds=time_window_ms)
            end_window = ts + pd.Timedelta(milliseconds=time_window_ms)
            
            # 窗口内检索音频
            audio_in_window = audio_df.loc[start_window:end_window]
            audio_features = audio_in_window[['desc', 'db']].to_dict('records') if not audio_in_window.empty else []
            
            # 窗口内检索震动
            spectrum_in_window = spectrum_df.loc[start_window:end_window]
            spectrum_features = spectrum_in_window[['freq', 'amp']].to_dict('records') if not spectrum_in_window.empty else []
            
            # 构建感知原子
            has_audio_anomaly = any(a.get('db', 0) > 80 for a in audio_features)
            has_vibration_anomaly = any(s.get('amp', 0) > 5.0 for s in spectrum_features)
            
            # 简单的融合逻辑：如果多模态数据同时存在，置信度更高
            confidence = 0.5
            if has_audio_anomaly: confidence += 0.2
            if has_vibration_anomaly: confidence += 0.3
            
            atom = PerceptualAtom(
                atom_id=f"atom_{int(ts.timestamp())}",
                start_time=start_window.to_pydatetime(),
                end_time=end_window.to_pydatetime(),
                is_anomaly=True,
                confidence=min(confidence, 1.0),
                modality_features={
                    "plc_status": "STOPPED",
                    "voltage_at_stop": row.get('voltage'),
                    "audio_events": audio_features,
                    "vibration_spectrum": spectrum_features
                },
                metadata={
                    "source": "multimodal_fusion_engine",
                    "trigger": "plc_stop"
                }
            )
            atoms.append(atom)
            
        except Exception as e:
            logger.error(f"Error creating atom for timestamp {ts}: {e}")
            continue
            
    return atoms

# ================= 使用示例 =================
if __name__ == "__main__":
    # 模拟数据
    base_time = pd.Timestamp("2023-11-15 14:00:00")
    
    # 1. 模拟PLC数据
    mock_plc = [
        {'timestamp': base_time, 'status_code': 1, 'voltage': 380}, # Running
        {'timestamp': base_time + pd.Timedelta(seconds=1), 'status_code': 1, 'voltage': 381}, # Running
        {'timestamp': base_time + pd.Timedelta(seconds=2), 'status_code': 0, 'voltage': 10}, # Stopping
        {'timestamp': base_time + pd.Timedelta(seconds=3), 'status_code': 0, 'voltage': 0}  # Stopped
    ]
    
    # 2. 模拟音频数据 (听到异响)
    mock_audio = [
        {'timestamp': base_time + pd.Timedelta(seconds=1, milliseconds=950), 'description': 'metal_screech', 'db_level': 92}
    ]
    
    # 3. 模拟震动数据 (高频震动)
    mock_spectrum = [
        {'timestamp': base_time + pd.Timedelta(seconds=2, milliseconds=10), 'peak_freq': 5000, 'amplitude': 6.2}
    ]

    print("--- Step 1: Cleaning PLC Data ---")
    plc_df = clean_plc_data(mock_plc)
    print(plc_df.head())

    print("\n--- Step 2: Aligning and Fusing Data ---")
    perceptual_atoms = align_multimodal_data(plc_df, mock_audio, mock_spectrum, time_window_ms=500)
    
    for atom in perceptual_atoms:
        print(f"\nAtom ID: {atom.atom_id}")
        print(f"Time: {atom.start_time} - {atom.end_time}")
        print(f"Confidence: {atom.confidence}")
        print(f"Audio Detected: {atom.modality_features['audio_events']}")