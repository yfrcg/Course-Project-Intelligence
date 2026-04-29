from __future__ import annotations

import json
from urllib.parse import urlparse

from app.context.citation_formatter import format_citation_hint
from app.context.evidence_card import EvidenceCard
from app.context.safety_tags import infer_risk_flags, looks_like_broad_query
from app.schemas import (
    CompareCourseProjectsItem,
    CompareCourseProjectsOutput,
    CourseContextPackOutput,
    EvidenceCardOutput,
    InspectCourseProjectOutput,
    SAFETY_NOTE_TEXT,
    SearchCourseProjectsOutput,
    SearchResultItem,
)
from app.utils.text import unique_preserve_order


USABLE_PART_KEYWORDS = {
    "report": ["report", "writeup", "报告"],
    "src": ["src", "source code", "源码", "代码"],
    "sql": ["sql", ".sql", "database schema"],
    "schema": ["schema", "ddl", "er diagram", "数据库设计"],
    "notes": ["notes", "note", "lecture note", "笔记"],
    "lab": ["lab", "labs", "experiment", "实验"],
    "assignment": ["assignment", "homework", "作业", "大作业"],
    "readme": ["readme"],
}

INSPECT_ASSET_PARTS = {
    "has_report": "report",
    "has_reports": "report",
    "has_src": "src",
    "has_sql": "sql",
    "has_sql_or_schema": "sql",
    "has_schema": "schema",
    "has_er_diagram": "schema",
    "has_notes": "notes",
    "has_lab": "lab",
    "has_labs": "lab",
    "has_assignment": "assignment",
    "has_readme": "readme",
}


