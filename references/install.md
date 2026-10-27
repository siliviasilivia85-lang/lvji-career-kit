# 安装一次，之后正常交流 · Install once

品牌：**履迹 LüJi**。仓库、安装目录和Skill标识统一使用 **`lvji-career-kit`**。既有资料的 `luji-markdown-0.1` 等格式标识保留，它们是兼容协议，不需要随品牌重命名。

Brand: **履迹 LüJi**. The public package and Skill identifier is **`lvji-career-kit`**. Existing workspace schema identifiers stay unchanged for compatibility.

## 把安装交给Agent · Ask your Agent

可以把公开仓库链接交给Agent：

> 请从 https://github.com/siliviasilivia85-lang/lvji-career-kit 安装并启用这个 Skill，职业资料放在Skill目录外；先陪我整理一段经历，正式保存前让我核对。

Give your Agent the public repository URL:

> Install and enable lvji-career-kit from https://github.com/siliviasilivia85-lang/lvji-career-kit. Keep my career workspace outside the installed Skill. Start with one experience, and let me review the draft before saving it.

已下载到本地时，也可以让Agent从当前文件夹安装。If you already downloaded the package, ask your Agent to install it from that folder instead.

Agent先读根SKILL，核对当前宿主的读写/执行权限，再使用该宿主的安装方式。无需用户逐轮复制内部指令。仅能聊天、不能操作本地文件的宿主，可以讨论和给草稿，但不能声称完成本地安装或留存。安装不创建职业事实、不启动后台任务、不修改用户的全局配置来扩大权限。目标安装目录已有内容时先说明，不递归删除或覆盖。

The Agent reads the root Skill and checks actual host capabilities. A chat-only host can discuss and draft, but cannot claim local installation or persistence. Do not delete an existing installation or change global permissions as part of setup.

## 现有宿主 · Host entry points

| 宿主 | 方式 |
| --- | --- |
| Codex | 可让内置Skill Installer从实际仓库链接安装；本地Skill支持项目 `.agents/skills/lvji-career-kit/` 或个人 `~/.agents/skills/lvji-career-kit/`。若宿主提供安装界面，优先使用其入口。 |
| Claude Code | 项目 `.claude/skills/lvji-career-kit/` 或个人 `~/.claude/skills/lvji-career-kit/`。独立Skill可直接使用，不代表已经上架插件市场。 |
| 其他本地Agent | 按其已支持的Skill目录或让它读取本包SKILL；缺执行/展示能力时按 [hosts.md](hosts.md) 降级。 |

官方说明：[Codex本地Skill与安装](https://learn.chatgpt.com/docs/build-skills)、[Claude Code Skills](https://code.claude.com/docs/en/skills)、[Claude插件与独立Skill](https://code.claude.com/docs/en/plugins/overview)。安装到文件目录不等于已获官方商店上架或所有宿主认证。

## 可选CLI安装 · Optional CLI

`skills` CLI支持仓库和本地目录。公开仓库的可选安装命令：

```text
npx skills add siliviasilivia85-lang/lvji-career-kit --skill lvji-career-kit
```

本地发现检查（不安装Skill，npx自身仍可能下载CLI并写缓存）：

```text
npx skills add ./lvji-career-kit --list
```

CLI路线额外需要该工具要求的Node.js版本；日常Skill文件助手仍只需Python 3.10+。先读[官方命令](https://github.com/vercel-labs/skills/blob/main/docs/commands.md)与[发现规则](https://github.com/vercel-labs/skills/blob/main/docs/creating-skills.md)。根目录SKILL可以被发现，无需为安装把全部资料读进对话。命令指向实际公开仓库；各宿主的安装与权限仍以当前环境为准。

The remote command points to the public repository. The optional CLI has its own Node.js requirement; this does not add Node.js to the Python helpers' runtime requirements. Local discovery with `--list` does not install the Skill, but may populate the npx cache. Installation and permissions still depend on the host environment.

## 个人资料放在安装目录之外 · Keep your workspace separate

安装工具可能替换整个Skill目录；`skills` 的[实际安装实现](https://github.com/vercel-labs/skills/blob/main/src/installer.ts#L198-L204)会清理目标目录。安装文件应可更新，职业资料应长期保留。

- 有已确认工作区或入口时继续沿用，不自动迁移。用户指定目录优先，其次 `LUJI_WORKSPACE_DIR`。
- 全新用户可以在Skill目录外使用 `~/lvji-workspace/`。它是新工作区的建议位置，Agent展开为实际绝对路径并告知；不是对已有用户的搬迁命令。
- 若旧包内 `data/workspace/` 已存在，提示原位置和重装风险，让用户决定如何保留。不要把“安装新版”当作搬动、删除或上传职业资料的授权。
- 文件助手调用总带 `--workspace <实际绝对路径>`。CLI为开发者兼容保留的默认相对路径不用于猜测用户资料归属。

Keep the installed Skill separate from personal files. Existing paths remain valid; no migration is automatic. For a new workspace, `~/lvji-workspace/` is a suggested external location. If an older workspace lives inside the package, preserve it and discuss a deliberate move before updating that installation. Always pass the actual workspace path to file helpers.

新对话从个人工作区AGENTS/AGENT-MAP定位已安装Skill。安装位置变化后按[navigation.md](navigation.md)显式setup重新连接，不改资料身份。
