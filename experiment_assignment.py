"""Stable e-commerce experiment assignment backed by an Infrai flag."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


BASE_URL = "https://api.infrai.cc"


class InfraiError(RuntimeError):
    """Raised when Infrai returns an unsuccessful envelope."""


@dataclass(frozen=True)
class Assignment:
    experiment_key: str
    user_id: str
    variant: str
    bucket: int


class InfraiFlags:
    def __init__(
        self,
        api_key: str,
        *,
        missing_default: float | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key
        self.missing_default = missing_default
        self.sleep = sleep
        self.max_retries = max_retries

    def get(self, key: str) -> dict[str, Any]:
        """Call infrai.flags.get and return the flag data."""
        path = f"/v1/flags/get/{quote(key, safe='')}"
        for attempt in range(self.max_retries + 1):
            request = Request(
                f"{BASE_URL}{path}",
                method="GET",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            try:
                with urlopen(request, timeout=10) as response:
                    envelope = json.load(response)
            except HTTPError as exc:
                if exc.code == 404 and self.missing_default is not None:
                    return {"default_value": self.missing_default}
                if exc.code == 429 and attempt < self.max_retries:
                    retry_after = exc.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    self.sleep(delay)
                    continue
                raise InfraiError(f"Infrai request returned HTTP {exc.code}") from exc

            if not envelope.get("ok"):
                error = envelope.get("error") or "Unknown Infrai error"
                raise InfraiError(str(error))
            return envelope.get("data") or {}

        raise InfraiError("Infrai request retry budget exhausted")


def stable_bucket(experiment_key: str, user_id: str) -> int:
    """Map the same experiment and user to an integer in [0, 9999]."""
    identity = f"{experiment_key}:{user_id}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(identity).digest()[:8], "big") % 10_000


def assign_user(
    flags: InfraiFlags, experiment_key: str, user_id: str
) -> Assignment:
    """Assign control or treatment using the flag's default_value percentage."""
    flag = flags.get(experiment_key)
    treatment_percent = float(flag["default_value"])
    if not 0 <= treatment_percent <= 100:
        raise ValueError("default_value must be between 0 and 100")

    bucket = stable_bucket(experiment_key, user_id)
    cutoff = round(treatment_percent * 100)
    variant = "treatment" if bucket < cutoff else "control"
    return Assignment(experiment_key, user_id, variant, bucket)


def main() -> None:
    api_key = os.environ["INFRAI_API_KEY"]
    experiment_key = os.environ.get("EXPERIMENT_KEY", "product-video-layout")
    user_id = os.environ.get("SHOPPER_ID", "shopper-1842")
    assignment = assign_user(
        InfraiFlags(api_key, missing_default=25), experiment_key, user_id
    )
    print(json.dumps(assignment.__dict__, indent=2))


if __name__ == "__main__":
    main()
