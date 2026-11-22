"""Client for searching the ORCID Registry."""

from dataclasses import dataclass
from typing import Protocol

import requests


class ORCIDClient(Protocol):
    """Describe the interface for ORCID searches."""

    def find_orcid(self, contributor_name: str) -> str | None:
        """Return the first matching ORCID, if available."""
        ...


@dataclass
class OrcidClient:
    """Search the ORCID Registry for contributor identifiers."""

    base_url: str = "https://pub.orcid.org/v3.0"
    access_token: str | None = None

    def find_orcid(self, contributor_name: str) -> str | None:
        """Return the first matching ORCID or None."""
        if not contributor_name.strip():
            return None

        params = {
            "q": f'credit-name:"{contributor_name}"',
        }

        headers = {
            "Accept": "application/json",
        }

        if self.access_token is not None:
            headers["Authorization"] = f"Bearer {self.access_token}"

        response = requests.get(
            f"{self.base_url}/search",
            params=params,
            headers=headers,
            timeout=30,
        )

        if response.status_code in {401, 403} and self.access_token is not None:
            response = requests.get(
                f"{self.base_url}/search",
                params=params,
                headers={"Accept": "application/json"},
                timeout=30,
            )

        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            return None

        raw_results = payload.get("result")

        if not isinstance(raw_results, list):
            return None

        for result in raw_results:
            if not isinstance(result, dict):
                continue

            identifier = result.get("orcid-identifier")

            if not isinstance(identifier, dict):
                continue

            path = identifier.get("path")

            if isinstance(path, str) and path:
                return path

        return None
