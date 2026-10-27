# 文件契约与Agent命令

只在需要文件操作时读。主文件是Markdown，索引/页面/简历不是第二套主数据。工具需Python3.10+；命令中的`<根>`是Skill绝对路径，`<工作区>`是已确认的绝对路径，用户不用敲命令。

## 目录

```text
manifest.json                    schema_version + workspace_id + created_at
MAP.md                           给人的地图（派生）
AGENT-MAP.md                     给Agent的导航（派生）
navigation/{inbox,past,present,future}.md  同源分区清单（派生）
inbox/                           直接投放、暂未分类的原件
past/
  materials/                     可直接投放的过往材料，自建子目录
  personal.md                    用户身份/联系方式（可选）
  work/ education/ projects/ awards/ learning/ photos/
  profile.md                     可推翻的职业画像（可选）
  originals/<kind>/              指定原件与receipt，不是已确认事实
present/
  materials/                     当前公共原件
  items/                         持续事项与续接摘要
    <事项>/materials/            该事项原件；主记录仍可为items/<事项>.md
  checks/                        差距与取舍分析
  notes/                         不必关联目标或事项的独立想法
  stages/                        职业阶段回看，以引用承接既有积累
  actions/                       行动：日期/状态唯一来源
  learning/ work/                 每次学习/工作记录与产出引用
  plans/daily/ weekly/ monthly/ yearly/
future/materials/                尚未明确方向的公开材料/JD
future/roles/<方向>/
  materials/                     本方向原件
  goal.md                        可独立方向
  thoughts/ research/ assessment.md
  common/resumes/<版本>/          派生通用简历
  common/interviews/              岗位通用准备、模拟；stories/存可复用故事
  companies/<公司>/<机会>/
    materials/                   本机会JD、截图、反馈等原件
    jd.md application.md feedback/
    resumes/<版本>/               派生公司简历
    interviews/<轮次ID>/          prep-<版本>.md、practice-<日期>-<标识>.md
views/                           可删后重建的HTML快照
.luji/proposals/ history/          本地草稿/写入历史，不随源码发布
.luji/navigation/catalog.json    工具维护的导航缓存，不是职业正文
.luji/navigation/settings.json   语言与Skill本地定位，非manifest身份
```

同一项目的过去事实不搬进present，item以sources引用；同一行动在各period plan只引用ID。路径可中文，ID稳定英文slug。目录初始化提供指南，不填假事实。

资料入口内的普通MD/PDF/Word/图片等按只读原件处理，不要求frontmatter；正式记录可用sources引用这些实际路径。旧past/originals继续有效，显式导入流程不变。propose不能写这些原件、manifest或派生地图。导航生成/状态与命令见[navigation.md](navigation.md)。

## Markdown格式

使用一个有意义的记录一个文件。Frontmatter是安全的YAML子集：每行一个key，值用JSON字面量或简单字符串，不支持多行YAML/锚点。正文是普通Markdown；Agent可用`dump_document(metadata,body)`生成。用户可直接改记录正文；行动改期和状态要修改 `scheduled_for`、`due_on`、`status` 元数据，正文里的日期不驱动日程。优先让Agent代改并保留其他字段；手动编辑保持ID和JSON值合法。

```markdown
---
id: "action-samples"
type: "action"
title: "整理十个评估样本"
status: "todo"
item_id: "item-evaluation"
goal_ids: ["ai-product"]
scheduled_for: "2026-10-23"
due_on: null
minutes: 90
depends_on: []
sources: ["past/projects/知识检索原型.md"]
---
完成条件：十个问题、预期结果与选择理由。
```

共用必需`id/type/title`。可选`sources`本地相对文件、`related_ids`、日期/标签/状态、`source_revisions`来源哈希。原件URL写source_url或正文，不伪作本地路径。自定义简单元数据保留；已知字段仍校验。变更不更换id/type、角色/公司/机会身份或抹掉来源历史。

