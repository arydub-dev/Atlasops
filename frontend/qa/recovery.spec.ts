import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {execFileSync} from 'node:child_process';
const run=process.env.ATLAS_QA_RUN!;
const fixture=JSON.parse(readFileSync(run+'/private.json','utf8'));
const api=process.env.ATLAS_QA_API!+'/api/v1';
const root=resolve(dirname(process.env.ATLAS_QA_ORACLE!),'../..');

test('RECOVERY-001 | critical workflow | imported risk, donor tradeoff, approval and recorded outcome',async({page,context})=>{
 test.setTimeout(150000);
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
 await page.getByRole('button',{name:'Readiness',exact:true}).click();await page.getByRole('button',{name:/WO-A.*SHORTAGE/}).click();
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
