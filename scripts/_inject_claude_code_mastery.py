#!/usr/bin/env python3
"""
Claude代码实现能力 → 认知格proven节点注入

将Claude在代码实现领域的全部核心能力总结为可验证的proven节点，
每个节点都是实际编程中可以直接应用的真实知识。
节点之间建立真实关系，形成可被本地模型复用的能力网络。
"""

# [PATH_BOOTSTRAP]
import sys as _sys, os as _os
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _d in [_PROJECT_ROOT, _os.path.join(_PROJECT_ROOT, 'core'), _os.path.join(_PROJECT_ROOT, 'api')]:
    if _d not in _sys.path:
        _sys.path.insert(0, _d)


import sys, sqlite3, json
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
DB_PATH = ROOT / "memory.db"

VERIFIED_SOURCE = "claude_code_mastery"

# ============================================================
# 节点数据：20个领域，每领域5-8个深度节点
# ============================================================

NODES = [
    # ── Python高级 ──
    ("Python高级", "装饰器链式组合原理：@a @b def f 等价于 f=a(b(f))。带参装饰器需三层嵌套：外层接受参数→中层接受函数→内层接受*args/**kwargs。functools.wraps保留元数据。实战：用装饰器实现缓存(@lru_cache)、重试(@retry)、权限校验(@auth_required)、计时(@timer)"),
    ("Python高级", "生成器与协程的本质区别：生成器用yield产出值(pull模型)，协程用yield接收值(push模型)。async/await是协程的语法糖，底层是生成器+事件循环。send()向生成器注入值，throw()注入异常，close()终止。yield from委托给子生成器，自动处理StopIteration"),
    ("Python高级", "上下文管理器(__enter__/__exit__)保证资源释放。contextlib.contextmanager用yield将函数变为上下文管理器。__exit__返回True抑制异常。实战模式：数据库连接池(获取/释放)、临时目录(创建/清理)、锁(获取/释放)、计时器(开始/结束)"),
    ("Python高级", "元类(metaclass)控制类的创建过程：type是所有类的元类，class Foo(metaclass=Meta)时Meta.__new__在类对象创建前调用。__init_subclass__是轻量替代方案。实战：ORM框架(Django Model)、接口强制(抽象基类ABC)、单例模式、自动注册"),
    ("Python高级", "GIL(全局解释器锁)限制同一时刻只有一个线程执行Python字节码。CPU密集→multiprocessing或C扩展；IO密集→threading或asyncio。multiprocessing.Pool的map/starmap并行计算，但进程间通信(Queue/Pipe)有序列化开销"),
    ("Python高级", "Python内存模型：引用计数为主+分代GC处理循环引用。__slots__替代__dict__节省40-50%内存。weakref避免循环引用导致内存泄漏。sys.getsizeof()查看对象大小，tracemalloc追踪内存分配。小整数池(-5~256)和字符串驻留(intern)优化"),
    ("Python高级", "类型标注(Type Hints)与运行时无关，仅供mypy/pyright静态检查。Union[A,B]或A|B表示联合类型，Optional[X]=X|None。TypeVar定义泛型，Protocol定义结构子类型(鸭子类型的静态版)。@overload为同一函数定义多个签名"),

    # ── JavaScript/TypeScript ──
    ("JavaScript", "事件循环(Event Loop)执行模型：调用栈(同步) → 微任务队列(Promise.then/queueMicrotask/MutationObserver) → 宏任务队列(setTimeout/setInterval/I/O)。每个宏任务执行完毕后清空所有微任务。async函数中await后的代码进入微任务队列"),
    ("JavaScript", "闭包(Closure)：函数捕获其词法作用域中的变量引用（不是值拷贝）。经典陷阱：for循环中var变量共享→用let或IIFE解决。闭包实现：模块模式(私有变量)、柯里化(curry)、记忆化(memoize)、偏函数(partial)"),
    ("JavaScript", "原型链：obj.__proto__指向构造函数的prototype。属性查找沿原型链向上直到null。Object.create(proto)创建指定原型的对象。class是原型继承的语法糖，super调用父类构造器。hasOwnProperty()区分自有属性和继承属性"),
    ("TypeScript", "TypeScript类型体操核心：条件类型 T extends U ? X : Y、映射类型 {[K in keyof T]: V}、模板字面量类型、infer关键字提取类型。Partial<T>/Required<T>/Pick<T,K>/Omit<T,K>/Record<K,V>五个核心工具类型。never类型表示不可达"),
    ("TypeScript", "TypeScript泛型约束与协变逆变：<T extends Constraint>限制泛型范围。函数参数位置是逆变的(接受更宽的类型)，返回值位置是协变的(接受更窄的类型)。strictFunctionTypes开启严格检查。readonly数组是可变数组的父类型"),

    # ── 设计模式 ──
    ("设计模式", "策略模式(Strategy)：将算法封装为独立类，通过接口互换。替代大量if-else/switch。Python实现：传入函数对象即可(函数是一等公民)。实战：支付方式选择、排序算法切换、验证规则组合、日志输出策略"),
    ("设计模式", "观察者模式(Observer/Pub-Sub)：主题维护观察者列表，状态变化时通知所有观察者。解耦事件发布者和订阅者。实战：事件总线(EventEmitter)、Vue响应式系统(Proxy+Dep+Watcher)、React状态管理(Redux dispatch→subscribe)"),
    ("设计模式", "工厂模式三层次：简单工厂(一个方法根据参数创建不同对象)→工厂方法(子类决定实例化哪个类)→抽象工厂(创建一族相关对象)。Python常用简单工厂+注册表模式(dict映射名称→类)。对比Builder：工厂一步创建，Builder分步构建复杂对象"),
    ("设计模式", "装饰器模式vs继承：装饰器动态组合行为(运行时)，继承静态定义(编译时)。装饰器遵循开闭原则(不修改原类)。Python的@decorator就是装饰器模式。Java I/O流是经典案例：BufferedInputStream(FileInputStream(f))层层包装"),
    ("设计模式", "依赖注入(DI)：不在类内部创建依赖，而是从外部注入。三种方式：构造器注入(推荐)、setter注入、接口注入。好处：可测试性(注入mock)、解耦(依赖抽象)、可配置(运行时切换实现)。IoC容器自动管理依赖图"),

    # ── 架构设计 ──
    ("架构设计", "Clean Architecture分层：Entity(业务规则)→UseCase(应用逻辑)→Interface Adapter(控制器/网关)→Framework(外部工具)。依赖规则：外层依赖内层，内层不知道外层。核心业务逻辑独立于框架/数据库/UI，可独立测试"),
    ("架构设计", "微服务拆分原则：按业务能力(Bounded Context)拆分，每个服务独立数据库(Database per Service)。服务间通信：同步(REST/gRPC)适合查询，异步(消息队列)适合命令。API Gateway统一入口，Service Mesh(Istio)管理服务间流量"),
    ("架构设计", "CQRS(命令查询分离)：写模型和读模型分开。写端处理命令→产生事件→更新写存储。读端消费事件→更新读优化视图(可以是不同数据库)。Event Sourcing：只存事件流不存状态，状态通过回放事件重建。适合审计追溯场景"),
    ("架构设计", "缓存策略四种模式：Cache-Aside(应用管理，先查缓存miss则查DB写入缓存)、Read-Through(缓存自动加载)、Write-Through(同步写缓存+DB)、Write-Behind(异步批量写DB)。缓存失效：TTL过期、主动失效、版本号。防穿透：布隆过滤器/空值缓存"),
    ("架构设计", "API版本化策略：URL路径(/v1/users)最直观但冗余、请求头(Accept: application/vnd.api.v1+json)符合REST但不直观、查询参数(?version=1)简单但不标准。推荐URL路径版本化。Breaking change定义：删除字段、改变类型、改变语义"),

    # ── 数据结构与算法 ──
    ("数据结构", "B-Tree/B+Tree：磁盘友好的平衡多路搜索树。B-Tree每个节点存键值对，B+Tree只在叶子存数据且叶子链表连接(范围查询友好)。MySQL InnoDB用B+Tree做索引，阶数由页大小(16KB)决定。插入可能导致节点分裂，删除可能导致节点合并"),
    ("数据结构", "跳表(Skip List)：有序链表+多层索引，查询O(logN)，实现比红黑树简单。Redis的Sorted Set用跳表实现。概率性平衡：每个节点以1/2概率晋升到上层。空间O(N)，插入/删除/查询都是O(logN)期望"),
    ("数据结构", "并查集(Union-Find/Disjoint Set)：高效处理集合合并与查询。两个优化：路径压缩(find时将节点直接挂到根)、按秩合并(矮树挂到高树)。双优化后近乎O(1)摊还。实战：连通性判断、Kruskal最小生成树、社交网络分组"),
    ("算法", "动态规划(DP)解题框架：1.定义状态(子问题是什么) 2.状态转移方程(子问题间关系) 3.初始条件 4.计算顺序(自底向上或记忆化搜索)。空间优化：滚动数组(只保留前一行)。经典：背包问题(0-1/完全/多重)、最长公共子序列、编辑距离"),
    ("算法", "图算法核心：BFS(最短路径/层序遍历)用队列、DFS(连通性/拓扑排序)用栈/递归。Dijkstra(非负权最短路)用最小堆O(ElogV)。拓扑排序(有向无环图DAG)：入度为0的节点先输出。强连通分量：Tarjan算法O(V+E)"),
    ("算法", "字符串匹配：暴力O(NM)→KMP O(N+M)通过next数组避免回溯→Rabin-Karp O(N+M)期望通过滚动哈希。后缀数组/后缀树处理多模式匹配。Trie树(前缀树)：前缀查询O(L)，自动补全/拼写检查/IP路由表(最长前缀匹配)"),

    # ── 数据库 ──
    ("数据库", "SQL查询优化核心：EXPLAIN分析执行计划，关注type(ALL全表扫描→ref索引→const常量)。覆盖索引(索引包含所有查询字段)避免回表。联合索引最左前缀原则。避免：SELECT *、WHERE函数转换(索引失效)、隐式类型转换、OR条件(用UNION替代)"),
    ("数据库", "事务隔离级别与问题：READ UNCOMMITTED(脏读)→READ COMMITTED(不可重复读,PostgreSQL默认)→REPEATABLE READ(幻读,MySQL InnoDB默认,通过MVCC+Next-Key Lock解决幻读)→SERIALIZABLE(性能最差)。MVCC：每行记录多版本，读不加锁"),
    ("数据库", "索引设计原则：高选择性列(区分度>30%)优先、覆盖查询避免回表、联合索引列顺序(等值在前范围在后)、避免过多索引(写入开销)。特殊索引：部分索引(WHERE条件过滤)、函数索引(表达式索引)、全文索引(GIN/倒排)"),
    ("数据库", "连接池设计：预创建连接复用(避免TCP三次握手+认证开销)。核心参数：最小空闲数、最大连接数、获取超时、空闲回收时间、连接验证(SELECT 1)。HikariCP最佳实践：maxPoolSize = CPU核心数*2+磁盘数。连接泄漏检测：借出超时告警"),

    # ── 测试 ──
    ("测试", "单元测试AAA模式：Arrange(准备数据)→Act(执行目标方法)→Assert(验证结果)。每个测试只验证一个行为。测试命名：test_<被测方法>_<场景>_<期望结果>。mock外部依赖(数据库/网络/文件系统)，只测试被测单元的逻辑"),
    ("测试", "测试替身(Test Double)五种：Dummy(占位)、Stub(返回固定值)、Spy(记录调用)、Mock(验证交互)、Fake(简化实现如内存数据库)。Python: unittest.mock.patch/MagicMock。原则：不mock你不拥有的东西(第三方库用Adapter包装后mock Adapter)"),
    ("测试", "集成测试策略：测试模块间交互而非单个函数。数据库测试：用testcontainers启动真实数据库容器，每个测试用事务回滚保证隔离。API测试：用测试客户端(Flask test_client/FastAPI TestClient)发送真实HTTP请求。避免测试间共享可变状态"),
    ("测试", "测试金字塔：大量单元测试(快速/隔离)→适量集成测试(模块交互)→少量E2E测试(用户场景)。反模式：冰淇淋锥(大量E2E少量单元)导致测试慢且脆弱。属性测试(Hypothesis/QuickCheck)：自动生成大量随机输入验证程序不变式"),

    # ── 安全 ──
    ("安全", "SQL注入防御：参数化查询(PreparedStatement/?占位符)是唯一可靠方案，ORM自动参数化。存储过程不能完全防御。二阶注入：存入DB的恶意数据在后续查询中被拼接。NoSQL注入：MongoDB的$where/$gt等操作符注入，用Schema验证"),
    ("安全", "XSS防御三层：输出编码(HTML实体转义&lt;&gt;&amp;&quot;)、Content-Security-Policy(限制脚本来源)、HttpOnly Cookie(JS无法读取)。存储型XSS>反射型XSS>DOM型XSS。React/Vue自动转义插值，但v-html/dangerouslySetInnerHTML绕过防护"),
    ("安全", "认证方案对比：Session(服务端存储,有状态,需sticky session或Redis共享)→JWT(客户端存储,无状态,不可撤销除非黑名单)→OAuth2(第三方授权)。JWT结构：Header.Payload.Signature。刷新令牌(Refresh Token)延长会话，短期Access Token减少泄露风险"),
    ("安全", "密码存储：bcrypt/scrypt/Argon2(自适应哈希,内置盐值,计算昂贵防暴力破解)。绝不用MD5/SHA256直接哈希(彩虹表攻击)。bcrypt的cost factor控制计算时间(推荐10-12)。密码策略：最小长度>8，检查已泄露密码库(HaveIBeenPwned API)"),

    # ── 并发编程 ──
    ("并发编程", "锁的层次：互斥锁(Mutex,独占)→读写锁(RWLock,读共享写独占)→自旋锁(SpinLock,忙等待适合短临界区)。死锁四条件：互斥、持有等待、不可剥夺、循环等待。预防：锁排序(所有线程按固定顺序获取锁)、超时获取(tryLock)、检测与恢复"),
    ("并发编程", "线程池模型：固定大小(CPU密集型,核心数+1)、缓存型(IO密集型,按需创建)、调度型(定时任务)。Java ThreadPoolExecutor核心参数：coreSize/maxSize/keepAlive/workQueue/handler。拒绝策略：AbortPolicy(抛异常)/CallerRunsPolicy(调用者执行)"),
    ("并发编程", "无锁编程核心：CAS(Compare-And-Swap)原子操作。ABA问题：值A→B→A，CAS误以为未变化。解决：版本号(AtomicStampedReference)。无锁队列(Michael-Scott Queue)、无锁栈(Treiber Stack)。内存序(Memory Ordering)：Sequential Consistency vs Relaxed"),
    ("并发编程", "异步编程模型对比：回调(Callback Hell)→Promise/Future(链式调用)→async/await(同步写法)。Python asyncio事件循环：协程+IO多路复用(epoll/kqueue)。Go的goroutine：M:N调度(M个goroutine映射到N个OS线程)，channel通信代替共享内存"),

    # ── API设计 ──
    ("API设计", "RESTful设计准则：资源名词复数(/users)、HTTP动词语义(GET查/POST创/PUT全量更/PATCH部分更/DELETE删)、嵌套资源(/users/123/orders)。状态码：200成功/201已创建/204无内容/400客户端错误/401未认证/403无权限/404不存在/409冲突/429限流/500服务器错误"),
    ("API设计", "分页设计：偏移分页(OFFSET/LIMIT,大偏移性能差)→游标分页(WHERE id > cursor LIMIT N,性能稳定)→键集分页(Keyset Pagination)。响应格式：{data:[],meta:{total,page,per_page},links:{next,prev}}。总数查询昂贵时可用has_more布尔代替"),
    ("API设计", "限流算法：固定窗口(简单但边界突刺)→滑动窗口(精确但内存大)→令牌桶(Token Bucket,允许突发)→漏桶(Leaky Bucket,平滑输出)。分布式限流：Redis+Lua脚本保证原子性。响应头：X-RateLimit-Limit/Remaining/Reset"),
    ("API设计", "GraphQL vs REST：GraphQL客户端指定返回字段(解决Over-fetching)，一次请求获取多资源(解决Under-fetching)。Schema定义类型系统。N+1问题：用DataLoader批量加载。缺点：缓存困难(POST请求)、文件上传复杂、学习曲线陡"),

    # ── 性能优化 ──
    ("性能优化", "数据库N+1问题：查询N个用户各自的订单 → 1(用户列表)+N(每个用户的订单)次查询。解决：JOIN查询(1次)、子查询(1-2次)、ORM的select_related/prefetch_related(Django)/joinedload(SQLAlchemy)/include(Prisma)。识别：日志中大量相似SQL"),
    ("性能优化", "前端性能优化：代码分割(import()动态加载)、Tree Shaking(移除未用代码)、图片懒加载(Intersection Observer)、虚拟列表(只渲染可见区域)、Web Worker(CPU密集任务移出主线程)。Core Web Vitals：LCP<2.5s/FID<100ms/CLS<0.1"),
    ("性能优化", "缓存层次：CPU L1/L2/L3(ns级)→内存(100ns)→SSD(100μs)→HDD(10ms)→网络(10-100ms)。代码中的缓存：函数记忆化(@lru_cache)、应用缓存(Redis/Memcached)、HTTP缓存(ETag/Last-Modified/Cache-Control)、CDN缓存(静态资源)"),
    ("性能优化", "Python性能优化：1.算法优先(O(n²)→O(nlogn)) 2.内置数据结构(set查找O(1)vs list O(n)) 3.列表推导式比for循环快30% 4.局部变量比全局变量快 5.C扩展(Cython/pybind11) 6.numpy向量化替代Python循环 7.profile先定位瓶颈(cProfile/line_profiler)"),

    # ── Git与工程实践 ──
    ("工程实践", "Git分支策略：Git Flow(develop/feature/release/hotfix,适合版本发布)、GitHub Flow(main+feature分支,持续部署)、Trunk-Based(主干开发+短命特性分支+Feature Flag)。Commit规范：<type>(<scope>): <description>，type=feat/fix/refactor/docs/test"),
    ("工程实践", "代码审查(Code Review)检查清单：逻辑正确性、边界条件、错误处理、安全漏洞(注入/越权)、性能影响(N+1/大循环)、可读性(命名/注释)、测试覆盖、向后兼容。不审查：代码风格(自动化linter)、个人偏好。PR大小：<400行变更"),
    ("工程实践", "重构安全策略：先写测试覆盖现有行为→小步重构(每步可编译可测试)→频繁提交。核心手法：提取方法(Extract Method)、内联变量、搬移方法(Move Method)、条件多态替代(Replace Conditional with Polymorphism)、引入参数对象(Introduce Parameter Object)"),
    ("工程实践", "技术债管理：识别(代码异味/测试覆盖率/复杂度指标)→量化(影响范围×修复成本)→规划(每个迭代分配20%时间还债)→追踪(JIRA标签/技术债看板)。高利率债务优先：核心路径的坏代码、频繁修改的模块、阻塞新功能的债务"),

    # ── Docker/容器化 ──
    ("DevOps", "Dockerfile最佳实践：多阶段构建(builder→runner减小镜像)、.dockerignore排除无关文件、合并RUN减少层数、非root用户运行、COPY比ADD更明确、固定基础镜像版本(不用latest)。Alpine镜像(5MB)vs Debian slim(80MB)vs Ubuntu(70MB)"),
    ("DevOps", "Docker Compose编排：services定义容器、depends_on控制启动顺序(但不等待ready)、volumes持久化数据、networks隔离通信、healthcheck检测就绪。开发环境：挂载源码目录+热重载。生产环境：用Kubernetes/Docker Swarm"),
    ("DevOps", "CI/CD流水线设计：代码提交→lint/format检查→单元测试→构建镜像→集成测试→安全扫描(Trivy/Snyk)→部署staging→smoke test→部署production(金丝雀/蓝绿)。关键指标：部署频率、变更前置时间、故障恢复时间、变更失败率"),

    # ── 分布式系统 ──
    ("分布式系统", "CAP定理实战选择：CP(一致性+分区容忍，牺牲可用性)→ZooKeeper/etcd/HBase。AP(可用性+分区容忍，牺牲强一致)→Cassandra/DynamoDB/Eureka。实际系统在网络分区时选择CP或AP，无分区时三者都满足。PACELC扩展：无分区时Latency vs Consistency"),
    ("分布式系统", "分布式事务解决方案：2PC(两阶段提交,阻塞+单点故障)→Saga模式(补偿事务链,最终一致)→TCC(Try-Confirm-Cancel,业务侵入)→本地消息表(事务写消息表+异步投递)→事务消息(RocketMQ)。Saga两种：编排(事件驱动)vs协调(中心协调器)"),
    ("分布式系统", "一致性哈希(Consistent Hashing)：节点映射到环上，数据分配到顺时针第一个节点。虚拟节点解决数据倾斜。节点加入/离开只影响相邻区间。应用：分布式缓存(Memcached)、负载均衡、分库分表"),
    ("分布式系统", "服务熔断器模式(Circuit Breaker)三状态：Closed(正常通过)→失败率超阈值→Open(快速失败)→超时后→Half-Open(放少量请求试探)→成功则Closed。Hystrix/Resilience4j/Sentinel实现。配合重试(指数退避+抖动)和降级(返回缓存/默认值)"),

    # ── 前端框架 ──
    ("前端框架", "React核心原理：虚拟DOM(JS对象树)→Diff算法(同层比较+key优化)→最小DOM操作。Fiber架构：可中断渲染(时间切片)，优先级调度(用户交互>数据更新>预渲染)。Hooks规则：只在顶层调用、只在函数组件中调用。useState闭包陷阱：用useRef或函数更新"),
    ("前端框架", "React状态管理演进：组件state→Context(简单全局)→Redux(单一Store+Reducer纯函数+Middleware)→Zustand(简化Redux)→Jotai/Recoil(原子化)→React Query/SWR(服务端状态)。原则：服务端状态和客户端状态分开管理"),
    ("前端框架", "Vue3响应式原理：Proxy替代Object.defineProperty(支持新增属性/数组索引)。track()收集依赖(effect与响应式数据绑定)，trigger()触发更新。ref()包装基本类型(需.value)，reactive()代理对象。computed()惰性求值+缓存。watchEffect自动追踪依赖"),

    # ── Rust ──
    ("Rust", "所有权(Ownership)三规则：1.每个值有且只有一个所有者 2.所有者离开作用域时值被drop 3.赋值/传参默认移动(Move)语义。引用借用：&T不可变借用(多个)、&mut T可变借用(唯一)，编译期保证无数据竞争。Clone显式深拷贝，Copy trait标记栈上可拷贝类型"),
    ("Rust", "生命周期(Lifetime)标注'a：告诉编译器引用的有效范围。函数签名fn foo<'a>(x: &'a str) -> &'a str表示返回值生命周期与x相同。结构体含引用必须标注生命周期。'static：整个程序运行期间有效(字符串字面量/全局变量)。生命周期省略规则简化常见情况"),
    ("Rust", "错误处理：Result<T,E>表示可恢复错误，?操作符自动传播(早返回Err)。panic!表示不可恢复错误。自定义错误：实现std::error::Error trait。thiserror(库代码)和anyhow(应用代码)简化错误处理。Option<T>处理空值，比null安全"),

    # ── Go ──
    ("Go", "Goroutine与Channel：go关键字启动轻量级协程(2KB栈，自动扩缩)。Channel是类型安全的管道：ch := make(chan int, bufSize)。select多路复用多个channel。模式：fan-out(一个生产者多个消费者)、fan-in(多个生产者一个消费者)、Pipeline(阶段串联)"),
    ("Go", "Go接口设计：隐式实现(无需implements关键字)，小接口原则(io.Reader只有Read方法)。空接口interface{}接受任何类型(类似Object)。类型断言v.(Type)和类型switch判断具体类型。error接口只有Error() string方法，errors.Is/As进行错误链比较"),
    ("Go", "Go并发陷阱：goroutine泄漏(channel永远阻塞→用context.WithCancel/WithTimeout控制)、data race(共享变量→用mutex或channel)、闭包变量捕获(循环中启动goroutine需传参)。-race检测数据竞争。sync.WaitGroup等待一组goroutine完成"),

    # ── 网络协议 ──
    ("网络协议", "HTTP/2优化：多路复用(一个TCP连接并行多个请求/响应流)、头部压缩(HPACK算法)、服务端推送、二进制帧(替代文本)、流优先级。HTTP/3基于QUIC(UDP)：0-RTT握手、连接迁移(换网络不断连)、独立流(一个流丢包不阻塞其他流)"),
    ("网络协议", "WebSocket协议：HTTP升级握手(Upgrade: websocket)建立全双工持久连接。帧协议：opcode区分文本/二进制/ping/pong/close。心跳保活(ping/pong每30-60秒)。断线重连：指数退避+最大重试。负载均衡需sticky session或基于用户ID路由"),
    ("网络协议", "TCP拥塞控制：慢启动(指数增长cwnd)→拥塞避免(线性增长)→丢包(快速重传+快速恢复或超时回到慢启动)。Nagle算法(合并小包)与TCP_NODELAY(禁用Nagle降低延迟)。TIME_WAIT状态持续2MSL防止旧包干扰新连接"),

    # ── 消息队列 ──
    ("消息队列", "消息队列选型：RabbitMQ(AMQP协议,路由灵活,吞吐万级)→Kafka(分区日志,吞吐百万级,消息持久化,适合流处理)→Redis Stream(轻量级,功能有限)→RocketMQ(事务消息,有序消息)。选择依据：吞吐量、延迟、持久化、消息顺序、事务支持"),
    ("消息队列", "消息可靠投递：生产端(确认机制ack)、Broker端(持久化+副本)、消费端(手动确认+幂等处理)。幂等方案：唯一消息ID+去重表、数据库唯一约束、Redis SETNX。消费失败：重试队列(指数退避)→死信队列(DLQ)→人工处理"),

    # ── 函数式编程 ──
    ("函数式编程", "函数式核心概念：纯函数(同输入同输出无副作用)、不可变数据(修改返回新对象)、高阶函数(函数作为参数/返回值)、组合(compose/pipe)。map/filter/reduce三件套。柯里化(curry)：f(a,b)→f(a)(b)，实现偏函数和函数组合"),
    ("函数式编程", "Monad模式：封装值+flatMap/bind链式操作+处理副作用。常见Monad：Optional/Maybe(空值处理)、Result/Either(错误处理)、Promise/Future(异步)、List(多值)。Python中的Optional链：maybe(x).map(f).map(g).get_or(default)"),

    # ── 正则表达式 ──
    ("正则表达式", "正则性能陷阱：灾难性回溯(Catastrophic Backtracking)——嵌套量词如(a+)+b在不匹配时指数级回溯。防御：使用占有量词(a++不回溯)、原子组(?>...)、避免嵌套量词。Python re.compile()预编译、re.VERBOSE多行注释。命名组(?P<name>...)提升可读性"),

    # ── 代码质量 ──
    ("代码质量", "SOLID五原则实战：S单一职责(一个类一个修改原因)、O开闭原则(对扩展开放对修改封闭→策略/模板方法)、L里氏替换(子类可替代父类→正方形不应继承矩形)、I接口隔离(小接口→Python的Protocol/ABC)、D依赖倒置(依赖抽象不依赖具体)"),
    ("代码质量", "代码异味与重构：过长方法(提取方法)、过长参数列表(引入参数对象)、数据泥团(多处出现的相同字段组→提取类)、发散式修改(一个类因多种原因修改→拆分)、霰弹式修改(一种变化影响多个类→合并)。重构频率：随时重构(红-绿-重构)而非集中重构"),
    ("代码质量", "命名规范：变量名反映意图不反映类型(user_count > int_c)、布尔变量用is/has/can前缀(is_active)、函数名用动词(calculate_total)、类名用名词(UserRepository)。避免：缩写(除非universally known如URL/ID)、单字母(除循环变量i/j)、否定布尔(not is_invalid→is_valid)"),
]

