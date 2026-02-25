# 提交 GitHub 时 MD 文档取舍建议

## 建议必须提交（核心文档）

| 文件 | 说明 |
|------|------|
| `README.md` | 项目入口，运行实验的主说明 |
| `README_LLM_SETUP.md` | LLM API 配置，README 末尾有引用 |
| `FINAL_EXPERIMENT_DESIGN.md` | 实验设计，README 文档索引引用 |
| `GENDER_FAIRNESS_METRICS.md` | 公平性指标说明，README 文档索引引用 |
| `ARCHITECTURE.md` | 系统架构，README 文档索引引用 |

这 5 个和主流程、文档索引一致，**建议都提交**。

---

## 建议保留提交（对理解/复现有用）

| 文件 | 说明 |
|------|------|
| `AGENT_TUNING.md` | Agent 调参（yaml、persona 等），方便他人调实验 |
| `AGENT_DEGREE_DIFFERENCES.md` | 三类 Agent 差异说明，帮助理解设计 |
| `EXPERIMENT_RECORDS.md` | 说明 logs 下产出含义与可追溯性 |
| `docs/CTR_VALIDATION_VERIFICATION.md` | CTR 验证/复现训练时有用 |
| `archive/README.md` | 说明 archive 目录用途，避免误用旧代码 |

可随项目一起提交，不提交也不影响“能跑起来”。

---

## 建议不提交（可删或靠 .gitignore 排除）

| 位置 | 说明 |
|------|------|
| **logs/** 下所有 `.md` | 如 `logs/formal_experiment/*.md`、`logs/summary_last6_metrics.md`、`logs/three_metrics_tables.md`、`logs/AUCTION_ROUNDS_USER_INFO_README.md` 等，多为单次实验报告/说明，会随实验变，不适合进仓库 |
| **models/ctr_validation_report.md** | 训练产出，和具体数据/模型绑定，一般不入库 |

**做法二选一即可：**

1. **不提交**：提交前不 `git add` 这些文件；或  
2. **用 .gitignore 排除**：在 `.gitignore` 里加一行 `logs/`（以及若不想提交模型产物可加 `models/`），这样 `logs/`、`models/` 下内容都不会被提交。

---

## 小结

- **必交**：`README.md`、`README_LLM_SETUP.md`、`FINAL_EXPERIMENT_DESIGN.md`、`GENDER_FAIRNESS_METRICS.md`、`ARCHITECTURE.md`
- **可选但推荐**：`AGENT_TUNING.md`、`AGENT_DEGREE_DIFFERENCES.md`、`EXPERIMENT_RECORDS.md`、`docs/CTR_VALIDATION_VERIFICATION.md`、`archive/README.md`
- **可不交**：`logs/` 下全部 `.md`、`models/ctr_validation_report.md`；建议把 `logs/` 加入 `.gitignore` 避免误提交
