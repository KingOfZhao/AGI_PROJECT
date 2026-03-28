"""
分布式数字免疫记忆网络

该模块实现了一个模拟生物体液免疫机制的分布式网络安全防御系统。
系统在检测到新型攻击时，会生成数字抗体并瞬间广播至集群所有节点，
实现毫秒级的全网免疫，无需依赖中心化云端规则下发。

核心特性：
- 模拟初次免疫和二次免疫应答
- 分布式特征共享机制
- 毫秒级全网防御能力部署
- 自适应威胁学习系统
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
from enum import Enum, auto
import threading
from queue import Queue
import socket
import struct

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DigitalImmuneNetwork")


class ThreatLevel(Enum):
    """威胁等级枚举"""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


class AntibodyType(Enum):
    """数字抗体类型枚举"""
    SIGNATURE_BASED = auto()      # 基于特征码
    BEHAVIOR_BASED = auto()       # 基于行为
    ANOMALY_BASED = auto()        # 基于异常
    ZERO_DAY = auto()             # 零日漏洞


@dataclass
class ThreatFeature:
    """威胁特征数据结构"""
    feature_id: str
    feature_hash: str
    source_ip: str
    destination_port: int
    protocol: str
    payload_pattern: str
    attack_signature: str
    timestamp: float = field(default_factory=time.time)
    threat_level: ThreatLevel = ThreatLevel.MEDIUM
    antibody_type: AntibodyType = AntibodyType.SIGNATURE_BASED
    ttl: int = 3600  # 抗体存活时间(秒)
    
    def is_expired(self) -> bool:
        """检查抗体是否过期"""
        return time.time() - self.timestamp > self.ttl
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        data = asdict(self)
        data['threat_level'] = self.threat_level.name
        data['antibody_type'] = self.antibody_type.name
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ThreatFeature':
        """从字典创建实例"""
        data['threat_level'] = ThreatLevel[data['threat_level']]
        data['antibody_type'] = AntibodyType[data['antibody_type']]
        return cls(**data)


@dataclass
class NetworkNode:
    """网络节点数据结构"""
    node_id: str
    ip_address: str
    port: int
    last_heartbeat: float = field(default_factory=time.time)
    is_active: bool = True
    antibodies_count: int = 0
    
    def is_alive(self, timeout: int = 30) -> bool:
        """检查节点是否存活"""
        return self.is_active and (time.time() - self.last_heartbeat < timeout)


class DigitalImmuneNetwork:
    """
    分布式数字免疫记忆网络核心类
    
    该类实现了模拟生物体液免疫的分布式防御系统，包含以下核心功能：
    1. 威胁特征提取与分析
    2. 数字抗体生成
    3. 免疫记忆广播
    4. 全网防御规则同步
    """
    
    def __init__(self, node_id: str, cluster_port: int = 5555):
        """
        初始化免疫网络节点
        
        Args:
            node_id: 当前节点唯一标识符
            cluster_port: 集群通信端口
        """
        self.node_id = node_id
        self.cluster_port = cluster_port
        self.immune_memory: Dict[str, ThreatFeature] = {}
        self.cluster_nodes: Dict[str, NetworkNode] = {}
        self.broadcast_queue: Queue = Queue()
        self.lock = threading.RLock()
        self.running = False
        
        # 启动后台服务线程
        self._start_background_services()
        
        logger.info(f"Digital Immune Network initialized on node {node_id}")
    
    def _start_background_services(self) -> None:
        """启动后台服务线程"""
        self.running = True
        
        # 广播服务线程
        self.broadcast_thread = threading.Thread(
            target=self._broadcast_service,
            daemon=True
        )
        self.broadcast_thread.start()
        
        # 抗体过期清理线程
        self.cleanup_thread = threading.Thread(
            target=self._antibody_cleanup_service,
            daemon=True
        )
        self.cleanup_thread.start()
        
        # 心跳检测线程
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_service,
            daemon=True
        )
        self.heartbeat_thread.start()
    
    def analyze_threat(self, network_packet: Dict) -> Optional[ThreatFeature]:
        """
        分析网络威胁并提取特征
        
        这是核心函数之一，负责从网络数据包中提取威胁特征，
        并生成数字抗体。模拟生物免疫系统中的抗原识别过程。
        
        Args:
            network_packet: 网络数据包字典，包含以下字段：
                - source_ip: 源IP地址
                - dest_port: 目标端口
                - protocol: 协议类型
                - payload: 数据载荷
                - timestamp: 时间戳
                
        Returns:
            ThreatFeature: 如果检测到威胁，返回威胁特征对象；否则返回None
            
        Raises:
            ValueError: 当输入数据包格式不正确时
        """
        # 数据验证
        required_fields = ['source_ip', 'dest_port', 'protocol', 'payload']
        for field_name in required_fields:
            if field_name not in network_packet:
                logger.error(f"Missing required field: {field_name}")
                raise ValueError(f"Invalid packet format: missing {field_name}")
        
        # 边界检查
        if not self._validate_ip_address(network_packet['source_ip']):
            logger.warning(f"Invalid source IP: {network_packet['source_ip']}")
            return None
            
        if not (0 < network_packet['dest_port'] <= 65535):
            logger.warning(f"Invalid port: {network_packet['dest_port']}")
            return None
        
        try:
            # 提取特征
            feature_hash = self._extract_feature_hash(network_packet)
            
            # 检查是否已存在免疫记忆(二次免疫应答)
            with self.lock:
                if feature_hash in self.immune_memory:
                    existing_feature = self.immune_memory[feature_hash]
                    logger.info(f"Secondary immune response triggered for known threat: {feature_hash[:8]}")
                    # 更新时间戳，延长TTL
                    existing_feature.timestamp = time.time()
                    return existing_feature
            
            # 初次免疫：分析并生成新抗体
            threat_level = self._assess_threat_level(network_packet)
            antibody_type = self._determine_antibody_type(network_packet)
            
            feature = ThreatFeature(
                feature_id=self._generate_feature_id(),
                feature_hash=feature_hash,
                source_ip=network_packet['source_ip'],
                destination_port=network_packet['dest_port'],
                protocol=network_packet['protocol'],
                payload_pattern=self._extract_payload_pattern(network_packet['payload']),
                attack_signature=self._generate_attack_signature(network_packet),
                threat_level=threat_level,
                antibody_type=antibody_type,
                ttl=self._calculate_ttl(threat_level)
            )
            
            # 存储到免疫记忆
            with self.lock:
                self.immune_memory[feature_hash] = feature
            
            logger.info(
                f"Primary immune response: New antibody generated for threat {feature_hash[:8]} "
                f"(Level: {threat_level.name}, Type: {antibody_type.name})"
            )
            
            # 广播到集群
            self._queue_broadcast(feature)
            
            return feature
            
        except Exception as e:
            logger.error(f"Error analyzing threat: {str(e)}", exc_info=True)
            return None
    
    def broadcast_antibody(self, feature: ThreatFeature) -> bool:
        """
        广播数字抗体到集群所有节点
        
        这是核心函数之二，负责将新生成的数字抗体瞬间广播至全网，
        实现毫秒级的集群免疫记忆共享。
        
        Args:
            feature: 要广播的威胁特征/数字抗体
            
        Returns:
            bool: 广播是否成功
        """
        if not feature or not isinstance(feature, ThreatFeature):
            logger.error("Invalid feature for broadcast")
            return False
        
        try:
            message = {
                'type': 'ANTIBODY_BROADCAST',
                'source_node': self.node_id,
                'feature': feature.to_dict(),
                'timestamp': time.time()
            }
            
            message_json = json.dumps(message).encode('utf-8')
            
            # 获取活跃节点列表
            active_nodes = self._get_active_nodes()
            
            if not active_nodes:
                logger.warning("No active nodes available for broadcast")
                return False
            
            success_count = 0
            
            # 使用UDP进行快速广播
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            for node in active_nodes:
                if node.node_id == self.node_id:
                    continue  # 跳过自身
                    
                try:
                    sock.sendto(message_json, (node.ip_address, self.cluster_port))
                    success_count += 1
                except Exception as e:
                    logger.warning(f"Failed to send to {node.node_id}: {str(e)}")
                    node.is_active = False
            
            sock.close()
            
            logger.info(
                f"Antibody broadcast completed: {success_count}/{len(active_nodes)-1} nodes reached"
            )
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error broadcasting antibody: {str(e)}", exc_info=True)
            return False
    
    def receive_antibody(self, message_data: bytes) -> bool:
        """
        接收并处理来自其他节点的抗体广播
        
        Args:
            message_data: 接收到的消息数据
            
        Returns:
            bool: 处理是否成功
        """
        try:
            message = json.loads(message_data.decode('utf-8'))
            
            if message.get('type') != 'ANTIBODY_BROADCAST':
                return False
            
            feature_data = message.get('feature')
            if not feature_data:
                return False
            
            feature = ThreatFeature.from_dict(feature_data)
            
            # 检查是否已存在
            with self.lock:
                if feature.feature_hash in self.immune_memory:
                    logger.debug(f"Antibody already exists: {feature.feature_hash[:8]}")
                    return True
                
                # 存储新的免疫记忆
                self.immune_memory[feature.feature_hash] = feature
            
            logger.info(
                f"Received new antibody from node {message['source_node']}: "
                f"{feature.feature_hash[:8]} (Level: {feature.threat_level.name})"
            )
            
            return True
            
        except json.JSONDecodeError:
            logger.error("Invalid JSON format in received message")
            return False
        except Exception as e:
            logger.error(f"Error processing received antibody: {str(e)}", exc_info=True)
            return False
    
    def check_immunity(self, packet_info: Dict) -> Tuple[bool, Optional[ThreatFeature]]:
        """
        检查数据包是否匹配已知威胁特征
        
        Args:
            packet_info: 数据包信息字典
            
        Returns:
            Tuple[bool, Optional[ThreatFeature]]: 
                (是否具有免疫力, 匹配的威胁特征)
        """
        feature_hash = self._extract_feature_hash(packet_info)
        
        with self.lock:
            feature = self.immune_memory.get(feature_hash)
            
            if feature and not feature.is_expired():
                return True, feature
            
            return False, None
    
    # ==================== 辅助函数 ====================
    
    def _extract_feature_hash(self, packet: Dict) -> str:
        """
        提取数据包特征哈希值
        
        这是辅助函数，用于生成唯一标识威胁的特征码。
        """
        hash_input = (
            f"{packet.get('source_ip', '')}:"
            f"{packet.get('dest_port', '')}:"
            f"{packet.get('protocol', '')}:"
            f"{self._extract_payload_pattern(packet.get('payload', ''))}"
        )
        
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def _extract_payload_pattern(self, payload: str) -> str:
        """提取载荷模式"""
        if not payload:
            return ""
        
        # 简化处理：取前100个字符并移除随机变化部分
        pattern = payload[:100] if len(payload) > 100 else payload
        
        # 移除数字和随机字符串，保留结构性模式
        import re
        pattern = re.sub(r'\d+', 'N', pattern)
        pattern = re.sub(r'[a-f0-9]{8,}', 'RAND', pattern)
        
        return pattern
    
    def _generate_attack_signature(self, packet: Dict) -> str:
        """生成攻击特征签名"""
        sig_input = (
            f"{packet.get('protocol', 'TCP')}:"
            f"{packet.get('dest_port', 0)}:"
            f"{len(packet.get('payload', ''))}:"
            f"{packet.get('flags', '')}"
        )
        return hashlib.md5(sig_input.encode()).hexdigest()
    
    def _assess_threat_level(self, packet: Dict) -> ThreatLevel:
        """评估威胁等级"""
        payload = packet.get('payload', '')
        port = packet.get('dest_port', 0)
        
        # 高危端口检测
        critical_ports = {22, 23, 445, 3389, 1433, 3306}
        if port in critical_ports:
            return ThreatLevel.HIGH
        
        # 载荷特征检测
        high_risk_keywords = ['exec', 'eval', 'system', 'cmd', 'shell', 'root']
        if any(keyword in payload.lower() for keyword in high_risk_keywords):
            return ThreatLevel.CRITICAL
        
        # 异常模式检测
        if len(payload) > 10000:  # 大流量
            return ThreatLevel.MEDIUM
        
        return ThreatLevel.LOW
    
    def _determine_antibody_type(self, packet: Dict) -> AntibodyType:
        """确定抗体类型"""
        payload = packet.get('payload', '')
        
        # 已知攻击特征
        known_patterns = ['sqlmap', 'nmap', 'metasploit', 'nikto']
        if any(p in payload.lower() for p in known_patterns):
            return AntibodyType.SIGNATURE_BASED
        
        # 行为异常
        if packet.get('request_rate', 0) > 100:
            return AntibodyType.BEHAVIOR_BASED
        
        # 零日漏洞特征
        if 'exploit' in payload.lower() or 'cve-202' in payload.lower():
            return AntibodyType.ZERO_DAY
        
        return AntibodyType.ANOMALY_BASED
    
    def _calculate_ttl(self, threat_level: ThreatLevel) -> int:
        """根据威胁等级计算抗体TTL"""
        ttl_map = {
            ThreatLevel.LOW: 1800,      # 30分钟
            ThreatLevel.MEDIUM: 3600,   # 1小时
            ThreatLevel.HIGH: 86400,    # 24小时
            ThreatLevel.CRITICAL: 604800 # 7天
        }
        return ttl_map.get(threat_level, 3600)
    
    def _generate_feature_id(self) -> str:
        """生成唯一特征ID"""
        import uuid
        return f"AB-{uuid.uuid4().hex[:12].upper()}"
    
    def _validate_ip_address(self, ip: str) -> bool:
        """验证IP地址格式"""
        try:
            socket.inet_aton(ip)
            return True
        except socket.error:
            return False
    
    def _get_active_nodes(self) -> List[NetworkNode]:
        """获取活跃节点列表"""
        with self.lock:
            return [node for node in self.cluster_nodes.values() if node.is_alive()]
    
    def _queue_broadcast(self, feature: ThreatFeature) -> None:
        """将抗体加入广播队列"""
        self.broadcast_queue.put(feature)
    
    def _broadcast_service(self) -> None:
        """后台广播服务"""
        while self.running:
            try:
                feature = self.broadcast_queue.get(timeout=1)
                self.broadcast_antibody(feature)
            except:
                continue
    
    def _antibody_cleanup_service(self) -> None:
        """后台抗体清理服务"""
        while self.running:
            time.sleep(300)  # 每5分钟清理一次
            
            with self.lock:
                expired_hashes = [
                    h for h, f in self.immune_memory.items() 
                    if f.is_expired()
                ]
                
                for h in expired_hashes:
                    del self.immune_memory[h]
                
                if expired_hashes:
                    logger.info(f"Cleaned up {len(expired_hashes)} expired antibodies")
    
    def _heartbeat_service(self) -> None:
        """后台心跳检测服务"""
        while self.running:
            time.sleep(10)
            
            # 更新本节点心跳
            if self.node_id in self.cluster_nodes:
                self.cluster_nodes[self.node_id].last_heartbeat = time.time()
    
    def register_node(self, node_id: str, ip_address: str, port: int) -> bool:
        """
        注册集群节点
        
        Args:
            node_id: 节点ID
            ip_address: 节点IP地址
            port: 节点端口
            
        Returns:
            bool: 注册是否成功
        """
        if not self._validate_ip_address(ip_address):
            logger.error(f"Invalid IP address: {ip_address}")
            return False
        
        if not (0 < port <= 65535):
            logger.error(f"Invalid port: {port}")
            return False
        
        with self.lock:
            self.cluster_nodes[node_id] = NetworkNode(
                node_id=node_id,
                ip_address=ip_address,
                port=port
            )
        
        logger.info(f"Node registered: {node_id} at {ip_address}:{port}")
        return True
    
    def get_statistics(self) -> Dict:
        """获取系统统计信息"""
        with self.lock:
            return {
                'node_id': self.node_id,
                'total_antibodies': len(self.immune_memory),
                'active_nodes': len(self._get_active_nodes()),
                'antibodies_by_level': {
                    level.name: sum(1 for f in self.immune_memory.values() 
                                  if f.threat_level == level)
                    for level in ThreatLevel
                },
                'antibodies_by_type': {
                    atype.name: sum(1 for f in self.immune_memory.values() 
                                   if f.antibody_type == atype)
                    for atype in AntibodyType
                }
            }
    
    def shutdown(self) -> None:
        """关闭系统"""
        self.running = False
        logger.info("Digital Immune Network shutting down...")


# ==================== 使用示例 ====================
if __name__ == "__main__":
    """
    使用示例：
    
    1. 初始化免疫网络节点
    2. 模拟攻击检测与分析
    3. 演示免疫记忆共享
    """
    
    # 创建免疫网络实例
    immune_net = DigitalImmuneNetwork(node_id="NODE-001", cluster_port=5555)
    
    # 注册其他集群节点
    immune_net.register_node("NODE-002", "192.168.1.102", 5555)
    immune_net.register_node("NODE-003", "192.168.1.103", 5555)
    
    # 模拟检测到DDoS攻击
    attack_packet = {
        'source_ip': '10.0.0.55',
        'dest_port': 80,
        'protocol': 'TCP',
        'payload': 'GET / HTTP/1.1\r\nHost: target.com\r\n' * 100,
        'flags': 'SYN',
        'request_rate': 500
    }
    
    print("\n=== 检测到可疑流量 ===")
    feature = immune_net.analyze_threat(attack_packet)
    
    if feature:
        print(f"生成数字抗体: {feature.feature_id}")
        print(f"威胁等级: {feature.threat_level.name}")
        print(f"抗体类型: {feature.antibody_type.name}")
        print(f"特征哈希: {feature.feature_hash[:16]}...")
    
    # 检查免疫状态
    print("\n=== 检查免疫状态 ===")
    is_immune, matched = immune_net.check_immunity(attack_packet)
    print(f"是否具有免疫力: {is_immune}")
    if matched:
        print(f"匹配特征: {matched.feature_id}")
    
    # 获取系统统计
    print("\n=== 系统统计 ===")
    stats = immune_net.get_statistics()
    print(json.dumps(stats, indent=2))
    
    # 关闭系统
    immune_net.shutdown()