| type | 特有字段/要求 |
| --- | --- |
| personal/work/education/project/award/learning/portrait/photo-note | 位于past；photo-note的asset_path指用户指定照片；portrait分事实/能力/偏好/推断 |
| item | 位于present；可选status(todo/doing/done/paused)、goal_ids；正文保存目标/已决定/未确定/下一步 |
| note | 位于present/notes/；recorded_on必需；目标/事项关联可为空，不是简历事实来源 |
| stage-summary | 位于present/stages/；recorded_on；可选transition(review/leaving/offer/joining/direction-change)、item_ids引用实际item；不自动变更状态或生成行动 |
| goal | role_id（通常同id）、priority整数0～5、可选desired_by/target_kind(role/startup/other)、decision_status(exploring/adopted/paused，省略代表尚未确认) |
| thought/research | role_id，recorded_on / researched_on；research可有source_url/company_name |
| jd | role_id/company_id/company_name/opportunity_id/collected_on/requirements[]；source_url可选 |
| assessment | role_id/evaluated_on/criteria[]；每条requirement/status/evidence[]/note，supported/partial必须有证据 |
| check | generated_on，可选goal_id/action_ids；正文写差距/优先级/取舍 |
| action | status(todo/doing/done/paused)，可选item_id/goal_ids/scheduled_for/due_on/minutes/spent_minutes/depends_on |
| learning-log/work-log | recorded_on，可选item_id/action_ids/evidence_paths/evidence_status(record/candidate/confirmed) |
| plan | period(daily/weekly/monthly/yearly)/start_date/end_date/action_ids，正文写该尺度的目的和取舍 |
| application | role/company/opportunity IDs、company_name、stage、updated_on、next_action、history[{date,stage,note,resume_ref?}]；历史只追加，末条与现阶段一致；resume_ref准确结构见future.md |
| feedback | role_id/company_id/opportunity_id/received_on，正文保留实际反馈和来源 |
| interview-story | role_id/updated_on，非空sources；仅在该岗位common/interviews/stories/；不带公司/机会/轮次 |
| interview-prep | role_id/prepared_on，非空sources；可选interview_on（日期或null）；公司版须company_id/opportunity_id/round_id |
| interview-practice | role_id/practiced_on，非空sources；实际模拟回答与建议分开；公司版须company_id/opportunity_id/round_id |

portrait/assessment/check与三种interview材料须记录全部所用来源revision，缺失或变化会显示需复核；新投放原件的整理记录同样记录其实际revision，供核实整理关联。不为了清掉警告直接替换哈希，须重新看原文和结论。

note/stage-summary有本地来源时同样声明实际source_revisions，无本地来源的口述可留空并注明依据。来源闭包统一包含sources/evidence_paths/asset_path及声明revision，保存与读取用同一循环检测；普通双向联系用related_ids。goal的role_id全库唯一，重复时应定位已有方向更新或选择确实不同的身份，不为通过校验随意改旧ID。

面试prep/practice可放岗位common/interviews/，也可放实际公司机会interviews/<轮次ID>/；公司与机会ID必须成对，公司版必须有round_id，通用版不带round_id。目录从已有goal/JD定位，不假定中文目录名等于ID。面试材料是带来源的表达与练习，不能作为个人事实供简历直接取证。真实面试反馈沿用feedback，可额外带round_id；详见[面试工作流](interview.md)。

## 文件助手

```text
python3 <根>/scripts/md_workspace.py --workspace <工作区> init --language zh
# English: init --language en；按需显式 --skill-root <根>
... index --area past --type project
... read --path past/projects/知识检索原型.md
... context --path present/actions/新行动.md --path past/projects/知识检索原型.md
... import-source <用户指定原件> --kind resume
... propose --file <临时草稿.json>
... apply <proposal_id> --confirmed
... validate
```

`read`只读显式路径，返回documents和draft_base。准备保存/续接所选事项时用`context --path ...`：自动追加这些文件声明的来源递归闭包（包括sources/evidence_paths/asset_path/source_revisions），返回同一draft_base及requested_paths/source_paths；原件仍无正文，不读取无关库。新草稿新增的引用也作为--path显式加入。新路径不存在时base值null，不伪造空正文。原件只返回元信息/哈希，理解内容需宿主另读原件。index只读正式记录前置信息，跳过资料入口；发现新原件用导航清单，不能因index未列原件就认为没有。

## 导航命令（Agent执行）

```text
python3 <根>/scripts/md_navigation.py --workspace <工作区> refresh --scope past
... setup --language zh --skill-root <根>
... refresh --scope future/roles/<方向>/companies/<公司>/<机会>
... catalog --scope present
... link --material past/materials/resume/简历.pdf --record past/work/经历.md
```

