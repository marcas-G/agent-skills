# 自动化优化

- [optloop](https://github.com/marcas-G/optloop)：外部监督器 + Docker 隔离执行循环。
- 入口 `/optloop:start-loop`，另有 stop/status/doctor/logs/reset 控制技能。
- 依赖 bash、Python、Docker daemon，以及容器内 Claude CLI 和认证/环境配置。
- 控制入口与运行时内部 Skill 必须作为整套插件维护，不直接拷贝单个文件。
