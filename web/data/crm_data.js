// AGI CRM Data — loads from deduction_export.json, persists to localStorage
let DB_LOADED=false;
const DATA={
  currentUser:null,
  projects:[],deductions:[],todos:[],skills:[],capabilities:[],strategies:[],
  codeGoals:[],sysGoals:[],milestones:[],deductionResults:[],
  problems:[],workflows:[],models:[],
};
const DEFAULTS={
  projects:[
    {id:'p_diepre',name:'刀模设计项目',description:'DiePre AI — 用户上传刀模图→ULDS推演→3D→2D制作图纸',status:'active',progress:65,color:'#ef4444',tags:['AI','制造','刀模','DiePre'],ultimate_goal:'用户免费使用现有刀模图, 经ULDS推演获取制作刀模2D图纸',short_term_goal:'Playwright自动验证+反馈→推演最佳实现'},
    {id:'p_rose',name:'予人玫瑰',description:'予人玫瑰项目 — 上线运转+快速商业化',status:'active',progress:30,color:'#ec4899',tags:['创意','商业','CRM'],ultimate_goal:'项目上线+商业化+分成方案',short_term_goal:'CRM用户登录+任务增删改查+反馈'},
    {id:'p_huarong',name:'刀模活字印刷3D',description:'华容道×乐高×活字印刷→模块化卡刀→平整刀模 IADD标准',status:'active',progress:20,color:'#f59e0b',tags:['3D打印','乐高','华容道','IADD','拓竹P2S'],ultimate_goal:'3D打印模块化刀模, 支持各尺寸刀+卡纸',short_term_goal:'IADD规格+拓竹P2S全模块2D图纸'},
    {id:'p_model',name:'本地模型超越计划',description:'终极:突破世界前沿认知 | 短期:代码能力超Claude Opus 4.6',status:'active',progress:56,color:'#6366f1',tags:['AGI','代码','超越','自成长'],ultimate_goal:'突破当下世界前沿认知',short_term_goal:'代码能力超Claude Opus 4.6'},
    {id:'p_mgmt',name:'最佳管理协作制度',description:'推演实践+圆桌决策借鉴历史人物高光',status:'active',progress:15,color:'#10b981',tags:['管理','协作','圆桌','历史人物'],ultimate_goal:'AI圆桌决策系统',short_term_goal:'最佳实践推演'},
    {id:'p_operators',name:'三个算子推演',description:'三个核心算子极致推演, 目标算法第一',status:'active',progress:5,color:'#8b5cf6',tags:['算子','算法'],ultimate_goal:'拿下算法第一',short_term_goal:'形式化定义+代码实现'},
    {id:'p_visual',name:'最佳视觉效果推演',description:'让AI理解人类觉得好看的视觉体验',status:'active',progress:0,color:'#f472b6',tags:['视觉','设计','美学'],ultimate_goal:'AI深度理解人类视觉审美',short_term_goal:'视觉规则体系+CRM美化'},
    {id:'p_workflow',name:'工作流可视化项目',description:'可视化定义SKILL调用链路+能力编排',status:'active',progress:0,color:'#0ea5e9',tags:['工作流','可视化','SKILL'],ultimate_goal:'用户可视化拖拽定义AI工作流',short_term_goal:'工作流编辑器原型'},
  ],
  skills:[
    {category:'代码生成',count:420,source:'自有',color:'#6366f1',items:['Python生成','Dart/Flutter','TypeScript','代码重构','AST分析'],desc:'支持多语言代码生成, AST级别精确重构'},
    {category:'算法数据结构',count:380,source:'自有',color:'#ec4899',items:['图算法','动态规划','并发结构','缓存策略','排序搜索'],desc:'核心算法库, 含并发安全LRU+DAG调度器'},
    {category:'系统设计',count:310,source:'自有',color:'#10b981',items:['分布式系统','微服务','消息队列','容错','负载均衡'],desc:'分布式架构与可靠性工程'},
    {category:'工业制造',count:250,source:'自有',color:'#f59e0b',items:['CAD/DXF解析','刀模设计','工艺规划','材料科学','3D建模'],desc:'刀模设计+工业制造全链路'},
    {category:'NLP/认知',count:751,source:'自有',color:'#8b5cf6',items:['语义搜索','幻觉检测','节点碰撞','知识图谱','对话管理'],desc:'认知格核心能力, 751个proven节点'},
    {category:'数学/公式',count:180,source:'自有',color:'#ef4444',items:['公式引擎','铁碳相图','温差推演','优化算法','统计'],desc:'数学公式编码+物理推演'},
    {category:'DevOps/工程',count:333,source:'自有+gstack',color:'#0ea5e9',items:['CI/CD','Docker/K8s','集群管理','安全审计','监控'],desc:'含gstack 29个工程流程skill'},
    {category:'自愈/可靠性',count:45,source:'自有',color:'#14b8a6',items:['断路器','混沌工程','自愈运行时','指数退避','降级'],desc:'极致推演R4成果, 自愈运行时'},
    {category:'多语言生成',count:35,source:'自有',color:'#a855f7',items:['Python','Dart','TypeScript','类型映射','Schema'],desc:'极致推演R5成果, 跨语言代码生成器'},
    {category:'OpenClaw开源',count:4717,source:'OpenClaw',color:'#06b6d4',items:['Web开发','移动端','数据库','安全','测试'],desc:'社区开源技能库'},
  ],
  capabilities:[
    {dim:'SWE-Bench',local:35,opus:49,gpt5:55,target:55},
    {dim:'Python生成',local:82,opus:92,gpt5:90,target:88},
    {dim:'多文件编辑',local:40,opus:70,gpt5:65,target:60},
    {dim:'代码解释',local:75,opus:88,gpt5:85,target:82},
    {dim:'任务分解',local:78,opus:82,gpt5:80,target:85},
    {dim:'API成本',local:95,opus:40,gpt5:35,target:95},
    {dim:'自成长',local:92,opus:10,gpt5:5,target:95},
    {dim:'多模型路由',local:88,opus:20,gpt5:15,target:92},
    {dim:'幻觉控制',local:80,opus:85,gpt5:82,target:88},
    {dim:'工具使用',local:72,opus:90,gpt5:88,target:85},
    {dim:'Dart/Flutter',local:70,opus:80,gpt5:75,target:80},
    {dim:'Rust生成',local:30,opus:75,gpt5:72,target:60},
    {dim:'Agent自治',local:40,opus:60,gpt5:55,target:70},
    {dim:'知识演化',local:90,opus:15,gpt5:10,target:95},
  ],
  strategies:[
    {name:'S1 规律约束注入',pct:85},{name:'S2 技能库锚定',pct:75},
    {name:'S3 王朝治理',pct:70},{name:'S4 四向碰撞',pct:92},
    {name:'S5 5级真实性',pct:88},{name:'S6 并行推理',pct:90},
    {name:'S7 零回避扫描',pct:90},{name:'S8 链式收敛',pct:80},
  ],
  codeGoals:[{name:'95维均分',current:84.2,target:87},{name:'SWE-Bench',current:35,target:45},{name:'Python生成',current:82,target:88},{name:'代码解释',current:75,target:82}],
  sysGoals:[{name:'proven节点',current:1200,target:2000},{name:'技能有效率%',current:64.5,target:80},{name:'认知领域',current:920,target:1200},{name:'API延迟s',current:3,target:1.5,invert:true}],
  milestones:[{name:'M1 认知格基础',pct:100},{name:'M2 君臣佐使v4',pct:100},{name:'M3 自成长v7',pct:100},{name:'M4 技能库6000+',pct:100},{name:'M5 极致推演引擎',pct:60},{name:'M6 SWE-Bench 55%',pct:10},{name:'M7 多语言75分',pct:5},{name:'M8 Agent自治',pct:3},{name:'M9 跨域迁移',pct:1}],
  deductionResults:[{round:'R1',name:'并发安全LRU缓存',laws:'L4+L9+L7+L6',test:'6/6'},{round:'R2',name:'多文件AST差分引擎',laws:'L1+L5+L4+L8',test:'6/6'},{round:'R3',name:'DAG任务调度器',laws:'L1+L6+L4+L10',test:'7/7'},{round:'R4',name:'自愈运行时+混沌工程',laws:'L6+L10+L7+L4',test:'8/8'},{round:'R5',name:'多语言代码生成器',laws:'L8+L10+L5+L9',test:'6/6'}],
  models:[
    {id:'ollama_local',name:'Ollama 14B',role:'君 Emperor',desc:'幻觉校验|路由决策|节点锚定',color:'red',enabled:true},
    {id:'glm5',name:'GLM-5',role:'臣 Minister',desc:'复杂推理|深度分析|创新',color:'blue',enabled:true},
    {id:'glm5_turbo',name:'GLM-5 Turbo',role:'快臣 Fast',desc:'快速推演|批量处理|高吞吐',color:'cyan',enabled:true},
    {id:'glm47',name:'GLM-4.7',role:'佐 Assistant',desc:'快速编码|代码补全|重构',color:'green',enabled:true},
    {id:'glm45air',name:'GLM-4.5-Air',role:'使 Messenger',desc:'轻量响应|分类路由|摘要',color:'yellow',enabled:true},
  ],
  problems:[],
  workflows:[
    {id:'wf1',name:'代码推演流水线',project:'p_model',steps:[{id:'s1',skill:'ULDS规律注入',type:'system'},{id:'s2',skill:'问题分解',type:'glm5'},{id:'s3',skill:'代码生成',type:'glm5_turbo'},{id:'s4',skill:'测试验证',type:'ollama'},{id:'s5',skill:'零回避扫描',type:'system'},{id:'s6',skill:'结果记录',type:'system'}],status:'active'},
    {id:'wf2',name:'刀模设计推演链',project:'p_diepre',steps:[{id:'s1',skill:'DXF解析',type:'system'},{id:'s2',skill:'F→V→F约束传播',type:'glm5'},{id:'s3',skill:'2D图纸生成',type:'glm5_turbo'},{id:'s4',skill:'Playwright验证',type:'system'},{id:'s5',skill:'精度反馈',type:'ollama'}],status:'draft'},
    {id:'wf3',name:'商业化推演链',project:'p_rose',steps:[{id:'s1',skill:'市场分析',type:'glm5'},{id:'s2',skill:'竞品对比',type:'glm5_turbo'},{id:'s3',skill:'定价推演',type:'glm5'},{id:'s4',skill:'分成方案',type:'glm5_turbo'},{id:'s5',skill:'法律合规',type:'glm5'}],status:'draft'},
  ],
  todos:[],
};

