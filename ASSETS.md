# 来源、依赖与用途

文档、提示词、Python、HTML/CSS/JavaScript模板与测试为履迹项目原创，沿用本包MIT LICENSE。六种简历排版沿用项目自有renderer；未复制第三方模板、截图、字体或私人简历。

examples下人物、学校、公司、JD和产出全部为原创虚构，不对应真实招聘。它们只用于协议示例、可复现测试和明确标注的虚构演示，不能作为用户事实。

面试工作流、提示词、元数据助手及演练示例为本项目原创；demo中的产品讨论、用户回答与确认均为模拟，没有采集真实公司的面试题或招聘反馈。

Python只使用标准库。页面无远程字体或CDN，样式画廊使用下述本地生成头像，不自动加载外部项目的照片/截图。系统字体随使用者系统许可，本包不分发字体。PDF调用本机已安装Chrome/Chromium，其许可归各自发行方；本包不下载、安装或分发浏览器。跨系统字体和打印可能不同。

目录导航助手、人/Agent地图模板、直接投放规则与虚构流程测试为本项目原创，无新增运行依赖。实际地图与材料清单在使用者工作区生成，不预装个人目录、职业内容或生成历史。

用户简历、照片、截图与工作产出由用户提供，不属于Skill源码，默认不公开。测试DOM可使用维护者已有jsdom（MIT）依赖；本包运行不需要Node/jsdom。MIT允许商业使用，本包没有通过技术限制阻止他人售卖。

玻璃表面与动效参考：[React Bits Glass Surface](https://reactbits.dev/components/glass-surface)、[Pill Nav](https://reactbits.dev/components/pill-nav)、[Motion布局原则](https://motion.dev/docs/layout-animations)。只参考交互与材质原则，未复制组件源码或引入React/Motion/GSAP。三节点品牌与岗位轨迹SVG、CSS和原生WAAPI逻辑均为本项目原创；没有添加图片/字体/新运行依赖。

## 虚构头像与简历样式画廊 · 2026-10-27

- `assets/demo-avatar.png`与`assets/demo-avatar-b.png`：由内置image_gen生成的虚构成年人物，分别为男性、女性形象；仅作演示占位，不代表用户或真实求职者。1254×1254 PNG，保留生成原图像素，未用程序重绘。A的SHA-256为`89339f74939d4cfe23b4c0e1a8241b62999a12887fb24f1f0f2d2329fe6ccc57`，B为`8d7d59a478d8b0e9f4558c63ae6fd5de6d6eb214f3769fa0bcbd5799fcdb6bd4`。生成方式与完整提示词见[头像提示词](assets/demo-avatars.prompts.md)。
- `assets/resume_gallery.html`、`scripts/demo_gallery.py`及测试为履迹原创。画廊使用自有六版renderer，支持两张虚构头像与无头像，不绑定性别；运行时样例由脚本生成，不把示例工作区或已生成简历打包发布。
- `references/resume-samples.json`保存2026-10-27实际读取的GitHub官方README、许可证和部分源码的核对结果。外部截图/演示只提供链接，未完成这些远程页面的截图目视；没有复制第三方模板、头像、截图或字体。
- 参考目录中的jglovier、VibeResume、Gratia、happysnaker标明MIT（各自第三方资产另计），casual-markdown-cv为Unlicense；Universal Résumé与Orbit保留原有限制，仅提供外链。具体许可范围以目录中链接的原项目LICENSE为准，不能用本包MIT替代它们的许可证。

## README与公开演示

- 五语言README为项目自写说明的译文，沿用MIT。未翻译并冒称已实现的功能，运行时指南仍仅支持中文/英文。
- `scripts/demo_site.py`、`assets/demo_intro.html`与配套测试为原创。它们只从固定虚构输入生成只读站点；不调用模型、账户或个人工作区。页面、头像和简历均由自有代码/上述生成头像派生，不复制真实Agent界面、个人聊天或外部项目截图。
- `assets/readme-overview.png`为内置image_gen生成的职业成长框架概念说明图，随本项目按MIT发布。1672×941无损PNG，保留生成原图像素；不是实际界面截图，也不代表在线Agent或真人经历。画面只使用产品概念与说明文案，未输入个人工作区、账号、简历或聊天记录。SHA-256为`ba2cde1078e834048889b3e2b4890f6cce3703808686433f17744b99216fb2df`；完整生成提示词见[说明图提示词](assets/readme-overview.prompt.md)。原低分辨率JPEG截图不再作为公开包首图。
- `.github/workflows/pages.yml`只引用GitHub官方Actions来构建和发布专用演示目录，需维护者手动触发；各Action适用其自身许可证，本包未复制Action源码。来源：[GitHub Pages工作流](https://docs.github.com/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)。
- `skills`是可选安装渠道，不是Skill运行依赖，未捆绑其代码；命令及来源见[安装说明](references/install.md)。
