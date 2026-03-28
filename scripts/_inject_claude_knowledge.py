#!/usr/bin/env python3
"""
Claude Opus 4 真实知识注入

用Claude的可验证知识填充认知格proven节点。
每个节点都是Claude能够确信为真的具体知识，
遵循认知格哲学：可实践、可验证、有真实物理路径。

覆盖领域：
1. 计算机科学基础（操作系统/网络/并发）
2. 数据库内核
3. 分布式系统
4. 安全工程
5. 算法设计模式
6. 机器学习基础
7. 工程实践
8. 数学基础
"""

# [PATH_BOOTSTRAP]
import sys as _sys, os as _os
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _d in [_PROJECT_ROOT, _os.path.join(_PROJECT_ROOT, 'core'), _os.path.join(_PROJECT_ROOT, 'api')]:
    if _d not in _sys.path:
        _sys.path.insert(0, _d)


import sys, sqlite3, json, time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import agi_v13_cognitive_lattice as agi

DB_PATH = ROOT / "memory.db"
VERIFIED_SOURCE = "claude_opus4_knowledge"

# ============================================================
# Claude 真实知识节点（每一条都是可验证的具体事实）
# ============================================================

CLAUDE_NODES = [
    # ---- 操作系统内核 ----
    {
        "content": "Linux进程调度器CFS(Completely Fair Scheduler)使用红黑树按虚拟运行时间(vruntime)排序所有可运行进程。每次调度选择vruntime最小的进程运行。验证方法：cat /proc/sched_debug 查看调度器状态，或阅读kernel/sched/fair.c源码。",
        "domain": "操作系统",
        "status": "proven",
    },
    {
        "content": "Linux虚拟内存通过页表(Page Table)将虚拟地址映射到物理地址。x86-64使用4级页表(PGD→PUD→PMD→PTE)，每级9位索引。缺页中断(Page Fault)时内核分配物理页并更新页表。验证：/proc/PID/maps显示进程虚拟内存映射。",
        "domain": "操作系统",
        "status": "proven",
    },
    {
        "content": "epoll是Linux高性能IO多路复用机制：epoll_create创建实例，epoll_ctl注册/修改/删除文件描述符，epoll_wait等待事件。内部使用红黑树存储监控的fd，就绪链表存储触发的事件。时间复杂度O(1)（不随fd数量增长）。Nginx/Node.js/Redis的事件循环都基于epoll。",
        "domain": "操作系统",
        "status": "proven",
    },
    {
        "content": "Linux容器技术的三大内核基础：(1)Namespace隔离资源视图(PID/Network/Mount/UTS/IPC/User)，(2)Cgroup限制资源用量(CPU/内存/IO/网络带宽)，(3)UnionFS分层文件系统(OverlayFS)。Docker/Podman都是这三者的用户态封装。验证：unshare命令可手动创建namespace。",
        "domain": "操作系统",
        "status": "proven",
    },

    # ---- 网络协议 ----
    {
        "content": "TCP三次握手具体过程：(1)客户端发SYN(seq=x)，(2)服务端回SYN-ACK(seq=y,ack=x+1)，(3)客户端发ACK(ack=y+1)。三次而非两次的原因：防止已失效的连接请求到达服务端后建立无效连接(RFC 793)。验证：tcpdump -i any tcp port 80 抓包观察。",
        "domain": "网络协议",
        "status": "proven",
    },
    {
        "content": "TCP拥塞控制四个阶段：(1)慢启动(cwnd从1指数增长到ssthresh)，(2)拥塞避免(cwnd线性增长)，(3)快速重传(收到3个重复ACK立即重传)，(4)快速恢复(cwnd减半继续传输)。Linux默认使用CUBIC算法(三次函数增长)。验证：ss -i命令查看cwnd值。",
        "domain": "网络协议",
        "status": "proven",
    },
    {
        "content": "HTTPS = HTTP + TLS。TLS 1.3握手只需1-RTT：ClientHello(支持的密码套件+密钥共享)→ServerHello(选定套件+密钥共享+证书+Finished)→客户端验证证书并发Finished。密钥交换使用ECDHE(椭圆曲线Diffie-Hellman)实现前向保密。验证：openssl s_client -connect example.com:443 -tls1_3",
        "domain": "网络协议",
        "status": "proven",
    },
    {
        "content": "DNS解析完整流程：浏览器缓存→OS缓存(/etc/hosts)→本地DNS递归服务器→根DNS(.)→顶级域DNS(.com)→权威DNS(example.com)→返回IP。DNS使用UDP 53端口(响应>512字节时切TCP)。验证：dig +trace example.com 可看到完整递归过程。",
        "domain": "网络协议",
        "status": "proven",
    },

    # ---- 数据库内核 ----
    {
        "content": "B+树是关系数据库索引的标准数据结构：所有数据存储在叶子节点，叶子节点通过链表相连支持范围查询，内部节点只存键值用于导航。MySQL InnoDB的主键索引(聚簇索引)就是B+树，数据页大小16KB。验证：EXPLAIN SELECT查看是否使用索引。",
        "domain": "数据库",
        "status": "proven",
    },
    {
        "content": "数据库MVCC(多版本并发控制)原理：每行数据保存多个版本（带事务ID和回滚指针），读操作访问快照版本不加锁，写操作创建新版本。PostgreSQL用xmin/xmax实现，MySQL InnoDB用undo log链实现。MVCC使读写互不阻塞。验证：BEGIN; SELECT txid_current(); 查看事务ID。",
        "domain": "数据库",
        "status": "proven",
    },
    {
        "content": "WAL(Write-Ahead Logging)是数据库持久性保证：数据修改前先写日志到磁盘(顺序写)，再异步刷数据页(随机写)。崩溃恢复时重放WAL即可。PostgreSQL的pg_wal/、MySQL的redo log、SQLite的WAL模式都使用此机制。顺序写比随机写快100倍以上。",
        "domain": "数据库",
        "status": "proven",
    },
    {
        "content": "SQL查询执行顺序(不同于书写顺序)：FROM→JOIN→WHERE→GROUP BY→HAVING→SELECT→DISTINCT→ORDER BY→LIMIT。理解执行顺序是SQL优化的基础。验证：EXPLAIN ANALYZE查看查询计划的实际执行路径和每步耗时。",
        "domain": "数据库",
        "status": "proven",
    },

    # ---- 分布式系统 ----
    {
        "content": "CAP定理(Eric Brewer 2000)：分布式系统不能同时满足一致性(Consistency)、可用性(Availability)、分区容错(Partition tolerance)三者。网络分区不可避免，因此必须在C和A之间选择。CP系统如ZooKeeper/etcd，AP系统如Cassandra/DynamoDB。",
        "domain": "分布式系统",
        "status": "proven",
    },
    {
        "content": "Raft一致性算法三个子问题：(1)领导选举(term编号+随机超时+多数派投票)，(2)日志复制(Leader将日志条目复制到多数派后提交)，(3)安全性(只有拥有最新日志的节点才能当选Leader)。etcd/Consul/TiKV都使用Raft。验证：阅读Raft论文(Ongaro & Ousterhout 2014)。",
        "domain": "分布式系统",
        "status": "proven",
    },
    {
        "content": "一致性哈希(Consistent Hashing)解决分布式缓存节点增减时的数据迁移问题：将节点和键都映射到环上，键归属于顺时针方向的第一个节点。添加/删除节点只影响相邻区间的数据。虚拟节点解决数据倾斜。Memcached/Redis Cluster/DynamoDB使用此技术。",
        "domain": "分布式系统",
        "status": "proven",
    },
    {
        "content": "分布式事务的两阶段提交(2PC)：(1)Prepare阶段协调者询问所有参与者能否提交，(2)Commit阶段协调者根据所有参与者的投票决定提交或回滚。缺点：协调者单点故障导致阻塞。改进：3PC(增加PreCommit阶段)和Saga模式(补偿事务)。",
        "domain": "分布式系统",
        "status": "proven",
    },

    # ---- 安全工程 ----
    {
        "content": "密码存储必须使用慢哈希：bcrypt(内置盐值+可调工作因子)或Argon2(抗GPU/ASIC攻击，赢得2015密码哈希竞赛)。绝不能用MD5/SHA256直接哈希密码(彩虹表攻击+GPU每秒数十亿次)。验证：python3 -c \"import bcrypt; print(bcrypt.hashpw(b'test', bcrypt.gensalt()))\"",
        "domain": "安全工程",
        "status": "proven",
    },
    {
        "content": "SQL注入防御唯一正确方法：参数化查询(Prepared Statement)。错误示例：f\"SELECT * FROM users WHERE name='{input}'\"。正确示例：cursor.execute('SELECT * FROM users WHERE name=?', (input,))。参数化查询让数据库将输入视为数据而非SQL代码。ORM框架默认使用参数化查询。",
        "domain": "安全工程",
        "status": "proven",
    },
    {
        "content": "JWT(JSON Web Token)结构：Header.Payload.Signature，Base64URL编码。签名用HMAC-SHA256或RSA验证完整性。安全要点：(1)永远在服务端验证签名，(2)检查exp过期时间，(3)使用HTTPS传输，(4)敏感数据不放payload(仅Base64编码非加密)。验证：jwt.io在线解码。",
        "domain": "安全工程",
        "status": "proven",
    },
    {
        "content": "CORS(跨域资源共享)机制：浏览器对跨域请求先发OPTIONS预检请求，服务端通过Access-Control-Allow-Origin/Methods/Headers响应头声明允许的来源。简单请求(GET/POST+简单Content-Type)不需要预检。CORS是浏览器行为，curl/后端请求不受限。",
        "domain": "安全工程",
        "status": "proven",
    },

    # ---- 算法设计模式 ----
    {
        "content": "动态规划的本质是记忆化递归：(1)定义状态和子问题，(2)找到状态转移方程，(3)确定初始条件，(4)确定计算顺序(自底向上)。经典例子：背包问题dp[i][w]=max(dp[i-1][w], dp[i-1][w-wi]+vi)。时间O(nW)空间可优化为O(W)。验证：实现01背包并对比暴力搜索结果。",
        "domain": "算法",
        "status": "proven",
    },
    {
        "content": "图的最短路径算法选择：(1)无权图用BFS O(V+E)，(2)非负权图用Dijkstra O((V+E)logV)，(3)有负权边用Bellman-Ford O(VE)，(4)全源最短路用Floyd-Warshall O(V³)。Dijkstra用最小堆贪心选择最近未访问节点。验证：手动模拟5节点图并对比结果。",
        "domain": "算法",
        "status": "proven",
    },
    {
        "content": "二分查找的正确实现要点：(1)循环条件left<=right(闭区间)或left<right(左闭右开)，(2)中间值mid=left+(right-left)//2(防溢出)，(3)边界更新left=mid+1和right=mid-1(闭区间)。常见bug：死循环(边界未收缩)、溢出(left+right)。验证：测试边界case[1]和空数组。",
        "domain": "算法",
        "status": "proven",
    },
    {
        "content": "哈希表解决冲突的两种主流方法：(1)链地址法(每个桶是链表/红黑树，Java HashMap当链表>8转红黑树)，(2)开放寻址法(线性探测/二次探测/双重哈希，Python dict使用开放寻址)。负载因子(元素数/桶数)超过阈值时需要扩容rehash。平均时间O(1)。",
        "domain": "算法",
        "status": "proven",
    },

    # ---- 机器学习基础 ----
    {
        "content": "梯度下降的三种变体：(1)批量GD(全数据集计算梯度，稳定但慢)，(2)随机SGD(单样本计算，快但噪声大)，(3)小批量Mini-batch SGD(通常32-256样本，平衡速度和稳定性)。学习率过大发散，过小收敛慢。Adam优化器结合动量和自适应学习率，是默认首选。",
        "domain": "机器学习",
        "status": "proven",
    },
    {
        "content": "Transformer的Self-Attention计算：Q=XWq, K=XWk, V=XWv, Attention(Q,K,V)=softmax(QK^T/√dk)V。除以√dk防止点积过大导致softmax梯度消失。多头注意力将QKV投影到h个子空间并行计算后拼接。时间复杂度O(n²d)，n是序列长度，d是维度。",
        "domain": "机器学习",
        "status": "proven",
    },
    {
        "content": "过拟合的诊断和解决：诊断标志是训练loss低但验证loss高(泛化差距大)。解决方法：(1)增加训练数据(最有效)，(2)正则化(L1稀疏/L2权重衰减/Dropout随机丢弃)，(3)早停(验证loss不再下降时停止)，(4)简化模型(减少参数)，(5)数据增强。",
        "domain": "机器学习",
        "status": "proven",
    },
    {
        "content": "Embedding是将离散符号映射到连续向量空间的技术。Word2Vec训练方式：(1)CBOW(用上下文预测中心词)，(2)Skip-gram(用中心词预测上下文)。语义关系通过向量运算体现：king-man+woman≈queen。现代大模型的token embedding维度通常2048-8192。",
        "domain": "机器学习",
        "status": "proven",
    },

    # ---- 工程实践 ----
    {
        "content": "Git内部是内容寻址文件系统：所有对象(blob/tree/commit/tag)用SHA-1哈希作为键存储在.git/objects/。commit对象包含tree指针+parent指针+作者+消息。分支只是指向commit的可变指针(.git/refs/heads/)。验证：git cat-file -p HEAD 查看commit对象内容。",
        "domain": "工程实践",
        "status": "proven",
    },
    {
        "content": "12-Factor App方法论核心原则：(1)代码库一份代码多次部署，(2)依赖显式声明(requirements.txt/package.json)，(3)配置存环境变量，(4)后端服务视为附加资源，(5)构建/发布/运行严格分离，(6)无状态进程，(7)端口绑定自包含，(8)并发通过进程模型扩展。来源：Heroku创始人Adam Wiggins。",
        "domain": "工程实践",
        "status": "proven",
    },
    {
        "content": "性能优化的正确顺序：(1)先测量(profiling)定位瓶颈，不要猜，(2)算法优化(O(n²)→O(nlogn))优先于微优化，(3)减少IO(批量查询/缓存/连接池)，(4)并发(多线程/异步IO)，(5)最后才考虑语言级微优化。Amdahl定律：加速比受不可并行部分限制。验证：python -m cProfile script.py",
        "domain": "工程实践",
        "status": "proven",
    },
    {
        "content": "API设计RESTful最佳实践：(1)URL用名词复数(/users不用/getUser)，(2)HTTP动词表达操作(GET读/POST创/PUT全更新/PATCH部分更新/DELETE删)，(3)状态码语义正确(200成功/201已创建/400客户端错误/404未找到/500服务端错误)，(4)分页用offset+limit或cursor，(5)版本号放URL(/v1/)或Header。",
        "domain": "工程实践",
        "status": "proven",
    },

    # ---- 数学基础 ----
    {
        "content": "大O复杂度常见级别(从快到慢)：O(1)常数→O(logn)二分→O(n)线性→O(nlogn)归并排序→O(n²)冒泡排序→O(2^n)子集枚举→O(n!)全排列。n=10^6时O(nlogn)≈2×10^7次运算(1秒内)，O(n²)=10^12次(超时)。面试/竞赛中1秒约10^8次运算。",
        "domain": "数学基础",
        "status": "proven",
    },
    {
        "content": "概率论贝叶斯定理：P(A|B)=P(B|A)*P(A)/P(B)。后验概率∝似然×先验。朴素贝叶斯分类器假设特征条件独立：P(C|x1,...,xn)∝P(C)∏P(xi|C)。垃圾邮件过滤是经典应用：P(垃圾|含'免费')=P('免费'|垃圾)*P(垃圾)/P('免费')。",
        "domain": "数学基础",
        "status": "proven",
    },
    {
        "content": "线性代数在AI中的核心应用：矩阵乘法是神经网络前向传播的基本运算(Y=XW+b)。特征值分解用于PCA降维。SVD(奇异值分解)用于推荐系统和数据压缩。GPU加速的本质是大规模并行矩阵运算(CUDA核心)。验证：numpy.linalg.svd()执行SVD分解。",
        "domain": "数学基础",
        "status": "proven",
    },

    # ---- 并发编程 ----
    {
        "content": "Python GIL(全局解释器锁)限制同一时刻只有一个线程执行Python字节码。CPU密集型任务用多进程(multiprocessing)绕过GIL。IO密集型任务用多线程(threading)或异步(asyncio)，因为IO等待时GIL会释放。验证：多线程CPU密集任务耗时≈单线程，多进程≈单线程/核数。",
        "domain": "并发编程",
        "status": "proven",
    },
    {
        "content": "死锁的四个必要条件(Coffman 1971)：(1)互斥(资源不可共享)，(2)持有并等待(持有资源同时请求新资源)，(3)不可抢占(已获取的资源不能被强制释放)，(4)循环等待(进程间形成环形等待链)。破坏任一条件可预防死锁。最实用方法：按固定顺序加锁(破坏循环等待)。",
        "domain": "并发编程",
        "status": "proven",
    },
    {
        "content": "asyncio事件循环的本质：单线程+协作式多任务。协程遇到await时主动让出控制权，事件循环切换到其他就绪的协程。适用于IO密集型(网络请求/文件读写)，不适用于CPU密集型。async def定义协程，await暂停执行，asyncio.gather并发执行多个协程。验证：asyncio.run(main())启动。",
        "domain": "并发编程",
        "status": "proven",
    },
]

