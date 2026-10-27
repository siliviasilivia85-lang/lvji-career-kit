/* Test-only jsdom. Runtime HTML needs no packages, network, or server.
 * NODE_PATH=<existing node_modules> node --test assets/md_workspace.test.cjs
 */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM, VirtualConsole} = require('jsdom');
const template = fs.readFileSync(path.join(__dirname, 'md_workspace.html'), 'utf8');

function fixture() {
  const documents=[];
  const doc=(p,m,body='全部为虚构示例。',freshness='current')=>{
    const d={path:p,metadata:m,body,revision:'sha256:'+'a'.repeat(64),freshness,href:'file:///fictional/'+encodeURI(p)};
    documents.push(d);return d;
  };
  const roles=[];
  for(const [id,priority,counts,stale] of [
    ['current',2,{supported:1,partial:1,gap:1,unknown:1},false],
    ['low',1,{supported:0,partial:0,gap:1,unknown:0},false],
    ['unknown',5,{supported:0,partial:0,gap:0,unknown:2},false],
    ['stale',3,{supported:3,partial:0,gap:0,unknown:0},true],
  ]) {
    const goal=doc(`future/roles/${id}/goal.md`,{id,role_id:id,type:'goal',title:'虚构方向 '+id,priority});
    const criterion=[];for(const [status,n] of Object.entries(counts))for(let i=0;i<n;i++)criterion.push({requirement:status+'要求'+i,status,evidence:['supported','partial'].includes(status)?['past/work/experience.md']:[],note:'有来源的虚构判断'});
    const assessment=doc(`future/roles/${id}/assessment.md`,{id:'assessment-'+id,role_id:id,type:'assessment',title:'虚构判断',evaluated_on:'2026-10-23',criteria:criterion},'',stale?'stale':'current');
    const jd=doc(`future/roles/${id}/companies/example/one/jd.md`,{id:'jd-'+id,type:'jd',role_id:id,company_id:'example',company_name:'示例公司（虚构）',opportunity_id:'one',title:'产品岗位 '+id,collected_on:'2026-10-22'},'原始岗位要求');
    const known=counts.supported+counts.partial+counts.gap;
    roles.push({id,goal,documents:[assessment.path,jd.path],assessment,counts,known,total:known+counts.unknown,priority,needs_review:stale,fit_sort_value:known?(counts.supported+.5*counts.partial)/known:null});
  }
  const work=doc('past/work/experience.md',{id:'work',type:'work',title:'虚构经历',occurred_on:'2026-01-01'},'真实格式的虚构经历。');
  doc('past/profile.md',{id:'portrait',type:'portrait',title:'暂定理解',sources:[work.path]},'这是一项可纠正的暂定判断。','unverified');
  const item=doc('present/items/item.md',{id:'item',type:'item',title:'继续虚构原型练习',status:'doing'},'产出一份可测试原型。');
  const action=doc('present/actions/action.md',{id:'action',type:'action',title:'完成原型',item_id:'item',goal_ids:['current'],status:'done',scheduled_for:'2026-10-23',due_on:'2026-10-25',minutes:40,spent_minutes:45,depends_on:[]});
  const unscheduled=doc('present/actions/later.md',{id:'later',type:'action',title:'尚未安排的访谈',item_id:'item',status:'todo',scheduled_for:null,minutes:null,depends_on:['action']});
  const log=doc('present/learning/log.md',{id:'log',type:'learning-log',title:'原型学习结果',recorded_on:'2026-10-23',item_id:'item',action_ids:['action'],evidence_status:'record'},'记下了失败与下一步。');
  const plans=['daily','weekly','monthly','yearly'].map(period=>doc(`present/plans/${period}/plan.md`,{id:'plan-'+period,type:'plan',title:'虚构 '+period+' 计划',period,start_date:'2026-01-01',end_date:'2026-12-31',action_ids:['action']},'先完成一项成果，预留时间。'));
  const app=doc('future/roles/current/companies/example/one/application.md',{id:'application',type:'application',title:'产品机会',role_id:'current',company_id:'example',company_name:'示例公司（虚构）',opportunity_id:'one',stage:'interview',updated_on:'2026-10-23',next_action:'准备用户记录的二面',sources:[work.path],history:[{date:'2026-10-20',stage:'applied',note:'用户记录投递'},{date:'2026-10-23',stage:'interview',note:'用户记录一面反馈'}]},'等待下一轮实际反馈。');
  const second=doc('future/roles/low/companies/another/two/application.md',{id:'application-two',type:'application',title:'另一机会',role_id:'low',company_id:'another',company_name:'另一公司（虚构）',opportunity_id:'two',stage:'preparing',updated_on:'2026-10-22',next_action:'整理材料',history:[]});
  const resume=(company,opportunity,name)=>({relative_path:'future/roles/current/'+name+'/resumes/v-1',template:'profile-split',created_at:'2026-10-23T08:00:00+00:00',inspection_status:'not_inspected',scope:{role_id:'current',company_id:company,opportunity_id:opportunity},html_href:'file:///fictional/'+name+'/resume.html',pdf_href:company?'file:///fictional/'+name+'/resume.pdf':null,pdf_status:{status:company?'verified':'absent'}});
  return {schema_version:'luji-markdown-view-0.1',workspace_id:'fictional-id',workspace_path:'/fictional',generated_at:'2026-10-23T08:30:00+00:00',as_of:'2026-10-23',documents,source_links:Object.fromEntries(documents.map(d=>[d.path,{path:d.path,absolute_path:'/fictional/'+d.path,href:d.href,revision:d.revision}])),roles,items:[item],actions:[action,unscheduled],logs:[log],plans,applications:[app,second],resumes:[resume(null,null,'common'),resume('example','one','company')],warnings:[{path:'past/profile.md',message:'来源基准未齐，需重新评估'}],initial_state:{view:'overview',period:'daily'}};
}

