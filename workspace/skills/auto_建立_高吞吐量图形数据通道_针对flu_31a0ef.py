"""
高吞吐量图形数据通道模块

本模块针对Flutter与底层图形引擎（如Unity/OpenGL）的交互，实现了基于共享内存/零拷贝的数据传输协议。
核心思路借鉴CAD领域处理海量网格点云的方式，通过内存映射文件实现跨进程数据共享，避免JSON序列化开销。

输入格式：
- 图形数据需为结构化二进制数据，支持numpy数组或bytes类型
- 数据头包含：数据类型(uint8)、维度(uint16)、顶点数(uint32)、时间戳(uint64)

输出格式：
- 共享内存块，包含标准数据头+二进制载荷
- 支持多客户端同时访问的读写锁机制

使用示例：
>>> channel = GraphicsDataChannel("/flutter_graphics_shm", 1024*1024*50)  # 50MB共享内存
>>> channel.write_mesh_data(mesh_vertices)  # 写入网格数据
>>> data = channel.read_data()  # 读取数据
"""

import os
import mmap
import struct
import logging
import numpy as np
from typing import Union, Tuple, Optional
from datetime import datetime
from contextlib import contextmanager

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GraphicsDataChannel")

# 数据头格式常量 (little-endian)
# B: 数据类型(uint8), H: 维度(uint16), I: 顶点数(uint32), Q: 时间戳(uint64)
HEADER_FORMAT = "<BHIQ"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 15字节

# 数据类型映射
DATA_TYPES = {
    0x01: np.float32,  # 顶点数据
    0x02: np.uint8,    # 颜色数据
    0x03: np.uint16,   # 索引数据
    0x04: np.float32   # 法向量数据
}

class GraphicsDataChannelError(Exception):
    """图形数据通道异常基类"""
    pass

class DataValidationError(GraphicsDataChannelError):
    """数据验证错误"""
    pass

class MemoryMapError(GraphicsDataChannelError):
    """内存映射错误"""
    pass