# 节点间关系
CLAUDE_RELATIONS = [
    # 操作系统内部关系
    (0, 1, "depends_on", 0.85, "进程调度依赖虚拟内存管理"),
    (2, 3, "enables", 0.9, "epoll是容器网络IO的基础"),
    # 网络协议关系
    (4, 5, "depends_on", 0.9, "TCP拥塞控制建立在三次握手之上"),
    (4, 6, "extends", 0.9, "TLS在TCP之上提供安全层"),
    (7, 6, "depends_on", 0.85, "DNS解析后通过HTTPS建立连接"),
    # 数据库内部关系
    (8, 9, "complements", 0.9, "B+树索引和MVCC共同支撑高并发查询"),
    (9, 10, "depends_on", 0.9, "MVCC的旧版本数据通过WAL恢复"),
    (11, 8, "depends_on", 0.85, "SQL查询优化依赖索引结构"),
    # 分布式系统关系
    (12, 13, "implements", 0.9, "Raft是CP系统的一致性实现"),
    (14, 12, "implements", 0.85, "一致性哈希用于AP系统的数据分布"),
    # 安全关系
    (16, 17, "complements", 0.85, "参数化查询防注入+JWT防伪造=API安全基础"),
    (17, 19, "depends_on", 0.85, "JWT跨域需要CORS配置配合"),
    # 算法→机器学习
    (20, 24, "enables", 0.85, "动态规划思想是理解优化算法的基础"),
    (23, 25, "extends", 0.85, "哈希表是Embedding向量索引的基础数据结构"),
    # 工程实践
    (28, 29, "complements", 0.85, "Git版本管理+12-Factor方法论=现代工程基础"),
    (30, 31, "extends", 0.9, "性能优化指导API设计中的效率选择"),
    # 并发→操作系统
    (34, 2, "depends_on", 0.9, "asyncio事件循环底层使用epoll"),
    (33, 0, "depends_on", 0.85, "死锁发生在操作系统进程/线程层"),
]