# ============================================================
# 关系数据：节点间的真实依赖/扩展/互补关系
# ============================================================

RELATIONS = [
    # Python高级内部关系
    ("装饰器链式组合原理", "上下文管理器(__enter__/__exit__)", "complements", "装饰器和上下文管理器都是Python的控制流抽象"),
    ("生成器与协程的本质区别", "异步编程模型对比", "extends", "协程是异步编程的基础"),
    ("元类(metaclass)控制类的创建过程", "装饰器链式组合原理", "alternative", "元类和类装饰器都可以修改类行为"),
    ("GIL(全局解释器锁)", "线程池模型", "depends_on", "理解GIL才能正确选择Python并发策略"),
    ("类型标注(Type Hints)", "测试替身(Test Double)", "complements", "类型标注和测试共同保证代码正确性"),

    # 设计模式与架构
    ("策略模式(Strategy)", "依赖注入(DI)", "depends_on", "策略模式通常通过依赖注入传入"),
    ("观察者模式(Observer/Pub-Sub)", "消息队列选型", "evolves_to", "观察者模式的分布式版本是消息队列"),
    ("工厂模式三层次", "依赖注入(DI)", "complements", "工厂创建对象，DI决定注入哪个实现"),
    ("装饰器模式vs继承", "装饰器链式组合原理", "implements", "Python装饰器是装饰器模式的语法级实现"),
    ("Clean Architecture分层", "依赖注入(DI)", "depends_on", "Clean Architecture通过DI实现依赖倒置"),
    ("Clean Architecture分层", "SOLID五原则实战", "implements", "Clean Architecture是SOLID的架构级实践"),
    ("微服务拆分原则", "API版本化策略", "depends_on", "微服务需要API版本管理"),
    ("微服务拆分原则", "服务熔断器模式(Circuit Breaker)", "depends_on", "微服务必须有熔断保护"),
    ("CQRS(命令查询分离)", "消息可靠投递", "depends_on", "CQRS的事件同步依赖消息队列"),

    # 数据结构与算法 → 数据库
    ("B-Tree/B+Tree", "索引设计原则", "implements", "B+Tree是数据库索引的底层数据结构"),
    ("跳表(Skip List)", "B-Tree/B+Tree", "alternative", "跳表是B-Tree在内存中的替代方案"),
    ("动态规划(DP)解题框架", "图算法核心", "complements", "DP和图算法是算法的两大核心范式"),

    # 数据库
    ("SQL查询优化核心", "索引设计原则", "depends_on", "查询优化依赖正确的索引设计"),
    ("事务隔离级别与问题", "分布式事务解决方案", "evolves_to", "单机事务隔离演进到分布式事务"),
    ("连接池设计", "数据库N+1问题", "complements", "连接池和查询优化共同提升数据库性能"),

    # 测试
    ("单元测试AAA模式", "测试替身(Test Double)", "depends_on", "单元测试用Mock隔离外部依赖"),
    ("集成测试策略", "Docker Compose编排", "depends_on", "集成测试用Docker启动依赖服务"),
    ("测试金字塔", "CI/CD流水线设计", "depends_on", "CI流水线执行各层测试"),

    # 安全
    ("SQL注入防御", "SQL查询优化核心", "complements", "安全和性能是SQL的两个核心关注点"),
    ("XSS防御三层", "React核心原理", "depends_on", "React自动转义是XSS防御的前端实践"),
    ("认证方案对比", "限流算法", "complements", "认证和限流共同保护API"),
    ("密码存储", "认证方案对比", "depends_on", "密码存储是认证系统的基础"),

    # 并发
    ("锁的层次", "无锁编程核心", "evolves_to", "从有锁演进到无锁编程"),
    ("线程池模型", "GIL(全局解释器锁)", "depends_on", "Python线程池受GIL影响"),
    ("异步编程模型对比", "事件循环(Event Loop)执行模型", "implements", "事件循环是异步编程的运行时"),
    ("Goroutine与Channel", "异步编程模型对比", "alternative", "Go的CSP模型是异步编程的另一种方案"),

    # API
    ("RESTful设计准则", "GraphQL vs REST", "alternative", "GraphQL是REST的替代方案"),
    ("分页设计", "RESTful设计准则", "extends", "分页是REST API的常见扩展"),
    ("限流算法", "服务熔断器模式(Circuit Breaker)", "complements", "限流和熔断共同保护服务"),

    # 性能
    ("数据库N+1问题", "SQL查询优化核心", "depends_on", "N+1是最常见的SQL性能问题"),
    ("前端性能优化", "React核心原理", "extends", "前端优化在React框架中的实践"),
    ("缓存层次", "缓存策略四种模式", "extends", "缓存策略在不同层次的应用"),
    ("Python性能优化", "GIL(全局解释器锁)", "depends_on", "Python性能优化需要理解GIL限制"),

    # 分布式
    ("CAP定理实战选择", "事务隔离级别与问题", "extends", "CAP是事务一致性在分布式场景的扩展"),
    ("分布式事务解决方案", "消息可靠投递", "depends_on", "Saga模式依赖可靠消息投递"),
    ("一致性哈希(Consistent Hashing)", "缓存策略四种模式", "complements", "一致性哈希用于分布式缓存节点分配"),

    # 跨领域
    ("所有权(Ownership)三规则", "Python内存模型", "alternative", "Rust编译期内存管理 vs Python运行时GC"),
    ("Go接口设计", "TypeScript类型体操核心", "alternative", "Go隐式接口 vs TS显式类型系统"),
    ("错误处理(Rust)", "Go接口设计", "complements", "Rust Result和Go error都是显式错误处理"),
    ("代码异味与重构", "重构安全策略", "depends_on", "识别异味后用安全策略执行重构"),
    ("命名规范", "代码审查(Code Review)检查清单", "depends_on", "命名是Code Review的基本检查项"),
    ("Git分支策略", "CI/CD流水线设计", "depends_on", "分支策略决定CI/CD的触发方式"),
    ("Dockerfile最佳实践", "CI/CD流水线设计", "depends_on", "CI中构建Docker镜像"),
    ("消息队列选型", "消息可靠投递", "extends", "选型后需要保证可靠投递"),
    ("函数式核心概念", "策略模式(Strategy)", "implements", "高阶函数是策略模式的函数式实现"),
    ("Monad模式", "错误处理(Rust)", "implements", "Result是Monad在Rust中的具体化"),
    ("正则性能陷阱", "Python性能优化", "extends", "正则回溯是常见的Python性能陷阱"),
    ("Vue3响应式原理", "观察者模式(Observer/Pub-Sub)", "implements", "Vue响应式是观察者模式的实现"),
    ("React状态管理演进", "React核心原理", "extends", "状态管理是React生态的核心扩展"),
    ("WebSocket协议", "HTTP/2优化", "alternative", "WebSocket和HTTP/2 SSE都支持服务端推送"),
    ("TCP拥塞控制", "HTTP/2优化", "depends_on", "HTTP/2依赖TCP可靠传输"),
    ("技术债管理", "代码异味与重构", "depends_on", "技术债识别需要识别代码异味"),
]