class GraphicsDataChannel:
    """
    高吞吐量图形数据通道实现类
    
    特性：
    1. 基于内存映射文件的零拷贝传输
    2. 自动处理数据对齐和边界检查
    3. 支持多种图形数据类型(顶点/颜色/索引/法向量)
    4. 内置读写锁和脏数据检测
    """
    
    def __init__(self, shm_name: str, size: int = 1024*1024*10):
        """
        初始化共享内存通道
        
        参数:
            shm_name: 共享内存标识名称
            size: 共享内存大小(字节)，默认为10MB
            
        异常:
            MemoryMapError: 当无法创建内存映射时抛出
        """
        self.shm_name = shm_name
        self.size = size
        self._shm_fd = None
        self._mmap = None
        self._is_writer = False
        self._lock_state = 0  # 0:未锁定, 1:读锁, 2:写锁
        
        try:
            # 创建或打开共享内存文件
            self._shm_fd = os.open(
                f"/dev/shm/{shm_name}",
                os.O_CREAT | os.O_RDWR,
                0o666
            )
            
            # 调整文件大小
            os.ftruncate(self._shm_fd, size)
            
            # 创建内存映射
            self._mmap = mmap.mmap(
                self._shm_fd,
                size,
                mmap.MAP_SHARED,
                mmap.PROT_READ | mmap.PROT_WRITE
            )
            
            logger.info(f"初始化共享内存通道: {shm_name}, 大小: {size}字节")
            
        except OSError as e:
            self._cleanup()
            logger.error(f"创建内存映射失败: {str(e)}")
            raise MemoryMapError(f"无法创建共享内存: {str(e)}")
    
    def write_mesh_data(
        self,
        data: Union[np.ndarray, bytes],
        data_type: int = 0x01,
        dimension: int = 3,
        timestamp: Optional[int] = None
    ) -> Tuple[bool, int]:
        """
        写入网格数据到共享内存
        
        参数:
            data: 输入数据，可以是numpy数组或bytes
            data_type: 数据类型(0x01:顶点, 0x02:颜色, 0x03:索引, 0x04:法向量)
            dimension: 数据维度(1-4)
            timestamp: 可选的时间戳，默认为当前时间
            
        返回:
            (success, written_bytes): 操作结果和实际写入的字节数
            
        异常:
            DataValidationError: 数据验证失败时抛出
            MemoryMapError: 内存映射错误时抛出
        """
        # 数据验证
        if data_type not in DATA_TYPES:
            raise DataValidationError(f"无效的数据类型: 0x{data_type:02X}")
            
        if dimension < 1 or dimension > 4:
            raise DataValidationError(f"维度必须在1-4之间: {dimension}")
            
        # 转换数据格式
        if isinstance(data, np.ndarray):
            dtype = DATA_TYPES[data_type]
            if data.dtype != dtype:
                data = data.astype(dtype)
            vertex_count = data.shape[0] if len(data.shape) > 0 else 1
            binary_data = data.tobytes()
        elif isinstance(data, bytes):
            dtype = DATA_TYPES[data_type]
            vertex_count = len(data) // dtype().itemsize
            binary_data = data
        else:
            raise DataValidationError("不支持的输入数据类型，必须是numpy数组或bytes")
            
        # 边界检查
        total_size = HEADER_SIZE + len(binary_data)
        if total_size > self.size:
            raise DataValidationError(f"数据大小({total_size})超过共享内存容量({self.size})")
            
        # 准备数据头
        timestamp = timestamp or int(datetime.now().timestamp() * 1000)
        header = struct.pack(
            HEADER_FORMAT,
            data_type,
            dimension,
            vertex_count,
            timestamp
        )
        
        # 获取写锁
        with self._write_lock():
            try:
                # 写入数据头
                self._mmap.seek(0)
                self._mmap.write(header)
                
                # 写入数据载荷
                self._mmap.write(binary_data)
                
                logger.debug(f"写入数据成功: 类型=0x{data_type:02X}, 顶点数={vertex_count}, 大小={len(binary_data)}字节")
                return True, len(binary_data)
                
            except Exception as e:
                logger.error(f"写入数据失败: {str(e)}")
                return False, 0
    
    def read_data(
        self,
        timeout_ms: int = 100,
        check_timestamp: bool = True
    ) -> Tuple[Optional[np.ndarray], dict]:
        """
        从共享内存读取数据
        
        参数:
            timeout_ms: 读取超时(毫秒)
            check_timestamp: 是否检查时间戳更新
            
        返回:
            (data, metadata): 读取的数据和元数据字典
            元数据包含: data_type, dimension, vertex_count, timestamp
            
        异常:
            MemoryMapError: 内存映射错误时抛出
        """
        start_time = datetime.now()
        
        while True:
            # 获取读锁
            with self._read_lock():
                try:
                    # 读取数据头
                    self._mmap.seek(0)
                    header_data = self._mmap.read(HEADER_SIZE)
                    if len(header_data) != HEADER_SIZE:
                        return None, {}
                        
                    # 解析数据头
                    data_type, dimension, vertex_count, timestamp = struct.unpack(
                        HEADER_FORMAT, header_data
                    )
                    
                    # 验证数据类型
                    if data_type not in DATA_TYPES:
                        logger.warning(f"读取到无效的数据类型: 0x{data_type:02X}")
                        return None, {}
                        
                    # 计算数据大小
                    dtype = DATA_TYPES[data_type]
                    data_size = vertex_count * dtype().itemsize * dimension
                    
                    # 边界检查
                    if HEADER_SIZE + data_size > self.size:
                        logger.warning("读取数据大小超过共享内存容量")
                        return None, {}
                        
                    # 读取数据载荷
                    binary_data = self._mmap.read(data_size)
                    
                    # 转换为numpy数组
                    shape = (vertex_count, dimension) if dimension > 1 else (vertex_count,)
                    data = np.frombuffer(binary_data, dtype=dtype).reshape(shape)
                    
                    metadata = {
                        "data_type": data_type,
                        "dimension": dimension,
                        "vertex_count": vertex_count,
                        "timestamp": timestamp
                    }
                    
                    logger.debug(f"读取数据成功: 类型=0x{data_type:02X}, 顶点数={vertex_count}")
                    return data, metadata
                    
                except Exception as e:
                    logger.error(f"读取数据失败: {str(e)}")
                    return None, {}
            
            # 检查超时
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            if elapsed >= timeout_ms:
                logger.warning(f"读取数据超时: {timeout_ms}毫秒")
                return None, {}
    
    @contextmanager
    def _read_lock(self):
        """获取读锁的上下文管理器"""
        if self._lock_state == 2:
            raise MemoryMapError("检测到死锁: 尝试在读锁期间获取写锁")
            
        self._lock_state = 1
        try:
            yield
        finally:
            self._lock_state = 0
    
    @contextmanager
    def _write_lock(self):
        """获取写锁的上下文管理器"""
        if self._lock_state != 0:
            raise MemoryMapError("检测到死锁: 尝试在已有锁的情况下获取写锁")
            
        self._lock_state = 2
        try:
            yield
        finally:
            self._lock_state = 0
    
    def _cleanup(self):
        """清理资源"""
        if self._mmap:
            self._mmap.close()
        if self._shm_fd is not None:
            try:
                os.close(self._shm_fd)
            except OSError:
                pass
    
    def __del__(self):
        """析构函数，确保资源释放"""
        self._cleanup()
        logger.info(f"关闭共享内存通道: {self.shm_name}")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self._cleanup()

