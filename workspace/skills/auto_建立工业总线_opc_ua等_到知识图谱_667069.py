"""
工业总线到知识图谱映射模块

本模块实现了从工业总线（如OPC-UA）到知识图谱节点的自动映射管道。
支持实时数据流的反向传播，确保知识图谱与生产现场数据保持同步。

典型使用场景：
- 智能工厂中的设备状态实时监控
- 生产流程的知识图谱建模
- 基于工业物联网的预测性维护

依赖：
- opcua (pip install opcua)
- py2neo (pip install py2neo)
- pandas (pip install pandas)

作者: AGI System
版本: 1.0.0
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from opcua import Client, Node, ua
from py2neo import Graph, NodeMatcher

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("industrial_kg_mapper.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@dataclass
class OPCNodeConfig:
    """
    OPC-UA节点配置数据类
    
    属性:
        node_id: OPC-UA节点ID (例如: "ns=2;i=2")
        browse_name: 节点浏览名称
        kg_label: 知识图谱节点标签
        kg_properties: 知识图谱节点属性映射
    """
    node_id: str
    browse_name: str
    kg_label: str
    kg_properties: Dict[str, str] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.kg_properties is None:
            self.kg_properties = {}


class IndustrialBusToKGMapper:
    """
    工业总线到知识图谱映射器
    
    将工业总线(如OPC-UA)的数据节点映射到知识图谱中的节点，
    支持基于真实生产数据的反向传播。
    """
    
    def __init__(
        self, 
        opc_server_url: str, 
        kg_uri: str, 
        kg_user: str = None, 
        kg_password: str = None
    ):
        """
        初始化映射器
        
        参数:
            opc_server_url: OPC-UA服务器地址
            kg_uri: 知识图谱数据库URI (例如: "bolt://localhost:7687")
            kg_user: 知识图谱用户名
            kg_password: 知识图谱密码
            
        异常:
            ValueError: 当输入参数为空时
        """
        if not opc_server_url or not kg_uri:
            raise ValueError("OPC服务器URL和知识图谱URI不能为空")
            
        self.opc_server_url = opc_server_url
        self.kg_uri = kg_uri
        self.kg_user = kg_user
        self.kg_password = kg_password
        
        # 初始化连接
        self.opc_client = None
        self.kg_graph = None
        self.node_matcher = None
        
        logger.info(f"初始化映射器: OPC={opc_server_url}, KG={kg_uri}")
    
    def connect(self) -> bool:
        """
        建立与OPC-UA服务器和知识图谱的连接
        
        返回:
            bool: 连接成功返回True，否则返回False
            
        异常:
            ConnectionError: 当连接失败时
        """
        try:
            # 连接OPC-UA服务器
            self.opc_client = Client(self.opc_server_url)
            self.opc_client.connect()
            logger.info(f"成功连接到OPC-UA服务器: {self.opc_server_url}")
            
            # 连接知识图谱
            self.kg_graph = Graph(
                self.kg_uri, 
                user=self.kg_user, 
                password=self.kg_password
            )
            self.node_matcher = NodeMatcher(self.kg_graph)
            logger.info(f"成功连接到知识图谱: {self.kg_uri}")
            
            return True
            
        except Exception as e:
            error_msg = f"连接失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ConnectionError(error_msg)
    
    def disconnect(self) -> None:
        """断开与OPC-UA服务器和知识图谱的连接"""
        if self.opc_client:
            self.opc_client.disconnect()
            logger.info("已断开与OPC-UA服务器的连接")
            
        self.kg_graph = None
        self.node_matcher = None
        logger.info("已断开与知识图谱的连接")
    
    def _validate_node_config(self, config: OPCNodeConfig) -> bool:
        """
        验证节点配置的有效性
        
        参数:
            config: 节点配置对象
            
        返回:
            bool: 配置有效返回True，否则返回False
            
        异常:
            ValueError: 当配置无效时
        """
        if not config.node_id or not config.browse_name or not config.kg_label:
            raise ValueError("节点配置缺少必要字段")
            
        if not isinstance(config.kg_properties, dict):
            raise ValueError("kg_properties必须是字典类型")
            
        return True
    
    def _get_opc_node_value(self, node_id: str) -> Any:
        """
        从OPC-UA节点获取当前值
        
        参数:
            node_id: OPC-UA节点ID
            
        返回:
            Any: 节点的当前值
            
        异常:
            ValueError: 当节点不存在或读取失败时
        """
        try:
            node = self.opc_client.get_node(node_id)
            value = node.get_value()
            logger.debug(f"从OPC节点 {node_id} 读取值: {value}")
            return value
        except Exception as e:
            error_msg = f"读取OPC节点 {node_id} 失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
    
    def map_node_to_kg(
        self, 
        config: OPCNodeConfig, 
        timestamp: datetime = None,
        batch_mode: bool = False
    ) -> Dict[str, Any]:
        """
        将单个OPC-UA节点映射到知识图谱
        
        参数:
            config: OPC节点配置
            timestamp: 可选的时间戳，默认为当前时间
            batch_mode: 是否批处理模式，批处理模式下不会立即提交事务
            
        返回:
            Dict[str, Any]: 包含映射结果的字典
            
        异常:
            ValueError: 当配置无效或映射失败时
        """
        # 验证配置
        self._validate_node_config(config)
        
        # 获取OPC节点值
        try:
            node_value = self._get_opc_node_value(config.node_id)
        except Exception as e:
            raise ValueError(f"无法获取OPC节点值: {str(e)}")
        
        # 准备知识图谱节点属性
        if timestamp is None:
            timestamp = datetime.utcnow()
            
        properties = {
            "source_node_id": config.node_id,
            "browse_name": config.browse_name,
            "last_updated": timestamp.isoformat(),
            **config.kg_properties,
            "value": node_value,
        }
        
        # 创建或更新知识图谱节点
        try:
            # 检查节点是否已存在
            existing_node = self.node_matcher.match(
                config.kg_label, 
                source_node_id=config.node_id
            ).first()
            
            if existing_node:
                # 更新现有节点
                for key, value in properties.items():
                    existing_node[key] = value
                
                if not batch_mode:
                    self.kg_graph.push(existing_node)
                    
                logger.info(f"更新知识图谱节点: {config.kg_label} [{config.node_id}]")
                return {
                    "status": "updated",
                    "node_id": config.node_id,
                    "kg_label": config.kg_label,
                    "value": node_value,
                }
            else:
                # 创建新节点
                tx = self.kg_graph.begin()
                node = Node(config.kg_label, **properties)
                tx.create(node)
                
                if not batch_mode:
                    tx.commit()
                    
                logger.info(f"创建知识图谱节点: {config.kg_label} [{config.node_id}]")
                return {
                    "status": "created",
                    "node_id": config.node_id,
                    "kg_label": config.kg_label,
                    "value": node_value,
                }
                
        except Exception as e:
            error_msg = f"映射到知识图谱失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
    
    def batch_map_nodes_to_kg(
        self, 
        configs: List[OPCNodeConfig],
        timestamp: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        批量映射多个OPC-UA节点到知识图谱
        
        参数:
            configs: OPC节点配置列表
            timestamp: 可选的时间戳，默认为当前时间
            
        返回:
            List[Dict[str, Any]]: 包含每个节点映射结果的列表
            
        异常:
            ValueError: 当配置列表为空时
        """
        if not configs:
            raise ValueError("配置列表不能为空")
            
        if timestamp is None:
            timestamp = datetime.utcnow()
            
        results = []
        
        try:
            # 开始事务
            tx = self.kg_graph.begin()
            
            for config in configs:
                try:
                    # 验证配置
                    self._validate_node_config(config)
                    
                    # 获取OPC节点值
                    node_value = self._get_opc_node_value(config.node_id)
                    
                    # 准备知识图谱节点属性
                    properties = {
                        "source_node_id": config.node_id,
                        "browse_name": config.browse_name,
                        "last_updated": timestamp.isoformat(),
                        **config.kg_properties,
                        "value": node_value,
                    }
                    
                    # 创建或更新知识图谱节点
                    existing_node = self.node_matcher.match(
                        config.kg_label, 
                        source_node_id=config.node_id
                    ).first()
                    
                    if existing_node:
                        # 更新现有节点
                        for key, value in properties.items():
                            existing_node[key] = value
                        tx.push(existing_node)
                        status = "updated"
                    else:
                        # 创建新节点
                        node = Node(config.kg_label, **properties)
                        tx.create(node)
                        status = "created"
                        
                    results.append({
                        "status": status,
                        "node_id": config.node_id,
                        "kg_label": config.kg_label,
                        "value": node_value,
                    })
                    
                except Exception as e:
                    logger.error(f"处理节点 {config.node_id} 失败: {str(e)}", exc_info=True)
                    results.append({
                        "status": "error",
                        "node_id": config.node_id,
                        "error": str(e),
                    })
            
            # 提交事务
            tx.commit()
            logger.info(f"批量映射完成: {len(results)} 个节点")
            return results
            
        except Exception as e:
            error_msg = f"批量映射失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
    
    def create_relationships(
        self,
        relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        在知识图谱中创建节点之间的关系
        
        参数:
            relationships: 关系配置列表，每个元素包含:
                - start_node_id: 起始节点ID
                - end_node_id: 结束节点ID
                - relationship_type: 关系类型
                - properties: 可选的关系属性
                
        返回:
            List[Dict[str, Any]]: 包含每个关系创建结果的列表
        """
        if not relationships:
            raise ValueError("关系列表不能为空")
            
        results = []
        
        try:
            for rel_config in relationships:
                start_node_id = rel_config.get("start_node_id")
                end_node_id = rel_config.get("end_node_id")
                rel_type = rel_config.get("relationship_type")
                properties = rel_config.get("properties", {})
                
                if not start_node_id or not end_node_id or not rel_type:
                    raise ValueError("关系配置缺少必要字段")
                    
                # 查找起始和结束节点
                start_node = self.node_matcher.match(source_node_id=start_node_id).first()
                end_node = self.node_matcher.match(source_node_id=end_node_id).first()
                
                if not start_node or not end_node:
                    raise ValueError(f"无法找到节点: {start_node_id} 或 {end_node_id}")
                    
                # 创建关系
                rel = Relationship(start_node, rel_type, end_node, **properties)
                self.kg_graph.create(rel)
                
                results.append({
                    "status": "created",
                    "start_node": start_node_id,
                    "end_node": end_node_id,
                    "relationship_type": rel_type,
                })
                logger.info(f"创建关系: {start_node_id} -[{rel_type}]-> {end_node_id}")
                
            return results
            
        except Exception as e:
            error_msg = f"创建关系失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
    
    def export_to_dataframe(self, node_ids: List[str]) -> pd.DataFrame:
        """
        将指定节点的数据导出为Pandas DataFrame
        
        参数:
            node_ids: 要导出的节点ID列表
            
        返回:
            pd.DataFrame: 包含节点数据的DataFrame
            
        异常:
            ValueError: 当节点ID列表为空时
        """
        if not node_ids:
            raise ValueError("节点ID列表不能为空")
            
        data = []
        
        try:
            for node_id in node_ids:
                node = self.node_matcher.match(source_node_id=node_id).first()
                if node:
                    node_data = dict(node)
                    node_data["node_id"] = node_id
                    data.append(node_data)
                else:
                    logger.warning(f"未找到节点: {node_id}")
                    
            df = pd.DataFrame(data)
            logger.info(f"导出 {len(data)} 个节点到DataFrame")
            return df
            
        except Exception as e:
            error_msg = f"导出到DataFrame失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)


# 使用示例
if __name__ == "__main__":
    # 示例配置
    OPC_SERVER_URL = "opc.tcp://localhost:4840"
    KG_URI = "bolt://localhost:7687"
    KG_USER = "neo4j"
    KG_PASSWORD = "password"
    
    # 创建映射器实例
    mapper = IndustrialBusToKGMapper(
        opc_server_url=OPC_SERVER_URL,
        kg_uri=KG_URI,
        kg_user=KG_USER,
        kg_password=KG_PASSWORD
    )
    
    try:
        # 连接到服务器
        mapper.connect()
        
        # 示例节点配置
        node_configs = [
            OPCNodeConfig(
                node_id="ns=2;i=2",
                browse_name="TemperatureSensor",
                kg_label="Sensor",
                kg_properties={"location": "Assembly Line 1", "unit": "°C"}
            ),
            OPCNodeConfig(
                node_id="ns=2;i=3",
                browse_name="PressureValve",
                kg_label="Actuator",
                kg_properties={"location": "Assembly Line 1", "max_pressure": "10 bar"}
            )
        ]
        
        # 映射节点到知识图谱
        results = mapper.batch_map_nodes_to_kg(node_configs)
        print("映射结果:", results)
        
        # 示例关系配置
        relationships = [
            {
                "start_node_id": "ns=2;i=2",
                "end_node_id": "ns=2;i=3",
                "relationship_type": "CONTROLS",
                "properties": {"since": "2023-01-01"}
            }
        ]
        
        # 创建关系
        rel_results = mapper.create_relationships(relationships)
        print("关系创建结果:", rel_results)
        
        # 导出数据
        df = mapper.export_to_dataframe(["ns=2;i=2", "ns=2;i=3"])
        print("导出数据:")
        print(df)
        
    finally:
        # 断开连接
        mapper.disconnect()