# 台账与闸门

CSV 使用 UTF-8 或 UTF-8-SIG 编码，固定表头及顺序：

```csv
id,date,company,role,resume_version,version_verified,greeting_version,status,stage,next_action,notes
```

- `id`：唯一、非空、无首尾空格的记录标识。
- `date`：已知时建议 `YYYY-MM-DD`；未知留空。脚本不验证日期含义。
- `company`、`role`：实际已知名称，不从缩写猜主体。
- `resume_version`：本条实际使用的版本标识，精确匹配，不自动去空格或转换大小写。
- `version_verified`：仅 `true`、`false` 或空。只有核实实际版本才填 `true`，用户说“现在用新版”不证明历史记录也用新版。
- `greeting_version`：本条实际招呼语版本，未知留空。
- `status`：仅 `contacted`（已联系）、`read_no_reply`（有已读证据且未回复）、`replied`（已回复）、`resume_sent`（已发简历）、`interview`（已进入面试阶段）、`offer`（已收到录用意向）、`closed`（流程结束）或空。空在输出中计入 `unknown`。
- `stage`、`next_action`、`notes`：证据支持的阶段、下一步与相关说明；不确定留空。

逗号、引号或换行按 CSV 规则转义。完全空文件属于坏表头；仅有正确表头是合法零行台账，结论为样本不足。缺列、多列、重复表头、非法枚举或重复 ID 均报错，不跳过坏行后输出部分结果。

## 执行示例

从本 Skill 目录执行；其他目录执行时把脚本替换为实际安装位置：

```bash
python3 scripts/version_gate.py --ledger /path/to/project/.qiuzhi/LEDGER.csv --current-version product-v2 --json
python3 scripts/version_gate.py --ledger /path/to/project/.qiuzhi/LEDGER.csv --current-version product-v2 --current-version operations-v3
```

以上路径和版本都是用法占位示例，应换成用户真实输入；版本允许清单由用户或已授权的可靠记录确认。省略 `--current-version` 是合法调用，全部记录归未知。

| 条件 | 分类 |
|---|---|
| 行版本核实为 `true`，非空版本精确命中当前允许清单 | `clean` 干净 |
| 行版本核实为 `true`，版本非空，有允许清单但未命中 | `contaminated` 污染（相对当前比较范围） |
| 未核实、版本空白，或未提供当前允许清单 | `unknown` 未知 |

名称中包含“新版”“定稿”不影响判定。分类仅核验传入字段之间的关系，脚本无法验证用户实际投递时用了哪个文件。

## 输出与退出码

退出码 `0`：解析成功，包含零行和零干净样本。退出码 `2`：参数、文件、编码或表格错误，明确错误写到标准错误，不提供半份诊断。`--json` 成功输出包含 `current_versions`、`total_rows`、`groups`（三类各自的 `ids`、`count`、`status_counts`）、`insufficient_clean_samples` 与提示说明。脚本只读，不访问网络、不修改台账。

## 分母纪律

状态计数不是漏斗人数，也不是转化率。每个指标必须先说明观察期、进入阶段的证据、分子与分母包含哪些 ID。不得默认用总行数作为所有阶段分母；不得把 `unknown` 当失败；不得把 `closed` 一律算拒绝；不得推断一个较后状态证明所有前序渠道动作发生过。

例如要算“发简历后进入面试”，需另行确认哪些记录实际发过简历、哪些已进入面试，且两者来自同一可比批次；只有当前状态字段往往不足。此时只报计数与缺口，不输出伪精确百分比。干净样本大于零也不意味着数量、观察期或分组已足够诊断效果。
