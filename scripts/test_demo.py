import base64
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from demo import ASSETS, run
from md_workspace import Workspace, StoreError, digest, parse_document
from md_resume import ResumeWorkspace
from md_views import build_snapshot

class DemoTests(unittest.TestCase):
    def test_full_loop_one_canonical_action_and_scoped_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'new'
            report=run(root)
            self.assertTrue(report['fictional_only'])
            self.assertTrue(report['validation']['ok'])
            self.assertFalse(report['validation']['warnings'])
            self.assertEqual(report['validation']['documents_count'],28)
            ws=Workspace(root); data=build_snapshot(ws,'2026-10-23')
            self.assertEqual(len(data['actions']),3)
            self.assertEqual(len(data['plans']),4)
            self.assertEqual(len(data['applications']),2)
            a=[d for d in data['actions'] if d['metadata']['id']=='action-samples'][0]
            self.assertEqual(a['metadata']['status'],'done')
            for p in data['plans']:
                self.assertIn(a['metadata']['id'],p['metadata']['action_ids'])
            app=[a for a in data['applications'] if a['metadata']['company_id']=='starbridge'][0]
            self.assertEqual(app['metadata']['stage'],'screening')
            self.assertEqual([e['stage'] for e in app['metadata']['history']],['preparing','applied','screening'])
            interviews=report['interviews']
            saved=ws.read(list(interviews.values()))['documents']
            self.assertEqual({d['metadata']['type'] for d in saved},{'interview-story','interview-prep','interview-practice'})
            revised=next(d for d in saved if d['path']==interviews['revised'])
            self.assertIn(interviews['practice'],revised['metadata']['sources'])
            self.assertNotIn(interviews['revised'],next(d for d in saved if d['path']==interviews['practice'])['metadata']['sources'])
            resumes=ResumeWorkspace(ws)
            self.assertEqual(len(resumes.list('ai-product')['versions']),1)
            self.assertEqual(len(resumes.list('ai-product','starbridge','starbridge-product')['versions']),1)
            inspected=resumes.inspect(report['resumes']['starbridge'])
            self.assertEqual(inspected['status'],'reviewable')
            avatar=report['avatar']
            self.assertEqual(avatar['variant'],'a')
            self.assertTrue(avatar['enabled'])
            self.assertTrue(avatar['fictional_only'])
            self.assertTrue(avatar['ai_generated'])
            original=ws.path(avatar['source_path']).read_bytes()
            self.assertEqual(original,(ASSETS/'demo-avatar.png').read_bytes())
            photo_note=ws.read([avatar['note_path']])['documents'][0]
            self.assertEqual(photo_note['metadata']['type'],'photo-note')
            self.assertEqual(photo_note['metadata']['asset_path'],avatar['source_path'])
            self.assertEqual(photo_note['metadata']['sources'],[avatar['source_path']])
            self.assertEqual(photo_note['metadata']['source_revisions'][avatar['source_path']],digest(original))
            self.assertIn('AI生成',photo_note['body'])
            self.assertIn('男性形象',photo_note['metadata']['title'])
            for draft in report['resumes'].values():
                directory=ws.path(draft)
                manifest=json.loads((directory/'manifest.json').read_text())
                content=json.loads((directory/'content.json').read_text())
                page=(directory/'resume.html').read_text()
                embedded=re.search(r'<img class="photo"[^>]+src="data:image/png;base64,([A-Za-z0-9+/=]+)"',page)
                self.assertIsNotNone(embedded)
                self.assertEqual(base64.b64decode(embedded.group(1)),original)
                self.assertEqual((directory/'photo.png').read_bytes(),original)
                self.assertEqual(manifest['files']['photo.png'],digest(original))
                self.assertEqual(manifest['source_revisions'][avatar['source_path']],digest(original))
                self.assertIn(avatar['note_path'],manifest['source_paths'])
                self.assertIn('虚构头像',content['person']['headline'])
                claims=[content['summary']['source_paths']]
                claims.extend(item['source_paths'] for section in content['sections'] for item in section['items'])
                claims.append(content['person'].get('source_paths',['past/personal.md']))
                for sources in claims:
                    self.assertNotIn(avatar['note_path'],sources)
                    self.assertNotIn(avatar['source_path'],sources)
            # The imported image is processed through the same verified material link.
            from md_navigation import NavigationWorkspace
            avatar_entry=next(entry for entry in NavigationWorkspace(ws).catalog('past')['entries']
                if entry['path']==avatar['source_path'])
            self.assertEqual(avatar_entry['state'],'processed')
            self.assertIn(avatar['note_path'],avatar_entry['link']['records'])
            self.assertFalse(list(root.rglob('*.pdf')))
            # Direct user edit changes the next snapshot, without a competing JSON action.
            meta,body=parse_document(ws.path(a['path']).read_text())
            meta['scheduled_for']='2026-10-26'
            from md_workspace import dump_document
            ws.path(a['path']).write_text(dump_document(meta,body))
            updated=build_snapshot(ws,'2026-10-26')
            self.assertEqual(next(x for x in updated['actions'] if x['metadata']['id']=='action-samples')['metadata']['scheduled_for'],'2026-10-26')

    def test_avatar_and_original_are_frozen_but_formal_default_stays_photo_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'new'
            report=run(root)
            ws=Workspace(root)
            resumes=ResumeWorkspace(ws)
            draft=report['resumes']['common']
            directory=ws.path(draft)
            content=json.loads((directory/'content.json').read_text())
            # A normal call without the explicit photo argument still adds no image.
            photo_free=resumes.build(content,'ai-product')
            photo_free_dir=ws.path(photo_free['relative_path'])
            self.assertNotIn('<img class="photo"',(photo_free_dir/'resume.html').read_text())
            self.assertNotIn('photo.png',json.loads((photo_free_dir/'manifest.json').read_text())['files'])
            self.assertEqual(resumes.inspect(photo_free['relative_path'])['status'],'reviewable')
            saved_photo=directory/'photo.png'
            original=saved_photo.read_bytes()
            saved_photo.write_bytes(original+b'changed')
            with self.assertRaises(StoreError) as changed:
                resumes.inspect(draft)
            self.assertEqual(changed.exception.code,'draft_changed')
            saved_photo.write_bytes(original)
            source=ws.path(report['avatar']['source_path'])
            source.write_bytes(source.read_bytes()+b'changed')
            with self.assertRaises(StoreError) as stale:
                resumes.inspect(draft)
            self.assertEqual(stale.exception.code,'stale_draft')

    def test_avatar_b_uses_selected_image_for_both_scoped_resumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'new'
            report=run(root,avatar='b')
            ws=Workspace(root)
            avatar=report['avatar']
            self.assertEqual(avatar['variant'],'b')
            self.assertTrue(avatar['enabled'])
            self.assertEqual(report['validation']['documents_count'],28)
            self.assertFalse(report['validation']['warnings'])
            expected=(ASSETS/'demo-avatar-b.png').read_bytes()
            self.assertNotEqual(expected,(ASSETS/'demo-avatar.png').read_bytes())
            self.assertEqual(ws.path(avatar['source_path']).read_bytes(),expected)
            note=ws.read([avatar['note_path']])['documents'][0]
            self.assertIn('女性',note['metadata']['title'])
            self.assertEqual(note['metadata']['source_revisions'][avatar['source_path']],digest(expected))
            for draft in report['resumes'].values():
                directory=ws.path(draft)
                self.assertEqual((directory/'photo.png').read_bytes(),expected)
                content=json.loads((directory/'content.json').read_text())
                self.assertIn('头像B',content['person']['headline'])
                self.assertNotIn('女性',content['person']['headline'])
                page=(directory/'resume.html').read_text()
                embedded=re.search(r'<img class="photo"[^>]+src="data:image/png;base64,([A-Za-z0-9+/=]+)"',page)
                self.assertIsNotNone(embedded)
                self.assertEqual(base64.b64decode(embedded.group(1)),expected)
                self.assertEqual(ResumeWorkspace(ws).inspect(draft)['status'],'reviewable')

    def test_avatar_none_creates_no_photo_records_or_false_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'new'
            report=run(root,avatar='none')
            ws=Workspace(root)
            self.assertEqual(report['avatar']['variant'],'none')
            self.assertFalse(report['avatar']['enabled'])
            self.assertFalse(report['avatar']['ai_generated'])
            self.assertIsNone(report['avatar']['source_path'])
            self.assertIsNone(report['avatar']['note_path'])
            self.assertEqual(report['validation']['documents_count'],27)
            self.assertFalse(report['validation']['warnings'])
            self.assertFalse(ws.index(area='past',types=['photo-note'])['documents'])
            self.assertFalse(list(root.glob('past/originals/photo/*')))
            self.assertNotIn('头像',ws.read(['past/personal.md'])['documents'][0]['body'])
            for draft in report['resumes'].values():
                directory=ws.path(draft)
                content=json.loads((directory/'content.json').read_text())
                manifest=json.loads((directory/'manifest.json').read_text())
                self.assertNotIn('头像',content['person']['headline'])
                self.assertNotIn('<img class="photo"',(directory/'resume.html').read_text())
                self.assertFalse(list(directory.glob('photo.*')))
                self.assertNotIn('photo.png',manifest['files'])
                self.assertTrue(all(not p.startswith('past/photos/') and not p.startswith('past/originals/photo/')
                    for p in manifest['source_paths']))
                self.assertEqual(ResumeWorkspace(ws).inspect(draft)['status'],'reviewable')

    def test_unknown_avatar_is_rejected_before_initialization_in_api_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'new'
            with self.assertRaisesRegex(ValueError,'avatar'):
                run(root,avatar='unknown')
            self.assertFalse(root.exists())
            result=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('demo.py')),
                '--workspace',str(root),'--avatar','unknown'],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertFalse(root.exists())

    def test_refuses_existing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):run(tmp)

if __name__=='__main__': unittest.main()
