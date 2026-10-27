#!/usr/bin/env python3
"""Deterministic fictional vertical-loop fixture. Never reads a default workspace."""
from __future__ import annotations
import argparse
from datetime import date as Date, timedelta
from calendar import monthrange
import json
from pathlib import Path
import sys
from md_workspace import Workspace, dump_document, parse_document, digest, StoreError
from md_views import render
from md_resume import ResumeWorkspace

EXAMPLES=Path(__file__).resolve().parents[1]/'examples'
ASSETS=Path(__file__).resolve().parents[1]/'assets'

def run(root, date='2026-10-23', avatar='a'):
    """Synthetic confirmations only: not an Agent understanding/human approval test."""
    if avatar not in ('a','b','none'):
        raise ValueError('Demo avatar must be a, b or none.')
    avatar_asset={'a':'demo-avatar.png','b':'demo-avatar-b.png'}.get(avatar)
    avatar_label={'a':'AI生成虚构头像A','b':'AI生成虚构头像B'}.get(avatar)
    avatar_description={'a':'男性形象','b':'女性形象'}.get(avatar)
    root=Path(root)
    if root.exists():
        raise ValueError('Demo needs a new, nonexistent directory; no overwrite or real data.')
    anchor=Date.fromisoformat(date); start=anchor-timedelta(days=anchor.weekday())
    d=lambda n:(start+timedelta(days=n)).isoformat()
    ws=Workspace(root);ws.initialize()
    imports={name:ws.import_source(EXAMPLES/name,kind) for name,kind in (
        ('resume.md','resume'),('learning-plan.md','learning'),
        ('jd-starbridge.md','reference'),('jd-farhill.md','reference'),('evaluation-notes.md','evidence'))}
    if avatar_asset:
        imports[avatar_asset]=ws.import_source(ASSETS/avatar_asset,'photo')
    src=lambda name:imports[name]['source_path']
    writes=[]
    def doc(path,id,type,title,body,**fields):
        meta={'id':id,'type':type,'title':title,**fields}
        if meta.get('sources'):
            staged={w['path']:w['content'] for w in writes}
            meta['source_revisions']={source:digest(staged[source].encode()) if source in staged else ws.read([source])['draft_base']['files'][source] for source in meta['sources']}
        writes.append({'path':path,'content':dump_document(meta,body)})
        return path
    personal_body='姓名：周同学\n联系方式：zhou@example.invalid\n所有内容原创虚构。'
    if avatar_asset:
        personal_body+='\n示例提示：'+avatar_label+'仅作头像占位与排版演示，不代表真实人物。'
    personal=doc('past/personal.md','personal','personal','周同学 · 虚构身份',
        personal_body,sources=[src('resume.md')])
    photo_note=None
    if avatar_asset:
        photo_note=doc('past/photos/虚构头像.md','demo-avatar','photo-note',avatar_label+' · '+avatar_description+' · 仅作演示',
            avatar_label+'（'+avatar_description+'），仅作为虚构简历的头像占位与排版演示，不对应周同学或其他真实人物。\n它不能作为身份、学历、工作经历或能力陈述的事实依据。',
            asset_path=src(avatar_asset),sources=[src(avatar_asset)],recorded_on=date)
    education=doc('past/education/本科.md','education','education','澄海大学 · 信息管理',
        '2021—2025，信息管理本科。学校与人物为虚构。',sources=[src('resume.md')])
    work=doc('past/work/产品助理.md','work-assistant','work','清样研究社 · 产品助理',
        '2025—2026，参与访谈整理和需求优先级讨论。没有可披露业务增长数字。',sources=[src('resume.md')])
    project=doc('past/projects/知识检索原型.md','project-search','project','知识检索交互原型',
        '整理用户问题、设计检索结果反馈流程，完成交互原型；当时尚无系统检索评估。',sources=[src('resume.md')])
    learning=doc('past/learning/RAG基础.md','learning-rag','learning','过去的RAG学习',
        '已读基础概念；旧计划中的测试样本与错误归因尚未完成。',sources=[src('learning-plan.md')])
    goal='future/roles/AI产品经理/goal.md'
    doc(goal,'ai-product','goal','AI产品经理',
        '希望通过真实作品验证AI产品工作是否适合自己，不锁定单家公司。',role_id='ai-product',priority=4,target_kind='role',decision_status='adopted',created_at=date)
    sales_goal=doc('future/roles/AI解决方案/goal.md','ai-solutions','goal','AI解决方案',
        '保留一个独立备选方向，暂时没有足够资料判断。',role_id='ai-solutions',priority=5,target_kind='role',decision_status='exploring')
    thought=doc('future/roles/AI产品经理/thoughts/选择理由.md','thought-product','thought','选择理由与未确定项',
        '更喜欢问题定义与原型验证，行业与团队条件尚待比较。此为虚构用户设想。',role_id='ai-product',recorded_on=date)
    item=doc('present/items/检索评估作品.md','item-evaluation','item','把原型做成可解释的评估作品',
        '目标：完成一份能展示评估方法的小作品。\n已决定：本周最多投入五小时。\n未确定：是否长期选择该方向。\n下一步：整理十个测试问题。',status='doing',goal_ids=['ai-product'],sources=[project,goal])
    a1=doc('present/actions/整理评估样本.md','action-samples','action','整理十个测试问题',
        '完成条件：十个问题及期望结果，不虚构业务指标。',item_id='item-evaluation',goal_ids=['ai-product'],scheduled_for=d(4),due_on=d(4),minutes=90,status='todo',depends_on=[])
    a2=doc('present/actions/运行错误归因.md','action-errors','action','运行测试并记录错误归因',
        '完成条件：记录预期、实际结果与错误类型。',item_id='item-evaluation',goal_ids=['ai-product'],scheduled_for=d(5),due_on=d(5),minutes=120,status='todo',depends_on=['action-samples'])
    a3=doc('present/actions/整理作品说明.md','action-writeup','action','整理作品说明与局限',
        '完成条件：说明方法、发现和局限；本周剩余90分钟。',item_id='item-evaluation',goal_ids=['ai-product'],scheduled_for=d(6),due_on=d(6),minutes=90,status='todo',depends_on=['action-errors'])
    doc('present/checks/检索评估差距.md','check-evaluation','check','从原型到评估的实践缺口',
        '需求整理已有记录。评估实践缺口通过样本、错误归因和作品说明验证，不是再列一份课程。数据分析经验仍未知。',goal_id='ai-product',generated_on=date,action_ids=['action-samples','action-errors','action-writeup'],sources=[goal,project,learning])
    for period,folder,end in [('daily','daily',anchor),('weekly','weekly',start+timedelta(days=6)),('monthly','monthly',Date(anchor.year,anchor.month,monthrange(anchor.year,anchor.month)[1])),('yearly','yearly',Date(anchor.year,12,31))]:
        first=anchor if period=='daily' else start if period=='weekly' else anchor.replace(day=1) if period=='monthly' else anchor.replace(month=1,day=1)
        doc(f'present/plans/{folder}/{date}.md',f'plan-{period}','plan',{'daily':'今日下一步','weekly':'本周成果','monthly':'本月里程碑','yearly':'年度方向'}[period],
            '这些尺度引用同一行动集；日期和状态以action文件为准。\n本周预算五小时，先做一个可展示的小作品，其他目标不排入。',period=period,start_date=first.isoformat(),end_date=end.isoformat(),action_ids=['action-samples','action-errors','action-writeup'])
    opps=[]
    for company,name,jdfile,stage in [('starbridge','星桥实验室','jd-starbridge.md','preparing'),('farhill','远山智能','jd-farhill.md','researching')]:
        base=f'future/roles/AI产品经理/companies/{name}/产品经理'
        jd=doc(base+'/jd.md','jd-'+company,'jd',name+' · AI产品经理',
            (EXAMPLES/jdfile).read_text(),role_id='ai-product',company_id=company,company_name=name,opportunity_id=company+'-product',collected_on=date,
            requirements=['需求分析','检索评估','协作表达','数据分析'],sources=[src(jdfile)])
        app=doc(base+'/application.md','app-'+company,'application',name+' · 机会进展',
            '虚构机会，尚未实际投递。',role_id='ai-product',company_id=company,company_name=name,opportunity_id=company+'-product',stage=stage,updated_on=date,next_action='先审阅公司定向简历' if stage=='preparing' else '比较JD与自己的偏好',history=[{'date':date,'stage':stage,'note':'虚构用户选择，未投递'}],sources=[jd])
        opps.append((jd,app))
    assessment='future/roles/AI产品经理/assessment.md'
    doc(assessment,'assessment-product','assessment','AI产品方向 · 初次判断',
        '只覆盖示例要求；不是录用概率。',role_id='ai-product',evaluated_on=date,sources=[work,project],criteria=[
            {'requirement':'需求分析','status':'supported','evidence':[work],'note':'有访谈整理记录'},
            {'requirement':'检索评估','status':'gap','evidence':[],'note':'历史材料明确尚未做系统评估'},
            {'requirement':'协作表达','status':'partial','evidence':[project],'note':'有反馈流程原型，协作效果还待验证'},
            {'requirement':'数据分析','status':'unknown','evidence':[],'note':'资料不足，不能判断缺能力'}])
    def apply(batch,title):
        staged={w['path']:parse_document(w['content'])[0] for w in batch}
        pending=set(staged); used=set()
        while pending:
            path=pending.pop()
            if path in used: continue
            used.add(path)
            if path in staged: meta=staged[path]
            else:
                entries=ws.read([path])['documents']
                meta=entries[0]['metadata'] if entries else {}
            pending.update(set(Workspace._source_paths(meta))-used)
        base=ws.read(sorted(used))['draft_base']
        p=ws.propose({'title':title,'base':base,'writes':batch})
        return ws.apply(p['proposal_id'],confirmed=True)
    apply(writes,'DEMO ONLY：模拟用户已审核初始草稿')
    # Actual demo artifact and confirmed progress, not task completion inferred as capability.
    resultpath='present/work/检索评估产出.md'
    writes=[]
    output=doc(resultpath,'output-evaluation','work-log','检索评估作品 · 虚构产出',
        '原创虚构测试记录：十个问题，逐项记录预期、检索结果、错误类型。该样例只证明有记录的方法，不虚构准确率、业务效果或复杂工程能力。',
        recorded_on=date,item_id='item-evaluation',action_ids=['action-samples'],evidence_status='confirmed',evidence_paths=[src('evaluation-notes.md')],sources=[project,src('evaluation-notes.md')])
    metadata,body=parse_document(ws.path(a1).read_text())
    metadata['status']='done';metadata['spent_minutes']=90
    writes.append({'path':a1,'content':dump_document(metadata,body)})
    apply(writes,'DEMO ONLY：模拟用户确认真实样例产出和进度')
    writes=[]
    oldmeta,_=parse_document(ws.path(assessment).read_text())
    oldmeta['sources']=[work,project,resultpath]
    oldmeta['source_revisions']={p:ws.read([p])['draft_base']['files'][p] for p in [work,project,resultpath]}
    oldmeta['criteria'][1]={'requirement':'检索评估','status':'partial','evidence':[resultpath],'note':'有小样本方法记录，尚无系统性质量结果'}
    writes.append({'path':assessment,'content':dump_document(oldmeta,'实际产出确认后重新评估，不因done自动升分。')})
    apply(writes,'DEMO ONLY：模拟用户确认产出、进度与新版判断')
    # Build source-backed HTML before the simulated application feedback event.
    resume=ResumeWorkspace(ws)
    headline='AI产品方向 · 虚构试用'
    if avatar_label:
        headline+=' · '+avatar_label+'占位'
    content={"person":{"name":"周同学","headline":headline,"contacts":["zhou@example.invalid"]},
      "summary":{"text":"有需求梳理与原型记录，正在通过小样本检索评估作品验证下一步方向。","source_paths":[work,project,resultpath]},
      "sections":[
        {"title":"教育经历","items":[{"heading":"澄海大学 · 信息管理本科","body":"2021—2025（原创虚构学校与人物）","source_paths":[education]}]},
        {"title":"工作经历","items":[{"heading":"清样研究社 · 产品助理","body":"2025—2026，参与访谈整理与需求优先级讨论。","source_paths":[work]}]},
        {"title":"项目经历","items":[{"heading":"知识检索原型与小样本评估","body":"整理用户问题，完成反馈流程原型；记录十个测试问题的预期、结果和错误类型。尚无系统性质量或业务效果结论。","source_paths":[project,resultpath]}]},
        {"title":"技能","items":[{"heading":"需求与原型","body":"需求梳理、访谈记录、基础原型设计。","source_paths":[work,project]}]}],
      "source_paths":[personal,education,work,project,resultpath]+([photo_note] if photo_note else [])}
    # The generated avatar is explicitly opt-in for this fictional fixture only.
    # It is provenance, never a source for any personal or experience claim.
    photo_options={'photo':ws.path(src(avatar_asset))} if avatar_asset else {}
    common=resume.build(content,'ai-product',**photo_options)
    company=resume.build(content,'ai-product','starbridge','starbridge-product',**photo_options)
    # These events are synthetic user reports, not actual sending/contacting.
    apppath=opps[0][1];m,b=parse_document(ws.path(apppath).read_text())
    m['history'].extend([{'date':date,'stage':'applied','note':'虚构用户报告已自行投递；工具未发送'},
      {'date':date,'stage':'screening','note':'虚构反馈：进入初筛，准备产品讨论'}])
    m['stage']='screening';m['next_action']='准备产品讨论中的作品讲解'
    apply([{'path':apppath,'content':dump_document(m,b)}],'DEMO ONLY：模拟确认投递反馈记录')
    # Interview content stays Markdown, distinct from facts, task commitments and
    # actual interview feedback. New versions point backward to avoid source cycles.
    writes=[]
    story=doc('future/roles/AI产品经理/common/interviews/stories/知识检索作品.md',
        'story-search','interview-story','把检索原型讲清楚',
        '## 经历故事\n场景：知识检索结果需要可理解的反馈。\n我的行动：梳理问题与反馈流程，随后记录十个测试问题、预期和错误类型。\n结果边界：有原型和小样本方法记录，没有业务增长或系统准确率结论。\n## 可能追问\n为什么选这十个问题？如何扩大样本？这些是待准备的问题，不代表已完成。\n## 来源\n'+project+'\n'+resultpath,
        role_id='ai-product',updated_on=date,sources=[work,project,resultpath])
    firstbase='future/roles/AI产品经理/companies/星桥实验室/产品经理/interviews/product-first/'
    prep=doc(firstbase+'prep-v1.md','prep-star-first-v1','interview-prep','星桥 · 产品讨论准备',
        '## 先准备什么\n先讲清需求、评估样本选择与作品局限；面试日期尚未确定。\n## JD与个人证据\nJD要求检索评估：有十题的小样本记录，系统性质量验证仍不足。\n## 回答提纲与可能追问\n用“问题—个人行动—可验证结果—局限”讲解，区分学习与落地产出。\n## 反问\n团队如何定义评估质量？产品与技术如何协作？\n## 待核实\n轮次按虚构产品讨论暂名，实际考察点未知；题目只是推演。',
        role_id='ai-product',company_id='starbridge',opportunity_id='starbridge-product',round_id='product-first',prepared_on=date,interview_on=None,sources=[goal,opps[0][0],story,learning])
    apply(writes,'DEMO ONLY：模拟用户审核通用故事与公司准备稿')
    writes=[]
    practice=doc(firstbase+'practice-01.md','practice-star-first','interview-practice','作品讲解 · 模拟记录',
        '## 模拟追问\n为什么只选十个问题？\n## 模拟回答摘要\n先用小样本记录方法与错误类型，尚未验证系统整体质量。\n## 观察与下一步建议\n表达时先讲选择理由，再讲样本规模局限；扩大样本是实践建议，未创建任务。\n本记录是模拟练习，不是面试官反馈，也不是新增工作成果。',
        role_id='ai-product',company_id='starbridge',opportunity_id='starbridge-product',round_id='product-first',practiced_on=date,sources=[prep,story])
    apply(writes,'DEMO ONLY：模拟用户确认练习摘要')
    writes=[]
    revised=doc(firstbase+'prep-v2.md','prep-star-first-v2','interview-prep','星桥 · 产品讨论准备（练习后）',
        '## 先准备什么\n先回答样本选择理由，再展示错误归因与可验证记录。\n## 经历故事\n复用岗位通用故事，不重写为新经历。\n## 回答边界\n十题只支持小样本方法说明，不声称系统准确率。\n## 待实践\n更大样本验证尚未完成；练习建议没有自动排入日程。\n## 反问\n团队现有评估口径与产品验收方式是什么？\n本版引用旧准备稿与模拟记录，旧版保留。',
        role_id='ai-product',company_id='starbridge',opportunity_id='starbridge-product',round_id='product-first',prepared_on=date,interview_on=None,sources=[goal,opps[0][0],story,prep,practice])
    apply(writes,'DEMO ONLY：模拟用户审核练习后的新版本')
    report={'fictional_only':True,'simulated_confirmations':True,'workspace':str(root),'validation':ws.validate(),
        'avatar':{'variant':avatar,'enabled':bool(avatar_asset),'fictional_only':True,'ai_generated':bool(avatar_asset),
            'note_path':photo_note,'source_path':src(avatar_asset) if avatar_asset else None},
        'resumes':{'common':common['relative_path'],'starbridge':company['relative_path']},'interviews':{'story':story,'prep':prep,'practice':practice,'revised':revised}}
    report['view']=render(ws,date=date)
    from md_navigation import NavigationWorkspace
    navigation=NavigationWorkspace(ws)
    navigation.refresh('all')
    indexed=ws.index()['documents']
    for imported in imports.values():
        source=imported['source_path']
        linked=[entry['path'] for entry in indexed if source in entry['metadata'].get('sources',[])]
        if linked:
            navigation.link(source,linked)
    report['navigation']=navigation.refresh('all')
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',required=True);p.add_argument('--date',default='2026-10-23')
    p.add_argument('--avatar',choices=('a','b','none'),default='a',help='Fictional portrait A, portrait B (female), or no portrait.')
    a=p.parse_args()
    try: print(json.dumps(run(a.workspace,a.date,avatar=a.avatar),ensure_ascii=False,indent=2))
    except (ValueError,StoreError,OSError) as e:
        print(json.dumps({'ok':False,'error':str(e)},ensure_ascii=False));sys.exit(1)
if __name__=='__main__':main()
