# 履迹 Agent 入口

先读同目录 [SKILL.md](SKILL.md)，再按 [Agent 读取地图](references/agent-map.md) 选择本轮路径。这是职业发展方案，不是让你开发完整应用。

English entry: [README.en.md](README.en.md), [Agent reading map](references/agent-map.en.md). Respond in the user's language; runtime guides use `--language zh|en`. The physical directory names stay compatible across languages.

- 公开Skill名称为 `lvji-career-kit`，品牌为“履迹 LüJi”。本目录是可替换的安装文件，个人职业资料应独立保存；续用已确认路径，其次用户指定目录、`LUJI_WORKSPACE_DIR`。全新用户可用Skill目录外的 `~/lvji-workspace/`，建档前说明实际位置；旧包内资料不自动迁移。首次安装按 [install.md](references/install.md)，助手调用总显式传工作区。
- 新格式是 `luji-markdown-0.1`，职业主数据仅在 `past/ present/ future/` Markdown，manifest只标识身份。旧格式不迁移。
- 用户可直接放入 `inbox/`、各部分 `materials/`，或在对话中给资料。工作区 `MAP.md` 给人，`AGENT-MAP.md` 给 Agent；两图引用同一派生清单，用户不手工登记。
- 开始相关任务时按范围刷新目录清单，再选对象摘要和必要来源；不每轮扫描所有正文。未检查区域保留旧时间，清单不作写入基准。详见 [navigation.md](references/navigation.md)。
- 用户要虚构试用时按 [examples/try-it.md](examples/try-it.md)，使用全新临时目录，不读取真实工作区或环境变量指向的资料。
- 用户表达过去经历、当前进展或未来想法时，在值得留存的自然停顿合并提出具体草稿；确认后应用、回读。浏览、分析不反复确认，不每句话建文件。事项摘要负责跨对话续接。
- 自然表达的触发、缺失资料提示和一次确认按[逐轮协议](references/turn-protocol.md)。没有过往资料也可直接规划；探索/愿望/已决定分开，用户跳过的补充项不机械追问。中英文按同一语义处理。
- 明确导入时，指定原件可以先复制留存；事实整理另行确认。用户不用选内部目录、填schema、运行命令。
- 已直接放入入口的原件保留原名原位，先按需读取；新记录引用实际路径与版本，保存后登记关联并刷新地图。处理状态不是事实或能力确认。
- 保留发生时间/记录时间、来源、稳定ID、已有历史与未要求修改字段。事实纠正、简历措辞、阶段更新分别处理。
- 文件/页面错误如实报告，保留成功部分与旧快照，不把读失败当空状态。无模型密钥仍可读写和生成页面。
- 不自动发送资料、投递、联系招聘方或启用后台任务。公开内容不包含真实工作区。
