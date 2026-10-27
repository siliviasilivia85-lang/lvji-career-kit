# 宿主能力与展示方式 · Host capabilities

履迹是一套可读文件、工作流和标准库助手。兼容性取决于当前 Agent 实际获得的工具与权限；产品名不能替代检查。首次启用只核对这次需要的能力，缺一项就用对应降级方式，不要求用户先安装完整应用。

LuJi is a method and local file toolkit, not a bundled Agent runtime. Check the capabilities available in this session. A host name alone does not guarantee file access, execution, attachment understanding, or preview support.

| 能力 / Capability | 完整路径 / Full path | 降级 / Fallback |
| --- | --- | --- |
| 读取本地文件 / Read | 读取SKILL、地图、所选正文与来源 / Read rules, maps, selected records | 只能读附件时可讨论和给草稿，不能声称已归档 / Attachment-only: analyze and draft; do not claim persistence |
| 写入本地文件 / Write | 确认后保存MD、回读 / Save approved records and read back | 提供可检查的草稿与目标路径，由用户保存 / Provide draft and destination for manual saving |
| 执行Python3.10+ / Execute | 版本检查、提案、地图、快照 / Revision checks, proposals, maps, snapshots | 仍可讨论/读文件；明确未运行校验和生成，不假称工具成功 / Read/discuss; report checks and generation not run |
| 理解附件 / Attachments | 宿主解析PDF、Word、图片、语音 / Host understands document/image/audio content | 说明不可读范围，请提供可读文本；不从文件名猜经历 / Request readable text; do not infer contents |
| 内联或文件预览 / Preview | 在宿主实际支持的位置展示HTML / Show HTML in supported panel | 提供实际HTML入口，在普通浏览器查看 / Open the actual file in a browser |
| 已安装Chrome/Chromium / PDF | 审阅确切HTML后导出同版PDF / Export reviewed version | 保留HTML，用户手动打印；手工PDF无导出回执时标未核验 / Keep HTML; manual PDF stays unverified without receipt |
| 通知或语音 / Reminders, voice | 仅按明确请求使用宿主能力 / Use host tools when explicitly requested | 本包不启动后台任务；对话中按需查看 / No built-in background task; request a view in conversation |

## 接入方式 · Entry modes

| 方式 / Mode | 第一次 / First use | 换对话 / New conversation |
| --- | --- | --- |
| 能打开本地目录的Agent / Local-folder Agent | 打开Skill包，读AGENTS与SKILL，初始化或连接工作区 / Open package and read entries, then initialize or connect | 打开个人工作区，沿AGENTS/AGENT-MAP定位Skill / Open workspace and follow its Skill locator |
| 已安装Skill的宿主 / Installed Skill | 按宿主提供的安装入口启用；仍核对文件/执行权限 / Enable using host-supported installation; check permissions | 复用已确认工作区；不要新建重复库 / Reuse the confirmed workspace |
| 仅对话/附件的Agent / Chat-only Agent | 可讨论职业路径与材料，提供待保存草稿 / Discuss and draft | 无本地读写时不能承诺跨对话持续归档 / No persistence guarantee without local file access |

不自动修改任何宿主的全局设置或安装目录。Skill位置失效时，沿 [navigation.md](navigation.md) 的setup修复；不重建manifest、不迁移职业数据。

Do not silently edit global host configuration or install the package elsewhere. Repair a moved Skill binding explicitly; preserve workspace identity and records.

## 实际验证 · Verification status

| 环境 / Environment | 当前证据 / Evidence | 仍需验证 / Remaining |
| --- | --- | --- |
| 本次本地Codex工作区 / This local Codex workspace | 标准库助手、隔离虚构目录读写、组件测试、IAB快照检查 / Local helpers, fictional fixtures, component tests, IAB snapshots | 真人首次启用、真实附件理解、定时通知 / Human first use, real attachments, scheduled notifications |
| 独立无前文Agent / Fresh Agent exercise | 包入口和虚构任务前向演练，见TESTING / Package-only exercises documented in TESTING | 模拟确认不是真人授权 / Simulated approval is not human approval |
| 其他Agent、Windows/Linux / Other hosts and OSes | 工具不依赖模型API；宿主实机状态未验证 / No model API dependency; host behavior unverified | Skill发现、路径、锁、中文字体、附件、预览 / Discovery, paths, locking, fonts, attachments, preview |

版本的实际检查见 [TESTING.md](../TESTING.md)。没有内联预览也能使用文件和对话；网页标签能被打开，不代表它能把选择自动传回Agent。当前快照不持续监听文件，也不实时写回。角色筛选仅影响显示，完整快照的资料范围没有因此缩小。

See [TESTING.md](../TESTING.md) for the specific version’s checks. Opening a page does not establish bidirectional Agent synchronization. Snapshots do not watch files or write back automatically. Filtering a role does not remove other records from the exported file.