def inject_nodes():
    """注入Claude真实知识节点"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    injected_ids = []
    new_count = 0
    skip_count = 0

    for i, node in enumerate(CLAUDE_NODES):
        content = node["content"]

        # 检查是否已存在
        c.execute("SELECT id FROM cognitive_nodes WHERE content = ?", (content[:200],))
        existing = c.fetchone()
        if existing:
            injected_ids.append(existing["id"])
            skip_count += 1
            continue

        # 生成embedding
        try:
            emb = agi.get_embedding(content)
        except Exception as e:
            print(f"  [警告] 节点{i} embedding失败: {e}")
            emb = None

        c.execute("""
            INSERT INTO cognitive_nodes (content, domain, status, embedding, verified_source)
            VALUES (?, ?, ?, ?, ?)
        """, (content, node["domain"], node["status"], emb, VERIFIED_SOURCE))
        injected_ids.append(c.lastrowid)
        new_count += 1
        print(f"  ✅ [{node['domain']}] {content[:60]}...")

    conn.commit()

    # 注入关系
    rel_count = 0
    for src_idx, tgt_idx, rel_type, conf, desc in CLAUDE_RELATIONS:
        if src_idx < len(injected_ids) and tgt_idx < len(injected_ids):
            src_id = injected_ids[src_idx]
            tgt_id = injected_ids[tgt_idx]
            try:
                c.execute("""
                    INSERT OR IGNORE INTO node_relations (node1_id, node2_id, relation_type, confidence)
                    VALUES (?, ?, ?, ?)
                """, (src_id, tgt_id, rel_type, conf))
                rel_count += 1
            except:
                pass

    conn.commit()
    conn.close()

    print(f"\n  新增: {new_count}, 跳过: {skip_count}, 关系: {rel_count}")
    return injected_ids


def verify():
    """验证注入结果"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute(f"SELECT COUNT(*) as cnt FROM cognitive_nodes WHERE verified_source = ?", (VERIFIED_SOURCE,))
    node_count = c.fetchone()["cnt"]

    c.execute(f"""
        SELECT domain, COUNT(*) as cnt FROM cognitive_nodes
        WHERE verified_source = ? GROUP BY domain ORDER BY cnt DESC
    """, (VERIFIED_SOURCE,))
    domains = c.fetchall()

    c.execute("SELECT COUNT(*) as cnt FROM cognitive_nodes WHERE status = 'proven'")
    total_proven = c.fetchone()["cnt"]

    c.execute("SELECT COUNT(*) as cnt FROM cognitive_nodes")
    total = c.fetchone()["cnt"]

    conn.close()

    print(f"\n  Claude知识节点: {node_count}")
    for d in domains:
        print(f"    [{d['domain']}]: {d['cnt']}")
    print(f"  全局proven: {total_proven}/{total}")