def inject():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # 确保有embedding列
    try:
        c.execute("SELECT embedding FROM cognitive_nodes LIMIT 1")
    except:
        c.execute("ALTER TABLE cognitive_nodes ADD COLUMN embedding BLOB")

    import agi_v13_cognitive_lattice as agi

    # 注入节点
    injected = 0
    node_map = {}  # content_prefix -> node_id
    for domain, content in NODES:
        # 检查是否已存在
        prefix = content[:60]
        c.execute("SELECT id FROM cognitive_nodes WHERE content LIKE ? AND verified_source = ?",
                  (prefix + "%", VERIFIED_SOURCE))
        existing = c.fetchone()
        if existing:
            node_map[prefix] = existing[0]
            continue

        # 生成embedding
        emb = agi.get_embedding(content)

        c.execute("""
            INSERT INTO cognitive_nodes (content, domain, status, verified_source, embedding)
            VALUES (?, ?, 'proven', ?, ?)
        """, (content, domain, VERIFIED_SOURCE, emb))
        nid = c.lastrowid
        node_map[prefix] = nid
        injected += 1

    conn.commit()

    # 建立ID映射（通过content前缀匹配）
    def find_node_id(content_start):
        for prefix, nid in node_map.items():
            if content_start in prefix or prefix in content_start:
                return nid
        # 数据库查找
        c.execute("SELECT id FROM cognitive_nodes WHERE content LIKE ? LIMIT 1",
                  (content_start[:40] + "%",))
        r = c.fetchone()
        return r[0] if r else None

    # 注入关系
    rel_count = 0
    for src_start, tgt_start, rel_type, desc in RELATIONS:
        src_id = find_node_id(src_start)
        tgt_id = find_node_id(tgt_start)
        if src_id and tgt_id and src_id != tgt_id:
            c.execute("SELECT 1 FROM node_relations WHERE node1_id=? AND node2_id=? AND relation_type=?",
                      (src_id, tgt_id, rel_type))
            if not c.fetchone():
                c.execute("""
                    INSERT INTO node_relations (node1_id, node2_id, relation_type, confidence, description)
                    VALUES (?, ?, ?, 0.85, ?)
                """, (src_id, tgt_id, rel_type, desc))
                rel_count += 1

    conn.commit()

    # 统计
    c.execute("SELECT COUNT(*) FROM cognitive_nodes WHERE verified_source = ?", (VERIFIED_SOURCE,))
    total_nodes = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT domain) FROM cognitive_nodes WHERE verified_source = ?", (VERIFIED_SOURCE,))
    total_domains = c.fetchone()[0]
    c.execute("SELECT domain, COUNT(*) as cnt FROM cognitive_nodes WHERE verified_source = ? GROUP BY domain ORDER BY cnt DESC", (VERIFIED_SOURCE,))
    domain_dist = c.fetchall()

    conn.close()

    print(f"\n{'='*60}")
    print(f"  Claude代码实现能力注入完成")
    print(f"{'='*60}")
    print(f"  本次新增: {injected} 节点, {rel_count} 关系")
    print(f"  总计: {total_nodes} 节点, {total_domains} 领域")
    print(f"\n  领域分布:")
    for domain, cnt in domain_dist:
        print(f"    {domain}: {cnt}")
    print(f"{'='*60}")

    return {"injected_nodes": injected, "injected_relations": rel_count,
            "total_nodes": total_nodes, "total_domains": total_domains}


if __name__ == "__main__":
    inject()
