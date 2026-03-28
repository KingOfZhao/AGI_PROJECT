"""
跨域异构数据适配中间件

该模块借鉴Flutter Channel的异步消息传递机制，构建了一套标准化的CAD/CAE数据管道。
它充当轻量级前端（如Flutter UI）与高性能后端（本地Native内核或云端仿真服务）之间的桥梁。

主要功能：
1. 异步方法调用：支持前端像调用本地API一样调用后端计算密集型任务。
2. 数据流式传输：支持将大规模仿真结果（如有限元分析数据）分片流式回传。
3. 数据标准化：在异构系统间进行数据格式的自动转换与验证。

输入格式 (JSON-like Dict):
{
    "task_id": "uuid",
    "method": "cae_simulation",
    "payload": { ... }  # 具体的CAD/CAE参数
}

输出格式:
成功: {"status": "success", "data": ...}
流式: Generator[Dict, None, None]
错误: {"status": "error", "message": "...", "code": ...}
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Dict, Optional, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("HeteroDataMiddleware")


class MiddlewareError(Exception):
    """中间件处理过程中的自定义错误基类。"""
    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code
        super().__init__(self.message)


@dataclass
class DataPacket:
    """标准化的数据包结构，用于跨域传输。"""
    task_id: str
    method: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


def validate_request_payload(payload: Dict[str, Any], required_keys: list) -> None:
    """
    辅助函数：验证请求数据的完整性和合法性。
    
    Args:
        payload: 待验证的字典数据。
        required_keys: 必须存在的键列表。
        
    Raises:
        ValueError: 如果缺少必要键或数据类型不匹配。
    """
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary.")
    
    missing_keys = [key for key in required_keys if key not in payload]
    if missing_keys:
        raise ValueError(f"Missing required keys in payload: {missing_keys}")
    
    logger.debug(f"Payload validation passed for keys: {required_keys}")


class CrossDomainMiddleware:
    """
    跨域异构数据适配中间件核心类。
    
    模拟Flutter Channel机制，管理前端请求与后端服务之间的通信。
    """

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._active_streams: Dict[str, bool] = {}

    def register_handler(self, method_name: str, handler: Callable) -> None:
        """
        注册一个后端处理器。
        
        Args:
            method_name: 方法名，对应前端调用的标识符。
            handler: 异步处理函数，接收DataPacket，返回处理结果。
        """
        if method_name in self._handlers:
            logger.warning(f"Handler for '{method_name}' is being overwritten.")
        self._handlers[method_name] = handler
        logger.info(f"Handler registered: {method_name}")

    async def dispatch_task(self, packet: DataPacket) -> Dict[str, Any]:
        """
        核心函数1：分发任务到对应的处理器。
        
        Args:
            packet: 包含任务信息的数据包。
            
        Returns:
            包含执行结果或错误信息的字典。
        """
        try:
            validate_request_payload(packet.payload, ["params"])
            
            if packet.method not in self._handlers:
                raise MiddlewareError(f"Method '{packet.method}' not found.", code=404)
            
            logger.info(f"Dispatching task {packet.task_id} for method {packet.method}")
            
            # 调用注册的Native/Cloud处理函数
            handler = self._handlers[packet.method]
            result = await handler(packet)
            
            return {
                "status": "success",
                "task_id": packet.task_id,
                "data": result
            }
            
        except ValueError as ve:
            logger.error(f"Validation error in task {packet.task_id}: {ve}")
            return {"status": "error", "message": str(ve), "code": 400}
        except MiddlewareError as me:
            logger.error(f"Middleware error in task {packet.task_id}: {me}")
            return {"status": "error", "message": me.message, "code": me.code}
        except Exception as e:
            logger.critical(f"Unexpected error in task {packet.task_id}: {e}", exc_info=True)
            return {"status": "error", "message": "Internal server error", "code": 500}

    async def stream_simulation_result(self, task_id: str, chunk_size: int = 1024) -> AsyncGenerator[Dict[str, Any], None]:
        """
        核心函数2：流式传输大规模仿真数据。
        
        模拟从CAE内核读取大量数据并分片发送回前端，避免UI阻塞。
        
        Args:
            task_id: 任务ID。
            chunk_size: 每个数据块的大小（模拟值）。
            
        Yields:
            包含数据片段的字典。
        """
        logger.info(f"Starting stream for task {task_id}")
        self._active_streams[task_id] = True
        
        try:
            # 模拟生成10个数据块
            for i in range(10):
                if not self._active_streams.get(task_id, False):
                    logger.warning(f"Stream {task_id} cancelled by client.")
                    break
                
                # 模拟计算延迟
                await asyncio.sleep(0.1)
                
                # 模拟异构数据转换 (例如：Native Binary -> JSON)
                chunk_data = {
                    "chunk_index": i,
                    "values": [x * 0.1 for x in range(i * 10, (i + 1) * 10)],
                    "metadata": {"type": "stress_tensor", "unit": "MPa"}
                }
                
                yield {
                    "status": "streaming",
                    "task_id": task_id,
                    "chunk": chunk_data
                }
            
            yield {"status": "completed", "task_id": task_id}
            
        except Exception as e:
            logger.error(f"Stream error for {task_id}: {e}")
            yield {"status": "error", "task_id": task_id, "message": str(e)}
        finally:
            self._active_streams.pop(task_id, None)
            logger.info(f"Stream finished for task {task_id}")

    def cancel_stream(self, task_id: str) -> None:
        """取消正在进行的流式传输。"""
        if task_id in self._active_streams:
            self._active_streams[task_id] = False
            logger.info(f"Stream cancellation requested for {task_id}")


# ==========================================
# 模拟后端服务
# ==========================================

async def mock_cae_kernel(packet: DataPacket) -> Dict[str, Any]:
    """
    模拟高性能CAE仿真内核。
    """
    params = packet.payload.get("params", {})
    mesh_id = params.get("mesh_id", "unknown")
    
    # 模拟耗时计算
    await asyncio.sleep(0.5)
    
    logger.info(f"CAE Kernel processed mesh {mesh_id}")
    return {
        "mesh_id": mesh_id,
        "nodes": 1000,
        "elements": 5000,
        "status": "converged"
    }


# ==========================================
# 使用示例
# ==========================================

async def main():
    # 初始化中间件
    middleware = CrossDomainMiddleware()
    
    # 注册后端服务
    middleware.register_handler("run_simulation", mock_cae_kernel)
    
    # 示例 1: 标准异步调用
    print("--- Example 1: Standard Async Call ---")
    task_packet = DataPacket(
        task_id=str(uuid.uuid4()),
        method="run_simulation",
        payload={"params": {"mesh_id": "MESH_001"}}
    )
    
    response = await middleware.dispatch_task(task_packet)
    print(f"Response: {response}\n")
    
    # 示例 2: 流式数据传输
    print("--- Example 2: Streaming Data ---")
    stream_task_id = str(uuid.uuid4())
    async for chunk in middleware.stream_simulation_result(stream_task_id):
        if chunk["status"] == "streaming":
            print(f"Received chunk {chunk['chunk']['chunk_index']}: {len(chunk['chunk']['values'])} values")
        else:
            print(f"Stream finished with status: {chunk['status']}")

if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())