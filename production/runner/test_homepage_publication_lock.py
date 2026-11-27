from __future__ import annotations
import unittest
from verify_homepage_publication_lock import validate_homepage_lock

BASE='032090e047a363e7654e36c12adadbe859666bc2'
PREVIEW='a'*40

class HomepagePublicationLockTests(unittest.TestCase):
    def test_baseline_homepage_is_allowed_unchanged(self):
        lock={'schema_version':'1.0','status':'BASELINE_LOCKED','index_git_blob_sha':BASE,'report_date':'2026-11-26','preview_path':None,'preview_git_blob_sha':None,'approved_by_owner':False,'previous_homepage':None,'approved_at':None,'approval_note':None}
        result=validate_homepage_lock(lock,BASE,None,'chore: lock homepage baseline')
        self.assertEqual(result['mode'],'BASELINE_LOCKED')

    def test_unapproved_index_change_blocks_pages(self):
        lock={'schema_version':'1.0','status':'BASELINE_LOCKED','index_git_blob_sha':BASE,'report_date':'2026-11-26','preview_path':None,'preview_git_blob_sha':None,'approved_by_owner':False,'previous_homepage':None,'approved_at':None,'approval_note':None}
        with self.assertRaisesRegex(ValueError,'differs from the locked homepage'):
            validate_homepage_lock(lock,'b'*40,None,'publish without approval')

    def test_approved_publication_requires_exact_marker_and_preview_sha(self):
        lock={'schema_version':'1.0','status':'APPROVED_PUBLICATION','index_git_blob_sha':PREVIEW,'report_date':'2026-11-30','preview_path':'preview/2026-11-30-review.html','preview_git_blob_sha':PREVIEW,'approved_by_owner':True,'approved_at':'2026-11-30T05:40:00+08:00','approval_note':'User explicitly approved 2026-11-30 preview.','previous_homepage':{'report_date':'2026-11-26','index_git_blob_sha':BASE,'status':'BASELINE_LOCKED'}}
        result=validate_homepage_lock(lock,PREVIEW,PREVIEW,'publish(tac): [publish-tac-report:2026-11-30]')
        self.assertEqual(result['mode'],'APPROVED_PUBLICATION')

    def test_approved_publication_without_user_approval_blocks(self):
        lock={'schema_version':'1.0','status':'APPROVED_PUBLICATION','index_git_blob_sha':'b'*40,'report_date':'2026-11-30','preview_path':'preview/2026-11-30-review.html','preview_git_blob_sha':PREVIEW,'approved_by_owner':False,'approved_at':'2026-11-30T05:40:00+08:00','approval_note':'no','previous_homepage':{'report_date':'2026-11-26','index_git_blob_sha':BASE,'status':'BASELINE_LOCKED'}}
        with self.assertRaisesRegex(ValueError,'explicit approved_by_owner'):
            validate_homepage_lock(lock,'b'*40,PREVIEW,'[publish-tac-report:2026-11-30]')

    def test_approved_publication_requires_matching_preview(self):
        lock={'schema_version':'1.0','status':'APPROVED_PUBLICATION','index_git_blob_sha':'b'*40,'report_date':'2026-11-30','preview_path':'preview/2026-11-30-review.html','preview_git_blob_sha':PREVIEW,'approved_by_owner':True,'approved_at':'2026-11-30T05:40:00+08:00','approval_note':'approved','previous_homepage':{'report_date':'2026-11-26','index_git_blob_sha':BASE,'status':'BASELINE_LOCKED'}}
        with self.assertRaisesRegex(ValueError,'preview Git blob SHA'):
            validate_homepage_lock(lock,'b'*40,PREVIEW,'[publish-tac-report:2026-11-30]')

    def test_approved_index_must_be_identical_to_approved_preview(self):
        lock={'schema_version':'1.0','status':'APPROVED_PUBLICATION','index_git_blob_sha':'b'*40,'report_date':'2026-11-30','preview_path':'preview/2026-11-30-review.html','preview_git_blob_sha':'c'*40,'approved_by_owner':True,'approved_at':'2026-11-30T05:40:00+08:00','approval_note':'approved'}
        with self.assertRaisesRegex(ValueError,'byte-identical'):
            validate_homepage_lock(lock,'b'*40,'c'*40,'[publish-tac-report:2026-11-30]')

    def test_archive_requires_approved_publication_not_baseline(self):
        lock={'schema_version':'1.0','status':'BASELINE_LOCKED','index_git_blob_sha':BASE,'report_date':None,'preview_path':None,'preview_git_blob_sha':None,'approved_by_owner':False,'approved_at':None,'approval_note':None}
        with self.assertRaisesRegex(ValueError,'archive requires an explicitly approved'):
            validate_homepage_lock(lock,BASE,None,'chore: baseline',require_approved=True)

    def test_approved_publication_requires_marker_on_lock_commit(self):
        lock={'schema_version':'1.0','status':'APPROVED_PUBLICATION','index_git_blob_sha':'b'*40,'report_date':'2026-11-30','preview_path':'preview/2026-11-30-review.html','preview_git_blob_sha':PREVIEW,'approved_by_owner':True,'approved_at':'2026-11-30T05:40:00+08:00','approval_note':'approved'}
        with self.assertRaisesRegex(ValueError,'exact publish marker'):
            validate_homepage_lock(lock,'b'*40,PREVIEW,'publish report')

if __name__=='__main__':
    unittest.main()
