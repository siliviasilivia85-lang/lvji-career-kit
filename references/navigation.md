# 双地图、资料入口与范围检查

需要发现直接投放的资料、定位具体文件或续接事项时读取。目录、清单、地图负责定位；职业正文仍在原 MD，用户无需登记字段或执行命令。

## 哪些文件给谁看

| 文件 | 用途 |
| --- | --- |
| 包根 `README.md` / [map.md](map.md) | 人的启用说明、资料放置与日常入口 |
| 包根 `SKILL.md` / [agent-map.md](agent-map.md) | Agent 的行为、任务路由与读取顺序 |
| 工作区 `MAP.md` | 给人浏览真实目录、材料状态和分区入口 |
| 工作区 `AGENT-MAP.md` | 给 Agent 定位范围与读取清单 |
| 新工作区 `AGENTS.md` | 短入口，保留Skill相对/绝对定位与Agent地图；自动发现取决于宿主 |
| 工作区 `从这里开始.md` / `START-HERE.md` | 按中文/英文生成的人用首用入口 |
| 工作区 `navigation/inbox.md`、`past.md`、`present.md`、`future.md` | 同一清单派生的分区目录，按需展开 |
| 工作区 `.luji/navigation/catalog.json` | 工具维护的派生清单；含路径/元信息/检查时间/关联，不存职业正文 |

两张地图共用清单，不让用户分别维护。初始化新空库时生成；已有 MD 工作区通过 `refresh` 补地图，不重新 `init`。工具不会覆盖非本工具生成的同名地图；遇到冲突保留用户文件并说明。

初始化按 `--language zh|en` 生成分区README、首用入口和地图，`.luji/navigation/settings.json` 记录语言与Skill相对/绝对候选。固定英文目录用于保持引用兼容，文件名与用户自建子目录可中文；不会翻译职业正文或重命名既有路径。用户自写同名文件不覆盖；生成内容使用所有权标记。

## 用户可以直接放在哪里

| 内容 | 资料入口 |
| --- | --- |
| 暂时不知道分类 | `inbox/` |
| 简历、证书、过往经历、学习笔记 | `past/materials/`，可按 resume/learning 等自建子目录 |
| 当前公共材料 | `present/materials/` |
| 某事项的材料 | `present/items/<事项>/materials/`；事项主记录仍可为 `present/items/<事项>.md` |
| 暂未明确方向的目标材料 | `future/materials/` |
| 某方向的公开资料或 JD 候选 | `future/roles/<方向>/materials/` |
| 某公司某机会的 JD、截图、反馈原件 | `future/roles/<方向>/companies/<公司>/<机会>/materials/` |

这些入口中的普通 Markdown、PDF、Word、图片等均是只读原件，不需要 frontmatter。只忽略已识别的固定生成指南；用户资料子目录中的 `README.md` 也会作为普通材料发现。保留文件名与位置，正式记录用 `sources` 引用，不能用 `propose` 覆盖原件。旧 `past/originals/` 及回执继续可用，不搬移、重命名或自动迁移。照片用于简历时仍遵循现有照片流程。

资料入口之外的正式 MD 仍按 [workspace.md](workspace.md) 校验。用户可直接编辑其正文，后续以实际读取为准；不要把损坏的正式 MD 当待整理材料而静默跳过。放错位置或读不清时说明路径和修复方式，不编内容。

手动编辑行动日期或状态，要改对应frontmatter字段 `scheduled_for`、`due_on`、`status`；只改正文不重排计划。保留稳定ID和JSON值。用户无需学字段，可直接请Agent做局部修改。

## Skill位置失效或切换语言

新对话先沿工作区入口验证Skill候选的根SKILL与脚本；有效位置才可调用。包移动、定位缺失或需要换指南语言时，使用：

```text
python3 <已确认的新Skill根>/scripts/md_navigation.py --workspace <原工作区> setup --language zh --skill-root <已确认的新Skill根>
# English guides: --language en
```

setup只修复派生定位、已标记的地图/指南，不扫描职业正文、不改manifest/ID、不搬动资料。已有MD工作区可由此显式接入；仍不迁移旧格式。只读refresh不应擅自换成另一个包。若用户自写AGENTS/同名指南冲突，保留并说明需人工或单独授权编辑的具体文件；不要删除它来完成修复。跨宿主自动发现的实测边界见[hosts.md](hosts.md)。

## 每次检查多大范围

```text
python3 <Skill根>/scripts/md_navigation.py --workspace <工作区> refresh --scope past
... refresh --scope future/roles/AI产品经理/companies/星桥实验室/产品经理
... catalog --scope present
... link --material past/materials/resume/我的简历.pdf --record past/work/产品经历.md
```

`--scope` 支持 `all`、`inbox`、`past`、`present`、`future` 或安全的具体目录。`all` 用于首次总览或用户明确要求全库核对；日常先选任务相关范围。`catalog` 只读已有缓存，不刷新目录、不证明所有材料最新，也不提供正式写入基准。

`refresh` 核对所选目录的文件列表、stat与正式 MD 前置信息，不读取所有正文、不对所有原件算哈希。未检查区域保留“未检查”或原检查时间；stat相同也不证明内容一致。读取、关联和正式保存时仍按实际文件核验。目录检查失败保留旧清单与旧地图，明确失败范围，不能输出空状态代替。

没有后台监听。用户放文件后，下次进入相关范围才发现；不能因为地图存在就声称持续掌握全库变化。与当前任务无关的新材料不打断用户。

## 材料状态与整理闭环

| 状态 | 含义 |
| --- | --- |
| `pending` | 已发现，尚无已核实的整理关联 |
| `processed` | 已核实有正式记录引用该材料的相应版本 |
| `changed` | 已关联材料的目录特征变化，需要实际重读复核 |
| `missing` | 以前登记的材料在本次检查范围内缺失 |

处理状态与事实确认分开。读取失败应说明具体限制，不能把文件不存在、未检查和无法理解混成一种状态。

1. 按地图检查范围，选中新增/更新原件；宿主读取实际内容，列来源与缺失。
2. 可以先只读分析。需要更新正式资料时给出具体草稿/差异，不自动把 JD、旧学习计划或模拟回答变成能力。
3. 新记录保留原件路径，并用本次 `md_workspace.py context` 的实际哈希填写 `source_revisions`。具体确认后按原提案流程保存并回读。
4. 调用 `link --material ... --record ...` 登记整理关联；多个记录重复传 `--record`。工具只在正式记录已经存在、`sources` 包含该原件且记录的版本与当前材料一致时登记；不能靠这个命令确认用户事实。
5. 刷新相关范围的双地图；如还需要看页面，再按需生成快照。没有实际保存的草稿仍是待采纳内容。

如果一份材料支持多个事项或方向，引用同一实际路径；不为三个时间角度复制同一事实。相关协议见 [turn-protocol.md](turn-protocol.md)。
