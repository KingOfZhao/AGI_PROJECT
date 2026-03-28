"""
模块名称: auto_validation_microservice_builder
描述: 验证AI能否基于现有2042个节点，自动构建一个可运行的'Hello World'级微服务架构。
      本模块负责生成Dockerfile、K8s配置、API代码以及自动化部署脚本，测试从'知识节点'
      到'可执行物理实体'的转化能力。
"""

import os
import logging
import subprocess
from typing import Dict, Optional, Any, List
from pathlib import Path
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("microservice_builder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class MicroServiceConfig:
    """
    微服务配置数据结构。
    
    属性:
        service_name: 服务名称
        port: 服务端口号
        image_name: Docker镜像名称
        replicas: K8s副本数量
        node_affinity: 节点亲和性标签
        resources: 资源限制
    """
    service_name: str
    port: int = 8080
    image_name: str = "hello-world-service"
    replicas: int = 1
    node_affinity: str = "worker-node"
    resources: Dict[str, Any] = field(default_factory=lambda: {
        "requests": {"cpu": "100m", "memory": "128Mi"},
        "limits": {"cpu": "500m", "memory": "512Mi"}
    })
    environment_vars: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """数据验证和边界检查"""
        if not isinstance(self.service_name, str) or not self.service_name:
            raise ValueError("service_name must be a non-empty string")
        if not (1 <= self.port <= 65535):
            raise ValueError(f"Invalid port number: {self.port}")
        if self.replicas < 1:
            raise ValueError("replicas must be at least 1")

def _generate_dockerfile_content() -> str:
    """
    生成Dockerfile内容。
    
    返回:
        str: Dockerfile文件内容
        
    使用示例:
        >>> content = _generate_dockerfile_content()
        >>> "FROM python:3.9-slim" in content
        True
    """
    return """# Auto-generated Dockerfile for Hello World Microservice
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port
EXPOSE 8080

# Define the command to run the application
CMD ["python", "app.py"]
"""

def _generate_requirements_content() -> str:
    """
    生成requirements.txt内容。
    
    返回:
        str: requirements.txt文件内容
    """
    return """flask==2.3.2
gunicorn==21.2.0
prometheus-client==0.17.1
"""

def _generate_k8s_deployment_content(config: MicroServiceConfig) -> str:
    """
    生成Kubernetes Deployment配置文件内容。
    
    参数:
        config: 微服务配置对象
        
    返回:
        str: YAML格式的K8s Deployment配置
        
    异常:
        ValueError: 如果配置无效
    """
    if not isinstance(config, MicroServiceConfig):
        raise TypeError("config must be an instance of MicroServiceConfig")
    
    # 转换环境变量为K8s格式
    env_vars = "\n".join([
        f"        - name: {k}\n          value: \"{v}\""
        for k, v in config.environment_vars.items()
    ]) if config.environment_vars else ""
    
    return f"""# Auto-generated Kubernetes Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {config.service_name}
  labels:
    app: {config.service_name}
spec:
  replicas: {config.replicas}
  selector:
    matchLabels:
      app: {config.service_name}
  template:
    metadata:
      labels:
        app: {config.service_name}
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: node-role.kubernetes.io/{config.node_affinity}
                operator: Exists
      containers:
      - name: {config.service_name}
        image: {config.image_name}:latest
        ports:
        - containerPort: {config.port}
        resources:
          requests:
            cpu: {config.resources['requests']['cpu']}
            memory: {config.resources['requests']['memory']}
          limits:
            cpu: {config.resources['limits']['cpu']}
            memory: {config.resources['limits']['memory']}
        env:
{env_vars}
---
apiVersion: v1
kind: Service
metadata:
  name: {config.service_name}-svc
spec:
  selector:
    app: {config.service_name}
  ports:
    - protocol: TCP
      port: 80
      targetPort: {config.port}
  type: LoadBalancer
"""

def _generate_app_code(config: MicroServiceConfig) -> str:
    """
    生成Flask应用代码。
    
    参数:
        config: 微服务配置对象
        
    返回:
        str: Flask应用Python代码
    """
    return f"""# Auto-generated Flask Application
from flask import Flask, jsonify
import logging
import os
from prometheus_client import start_http_server, Counter

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('request_count', 'Total request count')

@app.route('/')
def hello_world():
    REQUEST_COUNT.inc()
    logger.info("Hello World endpoint accessed")
    return jsonify({{"message": "Hello World", "service": "{config.service_name}"}})

@app.route('/health')
def health_check():
    return jsonify({{"status": "healthy"}})

if __name__ == '__main__':
    # Start Prometheus metrics server
    start_http_server(8000)
    
    # Run the Flask application
    app.run(host='0.0.0.0', port={config.port})
"""

def generate_microservice_structure(config: MicroServiceConfig, output_dir: str = "./generated_microservice") -> Dict[str, str]:
    """
    生成微服务架构的所有文件并保存到指定目录。
    
    参数:
        config: 微服务配置对象
        output_dir: 输出目录路径
        
    返回:
        Dict[str, str]: 生成的文件路径映射
        
    异常:
        OSError: 如果无法创建目录或文件
        ValueError: 如果配置无效
        
    使用示例:
        >>> config = MicroServiceConfig(service_name="test-service")
        >>> files = generate_microservice_structure(config)
        >>> "Dockerfile" in files
        True
    """
    logger.info(f"Generating microservice structure for {config.service_name}")
    
    try:
        # 创建输出目录
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created output directory: {output_dir}")
        
        # 生成文件内容
        dockerfile_content = _generate_dockerfile_content()
        requirements_content = _generate_requirements_content()
        k8s_content = _generate_k8s_deployment_content(config)
        app_code = _generate_app_code(config)
        
        # 定义文件路径
        file_paths = {
            "Dockerfile": os.path.join(output_dir, "Dockerfile"),
            "requirements.txt": os.path.join(output_dir, "requirements.txt"),
            "deployment.yaml": os.path.join(output_dir, "deployment.yaml"),
            "app.py": os.path.join(output_dir, "app.py"),
            "build_and_deploy.sh": os.path.join(output_dir, "build_and_deploy.sh")
        }
        
        # 写入文件
        for filename, content in {
            "Dockerfile": dockerfile_content,
            "requirements.txt": requirements_content,
            "deployment.yaml": k8s_content,
            "app.py": app_code
        }.items():
            with open(file_paths[filename], 'w') as f:
                f.write(content)
            logger.info(f"Generated {filename} at {file_paths[filename]}")
        
        # 生成部署脚本
        deploy_script = f"""#!/bin/bash
# Auto-generated deployment script for {config.service_name}

# Build Docker image
docker build -t {config.image_name}:latest .

# Push to container registry (optional)
# docker push {config.image_name}:latest

# Apply Kubernetes configuration
kubectl apply -f deployment.yaml

# Check deployment status
kubectl rollout status deployment/{config.service_name}

echo "Deployment complete for {config.service_name}"
"""
        with open(file_paths["build_and_deploy.sh"], 'w') as f:
            f.write(deploy_script)
        os.chmod(file_paths["build_and_deploy.sh"], 0o755)  # 设置可执行权限
        
        logger.info("Microservice structure generation completed successfully")
        return file_paths
        
    except OSError as e:
        logger.error(f"Failed to create directory or file: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during microservice generation: {e}")
        raise

def deploy_microservice(file_paths: Dict[str, str], auto_approve: bool = False) -> bool:
    """
    执行微服务部署。
    
    参数:
        file_paths: 文件路径映射 (来自generate_microservice_structure)
        auto_approve: 是否自动批准部署
        
    返回:
        bool: 部署是否成功
        
    异常:
        FileNotFoundError: 如果必需文件不存在
        subprocess.SubprocessError: 如果部署命令失败
    """
    logger.info("Starting microservice deployment")
    
    # 检查必需文件
    required_files = ["Dockerfile", "deployment.yaml", "app.py"]
    for file_type in required_files:
        if file_type not in file_paths or not os.path.exists(file_paths[file_type]):
            error_msg = f"Required file {file_type} not found"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
    
    if not auto_approve:
        # 在实际应用中，这里可以添加用户确认逻辑
        logger.info("Deployment would require approval in production environment")
        return False
    
    try:
        # 执行部署脚本
        deploy_script = file_paths["build_and_deploy.sh"]
        logger.info(f"Executing deployment script: {deploy_script}")
        
        # 使用subprocess运行部署脚本
        result = subprocess.run(
            ["bash", deploy_script],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"Deployment script output:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"Deployment script warnings:\n{result.stderr}")
        
        logger.info("Microservice deployed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Deployment failed with error:\n{e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during deployment: {e}")
        return False

def validate_deployment(service_name: str, timeout: int = 300) -> bool:
    """
    验证微服务部署是否成功。
    
    参数:
        service_name: 要验证的服务名称
        timeout: 验证超时时间(秒)
        
    返回:
        bool: 部署是否成功验证
        
    异常:
        subprocess.SubprocessError: 如果kubectl命令失败
    """
    logger.info(f"Validating deployment for service: {service_name}")
    
    try:
        # 检查部署状态
        result = subprocess.run(
            ["kubectl", "get", "deployment", service_name, "-o", "jsonpath='{.status.availableReplicas}'"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        
        if result.stdout.strip("'") == "0":
            logger.error("No available replicas found")
            return False
        
        # 检查服务状态
        service_result = subprocess.run(
            ["kubectl", "get", "service", f"{service_name}-svc", "-o", "jsonpath='{.status.loadBalancer.ingress}'"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        
        if not service_result.stdout.strip("'"):
            logger.warning("Service LoadBalancer IP not assigned yet")
        
        logger.info("Deployment validation successful")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error(f"Deployment validation timed out after {timeout} seconds")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"kubectl command failed: {e.stderr}")
        return False

if __name__ == "__main__":
    # 示例使用
    try:
        # 创建配置
        config = MicroServiceConfig(
            service_name="hello-world-service",
            port=8080,
            replicas=2,
            environment_vars={"ENV": "production", "LOG_LEVEL": "info"}
        )
        
        # 生成微服务结构
        file_paths = generate_microservice_structure(config)
        print("Generated files:", file_paths)
        
        # 在实际应用中，这里可以调用:
        # deploy_microservice(file_paths, auto_approve=True)
        # validate_deployment(config.service_name)
        
    except Exception as e:
        logger.error(f"Example execution failed: {e}")