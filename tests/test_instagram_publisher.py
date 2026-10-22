import tempfile
import unittest
from pathlib import Path

from instagram_publisher import (
    InstagramAPIError,
    NotApproved,
    PublisherService,
    PublishingDisabled,
    Queue,
)


class FakeClient:
    instances = []
    recent_media = None
    reject_container = False
    fail_publish = False

    def __init__(self, credentials):
        self.credentials = credentials
        self.calls = []
        type(self).instances.append(self)

    @classmethod
    def reset(cls):
        cls.instances = []
        cls.recent_media = None
        cls.reject_container = False
        cls.fail_publish = False

    def get_username(self):
        self.calls.append(("get_username",))
        return "quero.turismo"

    def find_recent_media(self, caption, not_before):
        self.calls.append(("find_recent_media", caption, not_before))
        return type(self).recent_media

    def create_image_container(self, image_url, caption, collaborators):
        self.calls.append(("create_image_container", image_url, caption, collaborators))
        if type(self).reject_container:
            raise InstagramAPIError("container rejected")
        return "container-123"

    def get_container_status(self, container_id):
        self.calls.append(("get_container_status", container_id))
        return "FINISHED"

    def publish_container(self, container_id):
        self.calls.append(("publish_container", container_id))
        if type(self).fail_publish:
            raise InstagramAPIError("ambiguous transport failure")
        return "media-456"

    def get_media(self, media_id):
        self.calls.append(("get_media", media_id))
        return {"id": media_id, "permalink": "https://www.instagram.com/p/example/"}


class FakeMediaValidator:
    def __init__(self):
        self.urls = []

    def validate(self, url):
        self.urls.append(url)
        return {"http_status": 200, "content_type": "image/jpeg", "bytes": 100}


class PublisherSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.media = Path(self.temp_dir.name, "piece.jpg")
        self.media.write_bytes(b"\xff\xd8safe-test-image\xff\xd9")
        self.queue = Queue(":memory:")
        self.validator = FakeMediaValidator()
        self.service = PublisherService(
            self.queue, FakeClient, media_validator=self.validator, sleep=lambda _: None
        )
        self.environment = {
            "INSTAGRAM_USER_ID": "test-user-id",
            "INSTAGRAM_ACCESS_TOKEN": "test-token-never-logged",
        }
        FakeClient.reset()

    def tearDown(self):
        self.queue.close()
        self.temp_dir.cleanup()

    def enqueue(self, piece_id="piece-1", *, remote=False,
                content_policy="other"):
        media = "https://cdn.example.com/piece.jpg" if remote else str(self.media)
        return self.queue.enqueue(
            piece_id, media, "Legenda de teste", "2030-01-01T12:00:00-03:00",
            content_policy,
        )

    def enabled_environment(self):
        return dict(self.environment, INSTAGRAM_PUBLISHING_ENABLED="true")

    def test_draft_is_blocked(self):
        self.enqueue()
        with self.assertRaises(NotApproved):
            self.service.dry_run("piece-1", self.environment)
        self.assertEqual(FakeClient.instances, [])

    def test_non_approved_failed_item_is_blocked(self):
        self.enqueue()
        self.queue.mark_failed("piece-1", "test_failure")
        with self.assertRaises(NotApproved):
            self.service.dry_run("piece-1", self.environment)
        self.assertEqual(FakeClient.instances, [])

    def test_publishing_disabled_blocks_approved_item(self):
        self.enqueue(remote=True)
        self.queue.approve("piece-1", "Arthur")
        environment = dict(self.environment, INSTAGRAM_PUBLISHING_ENABLED="false")
        with self.assertRaises(PublishingDisabled):
            self.service.publish("piece-1", environment)
        self.assertEqual(FakeClient.instances, [])

    def test_real_publish_requires_arthur(self):
        self.enqueue(remote=True)
        self.queue.approve("piece-1", "Outra pessoa")
        with self.assertRaises(NotApproved):
            self.service.publish("piece-1", self.enabled_environment())
        self.assertEqual(FakeClient.instances, [])

    def test_approval_records_actor_time_and_piece(self):
        self.enqueue()
        item = self.queue.approve("piece-1", "Arthur")
        self.assertEqual(item.status, "approved")
        self.assertEqual(item.approved_by, "Arthur")
        self.assertIsNotNone(item.approved_at)
        self.assertTrue(item.approved_at.endswith("-03:00"))
        approval = [e for e in self.queue.audit_entries() if e["event"] == "approved"][0]
        self.assertEqual(approval["piece_id"], "piece-1")
        self.assertEqual(approval["actor"], "Arthur")
        self.assertEqual(approval["details"]["piece_id"], "piece-1")

    def test_collaborators_are_derived_from_permanent_policy(self):
        sold = self.enqueue("sold", content_policy="ship_sold_by_quero_abada")
        lodging = self.enqueue("lodging", content_policy="carnival_lodging")
        external = self.enqueue(
            "external", content_policy="ship_not_sold_by_quero_abada"
        )
        self.assertEqual(sold.collaborators, ("queroabada", "queronavio"))
        self.assertEqual(lodging.collaborators, ("queroabada",))
        self.assertEqual(external.collaborators, ("queronavio",))

    def test_dry_run_reads_username_once_and_never_logs_token(self):
        self.enqueue()
        self.queue.approve("piece-1", "Arthur")
        result = self.service.dry_run("piece-1", self.environment)
        self.assertEqual(result["account"], "@quero.turismo")
        self.assertEqual(FakeClient.instances[0].calls, [("get_username",)])
        self.assertNotIn(
            self.environment["INSTAGRAM_ACCESS_TOKEN"], str(self.queue.audit_entries())
        )

    def test_mocked_publish_creates_and_publishes_exactly_once(self):
        item = self.enqueue(remote=True, content_policy="ship_sold_by_quero_abada")
        self.queue.approve(item.piece_id, "Arthur")
        result = self.service.publish(item.piece_id, self.enabled_environment())
        calls = FakeClient.instances[0].calls
        create = [call for call in calls if call[0] == "create_image_container"]
        publish = [call for call in calls if call[0] == "publish_container"]
        self.assertEqual(len(create), 1)
        self.assertEqual(create[0][3], ("queroabada", "queronavio"))
        self.assertEqual(len(publish), 1)
        self.assertEqual(result.status, "published")
        self.assertEqual(result.remote_container_id, "container-123")
        self.assertEqual(result.remote_media_id, "media-456")

    def test_existing_container_is_reused_not_recreated(self):
        item = self.enqueue(remote=True)
        self.queue.approve(item.piece_id, "Arthur")
        self.queue.record_container(item.piece_id, "existing-container")
        self.service.publish(item.piece_id, self.enabled_environment())
        calls = FakeClient.instances[0].calls
        self.assertFalse(any(call[0] == "create_image_container" for call in calls))
        self.assertEqual(
            [call for call in calls if call[0] == "publish_container"],
            [("publish_container", "existing-container")],
        )

    def test_reconciliation_skips_both_mutating_calls(self):
        item = self.enqueue(remote=True)
        self.queue.approve(item.piece_id, "Arthur")
        FakeClient.recent_media = {
            "id": "already-published", "permalink": "https://www.instagram.com/p/existing/"
        }
        result = self.service.publish(item.piece_id, self.enabled_environment())
        calls = FakeClient.instances[0].calls
        self.assertFalse(any(call[0] == "create_image_container" for call in calls))
        self.assertFalse(any(call[0] == "publish_container" for call in calls))
        self.assertEqual(result.remote_media_id, "already-published")

    def test_collaborator_rejection_has_no_degraded_retry(self):
        item = self.enqueue(remote=True, content_policy="ship_sold_by_quero_abada")
        self.queue.approve(item.piece_id, "Arthur")
        FakeClient.reject_container = True
        with self.assertRaises(InstagramAPIError):
            self.service.publish(item.piece_id, self.enabled_environment())
        calls = FakeClient.instances[0].calls
        self.assertEqual(
            len([call for call in calls if call[0] == "create_image_container"]), 1
        )
        self.assertFalse(any(call[0] == "publish_container" for call in calls))

    def test_ambiguous_publish_failure_is_not_retried(self):
        item = self.enqueue(remote=True)
        self.queue.approve(item.piece_id, "Arthur")
        FakeClient.fail_publish = True
        with self.assertRaises(InstagramAPIError):
            self.service.publish(item.piece_id, self.enabled_environment())
        calls = FakeClient.instances[0].calls
        self.assertEqual(len([call for call in calls if call[0] == "publish_container"]), 1)
        failed = self.queue.get(item.piece_id)
        self.assertEqual(failed.status, "failed")
        self.assertEqual(failed.failure_reason, "publishing_ambiguous")


if __name__ == "__main__":
    unittest.main()