scope可为all/inbox/past/present/future或安全的具体目录。refresh只检查所选范围；catalog只读缓存，不证明最新、不提供draft_base。link在正式记录的sources和source_revisions与实际材料版本相符后登记processed，可重复--record关联多个记录；它不确认事实、不改原件。详情见[navigation.md](navigation.md)。

Agent准备的提案结构：

```json
{
  "title": "只把该行动改到周五",
  "base": {"workspace_id": "实际身份", "files": {"present/actions/任务.md": "read返回的sha256:值"}},
  "writes": [{"path": "present/actions/任务.md", "content": "完整Markdown，包括原字段与本次最小变更"}]
}
```

base必须覆盖每个将改文件及实际引用来源的递归闭包（来源自身的sources/evidence_paths也在内），新增路径null；写入只允许职业MD，不用propose改原件或manifest。先具体草稿确认，再apply，保存后read。冲突保留提案，重读出新版，不只换base。多文件中断重试同一proposal会恢复/报告实际状态；不要删除锁或盲目覆盖。`validate`检查格式、引用、重复ID、依赖环与来源变化，不等于语义真实性审计。

## 派生命令

```text
python3 <根>/scripts/md_views.py --workspace <工作区> --date YYYY-MM-DD --view overview
# 直接看本周：--view plan --period weekly
# 视图可选overview/plan/roles/applications；日期和筛选按views.md与--help。
python3 <根>/scripts/md_resume.py --workspace <工作区> templates
... context --role <role_id>
... build --role <role_id> --company <company_id> --opportunity <机会ID> --file <正文.json>
... list --role <role_id>
... inspect --draft <版本相对路径>
... inspect --draft <历史版本相对路径> --historical
... binding --draft <实际使用的版本相对路径> --artifact resume.html
... pdf --draft <版本相对路径> --approved <确切版token>
```

视图/简历输出不改职业事实。照片可选`--photo`。PDF需用户审阅确切HTML；token只是完整性凭据。历史inspect把原件完整性、来源新鲜度与模板变化分开；历史查看不等于可直接导出新PDF。binding给出实际文件的版本/文件名/哈希，用于已发生投递事件，不推断发出哪版。PDF只有导出回执核验后才是verified，未知旧文件保留为unverified。所有助手路径显式指定，不借当前shell目录猜资料归属。

## 面试材料定位与保存

```text
python3 <根>/scripts/md_interview.py --workspace <工作区> context --role <role_id>
... context --role <role_id> --company <company_id> --opportunity <机会ID> --round <轮次ID>
... list --role <role_id> --company <company_id> --opportunity <机会ID>
```

这两个命令只返回元信息，用于选范围与找材料；不代表已读全文，不自动生成答案或写入记录。随后用md_workspace的read/context显式取实际来源，Agent按提示词起草，使用同一propose/apply流程保存。

下面演示Agent如何生成一份公司准备稿的前置信息。示例路径与ID仅用于说明，实际应取当前工作区已有目标/JD及用户选择的来源。`source_revisions`来自本次context实际返回值，不手填演示哈希：

```python
from md_workspace import Workspace, dump_document

ws = Workspace(workspace_absolute_path)
destination = "future/roles/AI产品经理/companies/星桥实验室/产品经理/interviews/round-1/prep-v1.md"
sources = ["future/roles/AI产品经理/companies/星桥实验室/产品经理/jd.md",
           "past/projects/知识检索原型.md"]
context = ws.context([destination, *sources])
metadata = {
    "id": "starbridge-round-1-prep-v1", "type": "interview-prep",
    "title": "星桥产品经理 · 首轮准备", "role_id": "ai-product",
    "company_id": "starbridge", "opportunity_id": "product-manager",
    "round_id": "round-1", "prepared_on": "2026-10-23", "interview_on": None,
    "sources": sources,
    "source_revisions": {p: context["draft_base"]["files"][p] for p in sources},
}
# body是已展示的准备内容，每段个人事实注明真实来源；缺失来源先解决再提案。
proposal = {"title": "保存首轮面试准备", "base": context["draft_base"],
            "writes": [{"path": destination, "content": dump_document(metadata, body)}]}
# propose只形成草稿；apply仍需用户对这一具体版本的确认，保存后read回读。
```

准备版本新建；模拟记录引用当时准备稿，新准备稿再引用模拟记录，不反改旧准备稿造成循环引用。准备/模拟的保存不修改application、past事实或行动日期。需要上述变更时分清草稿与授权范围。
