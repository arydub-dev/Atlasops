import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {execFileSync} from 'node:child_process';
const run=process.env.ATLAS_QA_RUN!;
const fixture=JSON.parse(readFileSync(run+'/private.json','utf8'));
const api=process.env.ATLAS_QA_API!+'/api/v1';
const root=resolve(dirname(process.env.ATLAS_QA_ORACLE!),'../..');

test('RECOVERY-001 | critical workflow | imported risk, donor tradeoff, approval and recorded outcome',async({page,context})=>{
 // Exercise the workflow at an operator pace without raising API rate limits.
 test.setTimeout(240000);
 let nextRequestAt=Date.now();
 await page.route(process.env.ATLAS_QA_API!+'/**',async route=>{
  const wait=Math.max(0,nextRequestAt-Date.now());nextRequestAt=Date.now()+wait+850;
  if(wait) await new Promise(resolve=>setTimeout(resolve,wait));
  await route.continue();
 });
 await context.addCookies([{name:fixture.cookie_name,value:fixture.sessions.empty,url:process.env.ATLAS_QA_API!}]);
 const directory=run+'/recovery-demo';
 execFileSync(process.env.ATLAS_QA_PYTHON!,[root+'/tools/recovery/demo.py','--output',directory]);
 for(const kind of ['suppliers','products','warehouses','inventory']){
  const buffer=readFileSync(directory+'/'+kind+'.csv');
  const preview=await page.request.post(api+'/data/import/preview',{multipart:{entity:kind,file:{name:kind+'.csv',mimeType:'text/csv',buffer}}});expect(preview.ok()).toBeTruthy();
  const result=await page.request.post(api+'/data/import/commit',{multipart:{entity:kind,mapping:JSON.stringify((await preview.json()).suggested_mapping),file:{name:kind+'.csv',mimeType:'text/csv',buffer}}});expect(result.ok()).toBeTruthy();
 }
 for(const kind of ['stock','inbound','rule']){
  const result=await page.request.post(api+'/recovery/import/'+kind,{multipart:{file:{name:kind+'.csv',mimeType:'text/csv',buffer:readFileSync(directory+'/'+kind+'.csv')}}});expect(result.ok()).toBeTruthy();
 }
 await page.goto('/recovery');await expect(page.getByRole('link',{name:'Critical spares readiness',exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'Critical spares readiness',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Import',exact:true}).click();
 const imported=page.waitForResponse(r=>r.url().endsWith('/recovery/import/requirement')&&r.request().method()==='POST');
 await page.getByLabel('Recovery file').setInputFiles(directory+'/requirement.csv');expect((await imported).ok()).toBeTruthy();
 await expect(page.getByRole('status')).toContainText('Saved');
 await page.goto('/mission-control');
 await expect(page.getByRole('heading',{name:'Maintenance requiring attention',exact:true})).toBeVisible();
 await expect(page.getByRole('region',{name:'Maintenance and recovery'})).toContainText('WO-A');
 await page.goto('/recovery');
 await page.getByRole('button',{name:'Readiness',exact:true}).click();
 await page.getByLabel('Search work order or part').fill('WO-A');
 await expect(page.getByRole('button',{name:/WO-B.*READY/})).toHaveCount(0);
 await expect(page.getByRole('button',{name:/WO-A.*SHORTAGE/})).toBeVisible();
 await page.getByLabel('Search work order or part').fill('');
 await page.getByRole('combobox',{name:'Readiness status',exact:true}).selectOption('READY');
 await expect(page.getByRole('button',{name:/WO-A.*SHORTAGE/})).toHaveCount(0);
 await expect(page.getByRole('button',{name:/WO-B.*READY/})).toBeVisible();
 await page.getByRole('combobox',{name:'Readiness status',exact:true}).selectOption('');
 await page.getByRole('combobox',{name:'Sort by',exact:true}).selectOption('status');
 await page.getByRole('button',{name:/WO-A.*SHORTAGE/}).click();
 const transfer=page.locator('article').filter({has:page.getByRole('heading',{name:'Transfer 3 recorded units for SPARE-1',exact:true})});
 await expect(transfer).toContainText('Not currently feasible');await expect(transfer).toContainText('WO-B: READY → SHORTAGE');
 const expedite=page.locator('article').filter({has:page.getByRole('heading',{name:'Expedite 3 recorded units for SPARE-1',exact:true})});
 await expect(expedite).toContainText('Preview: READY');await expect(expedite).toContainText('90 USD');
 await page.getByLabel('Decision rationale').fill('Expedite preserves recorded donor demand. Human reviewed.');
 const due=new Date(Date.now()+86400000).toISOString().slice(0,16);
 await page.getByLabel('Case due date (your local time)').fill(due);
 await expedite.getByRole('button',{name:'Propose action and open incident'}).click();await expect(page.getByRole('status')).toContainText('Saved');
 await page.getByRole('button',{name:'Resolution history',exact:true}).click();await page.getByRole('button',{name:'Approve decision (no external execution)',exact:true}).click();await expect(page.getByRole('heading',{name:'WO-A · approved',exact:true})).toBeVisible();
 // Source correction is a separate explicit action, never a simulator write.
 await page.getByRole('button',{name:'Data trust',exact:true}).click();await page.getByRole('button',{name:'inbound: PO-line-1',exact:true}).click();
 await page.getByLabel('promised at',{exact:true}).fill(new Date(Date.now()+86400000).toISOString());
 await page.getByLabel('Correction reason').fill('Synthetic supplier confirmed expedited delivery reference EXP-1');
 await page.getByRole('button',{name:'Save audited correction',exact:true}).click();await expect(page.getByRole('status')).toContainText('Saved');
 await page.getByRole('button',{name:'Readiness',exact:true}).click();await expect(page.getByRole('button',{name:/WO-A.*READY/})).toBeVisible();
 await page.getByRole('button',{name:'Resolution history',exact:true}).click();await page.getByRole('button',{name:'Record actual outcome',exact:true}).click();
 await page.getByLabel('Source reference',{exact:true}).fill('SYNTHETIC-OUTCOME-1');await page.getByLabel('Outcome notes',{exact:true}).fill('Supplier commitment updated and independently recorded in source evidence');
 await page.getByLabel('Actual completion (local time)').fill(new Date(Date.now()-86400000).toISOString().slice(0,16));
 await page.getByRole('button',{name:'Save recorded outcome',exact:true}).click();await expect(page.getByRole('heading',{name:'WO-A · outcome recorded',exact:true})).toBeVisible();
 const cases=await (await page.request.get(api+'/recovery/cases')).json();expect(cases).toHaveLength(1);expect(cases[0].data.final_readiness.status).toBe('READY');
 const incident=api+'/incidents/'+cases[0].incident_id;
 expect((await page.request.patch(incident,{data:{status:'investigating',assign_to_me:true}})).ok()).toBeTruthy();
 expect((await page.request.patch(incident,{data:{status:'mitigating'}})).ok()).toBeTruthy();
 expect((await page.request.post(incident+'/resolve',{data:{resolution:'Synthetic recorded expedited commitment reconciled'}})).ok()).toBeTruthy();
 await page.reload();await page.getByRole('button',{name:'Resolution history',exact:true}).click();await expect(page.getByRole('heading',{name:'WO-A · outcome recorded',exact:true})).toBeVisible();
 await page.screenshot({path:run+'/RECOVERY-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Readiness',exact:true}).click();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2)).toBeTruthy();
 await page.screenshot({path:run+'/RECOVERY-mobile.png',fullPage:true});
});

test('RECOVERY-PLAN-001 | critical workflow | multi-order comparison and reviewed combined plan persists',async({page,context})=>{
 test.setTimeout(240000);
 let nextRequestAt=Date.now();
 await page.route(process.env.ATLAS_QA_API!+'/**',async route=>{const wait=Math.max(0,nextRequestAt-Date.now());nextRequestAt=Date.now()+wait+850;if(wait)await new Promise(r=>setTimeout(r,wait));await route.continue();});
 await context.addCookies([{name:fixture.cookie_name,value:fixture.sessions.empty,url:process.env.ATLAS_QA_API!}]);
 const records=await (await page.request.get(api+'/recovery/records')).json();
 const stamp=new Date().toISOString();
 const deadline=(days:number)=>new Date(Date.now()+days*86400000).toISOString();
 // These explicit corrections act only on the disposable QA tenant, with audit reasons.
 for(const row of records){
  let corrected;
  if(row.kind==='inbound'&&row.data.record_id==='PO-line-1')corrected={...row.data,promised_at:deadline(5),source_updated_at:stamp};
  if(row.kind==='stock'&&row.data.site==='Plant B')corrected={...row.data,reserved_quantity:1,source_updated_at:stamp};
  if(row.kind==='requirement'&&row.data.work_order==='WO-B')corrected={...row.data,quantity:8,source_updated_at:stamp};
  if(corrected)expect((await page.request.patch(api+'/recovery/records/'+row.id,{data:{expected:row.data,corrected,reason:'Synthetic multi-order scenario preparation'}})).ok()).toBeTruthy();
 }
 const requirements=`record_id,source,source_updated_at,work_order,sku,site,quantity,required_by,status,asset,priority\nline-C,Synthetic maintenance plan,${stamp},WO-C,SPARE-1,Plant A,2,${deadline(4)},planned,Pump-C,2\n`;
 const rules=`record_id,source,source_updated_at,action,sku,site,quantity,lead_days,direct_cost,currency,approval_reference,repair_reference,owner,permitted\nrepair-1,Synthetic rotable ticket,${stamp},repair,SPARE-1,Plant A,2,2,40,USD,ENG-REPAIR,RT-1 two available rotables,Maintenance planner,true\n`;
 for(const [kind,raw] of [['requirement',requirements],['rule',rules]])expect((await page.request.post(api+'/recovery/import/'+kind,{multipart:{file:{name:kind+'.csv',mimeType:'text/csv',buffer:Buffer.from(raw)}}})).ok()).toBeTruthy();
 await page.goto('/mission-control');await expect(page.getByRole('region',{name:'Maintenance and recovery'})).toContainText('WO-C');await page.screenshot({path:run+'/SIMULATOR-dashboard.png',fullPage:true});
 await page.goto('/data-sources');await expect(page.getByRole('region',{name:'Integration capability catalogue'})).toBeVisible();await expect(page.getByRole('region',{name:'Integration capability catalogue'})).toContainText('PROTOTYPE');await page.screenshot({path:run+'/SIMULATOR-integrations.png',fullPage:true});
 await page.goto('/recovery');await expect(page.getByRole('button',{name:/WO-C.*SHORTAGE/})).toBeVisible();await page.screenshot({path:run+'/SIMULATOR-readiness.png',fullPage:true});
 await page.getByRole('button',{name:'Plan comparison',exact:true}).click();await page.getByRole('button',{name:'Compare recovery plans',exact:true}).click();
 const pair=page.getByRole('row').filter({hasText:'130 USD'}).filter({hasText:'Supported scenario'});
 await expect(pair).toHaveCount(1);await pair.getByRole('button',{name:'Inspect plan'}).click();
 await expect(page.getByRole('region',{name:'Multi-work-order recovery simulator'})).toContainText('WO-C');
 await page.screenshot({path:run+'/SIMULATOR-comparison.png',fullPage:true});
 await page.getByLabel('Plan decision rationale').fill('Expedite and repair cover both Plant A orders without consuming donor commitments.');await page.getByLabel('Plan due date').fill(deadline(2).slice(0,16));
 await page.getByRole('button',{name:'Propose plan for review',exact:true}).click();await expect(page.getByRole('status')).toContainText('Plan proposed');
 await page.getByRole('button',{name:'Resolution history',exact:true}).click();await page.getByRole('button',{name:'Approve decision (no external execution)',exact:true}).click();await expect(page.getByRole('heading',{name:'WO-A · approved',exact:true})).toBeVisible();
 await page.reload();await page.getByRole('button',{name:'Resolution history',exact:true}).click();await expect(page.getByRole('heading',{name:'WO-A · approved',exact:true})).toBeVisible();
 const cases=await (await page.request.get(api+'/recovery/cases')).json();const combined=cases.find((c:{data:{simulator?:boolean}})=>c.data.simulator);expect(combined.data.chosen.known_direct_cost).toBe(130);expect(combined.data.chosen.restored_work_orders).toEqual(['WO-A','WO-C']);
 const incident=api+'/incidents/'+combined.incident_id;
 expect((await page.request.patch(incident,{data:{status:'investigating',assign_to_me:true}})).ok()).toBeTruthy();expect((await page.request.patch(incident,{data:{status:'mitigating'}})).ok()).toBeTruthy();
 expect((await page.request.post(incident+'/resolve',{data:{resolution:'Synthetic outcome recorded; readiness remains evidence-based and execution is not implied'}})).ok()).toBeTruthy();
 expect((await page.request.post(api+'/recovery/cases/'+combined.id+'/outcome',{data:{reference:'QA-COMBINED-RESULT',notes:'Recorded review completed; no physical receipt or inventory change is asserted',completed_at:new Date().toISOString()}})).ok()).toBeTruthy();
 await page.reload();await page.getByRole('button',{name:'Resolution history',exact:true}).click();await expect(page.getByText('Actual reference: QA-COMBINED-RESULT',{exact:false})).toBeVisible();await page.screenshot({path:run+'/SIMULATOR-resolution.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Plan comparison',exact:true}).click();await page.getByRole('button',{name:'Compare recovery plans',exact:true}).click();await expect(page.getByRole('columnheader',{name:'Known direct cost',exact:true})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2)).toBeTruthy();await page.screenshot({path:run+'/SIMULATOR-mobile.png',fullPage:true});
});
