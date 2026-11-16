# 语言适配矩阵

| 语言 | 指纹 | 执行/覆盖 | 变异 | 模糊 | 假测试扫描 |
|---|---|---|---|---|---|
| Python | pyproject.toml / requirements.txt / setup.py | pytest + pytest-cov (coverage.json) | mutmut (native) 或内置 AST 启发式 | hypothesis | **AST 精确**（R1-R4） |
| JS/TS | package.json | jest/vitest --coverage --json | stryker (native) 或 BLOCKED 标注 | fast-check (手动) | 正则降级（标 engine=regex） |
| Go | go.mod | go test ./... -cover -json | go-mutesting (native) 或 BLOCKED | go native fuzz | 正则降级 |
| Rust | Cargo.toml | cargo test（未接覆盖细节→unknown 诚实标注） | cargo-mutants (native) | cargo-fuzz | 未实现→呈现为 BLOCKED |
| Java | pom.xml / build.gradle | mvn/gradle test（未接入） | pit (未接入) | jqwik (未接入) | 未实现→BLOCKED |
| Ruby | Gemfile | rspec（未接入） | mutant (未接入) | rspec-property | 未接入 |
| PHP | composer.json | phpunit（未接入） | infection (未接入) | — | 未接入 |

## 降级语义（REQ-D2）

未接入 ≠ 跳过。probe 对未接入组合报 `blocked` + reason，证据矩阵该维 BLOCKED，
放行需要显式弃权（C4 留痕）。新增语言时更新本表 + probe.py 指纹表 + verify.py RUNNERS，
复役判据：对样本项目三态判定正确（P5-E-2 Q6）。
