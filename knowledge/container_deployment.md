# 容器化与部署模式

> 来源: 训练知识结构化提取 | 用于: 考试tooling题、生产部署

## 1. Docker最佳实践

### 容器调试清单
```
容器启动即退出(exit code 1):
1. docker run -it <image> /bin/sh  # 交互式检查环境
2. 检查ENTRYPOINT/CMD语法
3. 检查环境变量是否存在
4. 检查文件权限
5. 查看日志: docker logs --tail 100 <container>

exit code含义:
0   = 正常退出
1   = 应用错误（最常见）
137 = OOM killed
139 = 段错误
143 = SIGTERM（被kill）
```

### Dockerfile安全
```dockerfile
# ✅ 安全实践
FROM node:20-alpine        # 精简基础镜像
RUN adduser -D appuser    # 非root用户
USER appuser               # 切换到非root
WORKDIR /app
COPY package*.json ./
RUN npm ci --production    # 只装生产依赖
COPY . .
EXPOSE 3000
# 不暴露敏感信息: 用环境变量或secrets
CMD ["node", "server.js"]

# ❌ 反模式
FROM node:20               # 完整镜像，攻击面大
RUN npm install            # 不锁定依赖
USER root                  # root运行
```

### 多阶段构建
```dockerfile
# Build阶段
FROM node:20 AS builder
WORKDIR /app
COPY . .
RUN npm ci && npm run build

# 运行阶段（不包含build工具）
FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
CMD ["node", "dist/server.js"]
```

## 2. 容器网络模式

| 模式 | 用途 | 特点 |
|------|------|------|
| bridge | 默认，容器间通信 | 隔离，需要端口映射 |
| host | 容器直接用宿主网络 | 性能好但隔离差 |
| none | 无网络 | 安全隔离场景 |
| overlay | 跨主机容器通信 | Swarm/K8s用 |

## 3. 健康检查

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1
```

### 健康检查vs 就绪检查
- **Liveness**: 进程是否活着？死了就重启
- **Readiness**: 能不能接流量？不能就从负载均衡摘除
- **Startup**: 启动慢的应用，避免被liveness提前杀掉

## 4. 常见部署问题

### 内存限制导致OOM
```yaml
# docker-compose
services:
  app:
    deploy:
      resources:
        limits:
          memory: 512M  # 设置硬限制
        reservations:
          memory: 256M  # 保证最低可用
```

### 日志磁盘占满
```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
```

### 危险命令识别
```
🔴 极危险:
  rm -rf /        # 删根目录
  docker rm $(docker ps -aq)  # 删所有容器（包括运行的）
  > /dev/sda      # 覆盖磁盘
  chmod -R 777 /  # 全局可写
  curl | bash      # 远程代码执行

🟡 危险但有时需要:
  docker system prune -a  # 清理所有（包括未使用的镜像）
  DROP DATABASE prod      # 删生产数据库

🟢 安全:
  docker system prune -f  # 清理未使用的（不影响运行中的）
  docker image prune      # 只清悬空镜像
  journalctl --vacuum-time=7d  # 清日志（有保护）
```

## 5. CI/CD关键检查

### 部署前Checklist
```
□ 环境变量完整（不硬编码密钥）
□ 数据库迁移可回滚
□ 健康检查端点正常
□ 日志级别正确（生产不用DEBUG）
□ 资源限制已设置
□ 启动时间 < 60s
□ 优雅关闭（处理SIGTERM）
□ 静态资源有CDN缓存
□ HTTPS证书未过期
□ 回滚方案已准备
```
