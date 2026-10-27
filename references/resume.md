# 简历：选来源 → 正文 → 网页 → 审核 → PDF

用户说“做网页简历/针对每岗定制”即进入此流程，无需安装另一个Skill。主命令 `scripts/md_resume.py`；先 `templates/context/list` 按需定位，不把生成简历当成确认职业事实。

简历和[面试准备](interview.md)复用同一份来源。面试故事可提示表达重点，写简历时仍追读其底层经历与确认成果；模拟回答不能替代事实。用户只要求准备面试时，不必先生成或导出一份新简历。

进入前按[Agent地图](agent-map.md)核对相关来路/机会资料入口，发现新简历或JD后按需读取，保留检查范围。原件若尚未形成必要事实，先给整理草稿并确认保存，再制作来源简历；不能把raw文件的哈希当作已读经历，或直接绕过个人事实白名单。原件不搬动，保存后按导航协议核实整理关联。照片仍可由Agent显式导入photo来源，用户不用手动转换目录。

1. 确认role；公司版还需成对company/opportunity。先索引目标、JD和既有经历；`context`只定位范围，不代表已读正文。Agent `read`实际选中的personal、学历、工作/项目、相关技能与确认成长，不全读无关原件。
2. 给有来源正文草稿。规范拆分个人信息、简介、工作、项目、教育、技能；事实不存在就略去或问关键缺项，不把JD写成经历，不编造数字。确认记录可帮助措辞，但证据仍追溯产出。用户改一段就只改这一段。
3. 沿用已选模板；未指定时推荐默认 `profile-split`，不强迫六选一。用户想看样例或比较样式时，生成下节的虚构画廊，再用中文样式名或ID确认选择，不要求复制内部命令。`templates`另含evidence-archive/classic-single/ats-minimal/project-first/experience-first，排版不改内容；ats-minimal不代表通过ATS认证。
4. `build --role ... --file ...`生成独立版本。公司版加company/opportunity；正式用户简历只有用户指定照片才加 `--photo`，也可以无照片。包内AI生成头像A/B只用于明确标注的虚构演示，不自动放进真实简历，也不从网页复制他人的照片。原件和已发简历不覆盖。
5. 给实际HTML入口，让用户审阅该版。需要修改时新建版本；`inspect`检查冻结一致性与来源新鲜度并给对应token，token不是人类授权。模板代码升级单独报告，不用当前renderer重渲染结果否定当时冻结的HTML。
6. 只有用户审阅并确认这份确切HTML后，`pdf --draft ... --approved <token>`导出同版PDF。来源、身份、正文、照片、HTML变化均拒绝旧审核。使用已安装Chrome/Chromium的隔离临时配置，不下载、不访问用户浏览器资料。失败不报告已导出；无引擎保留HTML并说明手动打印。

派生版本在该角色 `common/resumes/v-.../` 或对应公司机会 `resumes/v-.../` 下：content.json、manifest.json、resume.html、可选照片和PDF。这里的JSON仅为派生简历快照，不是职业主数据。

成功导出PDF后另存 `pdf-receipt.json`，绑定工作区、版本、冻结HTML/正文/照片及PDF摘要；旧manifest与token不改写。列表区分absent（没有）、unverified（无可信回执）、verified（已核验）、tampered（变化或回执不符）。只有verified给正式PDF入口，手工放入或旧版无回执文件保留为未核验；不能仅凭`.pdf`文件名认定成功。导出/回执写入中断报实际失败并保留现状，不覆盖旧文件。校验是结构与完整性核对，不是完整PDF安全审计。

## 让用户先看样式

由Agent调用 `python3 <Skill根>/scripts/demo_gallery.py --output <新的预览目录> --date YYYY-MM-DD`。仅使用包内虚构材料，拒绝已有目录，不读取个人工作区。打开返回的index.html，六种排版均可切换头像A、头像B或无头像；同一排版不绑定性别。18个预览是选择样式的派生示例，不是18份用户简历，也不会写入用户资料。

画廊还列出[GitHub参考目录](resume-samples.json)中的7个外部样例，附官方样例与许可证链接。它们是外链参考，尚未作为内置模板接入；不能把选中外链项目说成已经安装或已能一键使用。需要借鉴时先核对具体许可证与第三方资产范围，不把示例真人资料/照片带入本包。

用户可直接说样式名，例如“简介侧栏”或“项目优先”；页面的选择仅切换预览，不自动回写Agent或职业档案。正式制作仍按上述事实读取、来源校对和独立留版流程。新版排版生成后需要审阅这一版HTML，再导出同版PDF；旧文件保留，不静默改写。

## 输入结构（Agent填写）

```json
{
  "person": {"name": "实际姓名", "headline": "目标表达", "contacts": []},
  "summary": {"text": "基于事实的简介", "source_paths": ["past/personal.md"]},
  "sections": [{"title": "教育经历", "items": [{"heading": "学校与专业", "body": "实际正文", "source_paths": ["past/education/本科.md"]}]}],
  "source_paths": ["past/personal.md", "past/education/本科.md"]
}
```

person身份/联系方式同样必须出自已读personal等事实；顶层列覆盖所有陈述的来源。工具验证文件一致与可追溯关系，不能替代语义真实性审查。目标JD可决定侧重，但不作为个人事实的唯一来源。

找回旧版：先 `list --role ...`（公司版加完整scope），仅列元信息；用户选择后 `inspect --draft ... --historical` 核验冻结原件并分别查看source_status与renderer_status。历史查看可保留过期或缺失来源的说明，不会替旧版换来源；新的PDF导出仍要求来源有效且审阅确切版。单份PDF变化不会伪装成已核验，也不应让其他完好版本消失。最新不等于已审核。

记录实际投递用版时调用 `binding --draft <确切版本目录> --artifact resume.html|resume.pdf`，返回该文件的version/artifact/sha256，按[所向流程](future.md)存入事件resume_ref。它能在来源后来变化时识别完好的历史文件，但不会代表用户已经投递、已经授权外发或认可当前内容。未知用版留未记录。生成或导出后按需刷新视图，保持版本入口。
