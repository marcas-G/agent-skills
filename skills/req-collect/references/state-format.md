# state.md 持久化规约（E3）

> state.md 是收集上下文的**唯一权威**。会话记忆只是工作副本，每轮同步。

## 路径与命名

- 根目录：项目 CLAUDE.md 的 `REQ_COLLECT_DIR` 优先，否则 `docs/requirements/`
- 需求目录：`<YYYY-MM-DD>-<slug>/`，slug 取自需求一句话：优先英文 kebab-case（可英译），否则拼音连写，≤40 字符
- 状态机（status 字段）：`collecting` → `awaiting-confirmation`（呈现全文请求确认时设置）→ `finalized`（用户确认后，终态，目录只读）

## 损坏判定（进入路由用）

- **损坏**（不作为恢复点、绝不覆写）：缺 `## 元数据`、缺 `status` 字段、缺任一必备章节头（要素草稿五节/未决清单/已问历史/变更记录）
- **内容残缺 ≠ 损坏**：结构完整但个别节内容空缺 → 照常载入，空缺处标 [UNRESOLVED]

## state.md 固定结构

```markdown
# <需求标题>

## 元数据
- id: <目录名>
- status: collecting | awaiting-confirmation | finalized
- created: <ISO 日期>
- updated: <ISO 日期>
- 需求方: <如有，没有写"未提供">

## 要素草稿

### 问题
<确认的内容；未决写 [UNRESOLVED: 原因]；矛盾写 [CONFLICT: A | B]；节空白写"（空白）">

### 场景
<同上>

### 干系人
<同上>

### 边界
In Scope: <…>
Out Scope: <…>

### 验收标准
<可判定条目清单；未决写 [UNRESOLVED: 原因]>

## 未决清单
- [UNRESOLVED]/[CONFLICT] 条目汇总（每条注明所在要素）

## 已问历史
- <每行一问：问题 + 轮次 + 要素 + 已答/未答。只记要素追问与矛盾裁决请求；流程性提问（续收哪个/先收哪个）不记。用途：追问去重（INV-2）>

## 变更记录
- <每轮一行：日期 | 变更节 | 一句话摘要>
```

## 写读规则

- **写**：每轮把"加工结果 + 当轮追问（计入已问历史）"全量覆写当前活动需求的 state.md，**落盘先于向用户输出**（INV-1，消除最后一轮追问丢失窗口）。
- **读**：进入时扫描根目录全部 `*/state.md`；status ≠ finalized 的是恢复点；损坏判定见上节，损坏者绝不覆写。
- **多需求**：多目录天然并存；同一时刻只写活动需求那一个；切换活动需求前先落盘当前的。
- **定稿**：status=finalized 后整个目录不再写入（INV-7）；requirement.md 与 state.md 同目录共存。
- **手工维护**：格式自描述，用户可手工编辑；格式演进必须向前兼容（旧文件可解析）。
