from __future__ import annotations

from urllib.parse import urlparse


RELEVANCE_WEIGHTS = {
    "school_score": 0.35,
    "course_score": 0.30,
    "intent_score": 0.25,
    "keyword_score": 0.10,
}

SOURCE_VALUE_WEIGHTS = {
    "platform_trust": 0.15,
    "domain_trust": 0.10,
    "content_richness": 0.20,
    "structure_quality": 0.20,
    "course_specificity": 0.15,
    "repo_health": 0.10,
    "reference_utility_score": 0.10,
}

FRESHNESS_POPULARITY_WEIGHTS = {
    "freshness_score": 0.60,
    "popularity_score": 0.40,
}

RAW_SCORE_WEIGHTS = {
    "relevance_score": 0.55,
    "source_value_score": 0.35,
    "freshness_popularity_score": 0.10,
}

PLATFORM_TRUST_TABLE = {
    "github": 0.90,
    "gitee": 0.78,
    "gitlab": 0.75,
    "web_seed": 0.60,
    "web": 0.50,
    "unknown": 0.40,
}

DOMAIN_TRUST_TABLE_EXACT = {
    "github.com": 0.90,
    "gitee.com": 0.78,
    "gitlab.com": 0.75,
    "nankai.edu.cn": 0.90,
}

DOMAIN_TRUST_TABLE_SUFFIX = {
    ".edu.cn": 0.80,
}

DOMAIN_TRUST_DEFAULTS = {
    "web": 0.50,
    "unknown": 0.40,
}

SCORE_CAPS = {
    "org_meta_cap": 0.45,
    "school_none_cap": 0.65,
    "school_weak_cap": 0.75,
    "school_ambiguous_cap": 0.70,
    "broad_scope_no_school_cap": 0.76,
    "broad_scope_outside_group_cap": 0.74,
    "collection_cap": 0.72,
    "exam_solution_cap": 0.70,
    "generic_algorithm_cap": 0.68,
    "course_negative_signal_cap": 0.68,
    "readme_only_cap": 0.75,
    "archived_cap": 0.60,
}

VALUE_LEVEL_THRESHOLDS = {
    "high": 0.82,
    "medium": 0.65,
}


def resolve_platform_trust(source_provider: str | None) -> float:
    if not source_provider:
        return PLATFORM_TRUST_TABLE["unknown"]
    normalized = source_provider.lower()
    if normalized in PLATFORM_TRUST_TABLE:
        return PLATFORM_TRUST_TABLE[normalized]
    if "gitlab" in normalized:
        return PLATFORM_TRUST_TABLE["gitlab"]
    return PLATFORM_TRUST_TABLE["unknown"]


def resolve_domain_trust(url: str) -> float:
    host = urlparse(url or "").netloc.lower()
    if not host:
        return DOMAIN_TRUST_DEFAULTS["unknown"]
    if host in DOMAIN_TRUST_TABLE_EXACT:
        return DOMAIN_TRUST_TABLE_EXACT[host]
    for suffix, value in DOMAIN_TRUST_TABLE_SUFFIX.items():
        if host.endswith(suffix):
            return value
    if "." in host:
        return DOMAIN_TRUST_DEFAULTS["web"]
    return DOMAIN_TRUST_DEFAULTS["unknown"]