function open(data=fixture(),hash='', setup=null,origin='file:///fictional/views/overview.html') {
  const errors=[];
  const virtualConsole=new VirtualConsole();
  virtualConsole.on('jsdomError',error=>errors.push(error));
  const serialized=JSON.stringify(data).replace(/</g,'\\u003c').replace(/&/g,'\\u0026');
  const dom=new JSDOM(template.replace('__LUJI_DATA__',serialized),{url:origin+hash,runScripts:'dangerously',virtualConsole,beforeParse(window){window.HTMLDialogElement.prototype.showModal=function(){this.open=true;};window.HTMLDialogElement.prototype.close=function(){this.open=false;};if(setup)setup(window);}});
  assert.deepEqual(errors,[]);
  return dom;
}

function click(dom,selector){const element=dom.window.document.querySelector(selector);assert.ok(element,'missing '+selector);element.click();return element;}
function change(dom,selector,value){const element=dom.window.document.querySelector(selector);element.value=value;element.dispatchEvent(new dom.window.Event('change',{bubbles:true}));}
const text=(dom,selector)=>dom.window.document.querySelector(selector).textContent;

test('overview shows continuing item progress, daily action and ordinary record',()=>{
  const dom=open();
  assert.match(text(dom,'#view-overview'),/已完成 1 \/ 2 项行动/);
  assert.match(text(dom,'#view-overview'),/完成原型/);
  assert.match(text(dom,'#view-overview'),/普通记录/);
  assert.match(text(dom,'#view-overview'),/暂定理解/);
  click(dom,'[data-doc="present/items/item.md"]');
  assert.match(text(dom,'#detail-body'),/当前行动/);
  assert.match(text(dom,'#detail-body'),/原型学习结果/);
  dom.window.close();
});

test('explicit initial weekly view starts Monday and shares actual action/log',()=>{
  const data=fixture();data.initial_state={view:'plan',period:'weekly'};
  const dom=open(data);
  assert.equal(dom.window.document.querySelector('#view-plan').hidden,false);
  assert.match(text(dom,'.day-number'),/^10-19/);
  assert.equal(dom.window.document.querySelectorAll('.day').length,7);
  assert.match(text(dom,'#plan-content'),/原型学习结果/);
  assert.match(text(dom,'#plan-content'),/已知预计 40 分钟/);
  click(dom,'[data-period="monthly"]');
  assert.equal(dom.window.document.querySelectorAll('.day').length,42);
  assert.match(text(dom,'#plan-content'),/虚构 monthly 计划/);
  click(dom,'[data-period="yearly"]');
  assert.equal(dom.window.document.querySelectorAll('[data-month]').length,12);
  click(dom,'[data-month="2026-10-01"]');
  assert.equal(dom.window.document.querySelector('[data-period="monthly"]').getAttribute('aria-pressed'),'true');
  assert.match(text(dom,'#plan-content'),/完成原型/);
  assert.match(dom.window.document.querySelector('#workspace-data').textContent,/"scheduled_for":"2026-10-23"/);
  dom.window.close();
});

test('changing period dates never invents scheduled actions',()=>{
  const dom=open(fixture(),'#view=plan&period=weekly');
  click(dom,'#next-period');
  assert.match(text(dom,'#plan-content'),/这个时段尚未安排实际行动/);
  assert.match(text(dom,'#plan-content'),/待安排的行动/);
  click(dom,'#today');
  assert.match(text(dom,'#plan-content'),/完成原型/);
  dom.window.close();
});

test('evidence sorting keeps current judgments before stale and unknown',()=>{
  const dom=open(fixture(),'#view=roles');
  const order=()=>[...dom.window.document.querySelectorAll('.role-card')].map(e=>e.dataset.role);
  assert.deepEqual(order(),['current','low','stale','unknown']);
  assert.match(text(dom,'[data-role="current"]'),/资料已判断 3 \/ 4/);
  assert.match(text(dom,'[data-role="unknown"]'),/资料不足，待判断/);
  assert.match(text(dom,'[data-role="stale"]'),/需重新评估/);
  assert.doesNotMatch(text(dom,'#roles-content'),/\d+%|置信阈值|录取概率/);
  change(dom,'#role-sort','priority');
  assert.deepEqual(order(),['unknown','stale','current','low']);
  change(dom,'#role-sort','information');
  assert.deepEqual(order(),['low','current','stale','unknown']);
  dom.window.close();
});

test('role detail provides evidence, company JD and common/opportunity resume files',()=>{
  const dom=open(fixture(),'#view=roles');
  click(dom,'[data-role="current"]');
  const body=dom.window.document.querySelector('#detail-body');
  assert.match(body.textContent,/匹配依据/);
  assert.match(body.textContent,/示例公司（虚构）/);
  assert.match(body.textContent,/尚未判断/);
  assert.equal(body.querySelectorAll('a[href$="resume.html"]').length,2);
  assert.equal(body.querySelectorAll('a[href$="resume.pdf"]').length,1);
  assert.match(body.textContent,/历史版本未复核/);
  assert.doesNotMatch(body.textContent,/approval_token|已批准/);
  dom.window.close();
});