def test_search():
    """测试语义搜索"""
    lattice = agi.CognitiveLattice()
    queries = [
        "TCP拥塞控制算法",
        "数据库索引B+树",
        "分布式一致性Raft",
        "密码安全存储",
        "Python异步编程",
    ]

    print("\n  语义搜索测试:")
    hits = 0
    for q in queries:
        results = lattice.find_similar_nodes(q, threshold=0.2, limit=3)
        claude_results = [r for r in results if VERIFIED_SOURCE in str(r.get("content", "")[:200]) or
                          any(kw in r.get("content", "") for kw in ["TCP", "B+树", "Raft", "bcrypt", "asyncio", "GIL", "epoll", "WAL", "MVCC"])]
        if claude_results:
            hits += 1
            print(f"  ✅ '{q}' → {claude_results[0]['content'][:60]}...")
        elif results:
            print(f"  ⚠️  '{q}' → {results[0]['content'][:60]}...")
        else:
            print(f"  ❌ '{q}' → 无结果")

    print(f"\n  搜索命中: {hits}/{len(queries)}")


if __name__ == "__main__":
    print("=" * 60)
    print("  Claude Opus 4 真实知识注入")
    print("=" * 60)

    print("\n阶段1: 注入知识节点...")
    inject_nodes()

    print("\n阶段2: 验证注入...")
    verify()

    print("\n阶段3: 语义搜索测试...")
    test_search()

    print("\n" + "=" * 60)
    print("  完成!")
    print("=" * 60)
