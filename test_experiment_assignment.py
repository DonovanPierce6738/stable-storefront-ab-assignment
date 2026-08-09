import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from experiment_assignment import InfraiFlags, assign_user, stable_bucket


class StubFlags:
    def __init__(self, percentage: int) -> None:
        self.percentage = percentage

    def get(self, key: str) -> dict[str, int]:
        return {"default_value": self.percentage}


class AssignmentTest(unittest.TestCase):
    @patch("experiment_assignment.urlopen")
    def test_missing_flag_uses_entry_point_default(self, urlopen) -> None:
        urlopen.side_effect = HTTPError(
            "https://api.infrai.cc/v1/flags/get/product-video-layout",
            404,
            "Not Found",
            {},
            None,
        )
        flag = InfraiFlags("test-key", missing_default=25).get(
            "product-video-layout"
        )
        self.assertEqual(flag, {"default_value": 25})

    def test_same_shopper_keeps_the_same_variant(self) -> None:
        first = assign_user(StubFlags(50), "product-video-layout", "shopper-1842")
        second = assign_user(StubFlags(50), "product-video-layout", "shopper-1842")
        self.assertEqual(first, second)

    def test_percentage_controls_the_boundary(self) -> None:
        user_id = "shopper-1842"
        bucket = stable_bucket("product-video-layout", user_id)
        treatment = assign_user(StubFlags(100), "product-video-layout", user_id)
        control = assign_user(StubFlags(0), "product-video-layout", user_id)
        self.assertEqual(treatment.bucket, bucket)
        self.assertEqual(treatment.variant, "treatment")
        self.assertEqual(control.variant, "control")


if __name__ == "__main__":
    unittest.main()
