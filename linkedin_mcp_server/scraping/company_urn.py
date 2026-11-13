"""Resolve a LinkedIn company slug to the numeric people-search id.

The company about page normally exposes that id on a "See all employees"
anchor. When that page is a Cloudflare interstitial, the same id is still
available from LinkedIn's organization lookup by ``universalName``.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote

from linkedin_mcp_server.scraping.link_metadata import Reference

_COMPANY_URN_RE = re.compile(r"^urn:li:(?:fs_normalized_company|company):(\d+)$")

COMPANY_BY_UNIVERSAL_NAME_URL = (
    "https://www.linkedin.com/voyager/api/organization/companies"
    "?q=universalName&universalName={slug}"
)

CLOUDFLARE_ERROR_TYPE = "cloudflare"
CLOUDFLARE_ERROR_MESSAGE = (
    "[Cloudflare] LinkedIn served a security check instead of this section."
)


def company_lookup_url(slug: str) -> str:
    """Voyager organization lookup for one company slug."""
    return COMPANY_BY_UNIVERSAL_NAME_URL.format(slug=quote(slug.strip(), safe=""))


def extract_company_id_for_slug(
    payload: str | bytes | dict[str, Any],
    slug: str,
) -> str | None:
    """Return the numeric company id when ``universalName`` matches ``slug``.

    The id has to sit on the same included object as the requested slug. A
    sibling ``FollowingInfo`` urn is not a match: that object has no slug, so
    accepting it would return whatever company the payload happened to mention.
    """
    target = slug.strip().casefold()
    if not target:
        return None
    data = _parse_payload(payload)
    if data is None:
        return None
    included = data.get("included")
    if not isinstance(included, list):
        return None
    for item in included:
        if not isinstance(item, dict):
            continue
        name = item.get("universalName")
        if not isinstance(name, str) or name.strip().casefold() != target:
            continue
        company_id = _company_id_from_urn(item.get("entityUrn"))
        if company_id:
            return company_id
    return None


def company_urn_reference(company_id: str) -> Reference:
    """Build the same ``company_urn`` shape the about-page anchor produces."""
    encoded = quote(f'["{company_id}"]', safe="")
    return {
        "kind": "company_urn",
        "value": company_id,
        "url": f"/search/results/people/?currentCompany={encoded}",
    }


def cloudflare_interstitial(*, has_main: bool, hrefs: list[str]) -> bool:
    """True when the document has no ``<main>`` and links to cloudflare.com.

    The check uses element presence and the link host, not the interstitial
    copy, so it does not depend on the browser locale.
    """
    if has_main:
        return False
    return any("cloudflare.com" in href for href in hrefs)


def cloudflare_section_error() -> dict[str, str]:
    """Section error returned when the about page is a Cloudflare check."""
    return {
        "error_type": CLOUDFLARE_ERROR_TYPE,
        "error_message": CLOUDFLARE_ERROR_MESSAGE,
    }


def _parse_payload(
    payload: str | bytes | dict[str, Any],
) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if not isinstance(payload, str) or not payload.strip():
        return None
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _company_id_from_urn(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = _COMPANY_URN_RE.match(value)
    return match.group(1) if match else None