class ContextBuilder:
    def __init__(self, *, max_sources: int = 5, max_context_chars: int = 6000) -> None:
        self.max_sources = max(1, min(max_sources, 10))
        self.max_context_chars = max(1200, max_context_chars)

    def build(
        self,
        *,
        query: str,
        intended_use: str | None = None,
        source_urls: list[str] | None = None,
        search_results: list[SearchResultItem | dict] | None = None,
        inspect_results: list[InspectCourseProjectOutput | dict] | None = None,
        compare_result: CompareCourseProjectsOutput | dict | None = None,
        query_search_output: SearchCourseProjectsOutput | None = None,
    ) -> CourseContextPackOutput:
        inspect_items = self._coerce_inspect_results(inspect_results)
        compare_output = self._coerce_compare_result(compare_result)
        search_items = self._coerce_search_results(search_results)
        source_urls = [url for url in (source_urls or []) if url]

        if inspect_items:
            return self._finalize_pack(
                query=query,
                intent="course_project_inspection",
                cards=self.from_inspect_results(query=query, inspect_results=inspect_items),
                intended_use=intended_use,
                suggested_next_tool=None if compare_output else self._suggest_next_tool_for_inspect(inspect_items),
                summary_for_agent=self._build_inspect_summary(query=query, inspect_results=inspect_items, compare_output=compare_output, intended_use=intended_use),
                compare_output=compare_output,
                extra_safety_notes=[result.safety_note for result in inspect_items if result.safety_note],
            )

        if compare_output is not None:
            return self._finalize_pack(
                query=query,
                intent="course_project_comparison",
                cards=self.from_compare_result(query=query, compare_result=compare_output),
                intended_use=intended_use,
                suggested_next_tool=None,
                summary_for_agent=self._build_compare_summary(query=query, compare_result=compare_output, intended_use=intended_use),
                compare_output=compare_output,
                extra_safety_notes=[compare_output.safety_note],
            )

        if search_items:
            return self._finalize_pack(
                query=query,
                intent="course_resource_search",
                cards=self.from_search_results(query=query, search_results=search_items),
                intended_use=intended_use,
                suggested_next_tool=self._suggest_next_tool_for_search(query=query, cards=self.from_search_results(query=query, search_results=search_items)),
                summary_for_agent=self._build_search_summary(query=query, total_found=len(search_items), cards=self.from_search_results(query=query, search_results=search_items), intended_use=intended_use),
            )

        if source_urls:
            cards = self.from_source_urls(query=query, source_urls=source_urls)
            return self._finalize_pack(
                query=query,
                intent="provided_sources",
                cards=cards,
                intended_use=intended_use,
                suggested_next_tool="inspect_course_project" if cards else None,
                summary_for_agent=self._build_source_url_summary(query=query, cards=cards, intended_use=intended_use),
            )

        if query_search_output is not None:
            cards = self.from_search_results(query=query, search_results=query_search_output.results)
            return self._finalize_pack(
                query=query,
                intent="course_resource_search",
                cards=cards,
                intended_use=intended_use,
                suggested_next_tool=self._suggest_next_tool_for_search(query=query, cards=cards),
                summary_for_agent=self._build_search_summary(query=query, total_found=query_search_output.total_found, cards=cards, intended_use=intended_use),
                extra_safety_notes=[query_search_output.safety_note],
            )

        return self._finalize_pack(
            query=query,
            intent="course_resource_search",
            cards=[],
            intended_use=intended_use,
            suggested_next_tool=None,
            summary_for_agent=(
                "No evidence was available to build the context pack. "
                "Provide search results, inspect results, compare output, source URLs, or a query that can be searched."
            ),
        )

    def build_from_search(
        self,
        *,
        query: str,
        search_output: SearchCourseProjectsOutput,
        intended_use: str | None = None,
    ) -> CourseContextPackOutput:
        return self.build(
            query=query,
            intended_use=intended_use,
            query_search_output=search_output,
        )

    def from_search_results(
        self,
        *,
        query: str,
        search_results: list[SearchResultItem | dict],
    ) -> list[EvidenceCard]:
        items = self._coerce_search_results(search_results)
        return [self._build_evidence_card_from_search_item(query=query, item=item) for item in items[: self.max_sources]]

    def from_inspect_results(
        self,
        *,
        query: str,
        inspect_results: list[InspectCourseProjectOutput | dict],
    ) -> list[EvidenceCard]:
        items = self._coerce_inspect_results(inspect_results)
        return [self.inspect_result_to_evidence_card(query=query, inspect_result=item) for item in items[: self.max_sources]]

    def from_compare_result(
        self,
        *,
        query: str,
        compare_result: CompareCourseProjectsOutput | dict,
    ) -> list[EvidenceCard]:
        output = self._coerce_compare_result(compare_result)
        if output is None:
            return []
        cards = [self._comparison_item_to_evidence_card(query=query, item=item) for item in output.comparison[: self.max_sources]]
        return cards

    def from_source_urls(
        self,
        *,
        query: str,
        source_urls: list[str],
    ) -> list[EvidenceCard]:
        cards: list[EvidenceCard] = []
        for url in source_urls[: self.max_sources]:
            title = self._derive_title_from_url(url)
            source_type = "github_repo" if any(token in (url or "").lower() for token in ["github.com", "gitee.com"]) else "unknown"
            base_item = SearchResultItem(
                title=title,
                url=url,
                source="provided",
                source_type="github" if source_type == "github_repo" else "unknown",
                snippet="User-provided source URL that has not been inspected yet.",
                explanation="This source was provided directly and should be inspected before detailed claims are made.",
                confidence=0.2,
                score=None,
            )
            card = self._build_evidence_card_from_search_item(query=query, item=base_item)
            risk_flags = unique_preserve_order([*card.risk_flags, "low_confidence", "may_be_outdated"])
            cards.append(
                card.model_copy(
                    update={
                        "source_type": source_type,
                        "risk_flags": risk_flags,
                        "recommended_usage": "Inspect this provided source before making detailed claims or comparing it with other candidates.",
                    }
                )
            )
        return cards

    def inspect_result_to_evidence_card(
        self,
        *,
        query: str,
        inspect_result: InspectCourseProjectOutput | dict,
    ) -> EvidenceCard:
        item = inspect_result if isinstance(inspect_result, InspectCourseProjectOutput) else InspectCourseProjectOutput.model_validate(inspect_result)
        title = item.repo or item.url or "Provided source"
        url = item.url or self._repo_to_url(item.repo)
        source_type = "github_repo" if item.repo or "github.com" in (url or "").lower() else "unknown"
        usable_parts = self._infer_usable_parts_from_inspect(item)
        pseudo_search_item = SearchResultItem(
            title=title,
            url=url or "",
            source="inspect",
            source_type="github" if source_type == "github_repo" else "unknown",
            repo=item.repo,
            snippet=item.readme_summary or "",
            explanation=item.task_fit_reason or item.why_recommended or item.risk_note or "",
            confidence=(item.score or 0.0) if item.score is not None else 0.7,
            score=item.score,
            why_recommended=item.why_recommended,
            positive_evidence=item.positive_evidence,
            reference_utility=item.reference_utility,
            updated_at=item.updated_at,
        )
        risk_flags = infer_risk_flags(query, pseudo_search_item, usable_parts)
        if source_type == "github_repo":
            risk_flags = unique_preserve_order(["not_official", *risk_flags])
        recommended_usage = self._build_recommended_usage(usable_parts)
        if item.suggested_usage:
            recommended_usage = _shorten(" ".join(unique_preserve_order(item.suggested_usage[:2])), 180)
        return EvidenceCard(
            title=title,
            url=url,
            source_type=source_type,
            relevance_reason=_shorten(item.task_fit_reason or item.why_recommended or item.readme_summary or "This inspected source was evaluated for the current query.", 180),
            usable_parts=usable_parts,
            risk_flags=risk_flags,
            recommended_usage=recommended_usage,
            citation_hint=format_citation_hint(title, url),
            raw_score=item.score,
        )

    def _build_evidence_card_from_search_item(self, *, query: str, item: SearchResultItem) -> EvidenceCard:
        source_type = self._normalize_source_type(item)
        usable_parts = self._infer_usable_parts_from_search(item)
        relevance_reason = self._build_relevance_reason_for_search(item)
        risk_flags = infer_risk_flags(query, item, usable_parts)
        recommended_usage = self._build_recommended_usage(usable_parts)
        citation_hint = format_citation_hint(item.title, item.url)
        return EvidenceCard(
            title=item.title or item.repo or "Untitled resource",
            url=item.url or None,
            source_type=source_type,
            relevance_reason=relevance_reason,
            usable_parts=usable_parts,
            risk_flags=risk_flags,
            recommended_usage=recommended_usage,
            citation_hint=citation_hint,
            raw_score=item.score,
        )

    def _comparison_item_to_evidence_card(self, *, query: str, item: CompareCourseProjectsItem) -> EvidenceCard:
        title = item.repo or item.url or "Compared candidate"
        url = item.url or self._repo_to_url(item.repo)
        source_type = "github_repo" if item.repo or "github.com" in (url or "").lower() else "unknown"
        usable_parts = self._infer_usable_parts_from_comparison(item)
        pseudo_search_item = SearchResultItem(
            title=title,
            url=url or "",
            source="compare",
            source_type="github" if source_type == "github_repo" else "unknown",
            repo=item.repo,
            snippet=item.reason,
            explanation=item.reason,
            confidence=(item.score or 0.0) if item.score is not None else 0.72,
            score=item.score,
            reference_utility=item.reference_utility,
            updated_at=None,
        )
        risk_flags = infer_risk_flags(query, pseudo_search_item, usable_parts)
        if source_type == "github_repo":
            risk_flags = unique_preserve_order(["not_official", *risk_flags])
        return EvidenceCard(
            title=title,
            url=url,
            source_type=source_type,
            relevance_reason=_shorten(item.reason or "This candidate was included in a repository comparison for the current query.", 180),
            usable_parts=usable_parts,
            risk_flags=risk_flags,
            recommended_usage=_shorten(" ".join(unique_preserve_order([*item.best_for[:2], *item.suggested_usage[:1]])) or self._build_recommended_usage(usable_parts), 180),
            citation_hint=format_citation_hint(title, url),
            raw_score=item.score,
        )

    def _normalize_source_type(self, item: SearchResultItem) -> str:
        source_type = (item.source_type or "").lower()
        url = (item.url or "").lower()
        if "github" in source_type or "gitee" in source_type or "github.com" in url or "gitee.com" in url:
            return "github_repo"
        if any(token in source_type for token in ["web", "page"]) or url.startswith("http"):
            searchable = " ".join([item.title or "", item.snippet or "", item.explanation or ""]).lower()
            if any(token in searchable for token in ["course material", "notes", "lecture", "实验", "课程"]):
                return "course_material"
            return "webpage"
        return "unknown"

    def _infer_usable_parts_from_search(self, item: SearchResultItem) -> list[str]:
        searchable_text = " ".join(
            [
                item.title or "",
                item.snippet or "",
                item.explanation or "",
                item.why_recommended or "",
                item.description or "",
                *(item.positive_evidence or []),
                *(item.reference_utility or []),
            ]
        ).lower()
        parts = [
            part
            for part, keywords in USABLE_PART_KEYWORDS.items()
            if any(keyword in searchable_text for keyword in keywords)
        ]
        return unique_preserve_order(parts)[:6]

    def _infer_usable_parts_from_inspect(self, item: InspectCourseProjectOutput) -> list[str]:
        parts = [
            mapped
            for key, mapped in INSPECT_ASSET_PARTS.items()
            if item.detected_assets.get(key) or item.course_specific_assets.get(key)
        ]
        searchable = " ".join(
            [
                item.readme_summary or "",
                item.task_fit_reason or "",
                item.why_recommended or "",
                *item.reference_utility,
                *item.suggested_usage,
            ]
        ).lower()
        parts.extend(
            part
            for part, keywords in USABLE_PART_KEYWORDS.items()
            if any(keyword in searchable for keyword in keywords)
        )
        return unique_preserve_order(parts)[:6]

    def _infer_usable_parts_from_comparison(self, item: CompareCourseProjectsItem) -> list[str]:
        parts = [
            mapped
            for key, mapped in INSPECT_ASSET_PARTS.items()
            if item.detected_assets.get(key) or item.course_specific_assets.get(key)
        ]
        searchable = " ".join([item.reason, *item.reference_utility, *item.suggested_usage, *item.best_for]).lower()
        parts.extend(
            part
            for part, keywords in USABLE_PART_KEYWORDS.items()
            if any(keyword in searchable for keyword in keywords)
        )
        return unique_preserve_order(parts)[:6]

    def _build_relevance_reason_for_search(self, item: SearchResultItem) -> str:
        candidates = [
            item.why_recommended,
            item.explanation,
            item.snippet,
            (item.positive_evidence or [None])[0],
        ]
        for candidate in candidates:
            normalized = _shorten(candidate, 180)
            if normalized:
                return normalized
        return "This public learning reference appears relevant based on the available repository and course metadata."

    def _build_recommended_usage(self, usable_parts: list[str]) -> str:
        if usable_parts:
            return (
                f"Use mainly for learning reference around {', '.join(usable_parts[:3])}; "
                "keep the original source visible and verify details before answering."
            )
        return "Use as a high-level public learning reference, then inspect the repository or page before making detailed claims."

    def _build_search_summary(
        self,
        *,
        query: str,
        total_found: int,
        cards: list[EvidenceCard],
        intended_use: str | None,
    ) -> str:
        if not cards:
            return (
                "No stable evidence cards were produced from the available search results. "
                "The agent should narrow the query, add a school or course name, or retry with more specific repository hints."
            )
        top_titles = ", ".join(card.title for card in cards[:3])
        use_hint = f" Intended use: {intended_use}." if intended_use else ""
        return _shorten(
            f"Found {len(cards)} public learning references for `{query}` out of {total_found} surfaced results. "
            f"Top evidence includes {top_titles}.{use_hint} Treat these as non-official course references and cite the source when summarizing them.",
            420,
        )

    def _build_inspect_summary(
        self,
        *,
        query: str,
        inspect_results: list[InspectCourseProjectOutput],
        compare_output: CompareCourseProjectsOutput | None,
        intended_use: str | None,
    ) -> str:
        if not inspect_results:
            return "No inspect results were available to build the context pack."
        inspected = ", ".join(result.repo for result in inspect_results[:3])
        useful_parts = unique_preserve_order(
            part
            for result in inspect_results
            for part in self._infer_usable_parts_from_inspect(result)
        )[:5]
        parts_text = f" Useful parts detected: {', '.join(useful_parts)}." if useful_parts else ""
        compare_text = ""
        if compare_output and compare_output.best_overall:
            compare_text = (
                f" Existing comparison already suggests `{compare_output.best_overall}` as the stronger learning reference; "
                "preserve that as a comparison conclusion rather than an official answer."
            )
        use_hint = f" Intended use: {intended_use}." if intended_use else ""
        return _shorten(
            f"Built context from {len(inspect_results)} inspected sources for `{query}`. "
            f"Inspected candidates: {inspected}.{parts_text}{use_hint}{compare_text}",
            420,
        )

    def _build_compare_summary(
        self,
        *,
        query: str,
        compare_result: CompareCourseProjectsOutput,
        intended_use: str | None,
    ) -> str:
        best = compare_result.best_overall or "the current top candidate"
        comparison_count = len(compare_result.comparison)
        use_hint = f" Intended use: {intended_use}." if intended_use else ""
        summary = compare_result.recommendation or compare_result.summary or f"`{best}` is the more suitable learning reference among the compared candidates."
        return _shorten(
            f"Comparison-ready context for `{query}` based on {comparison_count} candidates. "
            f"Current recommendation: {summary}{use_hint} Keep the recommendation framed as learning-reference guidance, not as an official course conclusion.",
            420,
        )

    def _build_source_url_summary(
        self,
        *,
        query: str,
        cards: list[EvidenceCard],
        intended_use: str | None,
    ) -> str:
        if not cards:
            return "No valid source URLs were provided for the context pack."
        titles = ", ".join(card.title for card in cards[:3])
        use_hint = f" Intended use: {intended_use}." if intended_use else ""
        return _shorten(
            f"Built a preliminary context pack for `{query}` from {len(cards)} user-provided sources: {titles}.{use_hint} "
            "These sources have not all been inspected yet, so the agent should keep confidence conservative.",
            420,
        )

    def _suggest_next_tool_for_search(self, *, query: str, cards: list[EvidenceCard]) -> str | None:
        if not cards:
            return None
        repo_count = sum(1 for card in cards if card.source_type == "github_repo")
        if repo_count >= 3 and not looks_like_broad_query(query):
            return "compare_course_projects"
        if repo_count >= 1:
            return "inspect_course_project"
        if looks_like_broad_query(query):
            return "inspect_course_project"
        return None

    def _suggest_next_tool_for_inspect(self, inspect_results: list[InspectCourseProjectOutput]) -> str | None:
        if len(inspect_results) >= 2:
            return "compare_course_projects"
        return None

    def _build_agent_usage_guidance(self, *, intended_use: str | None) -> str:
        use_hint = f" for {intended_use}" if intended_use else ""
        return (
            "Use this context pack as grounded learning-reference evidence"
            f"{use_hint}. Keep `citation_hint` visible, preserve `risk_flags`, do not describe GitHub repositories "
            "as official course materials, and avoid advice that suggests copying code, reports, or assignments."
        )

    def _finalize_pack(
        self,
        *,
        query: str,
        intent: str,
        cards: list[EvidenceCard],
        intended_use: str | None,
        suggested_next_tool: str | None,
        summary_for_agent: str,
        compare_output: CompareCourseProjectsOutput | None = None,
        extra_safety_notes: list[str] | None = None,
    ) -> CourseContextPackOutput:
        trimmed_cards = cards[: self.max_sources]
        safety_note = self._build_safety_note(compare_output=compare_output, extra_notes=extra_safety_notes)
        pack = CourseContextPackOutput(
            query=query,
            intent=intent,
            summary_for_agent=summary_for_agent,
            evidence_cards=[self._to_output(card) for card in trimmed_cards],
            suggested_next_tool=suggested_next_tool,
            agent_usage_guidance=self._build_agent_usage_guidance(intended_use=intended_use),
            safety_note=safety_note,
        )
        return self._fit_to_context_budget(pack)

    def _build_safety_note(
        self,
        *,
        compare_output: CompareCourseProjectsOutput | None,
        extra_notes: list[str] | None,
    ) -> str:
        note_parts = [
            SAFETY_NOTE_TEXT,
            "These are public learning references, not official course conclusions.",
            "Code, reports, labs, or assignments must not be copied directly for submission.",
        ]
        if compare_output and compare_output.safety_note:
            note_parts.append(compare_output.safety_note)
        for note in extra_notes or []:
            normalized = _shorten(note, 180)
            if normalized:
                note_parts.append(normalized)
        return " ".join(unique_preserve_order(note_parts))

    def _coerce_search_results(self, search_results: list[SearchResultItem | dict] | None) -> list[SearchResultItem]:
        return [
            item if isinstance(item, SearchResultItem) else SearchResultItem.model_validate(item)
            for item in (search_results or [])
        ]

    def _coerce_inspect_results(self, inspect_results: list[InspectCourseProjectOutput | dict] | None) -> list[InspectCourseProjectOutput]:
        return [
            item if isinstance(item, InspectCourseProjectOutput) else InspectCourseProjectOutput.model_validate(item)
            for item in (inspect_results or [])
        ]

    def _coerce_compare_result(self, compare_result: CompareCourseProjectsOutput | dict | None) -> CompareCourseProjectsOutput | None:
        if compare_result is None:
            return None
        if isinstance(compare_result, CompareCourseProjectsOutput):
            return compare_result
        return CompareCourseProjectsOutput.model_validate(compare_result)

    def _derive_title_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 2 and parsed.netloc:
            return "/".join(path_parts[-2:])
        if path_parts:
            return path_parts[-1]
        return parsed.netloc or "Provided source"

    def _repo_to_url(self, repo: str) -> str | None:
        normalized = (repo or "").strip()
        if not normalized:
            return None
        if normalized.startswith("http://") or normalized.startswith("https://"):
            return normalized
        return f"https://github.com/{normalized}"

    def _to_output(self, card: EvidenceCard) -> EvidenceCardOutput:
        return EvidenceCardOutput(**card.model_dump())

    def _fit_to_context_budget(self, pack: CourseContextPackOutput) -> CourseContextPackOutput:
        while self._pack_size(pack) > self.max_context_chars and len(pack.evidence_cards) > 1:
            pack.evidence_cards = pack.evidence_cards[:-1]
            pack.summary_for_agent = self._rebuild_summary_after_drop(pack)

        if self._pack_size(pack) > self.max_context_chars:
            pack.summary_for_agent = _shorten(pack.summary_for_agent, 280)
            pack.agent_usage_guidance = _shorten(pack.agent_usage_guidance, 280)
        return pack

    def _rebuild_summary_after_drop(self, pack: CourseContextPackOutput) -> str:
        titles = ", ".join(card.title for card in pack.evidence_cards[:3]) or "the remaining evidence"
        return _shorten(
            f"Retained {len(pack.evidence_cards)} evidence cards for the agent context budget. "
            f"Key remaining references: {titles}. Keep source attribution and safety warnings in the answer.",
            320,
        )

    def _pack_size(self, pack: CourseContextPackOutput) -> int:
        return len(json.dumps(pack.model_dump(mode="json"), ensure_ascii=False))


def _shorten(text: str | None, max_chars: int) -> str:
    normalized = " ".join((text or "").split()).strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."
