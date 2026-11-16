# 系统与软件工程

| 能力 | 入口 | 完整组成 |
|---|---|---|
| [fractal](https://github.com/marcas-G/fractal) | `/fractal-start` | P0–P8 + 递归检查，状态机与 Gate |
| [refactor-agent](https://github.com/marcas-G/refactor-agent) | `/refactor` | 内部六个 Skill + 状态与回滚流程 |
| [test-enforcer](https://github.com/marcas-G/test-enforcer) | `/test-enforcer` | Skill + Agent + 验证脚本 + Hooks |

这些均为**完整插件**，必须保留依赖及工具调用；内部 Skill 不单独发布。`refactor-agent` 和 `test-enforcer` 源仓库目前为私有，访问需要授权。
