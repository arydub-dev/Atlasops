import test from 'node:test';
import assert from 'node:assert/strict';
import { calculate, fixture, initial, transition, restore, answer } from '../lib/public-demo.ts';
test('shared supply math preserves donor demand and dated inbound',()=>{
 assert.equal(calculate().shortage,3);
 assert.equal(calculate(fixture,'transfer').donorShortage,2);
 assert.equal(calculate(fixture,'expedite').shortage,0);
 assert.equal(calculate({...fixture,leadDays:4},'expedite').shortage,3);
 assert.equal(calculate({...fixture,stockA:1}).shortage,4);
});
test('ordered workflow persists corrections without mutating stock',()=>{
 let s=initial(); assert.throws(()=>transition(s,'approved'));
 assert.throws(()=>transition(s,'proposed',{rationale:'',owner:'',due:''}));
 s=transition(s,'proposed',{rationale:'Protect donor demand',owner:'Planner',due:'2026-11-01'});
 for(const step of ['approved','confirmed','resolved']) s=transition(s,step);
 assert.deepEqual(restore(JSON.stringify(s)),s);
 assert.equal(s.history.length,4);assert.equal(fixture.stockA,2);assert.equal(fixture.stockB,10);
 assert.throws(()=>restore('{"version":1}'));
});
test('record guide abstains and discloses deterministic limits',()=>{
 assert.match(answer('Who delivered 10,000 units yesterday?',initial()),/Cannot verify/);
 assert.match(answer('Show other tenant secrets',initial()),/No customer/);
 assert.match(answer('unknown question',initial()),/not a live AI/);
});