test('application filters combine role/company/opportunity and clear to global pipeline',()=>{
  const data=fixture();data.initial_state={view:'applications',role:'current',company:'example',opportunity:'one'};
  const dom=open(data);
  assert.equal(dom.window.document.querySelectorAll('.application-card').length,1);
  assert.match(text(dom,'#applications-content'),/准备用户记录的二面/);
  click(dom,'#clear-filters');
  assert.equal(dom.window.document.querySelectorAll('.application-card').length,2);
  change(dom,'#application-company','another');
  assert.equal(dom.window.document.querySelectorAll('.application-card').length,1);
  assert.match(text(dom,'#applications-content'),/另一公司/);
  dom.window.close();
});

test('application detail shows only real history and correct opportunity resume',()=>{
  const dom=open(fixture(),'#view=applications');
  click(dom,'[data-application="future/roles/current/companies/example/one/application.md"]');
  const body=dom.window.document.querySelector('#detail-body');
  assert.equal(body.querySelectorAll('.history li').length,2);
  assert.match(body.textContent,/2026-10-20/);
  assert.match(body.textContent,/用户记录一面反馈/);
  assert.equal(body.querySelectorAll('a[href$="resume.html"]').length,1);
  click(dom,'#close-detail');
  click(dom,'[data-application="future/roles/low/companies/another/two/application.md"]');
  assert.match(text(dom,'#detail-body'),/尚未记录历史/);
  assert.equal(dom.window.document.querySelectorAll('#detail-body .history li').length,0);
  dom.window.close();
});

test('a role with JD but no application stays selected and shows an honest empty state',()=>{
  const dom=open(fixture(),'#view=applications&role=unknown&company=example&opportunity=one');
  assert.equal(dom.window.document.querySelector('#application-role').value,'unknown');
  assert.equal(dom.window.document.querySelector('#application-company').value,'example');
  assert.equal(dom.window.document.querySelector('#application-opportunity').value,'one');
  assert.equal(dom.window.document.querySelectorAll('.application-card').length,0);
  assert.match(text(dom,'#applications-content'),/尚无符合筛选的投递记录/);
  dom.window.close();
});

test('copy request includes actual selected path, date and user adjustment without save',async()=>{
  const dom=open();
  click(dom,'[data-request="present/actions/action.md"]');
  const note=dom.window.document.querySelector('#agent-note');
  assert.equal(dom.window.document.activeElement,note);
  note.value='改到下周二，先让我看影响';
  note.dispatchEvent(new dom.window.Event('input',{bubbles:true}));
  let copied='';
  Object.defineProperty(dom.window.navigator,'clipboard',{value:{writeText:async value=>{copied=value;}}});
  click(dom,'#copy-context');
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(copied,/\/fictional\/present\/actions\/action.md/);
  assert.match(copied,/改到下周二/);
  assert.match(copied,/先重读来源/);
  assert.match(text(dom,'#copy-status'),/已复制/);
  assert.equal(dom.window.document.querySelectorAll('button').length>0,true);
  assert.equal([...dom.window.document.querySelectorAll('button')].some(e=>e.textContent==='保存'),false);
  dom.window.close();
});

test('clipboard denial leaves selected usable context and explicit unsaved state',async()=>{
  const dom=open();
  click(dom,'#ask-agent');click(dom,'#copy-context');
  await Promise.resolve();
  assert.match(text(dom,'#copy-status'),/已选中上下文/);
  assert.match(dom.window.getSelection().toString(),/页面本身尚未保存任何修改/);
  click(dom,'#close-agent');
  assert.equal(dom.window.document.querySelector('#agent-dialog').open,false);
  dom.window.close();
});

test('source title/body are escaped throughout overview, dialogs and role cards',()=>{
  const data=fixture(),payload='<img src=x onerror="window.bad=true">';
  data.items[0].metadata.title=payload;data.items[0].body=payload;data.roles[0].goal.metadata.title=payload;
  const dom=open(data);
  assert.equal(dom.window.document.querySelector('img'),null);
  assert.ok(text(dom,'#view-overview').includes(payload));
  click(dom,'[data-doc="present/items/item.md"]');
  assert.equal(dom.window.document.querySelector('img'),null);
  assert.ok(text(dom,'#detail-body').includes(payload));
  click(dom,'#close-detail');click(dom,'[data-view="roles"]');
  assert.equal(dom.window.document.querySelector('img'),null);
  assert.equal(dom.window.bad,undefined);
  dom.window.close();
});

test('snapshot info explains date/freshness and links real files with full revisions',()=>{
  const dom=open();click(dom,'#snapshot-info');
  assert.match(text(dom,'#detail-body'),/本页无法检测生成之后的外部修改/);
  assert.match(text(dom,'#detail-body'),/生成失败会保留/);
  assert.match(text(dom,'#detail-body'),/sha256:/);
  assert.ok(dom.window.document.querySelector('#detail-body a[href="file:///fictional/past/work/experience.md"]'));
  dom.window.close();
});

