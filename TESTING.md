# 验证与试用 · Verification and trials

本文件提供使用者和贡献者可复现的验证方法。内部逐轮测试日期、执行日志、截图、模拟确认记录与生成的测试工作区留在本地，不随源码分发。源码内的固定示例日期用于复现虚构案例，不是任何人的真实日程；资产来源与外部参考的核对日期按用途保留。

This guide describes reproducible checks. Internal run histories, dated test reports, screenshots, simulated approval transcripts, and generated test workspaces are excluded from the source package. Fixed dates in test code and fictional examples are fixtures, not a real person's schedule. Asset provenance and reference-verification dates are retained where relevant.

## 本地文件流程 · Local file workflow

在Skill根目录执行：

```text
python3 -B -m unittest discover -s scripts -p 'test_*.py'
```

当前功能与公开演示包含202项Python测试，覆盖身份与版本、来源闭包、并发/恢复、原件发现与双地图、独立想法/阶段摘要、统一行动、岗位判断、投递实际用版、来源简历、PDF回执和面试材料。Python助手使用标准库，无需模型密钥。结构和摘要校验不能证明每句职业经历真实，仍需Agent与用户核对材料。

The current functional and public-demo suite contains 202 Python tests. They check structure, revisions, provenance, recovery, discovery, planning, historical artifacts, and scoped workflows. They do not establish the semantic truth of career claims.

## 页面交互 · Page interactions

维护者需要已有Node.js、jsdom；它们不是日常运行Skill的依赖：

```text
NODE_PATH=<已有node_modules目录> node --test assets/md_workspace.test.cjs assets/resume_gallery.test.cjs assets/demo_intro.test.cjs
```

当前页面包含48项DOM检查，覆盖视图、筛选、键盘/焦点、减少动态效果、内容转义、确切版本入口及画廊选择。类型检查可将两个HTML中的可执行script提取为临时JS，再使用TypeScript的 `--allowJs --checkJs --noEmit --target ES2022 --lib DOM,ES2022 --skipLibCheck`；不要把application/json数据占位块当成可执行JS。

The page suite contains 48 DOM checks. The public demo intro is static HTML; the interactive gallery reuses the existing tested script. Node.js, jsdom, and TypeScript are maintenance tools, not runtime requirements. Browser rendering and human usability remain separate from DOM checks.

## 用虚构资料试用 · Try fictional materials

请先读[试用说明](examples/try-it.md)。自然任务用于检查Agent能否沿地图找到资料、先展示草稿、确认后保存，并在新对话中只恢复已存内容。测试中的模拟确认不等于真实使用时的人类授权。

确定性演示由Agent或维护者执行，替换占位目录和日期，且输出目录必须全新：

```text
python3 -B scripts/demo.py --workspace <全新且不存在的临时目录> --date YYYY-MM-DD
python3 -B scripts/demo_gallery.py --output <新的画廊目录> --date YYYY-MM-DD
python3 -B scripts/demo_site.py --output <新的公开演示目录>
```

演示仅使用包内虚构输入，不读取真实工作区；拒绝覆盖已有目录。画廊生成六排版×头像A/B/无图的18种选择，完整与内嵌页面均为派生文件，不装入源码包。

Follow the trial guide for natural Agent tasks. Deterministic demos use fictional inputs and fresh output directories. Simulated approval in a test never substitutes for approval of a real user's concrete draft.

## 实际展示与PDF · Real previews and PDF

网页是带生成时间的离线快照，需另做浏览器目视检查；筛选不会缩小HTML内的数据范围。PDF使用本机已安装的Chrome/Chromium，在用户审阅并确认确切HTML之后导出同版文件，再检查回执、PDF页数、字体、图片和分页。无引擎时保留HTML；没有可信回执的手工PDF标为未核验。

Inspect rendered pages separately. Export a PDF only after approval of that exact HTML, then check its receipt and visual layout. A generated token is not human consent. A PDF without a trusted receipt is unverified.

## 公开范围与验证边界 · Publication scope and limits

发布只按白名单导出规则、工具、固定模板、许可与虚构原始输入；不带实际data、.luji、Git历史、生成简历/PDF、临时测试目录或内部测试报告。发布清单记录逐源文件摘要，不能替代完整安全审计。

README有五种语言；运行时首用指南和地图仍为中文或英文，固定界面主要中文。新用户建议将职业资料放在安装目录之外，已有路径不自动迁移。尚未完成所有宿主/操作系统实机、真人首用、全部真实附件和所有简历组合的PDF目视验收。Windows锁包含分支测试，不代表Windows实机验证。后台提醒、实时同步不内置。

Source exports exclude personal data, runtime history, generated artifacts, and internal test reports. A source manifest does not constitute a complete security audit. Read the [host capability guide](references/hosts.md) for fallbacks; tests do not imply verification on every host or OS. Background reminders and live synchronization are not built in.
