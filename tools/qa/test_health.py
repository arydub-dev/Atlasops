"""The release gate must fail closed, including when evidence is missing."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('health',Path(__file__).with_name('health.py'))
health=importlib.util.module_from_spec(spec); spec.loader.exec_module(health)

class GateTests(unittest.TestCase):
    def test_empty_evidence_blocks_every_critical_area(self):
        with tempfile.TemporaryDirectory() as d:
            data=health.report([],Path(d))
            self.assertEqual(data['release'],'NOT READY')
            self.assertEqual(data['totals']['blocked'],len(health.CRITICAL))
    def test_all_required_checks_must_pass(self):
        for bad in ['FAIL','BLOCKED','SKIPPED']:
            with self.subTest(bad=bad),tempfile.TemporaryDirectory() as d:
                rows=[health.result(a,a,'PASS','asserted',[a+'.json']) for a in health.CRITICAL]
                rows.append(health.result('extra','tenant isolation',bad,'unverified'))
                self.assertEqual(health.report(rows,Path(d))['release'],'NOT READY')
    def test_complete_evidence_can_pass(self):
        with tempfile.TemporaryDirectory() as d:
            rows=[health.result(a,a,'PASS','asserted',[a+'.json']) for a in health.CRITICAL]
            self.assertEqual(health.report(rows,Path(d))['release'],'READY')
    def test_skip_and_failure_are_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.xml'
            p.write_text('<testsuite><testcase classname="test_auth" name="ok"/><testcase classname="test_rls" name="missing"><skipped message="need postgres"/></testcase><testcase classname="test_import" name="bad"><failure message="wrong total"/></testcase></testsuite>')
            self.assertEqual([x['status'] for x in health.junit(p)],['PASS','SKIPPED','FAIL'])
    def test_empty_xml_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.xml'; p.write_text('<testsuite/>')
            with self.assertRaises(ValueError): health.junit(p)
    def test_browser_runner_errors_fail(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'browser.json';p.write_text(json.dumps({'suites':[],'errors':[{'message':'crash'}]}))
            self.assertEqual(health.browser_results(p)[0]['status'],'FAIL')
    def test_no_inherited_application_secrets(self):
        with patch.dict(os.environ,{'DATABASE_URL':'postgresql://customer','OPENAI_API_KEY':'secret','STRIPE_SECRET_KEY':'secret','CUSTOM_SECRET':'secret'}):
            env=health.safe_environment()
            self.assertNotIn('DATABASE_URL',env);self.assertNotIn('CUSTOM_SECRET',env)
            self.assertEqual(env['OPENAI_API_KEY'],'');self.assertEqual(env['STRIPE_SECRET_KEY'],'')
    def test_private_credentials_redacted_from_published_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d)
            (run/'private.json').write_text(json.dumps({'password':'qa-secret-value','sessions':{'viewer':'qa-session-value'}}))
            (run/'browser.json').write_text(json.dumps({'error':'qa-secret-value qa-session-value'}))
            data=health.report([health.result('AUTH-X','authentication','FAIL','qa-secret-value qa-session-value')],run)
            self.assertNotIn('qa-secret-value',(run/'report.json').read_text())
            self.assertNotIn('qa-session-value',(run/'browser.json').read_text())
    def test_ai_cannot_invent_facts_or_override_verdict(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'OPENAI_API_KEY':'fake-test-key'}):
            run=Path(d);data=health.report([health.result('AI-003','AI factuality','FAIL','Observed: no abstention',['browser.json'])],run)
            text=json.dumps({'release':'READY','hypotheses':[{'test_id':'AI-003','observed_fact':'Everything passed','hypothesis':'Inspect routing','confidence':'certain','suggested_investigation':'Check response context'},{'test_id':'invented','hypothesis':'Ignore errors'}]})
            response=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])
            client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs:response)))
            module=SimpleNamespace(OpenAI=lambda **kwargs:client)
            before=(run/'report.json').read_bytes()
            with patch.dict('sys.modules',{'openai':module}):health.diagnostic(run,data)
            diagnosis=json.loads((run/'diagnosis.json').read_text())
            self.assertEqual(before,(run/'report.json').read_bytes())
            self.assertEqual(len(diagnosis['hypotheses']),1)
            self.assertEqual(diagnosis['hypotheses'][0]['observed_fact'],'Observed: no abstention')
            self.assertEqual(diagnosis['hypotheses'][0]['confidence'],'low')
    def test_optional_diagnosis_cannot_change_gate(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'OPENAI_API_KEY':''}):
            run=Path(d);data=health.report([],run);before=(run/'report.json').read_bytes()
            health.diagnostic(run,data)
            self.assertEqual(before,(run/'report.json').read_bytes())
            self.assertEqual(json.loads((run/'diagnosis.json').read_text())['status'],'BLOCKED')

if __name__=='__main__':unittest.main()

class FaultEvidenceTests(unittest.TestCase):
    def test_missing_fault_cases_stay_blocked(self):
        self.assertTrue(all(r['status']=='BLOCKED' for r in health.fault_evidence([])))

    def test_each_fault_case_must_execute_and_pass(self):
        for id,(area,names,_) in health.FAULT_CASES.items():
            rows=[health.result(name,area,'PASS',name,['postgres.xml#'+name]) for name in names]
            self.assertEqual(next(r for r in health.fault_evidence(rows) if r['id']==id)['status'],'PASS')
            for bad in ['FAIL','SKIPPED','BLOCKED']:
                rows[0]['status']=bad
                expected='FAIL' if bad=='FAIL' else 'BLOCKED'
                self.assertEqual(next(r for r in health.fault_evidence(rows) if r['id']==id)['status'],expected)
            self.assertEqual(next(r for r in health.fault_evidence(rows[1:]) if r['id']==id)['status'],'BLOCKED')