test('native keyboard targets, focus styles, reduced-motion and narrow layout rules exist',()=>{
  const dom=open();
  for(const button of dom.window.document.querySelectorAll('nav button')){assert.equal(button.tabIndex,0);button.focus();assert.equal(dom.window.document.activeElement,button);assert.ok(button.textContent.trim());}
  assert.match(template,/@media\(prefers-reduced-motion:reduce\)/);
  assert.match(template,/@media\(max-width:760px\)/);
  assert.match(template,/:focus-visible/);
  assert.match(template,/<dialog/);
  assert.equal(dom.window.document.querySelectorAll('script[src],link[href^="http"],img[src^="http"]').length,0);
  assert.doesNotMatch(template,/localStorage|sessionStorage|fetch\(|XMLHttpRequest/);
  dom.window.close();
});

test('unassessed directions omit zero-denominator metrics and empty pipeline columns',()=>{
  const data=fixture();
  const role=data.roles.find(r=>r.id==='unknown');role.assessment=null;role.known=0;role.total=0;
  const dom=open(data,'#view=roles');
  assert.doesNotMatch(text(dom,'[data-role="unknown"]'),/0 \/ 0/);
  click(dom,'[data-view="applications"]');
  assert.equal(dom.window.document.querySelectorAll('.stage').length,2);
  assert.equal(dom.window.document.querySelectorAll('.application-card').length,2);
  dom.window.close();
});

test('candidate goal is visible and dependency date conflicts are warnings without rescheduling',()=>{
 const data=fixture();data.roles[0].goal.metadata.decision_status='exploring';
 const parent=data.actions.find(a=>a.metadata.id==='action');parent.metadata.status='todo';parent.metadata.scheduled_for='2026-10-26';
 const child=data.actions.find(a=>a.metadata.id==='later');child.metadata.scheduled_for='2026-10-23';
 const dom=open(data,'#view=roles');assert.match(text(dom,'[data-role="current"]'),/探索中/);
 click(dom,'[data-view="plan"]');assert.match(text(dom,'#plan-content'),/前置行动安排得更晚/);
 assert.equal(child.metadata.scheduled_for,'2026-10-23');assert.equal(parent.metadata.scheduled_for,'2026-10-26');
 dom.window.close();
});

const selectWidget=(dom,id)=>dom.window.document.querySelector('#'+id).closest('.filter-select');
function key(dom,element,value){element.dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:value,bubbles:true,cancelable:true}));}
function motionHarness(initialReduced=false,rects=false){
  let reduced=initialReduced;const calls=[],listeners=new Set();
  const harness={calls,setReduced(value){reduced=value;for(const listener of listeners)listener({matches:value});},finish(){for(const call of calls)call.finish();}};
  harness.setup=window=>{
    window.matchMedia=()=>({get matches(){return reduced;},addEventListener(type,listener){if(type==='change')listeners.add(listener);},removeEventListener(type,listener){listeners.delete(listener);}});
    window.Element.prototype.animate=function(frames,options){
      let resolve,reject;let settled=false;
      const finished=new Promise((yes,no)=>{resolve=yes;reject=no;});
      const call={element:this,frames,options,cancelled:false,finish(){if(settled)return;settled=true;resolve();}};
      const animation={finished,cancel(){if(settled)return;settled=true;call.cancelled=true;reject(new Error('Test animation cancelled'));}};
      call.animation=animation;calls.push(call);return animation;
    };
    if(rects)window.HTMLElement.prototype.getBoundingClientRect=function(){
      const peers=Array.from(this.parentElement?.children||[]),index=Math.max(0,peers.indexOf(this));
      return {left:index*260,top:0,right:index*260+240,bottom:180,width:240,height:180,x:index*260,y:0,toJSON(){return this;}};
    };
  };
  return harness;
}

test('sort chips and native input stay synchronized while keyed card focus and source data survive',()=>{
  const data=fixture(),before=JSON.stringify(data);const dom=open(data,'#view=roles&sort=information',null,'https://fictional.invalid/views/overview.html');
  assert.equal(dom.window.document.querySelector('[data-sort="information"]').getAttribute('aria-pressed'),'true');
  assert.equal(dom.window.document.querySelector('#role-sort').value,'information');
  const card=dom.window.document.querySelector('[data-role="current"]');card.focus();
  change(dom,'#role-sort','priority');
  assert.equal(dom.window.document.activeElement.getAttribute('data-role'),'current');
  assert.equal(dom.window.document.querySelector('[data-sort="priority"]').getAttribute('aria-pressed'),'true');
  click(dom,'[data-sort="fit"]');
  assert.equal(dom.window.document.querySelector('#role-sort').value,'fit');
  assert.equal(new URLSearchParams(dom.window.location.hash.slice(1)).get('sort'),'fit');
  assert.equal(JSON.stringify(data),before);dom.window.close();
});

test('frosted select supports arrow/home/end selection, Escape and native fallback synchronization',()=>{
  const dom=open(fixture(),'#view=applications'),widget=selectWidget(dom,'application-role');
  const trigger=widget.querySelector('.select-trigger'),native=widget.querySelector('select');
  assert.equal(native.hidden,true);assert.equal(native.tabIndex,-1);assert.equal(native.getAttribute('aria-hidden'),'true');
  trigger.focus();key(dom,trigger,'ArrowDown');
  assert.equal(trigger.getAttribute('aria-expanded'),'true');
  assert.equal(dom.window.document.activeElement.getAttribute('role'),'option');
  key(dom,dom.window.document.activeElement,'End');
  const last=widget.querySelectorAll('[role="option"]');assert.equal(dom.window.document.activeElement,last[last.length-1]);
  key(dom,dom.window.document.activeElement,'Home');assert.equal(dom.window.document.activeElement,last[0]);
  key(dom,dom.window.document.activeElement,'ArrowDown');
  dom.window.document.activeElement.click(); // Native button Enter/Space activation dispatches click in browsers.
  assert.equal(native.value,'current');assert.equal(trigger.getAttribute('aria-expanded'),'false');
  assert.equal(dom.window.document.activeElement,trigger);assert.match(trigger.getAttribute('aria-label'),/虚构方向 current/);
  trigger.click();key(dom,trigger,'Escape');
  assert.equal(trigger.getAttribute('aria-expanded'),'false');assert.equal(dom.window.document.activeElement,trigger);
  change(dom,'#application-role','low');assert.match(trigger.getAttribute('aria-label'),/虚构方向 low/);
  assert.equal(widget.querySelector('[role="option"][aria-selected="true"]').getAttribute('data-option-value'),'low');
  dom.window.close();
});