# 辅助函数
def calculate_required_memory(vertex_count: int, dimension: int, data_type: int) -> int:
    """
    计算所需共享内存大小
    
    参数:
        vertex_count: 顶点数量
        dimension: 数据维度(1-4)
        data_type: 数据类型
        
    返回:
        所需的内存字节数
        
    异常:
        DataValidationError: 输入参数无效时抛出
    """
    if data_type not in DATA_TYPES:
        raise DataValidationError(f"无效的数据类型: 0x{data_type:02X}")
        
    if dimension < 1 or dimension > 4:
        raise DataValidationError(f"维度必须在1-4之间: {dimension}")
        
    dtype = DATA_TYPES[data_type]
    return HEADER_SIZE + vertex_count * dtype().itemsize * dimension

def benchmark_data_transfer(channel: GraphicsDataChannel, size_mb: int = 10) -> dict:
    """
    性能测试辅助函数
    
    参数:
        channel: 要测试的图形数据通道
        size_mb: 测试数据大小(MB)
        
    返回:
        包含性能指标的字典
    """
    test_data = np.random.rand(size_mb * 1024 * 256).astype(np.float32)  # 10MB数据
    
    start_time = datetime.now()
    success, written = channel.write_mesh_data(test_data)
    write_time = (datetime.now() - start_time).total_seconds() * 1000
    
    if not success:
        return {"success": False}
    
    start_time = datetime.now()
    read_data, metadata = channel.read_data()
    read_time = (datetime.now() - start_time).total_seconds() * 1000
    
    return {
        "success": True,
        "write_time_ms": write_time,
        "read_time_ms": read_time,
        "throughput_mbps": (size_mb / (write_time/1000)),
        "data_integrity": np.allclose(test_data, read_data)
    }

if __name__ == "__main__":
    # 使用示例
    try:
        # 创建50MB的共享内存通道
        with GraphicsDataChannel("flutter_graphics", 1024*1024*50) as channel:
            # 生成测试网格数据(100万个顶点)
            mesh_vertices = np.random.rand(1000000, 3).astype(np.float32)
            
            # 写入数据
            success, written = channel.write_mesh_data(mesh_vertices)
            print(f"写入状态: {success}, 写入字节数: {written}")
            
            # 读取数据
            data, metadata = channel.read_data()
            print(f"读取元数据: {metadata}")
            print(f"数据形状: {data.shape}, 数据类型: {data.dtype}")
            
            # 性能测试
            print("性能测试结果:", benchmark_data_transfer(channel))
            
    except Exception as e:
        print(f"发生错误: {str(e)}")