// Load from DB export, then localStorage overrides
async function loadFromDB(){
  try{
    const r=await fetch('data/deduction_export.json');
    if(!r.ok)return;
    const db=await r.json();
    if(db.projects){
      DATA.projects=db.projects.map(p=>({...p,desc:p.description,tags:typeof p.tags==='string'?JSON.parse(p.tags):p.tags||[]}));
    }
    if(db.deductions){
      DATA.deductions=db.deductions.map(d=>({id:d.id,title:d.title,desc:d.description||'',priority:d.priority||'medium',status:d.status||'queued',laws:d.ulds_laws||'',project:d.project_id,model:d.model_preference||'glm5',rounds:d.estimated_rounds||5,strategies:d.surpass_strategies||''}));
    }
    if(db.problems) DATA.problems=db.problems;
    if(db.workflows) DATA.workflows=[...DATA.workflows,...db.workflows];
    DB_LOADED=true;
  }catch(e){console.warn('DB load failed:',e)}
}
function saveData(){localStorage.setItem('agi_crm_v2',JSON.stringify(DATA))}
function loadSaved(){
  try{
    const s=localStorage.getItem('agi_crm_v2');
    if(s){const d=JSON.parse(s);Object.keys(d).forEach(k=>{if(d[k]&&(Array.isArray(d[k])?d[k].length:true))DATA[k]=d[k]})}
  }catch(e){}
  // Ensure defaults for missing arrays
  if(!DATA.projects.length)DATA.projects=DEFAULTS.projects;
  if(!DATA.skills.length)DATA.skills=DEFAULTS.skills;
  if(!DATA.capabilities.length)DATA.capabilities=DEFAULTS.capabilities;
  if(!DATA.strategies.length)DATA.strategies=DEFAULTS.strategies;
  if(!DATA.codeGoals.length)DATA.codeGoals=DEFAULTS.codeGoals;
  if(!DATA.sysGoals.length)DATA.sysGoals=DEFAULTS.sysGoals;
  if(!DATA.milestones.length)DATA.milestones=DEFAULTS.milestones;
  if(!DATA.deductionResults.length)DATA.deductionResults=DEFAULTS.deductionResults;
  if(!DATA.models.length)DATA.models=DEFAULTS.models;
}