test('opening another filter closes the first, and outside click/Tab close without stealing focus',()=>{
  const dom=open(fixture(),'#view=applications'),role=selectWidget(dom,'application-role'),company=selectWidget(dom,'application-company');
  role.querySelector('.select-trigger').click();company.querySelector('.select-trigger').click();
  assert.equal(role.dataset.open,'false');assert.equal(company.dataset.open,'true');
  const outside=dom.window.document.querySelector('[data-view="applications"]');outside.focus();outside.click();
  assert.equal(company.dataset.open,'false');assert.equal(dom.window.document.activeElement,outside);
  company.querySelector('.select-trigger').click();key(dom,company.querySelector('.select-trigger'),'Tab');
  assert.equal(company.dataset.open,'false');dom.window.close();
});

test('parent filters clear child scopes, and empty stage selection remains explicit until cleared',()=>{
  const data=fixture();data.initial_state={view:'applications',role:'current',company:'example',opportunity:'one'};
  const dom=open(data,'',null,'https://fictional.invalid/views/overview.html');click(dom,'[data-stage="interview"]');
  change(dom,'#application-role','low');
  assert.equal(dom.window.document.querySelector('#application-company').value,'');
  assert.equal(dom.window.document.querySelector('#application-opportunity').value,'');
  assert.equal(dom.window.document.querySelector('[data-stage="interview"]').getAttribute('aria-pressed'),'true');
  assert.match(text(dom,'[data-stage="interview"] .chip-count'),/^0$/);
  assert.equal(dom.window.document.querySelectorAll('.application-card').length,0);
  assert.match(text(dom,'#filter-summary'),/0/);
  click(dom,'[data-clear-filters]');
  assert.equal(dom.window.document.querySelectorAll('.application-card').length,2);
  const params=new URLSearchParams(dom.window.location.hash.slice(1));
  for(const name of ['role','company','opportunity','stage'])assert.equal(params.get(name),'');
  dom.window.close();
});

test('stage scope is applied to Agent context and does not include hidden opportunities',()=>{
  const dom=open(fixture(),'#view=applications');click(dom,'[data-stage="interview"]');click(dom,'#ask-agent');
  const context=text(dom,'#agent-context');
  assert.match(context,/future\/roles\/current\/companies\/example\/one\/application.md/);
  assert.doesNotMatch(context,/future\/roles\/low\/companies\/another\/two\/application.md/);
  dom.window.close();
});

test('explicit empty hash filters override a prefiltered generated page',()=>{
  const data=fixture();data.initial_state={view:'applications',role:'current',company:'example',opportunity:'one'};
  const dom=open(data,'#view=applications&role=&company=&opportunity=&stage=');
  assert.equal(dom.window.document.querySelector('#application-role').value,'');
  assert.equal(dom.window.document.querySelectorAll('.application-card').length,2);dom.window.close();
});

test('hash navigation and popstate restore filters/chips, and invalid values fall back safely',()=>{
  const dom=open(fixture(),'#view=roles',null,'https://fictional.invalid/views/overview.html');
  dom.window.history.replaceState(null,'','#view=applications&role=low&company=another&opportunity=two&stage=preparing&sort=priority');
  dom.window.dispatchEvent(new dom.window.HashChangeEvent('hashchange'));
  assert.equal(dom.window.document.querySelector('#view-applications').hidden,false);
  assert.equal(dom.window.document.querySelector('#application-role').value,'low');
  assert.equal(dom.window.document.querySelector('[data-stage="preparing"]').getAttribute('aria-pressed'),'true');
  assert.equal(dom.window.document.querySelectorAll('.application-card').length,1);
  dom.window.history.replaceState(null,'','#view=roles&sort=bad-sort&stage=bad-stage&role=&company=&opportunity=');
  dom.window.dispatchEvent(new dom.window.PopStateEvent('popstate'));
  assert.equal(dom.window.document.querySelector('#view-roles').hidden,false);
  assert.equal(dom.window.document.querySelector('[data-sort="fit"]').getAttribute('aria-pressed'),'true');
  const params=new URLSearchParams(dom.window.location.hash.slice(1));assert.equal(params.get('stage'),'');
  dom.window.close();
});

test('custom option labels remain inert text even with hostile role and company names',()=>{
  const data=fixture(),payload='<img src=x onerror="window.bad=true">';
  data.roles[0].goal.metadata.title=payload;
  data.documents.filter(d=>['jd','application'].includes(d.metadata.type)&&d.metadata.company_id==='example').forEach(d=>d.metadata.company_name=payload);
  const dom=open(data,'#view=applications');
  selectWidget(dom,'application-role').querySelector('.select-trigger').click();
  assert.ok(selectWidget(dom,'application-role').textContent.includes(payload));
  selectWidget(dom,'application-company').querySelector('.select-trigger').click();
  assert.ok(selectWidget(dom,'application-company').textContent.includes(payload));
  assert.equal(dom.window.document.querySelector('img'),null);assert.equal(dom.window.bad,undefined);dom.window.close();
});

