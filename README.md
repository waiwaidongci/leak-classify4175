# 澄湾 · 管网漏损判别席

沿着匿名工况窗口、模型比较和漏报/误报成本，形成一份供人工巡检复核的参考。

澄湾水务分析组有22位分析与复核人员。现有流程将夜间流量、压力和声学窗口粘进表格，按单一报警阈值筛查，再手工整理巡检参考；痛点是类别不均衡时只看准确率、标准化与训练验证边界不清、漏报与误报的代价没有进入阈值。这里承接“匿名窗口→监督分类研究→固定成本阈值→负责人审批→人工复核参考”，没有自动派工功能。

## 启动

```sh
cp .env.example .env
docker compose config --quiet
docker compose up -d --build --wait
docker compose exec -T backend python -m scripts.seed_demo
```

前端 [http://localhost:18212](http://localhost:18212)，后端 [API文档](http://localhost:19212/docs)，数据库映射17712。首次API启动自动seed，失败记录日志但不阻塞API；脚本可单独再运行。数据库初始有1500个匿名合成窗口、350个漏损标签（23.3%）、六个数值特征、1份真算基准训练和1个待审核策略，固定种子73。

| 账号 | 密码 | 角色与权限 |
|---|---|---|
| admin@chengwan.demo | Chengwan2026! | 水务负责人admin：读、导入、训练、建策略、审核策略、记录人工复核；仅获批策略可导出 |
| analyst@chengwan.demo | Chengwan2026! | 工况分析师analyst：读、导入、训练、建策略、记录人工复核；审核返回403；仅获批策略可导出 |
| viewer@chengwan.demo | Chengwan2026! | 巡检观察员viewer：只读与获批策略导出；所有写入返回403 |

## 工作剧本

1. 07:00 周沅以analyst登录，核对 `cw-pressure-windows.csv` 的1500窗口/350阳性。
2. 在“窗口样本”看前100个匿名工况；label独立显示，永不进入特征矩阵。
3. 建立“夜间漏损成本研究”，选择全部六特征，同时比较前三个特征的精简候选，C为0.1、1、10。
4. 在看任何最终留出结果前，确定漏报成本8、误报成本1，提交独立Celery队列。
5. worker在训练集内部做分层三折CV，Pipeline每折单独拟合StandardScaler，再拟合Logistic。
6. 读取模型比较与固定阈值：阈值仅由独立验证集成本选出；模型和阈值锁定后才评估留出集。
7. 建立“夜间优先复核”策略，后端复制该验证阈值，界面没有手改阈值入口。
8. 沈泊以admin审核策略；分析师在获批策略候选中记录“待复核/复核确认/复核排除”与现场说明。
9. viewer下载获批巡检参考CSV；人工复核不从训练标签自动生成，系统不自动派工。

## 数据和模型口径

五个核心实体：WindowDataset、SensorWindow、TrainingRun、ThresholdPolicy、InspectionReview，分别经过数据库模型、Pydantic schema、service、route/API、store与页面。六个页面为判别席、窗口样本、训练配置、封存结果、阈值与复核、研究留痕。PerformanceSummary、CurvePlot、RunTable等业务组件跨页复用；同时有共享表格、Badge、Notice、Empty。

允许六特征：night_flow（夜间流量L/s）、pressure_drop（有符号压力降kPa）、acoustic_energy（声学能量）、flow_variation（流量变异）、pipe_age（管龄年）、ambient_temp（环境温度°C）。label单独为0/1，API拒绝任何额外/缺失特征及把label作为入模特征。导入接受JSON窗口数组，100–5000行，每类至少20；reference批内唯一。没有CSV解析器，源文件名用于演示台账。

`services/splits.py` 先按reference稳定排序，使用seed73分层切出60%训练/40%余下，再seed74将余下分成20%验证/20%留出。初始数据为900/300/300，阳性分别210/70/70，索引随结果持久化，三组不相交。

`services/training.py` 使用Pipeline(StandardScaler, LogisticRegression)。分层三折CV只接触训练集，每折训练均单独拟合标准化；class_weight='balanced'、lbfgs、max_iter2000、seed73，按平均ROC AUC选特征与C。同均值时依次优先少特征、小C和特征字典序；最终模型仍只拟合训练集。系数解释为每个标准差对应的log-odds变化，不是因果效应。balanced模型得分未经概率校准。

`services/thresholds.py` 只对验证集概率枚举0、各独特得分、1及`nextafter(max(validation_score),+inf)`，严格高于最大验证得分的候选覆盖“无人标记”策略，即使最大得分等于1。阈值是决策切点，不是概率；当哨兵大于1时，所有[0,1]得分均不标记，UI明确标为“无人标记”。按 `FN * false_negative_cost + FP * false_positive_cost` 最小选阈值；`score >= threshold`为候选。同成本取更高阈值。仅在选择结束后计算留出集的ROC/PR、ROC AUC、average precision、混淆矩阵与固定阈值成本；测试集没有进入模型或阈值选择。ROC首个无穷阈值编码为null；PR使用真实precision_recall_curve，AP为分段召回增量加权精确率，非梯形PR AUC。阈值不可在策略API中自填；结果没有更新接口。

输入指纹为全量窗口id/reference/全部六特征/label、完整训练候选和成本、算法版本与split seed的稳定排序SHA-256，包含未被胜出模型选用的特征，防止遗漏影响字段。结果保留标准化均值/尺度、系数/截距、CV逐折AUC、分割ID、验证成本候选和最终留出得分，可复算。worker将JSON写入共享artifacts卷并落库。

失败态：太少窗口/单类/任一类不足20/常量训练特征/非有限数值/未知特征/非法C和成本明确拒绝或记为failed；运行配额为最多3组特征×5个C。合成窗口假设独立可交换，没有按真实管段或时间分组的外部验证，也没有未来现场泛化承诺。每个运行只最终评估所选模型一次；若人为基于已经看到的留出结果反复改方案，会破坏留出意义，应另建新的外部数据集验证。

## 技术与开发

| 层 | 实现 |
|---|---|
| UI | React18.3 / TypeScript5.7 / Vite6.4.6 / Nginx1.27 |
| API | Python3.11 / FastAPI / Pydantic / SQLAlchemy2 |
| 计算 | NumPy2.2 / SciPy1.15 / scikit-learn1.6 |
| 持久化 | PostgreSQL16、JSON训练结果 |
| 队列 | Celery5.4 / Kombu5.4.2 / Redis7，独立worker |
| 认证 | PBKDF2-SHA256 210000轮密码哈希、JWT HS256 8小时、后端角色鉴权 |

Compose恰有frontend/backend/worker/db/redis五服务。所有服务具healthcheck与依赖健康条件；worker使用定向Celery ping，Nginx探针使用127.0.0.1。db-data、redis-data、artifacts命名卷分别存库、队列和共享训练JSON。Nginx剥离 `/api/` 前缀，原生后端不重复加前缀。Kombu固定5.4.2避免Celery5.4 Redis extra与较新Kombu的redis-py范围冲突。

环境变量在.env.example：COMPOSE_PROJECT_NAME、FRONTEND_PORT、BACKEND_PORT、DB_PORT隔离部署；POSTGRES_DB/USER/PASSWORD配置数据库；JWT_SECRET签名；SEED_DEMO控制自动演示数据。演示口令仅用于本机，部署时替换环境变量。

```sh
# 后端，先设置本机可达 DATABASE_URL / REDIS_URL / JWT_SECRET
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 19212
# 另一个终端，同环境变量
celery -A src.worker.app worker --concurrency=1
# 前端，Vite开发代理已映射到127.0.0.1:19212
cd frontend
npm ci
npm run dev
```

目录：backend/src/{routes,controllers,services,models,schemas,middlewares,utils,constants,config}；backend/scripts/seed_demo.py；backend/migrations/；frontend/src/{api,stores,types,components/common,hooks,pages,router,utils,constants}。首次使用SQLAlchemy metadata建表，migrations内记结构，未配生产增量迁移工具。

自然键插入确保seed可重复、不覆盖用户修改；只在没有基准研究时计算一次基准。RequestID和全局错误两个中间件提供可追踪请求；AuditLog保留登录、训练、策略和人工复核。CSV对公式前缀转义。共享枚举：backend/src/constants/enums.py的Role/RunStatus/PolicyStatus/Verdict，frontend/src/constants/enums.ts对应角色、运行/策略状态、复核标签；使用处为依赖鉴权、训练/策略/复核service/schema以及Badge/Layout/页面。全部测试脚本、截图、日志、CSV、结果报告位于批次根test-artifacts/gb-0008，不进入源码。

## 验收与边界

真实验收结果与已知差异见批次根 `test-artifacts/gb-0008/TESTING.md`。独立小数据oracle验证已知阈值、AUC/AP与计数；训练折拟合追踪和测试标签翻转实验验证选择边界。API真实验证三角色与审批/导出保护；Playwright走训练→策略→审批→人工复核→获批导出。收尾使用 `docker compose down -v --remove-orphans` 删除本栈演示卷。

## License

MIT，见LICENSE。
