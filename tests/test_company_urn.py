"""Tests for slug-to-company-id parsing and Cloudflare interstitial detection."""

import json
from pathlib import Path

from linkedin_mcp_server.scraping.company_urn import (
    cloudflare_interstitial,
    company_urn_reference,
    extract_company_id_for_slug,
)

_FIXTURE = Path(__file__).parent / "fixtures" / "voyager_company_supportiv.json"
_SUPPORTIV = json.loads(_FIXTURE.read_text())


def test_extracts_id_when_universal_name_matches_slug():
    assert extract_company_id_for_slug(_SUPPORTIV, "supportiv") == "18645720"
    assert extract_company_id_for_slug(json.dumps(_SUPPORTIV), "Supportiv") == (
        "18645720"
    )


def test_ignores_following_info_urn_without_a_matching_slug():
    following_only = {
        "included": [
            {
                "entityUrn": "urn:li:fs_followingInfo:urn:li:company:18645720",
            }
        ]
    }
    assert extract_company_id_for_slug(following_only, "supportiv") is None


def test_rejects_a_payload_for_a_different_slug():
    assert extract_company_id_for_slug(_SUPPORTIV, "life360") is None
    assert extract_company_id_for_slug("not-json", "supportiv") is None
    assert extract_company_id_for_slug(_SUPPORTIV, "  ") is None


def test_company_urn_reference_matches_people_search_shape():
    reference = company_urn_reference("18645720")
    assert reference == {
        "kind": "company_urn",
        "value": "18645720",
        "url": "/search/results/people/?currentCompany=%5B%2218645720%22%5D",
    }


def test_cloudflare_interstitial_needs_no_main_and_a_cloudflare_link():
    splash_hrefs = [
        "https://www.cloudflare.com/5xx-error-landing",
        "https://www.linkedin.com/",
    ]
    assert cloudflare_interstitial(has_main=False, hrefs=splash_hrefs) is True
    assert cloudflare_interstitial(has_main=True, hrefs=splash_hrefs) is False
    assert (
        cloudflare_interstitial(
            has_main=False,
            hrefs=["https://www.linkedin.com/company/supportiv/"],
        )
        is False
    )