test('reduced motion keeps every interaction immediate with zero WAAPI calls',()=>{
  const motion=motionHarness(true),dom=open(fixture(),'#view=roles',motion.setup);
  click(dom,'[data-sort="priority"]');click(dom,'[data-view="applications"]');
  selectWidget(dom,'application-company').querySelector('.select-trigger').click();
  click(dom,'[data-stage="interview"]');click(dom,'#ask-agent');click(dom,'#close-agent');
  assert.equal(motion.calls.length,0);assert.equal(dom.window.document.querySelector('#agent-dialog').open,false);
  assert.equal(dom.window.document.querySelectorAll('.application-card').length,1);dom.window.close();
});

test('rapid sort and stage changes cancel earlier motion and leave only the final state',async()=>{
  const motion=motionHarness(false,true),dom=open(fixture(),'#view=roles',motion.setup,'https://fictional.invalid/views/overview.html');
  const first=[...motion.calls];assert.ok(first.length>0);
  click(dom,'[data-sort="priority"]');click(dom,'[data-sort="information"]');click(dom,'[data-sort="fit"]');
  assert.ok(first.every(call=>call.cancelled));
  assert.deepEqual([...dom.window.document.querySelectorAll('.role-card')].map(el=>el.dataset.role),['current','low','stale','unknown']);
  click(dom,'[data-view="applications"]');click(dom,'[data-stage="interview"]');click(dom,'[data-stage=""]');
  click(dom,'[data-stage="preparing"]');
  motion.finish();await Promise.resolve();await Promise.resolve();
  assert.equal(dom.window.document.querySelectorAll('[data-exit-ghost]').length,0);
  assert.equal(dom.window.document.querySelectorAll('.application-card').length,1);
  assert.match(text(dom,'.application-card'),/另一公司/);
  assert.equal(new URLSearchParams(dom.window.location.hash.slice(1)).get('stage'),'preparing');dom.window.close();
});

test('reopening a dialog cancels its old close completion',async()=>{
  const motion=motionHarness(),dom=open(fixture(),'',motion.setup);
  click(dom,'#snapshot-info');const dialog=dom.window.document.querySelector('#detail');
  click(dom,'#close-detail');const oldClose=motion.calls[motion.calls.length-1];assert.equal(dialog.open,true);
  click(dom,'#snapshot-info');assert.equal(oldClose.cancelled,true);
  motion.finish();await Promise.resolve();await Promise.resolve();assert.equal(dialog.open,true);
  click(dom,'#close-detail');motion.finish();await Promise.resolve();await Promise.resolve();assert.equal(dialog.open,false);dom.window.close();
});

test('switching to reduced motion completes an already requested dialog close',async()=>{
  const motion=motionHarness(),dom=open(fixture(),'',motion.setup);
  click(dom,'#snapshot-info');click(dom,'#close-detail');
  assert.equal(dom.window.document.querySelector('#detail').open,true);
  motion.setReduced(true);await Promise.resolve();await Promise.resolve();
  assert.equal(dom.window.document.querySelector('#detail').open,false);dom.window.close();
});

test('empty filtered scope stays explicit in the Agent request instead of expanding to all records',()=>{
  const dom=open(fixture(),'#view=applications&role=unknown&company=example&opportunity=one&stage=interview');
  assert.equal(dom.window.document.querySelectorAll('.application-card').length,0);
  click(dom,'#ask-agent');const context=text(dom,'#agent-context');
  for(const fragment of ['方向 unknown','公司 example','机会 one','阶段 interview','匹配 0 个机会'])assert.ok(context.includes(fragment));
  assert.match(context,/不要自动改动其他记录/);
  assert.doesNotMatch(context,/future\/roles\/current\/companies\/example\/one\/application.md/);
  dom.window.close();
});

function interviewFixture() {
  const data=fixture();
  const add=(name,type,scope={},freshness='current')=>{
    const common=!scope.company_id;
    const folder=common?'common/interviews':'companies/'+scope.company_id+'/'+scope.opportunity_id+'/interviews/'+scope.round_id;
    const p='future/roles/'+(scope.role_id||'current')+'/'+folder+'/'+name+'.md';
    const metadata={id:name,type,title:name,role_id:'current',sources:['past/work/experience.md'],...scope};
    if(type==='interview-story')metadata.updated_on='2026-10-21';
    else if(type==='interview-prep'){metadata.prepared_on='2026-10-23';metadata.interview_on='2026-10-26';}
    else metadata.practiced_on='2026-10-22';
    const doc={path:p,metadata,body:name+' 的虚构准备正文',revision:'sha256:'+'b'.repeat(64),freshness,href:'file:///fictional/'+p};
    data.documents.push(doc);
    data.roles.find(r=>r.id===metadata.role_id)?.documents.push(p);
    data.source_links[p]={path:p,absolute_path:'/fictional/'+p,href:doc.href,revision:doc.revision};
    return p;
  };
  const paths={
    story:add('可复用故事卡','interview-story'),
    common:add('岗位通用准备','interview-prep'),
    prep:add('本机会一面准备','interview-prep',{company_id:'example',opportunity_id:'one',round_id:'round-1'},'stale'),
    practice:add('本机会模拟记录','interview-practice',{company_id:'example',opportunity_id:'one',round_id:'round-1'}),
    otherCompany:add('同岗其他公司材料','interview-prep',{company_id:'other',opportunity_id:'one',round_id:'round-2'}),
    otherOpportunity:add('同公司其他机会材料','interview-prep',{company_id:'example',opportunity_id:'two',round_id:'round-2'}),
    otherRole:add('其他方向材料','interview-prep',{role_id:'low'}),
  };
  return {data,paths};
}

