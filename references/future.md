# 所向：方向、公司机会与判断

用户可以先有方向，没有JD、过去关联或截止日期也有效。用goal.decision_status明确exploring（探索）、adopted（已采纳）或paused（暂停）；未写表示尚未确认，不能假定已采纳。保存候选档案不会自动产生执行承诺，探索行动本身可单独确认。`future/roles/<方向>/goal.md` 写想去哪里、为什么、偏好和约束；`thoughts/<日期>-<主题>.md` 保存当时的思考/取舍，不用新目标抹掉旧选择。

“想了解”先探索，“我想做产品经理”等可能去向适时提出exploring草稿，“我决定往这个方向发展”才提出adopted草稿；先定位是否已有同一方向，重复提及不降低原有采纳状态。按[逐轮协议](turn-protocol.md)展示目标、已知理由/约束、待定项与存放位置，一次具体确认后即可初步建档；公司/JD/匹配分析可后补，不当作建档门槛。希望达到的未来状态不是已经发生的经历。

先查该方向或机会的地图清单。用户可把原始JD/截图放进 `future/materials/`、方向 `materials/` 或具体公司机会的 `materials/`。未建方向也能先读资料讨论，不因内部ID强迫建目标。要正式留存时，再给候选方向/JD草稿；保留原件路径与版本，确认保存后登记整理关联和刷新该范围地图。

## 同岗多公司

```text
future/roles/AI产品经理/
├── goal.md
├── materials/                     直接投放的方向资料
├── thoughts/2026-10-23-选择理由.md
├── assessment.md
├── research/行业观察.md
├── common/resumes/<版本>/
├── common/interviews/             通用准备、故事与模拟
└── companies/星桥实验室/产品经理/
    ├── materials/                 直接投放的JD、截图与反馈原件
    ├── jd.md
    ├── application.md
    ├── feedback/<日期>.md
    ├── resumes/<版本>/
    └── interviews/<轮次ID>/       本机会准备与模拟
```

同一公司可有多个机会，用稳定role/company/opportunity ID识别；路径可中文，但不因改标题改身份。

一个方向只有一个role_id。重复提及时先定位已有goal，更新该方向；确实不同的方向才另建独立身份，避免简历和面试定位产生歧义。

先请用户给现成JD；没有且需要调研时，用宿主真实搜索能力查公开职位，记录实际URL、收集日期、地点/级别等限制。过期/无法验证说明，不能虚设真实招聘。用户职业资料不作为公开搜索词发送。research保留产品/行业公开依据；jd保存原始要求，不写用户已经具备。

## 匹配、信息、偏好分开

角色assessment比较共性要求；公司差异在每条requirement中注明公司名称，并引用具体JD，不把某家公司专属要求当全岗位共性。每条要求标 `supported / partial / gap / unknown`，写实际证据路径、理由与评估日期。supported/partial必须有相应证据；使用当前日志时只用已确认且有真实产出的内容。unknown表示资料不足，不是确定不匹配。

页面展示各类数量与依据；排序可按已知要求的支持程度、信息充分度、用户priority。内部排序启发式 `(支持+0.5×部分)/(支持+部分+缺口)` 仅用于比较本轮已列要求，不是录用概率；无已知项就未评估。范围/要求不同不能声称具有跨行业科学可比性。评估过期显示需复核，用户偏好不被自动覆盖。

源变化后，先读新的事实和原判断，再形成新assessment草稿。完成行动不自动升分，职位数不等于目标清晰度。差距转行动另走 [present.md](present.md)。

## 投递节点

application保存当前stage、next_action和追加式history。基础stage：researching调研、preparing准备、applied已投递、screening初筛、interview面试、offer录用、closed结束。面试轮次/笔试/复试写history.note，可自定义其他元数据；不强制每家公司走同一线性路径，允许回退、重复面试、直接结束。

用户反馈截图先理解，再展示“哪家公司、什么岗位、发生何事、拟改阶段、下一步”的草稿；确认后追加事件、同步当前stage。不能因做了简历就标已投递。全局和单岗页面读取同一application。收到真实反馈后，简历改措辞与源事实纠正分开；已发出去的版本保留。

记录投递或补交材料时，同时核对实际使用的简历文件。已知版本用 `md_resume.py binding --draft <确切版本目录> --artifact resume.html|resume.pdf` 取得绑定，写入该次 `history` 事件的可选 `resume_ref`：

```json
{
  "version": "future/roles/<方向>/companies/<公司>/<机会>/resumes/v-<实际标识>",
  "artifact": "resume.pdf",
  "sha256": "sha256:<binding实际返回的64位摘要>"
}
```

不手填演示哈希。仅可绑定同方向通用版或这个公司机会的专属版，不串到其他机会。用户不确定用哪版时允许省略或null，在正文/事件说明未记录，不用“最新版本”补猜。旧版本来源后来变化不抹掉实际使用历史；旧PDF没有可信导出回执时标未核验，不能伪造绑定。既有绑定不可重写，缺失/变化只提示复核；纠正误记通过追加说明事件保留原历史。页面历史节点会展示实际用版与可核验入口。

简历与面试共用证据，属于同一应聘准备链路。需要故事卡、岗位提问、逐轮模拟或面后复盘时读 [interview.md](interview.md)；准备材料和模拟不会自动推进application。真实反馈继续存feedback，可用round_id标轮次，不另维护一套投递状态。