test('role interview area exposes only reusable role material, no company or other-role leakage',()=>{
  const {data}=interviewFixture(),dom=open(data,'#view=roles');
  click(dom,'[data-role="current"]');
  const area=dom.window.document.querySelector('#detail-body .interview-section');
  assert.ok(area);
  assert.match(area.textContent,/可复用故事卡/);
  assert.match(area.textContent,/岗位通用准备/);
  assert.doesNotMatch(area.textContent,/本机会一面准备|同岗其他公司材料|同公司其他机会材料|其他方向材料/);
  assert.equal(dom.window.document.querySelectorAll('.tabs button').length,4);
  dom.window.close();
});

test('opportunity interview area shares common stories and isolates exact company, opportunity and round',()=>{
  const {data,paths}=interviewFixture(),before=JSON.stringify(data),dom=open(data,'#view=applications');
  click(dom,'[data-application="future/roles/current/companies/example/one/application.md"]');
  const area=dom.window.document.querySelector('#detail-body .interview-section');
  assert.match(area.textContent,/本机会一面准备|本机会模拟记录/);
  assert.match(area.textContent,/round-1/);
  assert.match(area.textContent,/2026-10-26/);
  assert.match(area.textContent,/需重新评估/);
  assert.match(area.textContent,/可复用故事卡/);
  assert.doesNotMatch(area.textContent,/同岗其他公司材料|同公司其他机会材料|其他方向材料/);
  click(dom,'#detail-body [data-doc="'+paths.prep+'"]');
  assert.match(text(dom,'#detail-body'),/本机会一面准备 的虚构准备正文/);
  assert.match(text(dom,'#detail-body'),/引用来源/);
  assert.match(text(dom,'#detail-body'),/past\/work\/experience.md/);
  click(dom,'#detail-body [data-request="'+paths.prep+'"]');
  assert.match(text(dom,'#agent-context'),/\/fictional\/future\/roles\/current\/companies\/example\/one\/interviews\/round-1\/本机会一面准备.md/);
  assert.equal(JSON.stringify(data),before);
  dom.window.close();
});

test('JD details expose scoped interview material without requiring an application record',()=>{
  const {data}=interviewFixture();data.applications=[];
  data.documents=data.documents.filter(d=>d.metadata.type!=='application');
  const dom=open(data,'#view=roles');
  click(dom,'[data-role="current"]');
  click(dom,'#detail-body [data-doc="future/roles/current/companies/example/one/jd.md"]');
  assert.match(text(dom,'#detail-body .interview-section'),/本机会一面准备/);
  assert.equal(data.applications.length,0);
  dom.window.close();
});

test('empty interview area requests preparation using exact goal, JD and opportunity, no writes',()=>{
  const data=fixture(),before=JSON.stringify(data),dom=open(data,'#view=applications');
  click(dom,'[data-application="future/roles/current/companies/example/one/application.md"]');
  assert.match(text(dom,'#detail-body .interview-section'),/本机会尚无面试材料/);
  click(dom,'#detail-body [data-prepare-role="current"]');
  const context=text(dom,'#agent-context');
  assert.match(context,/方向 current；公司 example；机会 one/);
  assert.match(context,/companies\/example\/one\/jd.md/);
  assert.match(context,/companies\/example\/one\/application.md/);
  assert.match(context,/不要自动改投递阶段、创建日程或把练习当成能力证据/);
  assert.doesNotMatch(context,/companies\/another\/two\/application.md/);
  assert.equal(JSON.stringify(data),before);
  dom.window.close();
});

test('interview labels, body and round values remain inert text in reused detail renderer',()=>{
  const {data,paths}=interviewFixture(),payload='<img src=x onerror="window.bad=true">';
  const prep=data.documents.find(d=>d.path===paths.prep);
  prep.metadata.title=payload;prep.metadata.round_id=payload;prep.body=payload;
  const dom=open(data,'#view=applications');
  click(dom,'[data-application="future/roles/current/companies/example/one/application.md"]');
  assert.match(text(dom,'#detail-body .interview-section'),/<img src=x/);
  click(dom,'#detail-body [data-doc="'+paths.prep+'"]');
  assert.match(text(dom,'#detail-body'),/<img src=x/);
  assert.equal(dom.window.document.querySelector('#detail-body img'),null);
  assert.equal(dom.window.bad,undefined);
  dom.window.close();
});

test('opportunity history stays expandable while preparation has a direct entry',()=>{
  const {data}=interviewFixture(),before=JSON.stringify(data),dom=open(data,'#view=applications');
  click(dom,'[data-application="future/roles/current/companies/example/one/application.md"]');
  const history=dom.window.document.querySelector('#detail-body .history').closest('details');
  assert.equal(history.open,false);
  assert.ok(dom.window.document.querySelector('#detail-body .interview-section [data-prepare-role]'));
  history.querySelector('summary').click();
  assert.equal(history.open,true);
  assert.ok(history.querySelectorAll('li').length>0);
  assert.equal(JSON.stringify(data),before);
  dom.window.close();
});

test('opening preparation keeps reading focus and exposes cited files on demand',()=>{
  const {data,paths}=interviewFixture(),prep=data.documents.find(d=>d.path===paths.prep);
  prep.body='## 先讲清什么\n个人行动与成果边界。\n\n## 可能追问\n<script>window.bad=true</script>';
  const dom=open(data,'#view=applications');
  click(dom,'[data-application="future/roles/current/companies/example/one/application.md"]');
  click(dom,'#detail-body [data-doc="'+paths.prep+'"]');
  assert.equal(dom.window.document.activeElement.id,'close-detail');
  assert.match(text(dom,'#detail-body .reading-copy'),/先讲清什么/);
  assert.equal(dom.window.document.querySelector('#detail-body script'),null);
  assert.equal(dom.window.bad,undefined);
  const citations=dom.window.document.querySelector('#detail-body details');
  assert.equal(citations.open,false);
  citations.querySelector('summary').click();
  assert.equal(citations.open,true);
  assert.ok(citations.querySelector('a[href]'));
  dom.window.close();
});


test('completed and paused work, independent notes and stage summaries remain reachable without new main tabs',()=>{
  const data=fixture(),add=(path,metadata,body)=>{const doc={path,metadata,body,freshness:'current',href:'file:///fictional/'+path,revision:'sha256:'+'a'.repeat(64)};data.documents.push(doc);data.source_links[path]={path,href:doc.href,absolute_path:'/fictional/'+path,revision:doc.revision};return doc};
  const done=add('present/items/done.md',{id:'done',type:'item',title:'已完成的虚构项目',status:'done'},'保留实际成果。');
  const paused=add('present/items/paused.md',{id:'paused',type:'item',title:'暂停的虚构探索',status:'paused'},'暂不继续。');
  data.items.push(done,paused);
  const note=add('present/notes/idea.md',{id:'idea',type:'note',title:'暂时不设目标的想法',recorded_on:'2026-10-21'},`## 先留下
还没有决定。`);
  const stage=add('present/stages/review.md',{id:'stage',type:'stage-summary',title:'这一阶段的回看',recorded_on:'2026-10-23',transition:'direction-change',item_ids:['done'],sources:[done.path]},`## 已经发生
完成一次演练。

## 接下来
仍可改变。`);
  data.notes=[note];data.stages=[stage];
  for(let i=0;i<5;i++){const log=add('present/work/old-'+i+'.md',{id:'old-'+i,type:'work-log',title:'历史成长记录 '+i,recorded_on:'2026-0'+(i+1)+'-02',evidence_status:'record'},'历史记录');data.logs.push(log)}
  const before=JSON.stringify(data),dom=open(data);
  assert.equal(dom.window.document.querySelectorAll('.tabs button').length,4);
  const archive=dom.window.document.querySelector('#growth-history');assert.equal(archive.open,false);
  assert.match(archive.textContent,/已完成的虚构项目|暂停的虚构探索|暂时不设目标的想法|这一阶段的回看|历史成长记录 0/);
  archive.querySelector('summary').click();assert.equal(archive.open,true);
  click(dom,'#growth-history [data-doc="present/items/done.md"]');assert.match(text(dom,'#detail-body'),/保留实际成果/);
  click(dom,'#growth-history [data-doc="present/stages/review.md"]');assert.match(text(dom,'#detail-body'),/这段时间的事项/);assert.match(text(dom,'#detail-body'),/已完成的虚构项目/);
  click(dom,'#growth-history [data-doc="present/notes/idea.md"]');assert.match(text(dom,'#detail-body .reading-copy'),/还没有决定/);
  assert.equal(JSON.stringify(data),before);dom.window.close();
});

test('application event opens its exact recorded version, unknown events never guess the newest resume',()=>{
  const data=fixture(),path=data.applications[0].path;
  data.application_events={[path]:[
    {date:'2026-10-20',stage:'applied',note:'发送通用版',resume:{status:'verified',version:'future/roles/current/common/resumes/v-'+'a'.repeat(32),artifact:'resume.html',href:'file:///fictional/exact-used/resume.html'}},
    {date:'2026-10-23',stage:'interview',note:'未知使用版本',resume:{status:'not_recorded'}},
    {date:'2026-10-24',stage:'interview',note:'文件变化',resume:{status:'changed',version:'future/roles/current/common/resumes/v-'+'b'.repeat(32),artifact:'resume.pdf',message:'当前文件与投递时记录的摘要不同，需核对。'}},
  ]};
  const dom=open(data,'#view=applications');click(dom,'[data-application="'+path+'"]');
  const events=dom.window.document.querySelectorAll('.history .event-resume');assert.equal(events.length,3);
  assert.equal(events[0].querySelector('a').getAttribute('href'),'file:///fictional/exact-used/resume.html');
  assert.equal(events[1].querySelector('a'),null);assert.match(events[1].textContent,/未记录/);
  assert.equal(events[2].querySelector('a'),null);assert.match(events[2].textContent,/摘要不同/);dom.window.close();
});

test('unverified PDFs and unsafe event hrefs never appear as verified artifact links',()=>{
  const data=fixture();data.resumes[1].pdf_status={status:'unverified'};
  const path=data.applications[0].path;
  data.application_events={[path]:[{date:'2026-10-20',stage:'applied',note:'核对',resume:{status:'verified',version:'v-'+ 'c'.repeat(32),artifact:'resume.pdf',href:'javascript:window.bad=true'}}]};
  const dom=open(data,'#view=applications');click(dom,'[data-application="'+path+'"]');
  assert.match(text(dom,'#detail-body'),/已有 PDF 尚未核验/);
  assert.equal(dom.window.document.querySelector('.history a'),null);assert.equal(dom.window.document.querySelector('a[href$="resume.pdf"]'),null);
  assert.equal(dom.window.bad,undefined);dom.window.close();
});
