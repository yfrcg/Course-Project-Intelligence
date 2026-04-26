from __future__ import annotations

import asyncio
import inspect
from typing import Any

from app.core.broad_school_planner import (
    BroadSchoolPlan,
    BroadSchoolPlannerConfig,
    plan_broad_school_retrieval,
)
from app.core.course_profiles import get_course_profile
from app.core.normalizer import dedupe_results, infer_tech_tags, normalize_provider_result
from app.core.query_analyzer import analyze_query
from app.core.retrieval_intents import classify_query_intent
from app.core.university_profiles import BROAD_SCHOOL_SCOPE_KINDS, is_broad_school_scope
from app.providers.base import BaseProvider
from app.providers.github import GitHubProvider
from app.providers.registry import ProviderRegistry
from app.ranking.scorer import explain_score
from app.schemas import (
    CitationItem,
    CompareCourseProjectsInput,
    CompareCourseProjectsItem,
    CompareCourseProjectsOutput,
    ComparedItem,
    CompareProjectRoutesInput,
    CompareProjectRoutesOutput,
    CourseResourceItem,
    FailedRepoItem,
    GetProjectBriefInput,
    GetProjectBriefOutput,
    InspectCourseProjectInput,
    InspectCourseProjectOutput,
    ListCourseResourcesInput,
    ListCourseResourcesOutput,
    ProviderSearchResult,
    SearchCourseProjectsInput,
    SearchCourseProjectsOutput,
    SAFETY_NOTE_TEXT,
)
from app.utils.logging import get_logger
from app.utils.text import extract_keywords, truncate_text, unique_preserve_order


logger = get_logger(__name__)

DEFAULT_COMPARE_CRITERIA = [
    "课程相关性",
    "学校证据",
    "项目/实验/笔记类型匹配",
    "代码结构参考价值",
    "报告/文档参考价值",
    "课程专属性",
    "风险等级",
]

FIT_SCORE_MAP = {
    "high": 1.0,
    "medium": 0.65,
    "low": 0.2,
    "unknown": 0.45,
}

RISK_SCORE_MAP = {
    "low": 1.0,
    "medium": 0.68,
    "high": 0.25,
}


class CourseProjectIntelligenceService:
    def __init__(self) -> None:
        self.registry = ProviderRegistry()
        self.settings = self.registry.settings

    @property
    def github(self) -> BaseProvider:
        return self.registry.get("github")

    @github.setter
    def github(self, provider: BaseProvider) -> None:
        self.registry.set_provider("github", provider)

    @property
    def gitee(self) -> BaseProvider:
        return self.registry.get("gitee")

    @gitee.setter
    def gitee(self, provider: BaseProvider) -> None:
        self.registry.set_provider("gitee", provider)

    @property
    def web_seed(self) -> BaseProvider:
        return self.registry.get("web_seed")

    @web_seed.setter
    def web_seed(self, provider: BaseProvider) -> None:
        self.registry.set_provider("web_seed", provider)

    def _diversity_key(self, item) -> str | None:
        metadata = item.metadata or {}
        seed_url = metadata.get("seed_url")
        if item.source_type == "web" and seed_url:
            return f"seed:{seed_url}"
        return None

    def _diversify_search_results(self, items, *, top_k: int):
        if len(items) <= 1:
            return items

        selected = []
        selected_urls: set[str] = set()
        seen_diversity_keys: set[str] = set()

        for item in items:
            diversity_key = self._diversity_key(item)
            if diversity_key and diversity_key in seen_diversity_keys:
                continue
            selected.append(item)
            selected_urls.add(item.url.rstrip("/").lower())
            if diversity_key:
                seen_diversity_keys.add(diversity_key)
            if len(selected) >= top_k:
                return selected

        for item in items:
            url_key = item.url.rstrip("/").lower()
            if url_key in selected_urls:
                continue
            selected.append(item)
            selected_urls.add(url_key)
            if len(selected) >= top_k:
                break
        return selected

    def _owner_key(self, item) -> str | None:
        metadata = item.metadata or {}
        owner = str(metadata.get("owner") or "").strip().lower()
        if owner:
            return owner
        repo = str(getattr(item, "repo", None) or metadata.get("full_name") or getattr(item, "title", "") or "")
        if "/" in repo:
            return repo.split("/", 1)[0].strip().lower() or None
        return None

    def _school_key(self, item) -> str | None:
        school_id = str(getattr(item, "school_id", None) or "").strip().lower()
        if school_id:
            return school_id
        school = str(getattr(item, "school", None) or "").strip().lower()
        return school or None

    def _provider_supports_broad_school_fanout(self, provider: BaseProvider) -> bool:
        return provider.name in {"github", "gitee"} or provider.source_type in {"github", "gitee"}

    def _broad_school_planner_config(self) -> BroadSchoolPlannerConfig:
        return BroadSchoolPlannerConfig(
            max_schools_per_broad_query=self.settings.max_schools_per_broad_query,
            per_school_candidate_budget=self.settings.per_school_candidate_budget,
            max_total_candidates=self.settings.max_total_candidates,
            max_results_per_school_in_top=self.settings.max_results_per_school_in_top,
        )

    async def _search_provider_with_broad_plan(
        self,
        provider: BaseProvider,
        *,
        plan: BroadSchoolPlan,
        allow_domains: list[str] | None,
        deny_domains: list[str] | None,
    ) -> tuple[list[ProviderSearchResult], dict[str, Any]]:
        collected: list[ProviderSearchResult] = []
        profiles_with_results: list[str] = []
        failed_school_queries: list[dict[str, str]] = []

        for school_query in plan.school_queries:
            remaining_budget = plan.max_total_candidates - len(collected)
            if remaining_budget <= 0:
                break
            candidate_budget = max(1, min(school_query.candidate_budget, remaining_budget))
            try:
                items = await provider.search(
                    school_query.analysis,
                    top_k=candidate_budget,
                    allow_domains=allow_domains,
                    deny_domains=deny_domains,
                )
            except Exception as exc:
                logger.warning(
                    "Provider %s broad school search failed for %s: %s",
                    provider.name,
                    school_query.profile.canonical_name,
                    exc,
                )
                failed_school_queries.append(
                    {
                        "school": school_query.profile.canonical_name,
                        "school_id": school_query.profile.id,
                        "error": str(exc),
                    }
                )
                continue

            if items:
                profiles_with_results.append(school_query.profile.canonical_name)
            for item in items[:candidate_budget]:
                metadata = dict(item.metadata or {})
                metadata.setdefault("broad_scope_profile_id", school_query.profile.id)
                metadata.setdefault("broad_scope_profile_school", school_query.profile.canonical_name)
                item.metadata = metadata
                collected.append(item)
                if len(collected) >= plan.max_total_candidates:
                    break

        status = {
            "ok": bool(collected) or not failed_school_queries,
            "result_count": len(collected),
            "source_type": provider.source_type,
            "profiles_considered": plan.profile_count,
            "profiles_with_results": len(unique_preserve_order(profiles_with_results)),
            "broad_scope": True,
        }
        if failed_school_queries:
            status["metadata"] = {"failed_school_queries": failed_school_queries}
        if failed_school_queries and not collected:
            status["error"] = "all planned school queries failed"
        return collected[: plan.max_total_candidates], status

    def _is_broad_scope_low_priority(self, item, *, analysis) -> bool:
        repo_type = getattr(item, "repo_type", None)
        if repo_type == "org_meta":
            return True
        query_intent = classify_query_intent(analysis)
        if repo_type in {"collection", "exam_solution", "generic_algorithm"} and not self._repo_type_matches_intent(
            repo_type,
            query_intent,
        ):
            return True
        return False

    def _diversify_broad_scope_results(self, items, *, analysis, top_k: int):
        if len(items) <= 1:
            return items[:top_k]

        selected = []
        overflow = []
        selected_urls: set[str] = set()
        seen_owners: set[str] = set()
        school_counts: dict[str, int] = {}
        per_school_limit = max(1, self.settings.max_results_per_school_in_top)
        if top_k > 10:
            per_school_limit += 1

        def register(item) -> None:
            selected.append(item)
            selected_urls.add(item.url.rstrip("/").lower())
            owner_key = self._owner_key(item)
            school_key = self._school_key(item)
            if owner_key:
                seen_owners.add(owner_key)
            if school_key:
                school_counts[school_key] = school_counts.get(school_key, 0) + 1

        for item in items:
            owner_key = self._owner_key(item)
            school_key = self._school_key(item)
            if school_key and school_counts.get(school_key, 0) >= per_school_limit:
                overflow.append(item)
                continue
            if owner_key and owner_key in seen_owners:
                overflow.append(item)
                continue
            if len(selected) < 5 and self._is_broad_scope_low_priority(item, analysis=analysis):
                overflow.append(item)
                continue
            register(item)
            if len(selected) >= top_k:
                return selected

        for item in overflow:
            url_key = item.url.rstrip("/").lower()
            school_key = self._school_key(item)
            if url_key in selected_urls:
                continue
            if school_key and school_counts.get(school_key, 0) >= per_school_limit:
                continue
            if len(selected) < 5 and getattr(item, "repo_type", None) == "org_meta":
                continue
            register(item)
            if len(selected) >= top_k:
                return selected

        for item in items:
            url_key = item.url.rstrip("/").lower()
            if url_key in selected_urls:
                continue
            register(item)
            if len(selected) >= top_k:
                break
        return selected

    def _build_scope_coverage(
        self,
        *,
        plan: BroadSchoolPlan | None,
        visible_items,
        provider_status: dict[str, Any],
    ) -> dict[str, Any]:
        if plan is None:
            return {}

        schools_covered = unique_preserve_order([item.school for item in visible_items if getattr(item, "school", None)])
        profiles_with_results = 0
        for status in provider_status.values():
            if not isinstance(status, dict) or not status.get("broad_scope"):
                continue
            profiles_with_results = max(profiles_with_results, int(status.get("profiles_with_results") or 0))

        return {
            "schools_covered": schools_covered,
            "profiles_considered": plan.profile_count,
            "profiles_with_results": profiles_with_results,
        }

    def _demote_org_meta_results(self, items, *, analysis) -> list:
        query_intent = classify_query_intent(analysis)
        if query_intent == "collection":
            return items
        raw = (analysis.raw_query or "").lower()
        if any(term in raw for term in (".github", "profile", "organization profile", "community health", "组织主页")):
            return items
        non_meta = [item for item in items if item.repo_type != "org_meta"]
        meta = [item for item in items if item.repo_type == "org_meta"]
        return [*non_meta, *meta] if non_meta else items

    def _provider_supports_query_inspect(self, provider: Any) -> bool:
        inspect_repository = getattr(provider, "inspect_repository", None)
        if inspect_repository is None:
            return False
        try:
            parameters = inspect.signature(inspect_repository).parameters
        except (TypeError, ValueError):
            return False
        return "query" in parameters

    def _normalize_compare_criteria(self, criteria: list[str]) -> list[str]:
        normalized = [criterion.strip() for criterion in criteria if criterion and criterion.strip()]
        return unique_preserve_order(normalized) or list(DEFAULT_COMPARE_CRITERIA)

    def _repo_type_matches_intent(self, repo_type: str, query_intent: str) -> bool:
        compatibility = {
            "project": {"course_project", "lab_code"},
            "lab": {"lab_code", "course_project"},
            "notes": {"notes", "report_only"},
            "exam": {"exam_solution"},
            "collection": {"collection"},
            "generic": {
                "course_project",
                "lab_code",
                "notes",
                "report_only",
                "collection",
                "exam_solution",
                "generic_algorithm",
            },
        }
        allowed = compatibility.get(query_intent, compatibility["generic"])
        return repo_type in allowed

    def _criterion_score(
        self,
        criterion: str,
        item: InspectCourseProjectOutput,
        *,
        query_intent: str,
        course_profile=None,
    ) -> float:
        criterion_text = criterion.lower()
        detected_assets = item.detected_assets or {}
        course_assets = item.course_specific_assets or {}
        fit_score = FIT_SCORE_MAP.get(item.fit_for_query, FIT_SCORE_MAP["unknown"])
        risk_score = RISK_SCORE_MAP.get(item.risk_level, RISK_SCORE_MAP["medium"])

        if any(token in criterion_text for token in ("数据库设计", "表设计", "表结构", "sql", "schema", "er图", "erd")):
            score = 1.0 if detected_assets.get("has_sql_or_schema") else 0.2
            if course_assets.get("has_models"):
                score = min(1.0, score + 0.08)
            if any(token in criterion_text for token in ("er图", "erd")):
                return 1.0 if course_assets.get("has_er_diagram") else 0.2
            return min(1.0, score)
        if any(token in criterion_text for token in ("调度器", "scheduler")):
            return 1.0 if course_assets.get("has_scheduler_hint") else 0.2
        if any(token in criterion_text for token in ("内存管理", "memory", "paging")):
            return 1.0 if course_assets.get("has_memory_hint") else 0.2
        if any(token in criterion_text for token in ("内核", "kernel", "ucore")):
            return 1.0 if (course_assets.get("has_kernel_dir") or course_assets.get("has_ucore")) else 0.2
        if any(token in criterion_text for token in ("文件系统", "file system", "filesystem")):
            return 1.0 if course_assets.get("has_file_system_hint") else 0.2
        if any(token in criterion_text for token in ("词法", "lexer")):
            return 1.0 if course_assets.get("has_lexer") else 0.2
        if any(token in criterion_text for token in ("语法", "parser")):
            return 1.0 if course_assets.get("has_parser") else 0.2
        if "ast" in criterion_text:
            return 1.0 if course_assets.get("has_ast") else 0.2
        if any(token in criterion_text for token in (" ir", "ir ", "llvm", "codegen")):
            return 1.0 if (
                course_assets.get("has_ir")
                or course_assets.get("has_llvm")
                or course_assets.get("has_codegen")
            ) else 0.2
        if any(token in criterion_text for token in ("章节笔记", "chapter", "dp", "graph", "greedy", "complexity")):
            return 1.0 if (
                course_assets.get("has_chapter_notes")
                or course_assets.get("has_dp_notes")
                or course_assets.get("has_graph_notes")
                or course_assets.get("has_complexity_notes")
            ) else 0.2
        if any(token in criterion_text for token in ("dataset", "train", "eval", "训练", "评估", "notebook")):
            return 1.0 if (
                course_assets.get("has_dataset")
                or course_assets.get("has_train_script")
                or course_assets.get("has_eval_script")
                or course_assets.get("has_notebook")
            ) else 0.2
        if any(token in criterion_text for token in ("报告结构", "实验报告", "报告", "文档")):
            if detected_assets.get("has_report"):
                return 1.0
            if detected_assets.get("has_notes"):
                return 0.6
            return 0.2
        if any(token in criterion_text for token in ("代码结构", "项目结构", "模块划分", "实验流程")):
            return 1.0 if (detected_assets.get("has_src") or detected_assets.get("has_lab")) else 0.2
        if any(token in criterion_text for token in ("项目选题", "选题路线")):
            if item.repo_type == "course_project":
                return 1.0
            if item.repo_type in {"lab_code", "notes"}:
                return 0.55
            return 0.2
        if any(token in criterion_text for token in ("课程相关性", "课程专属性", "学校证据")):
            return fit_score if item.fit_for_query != "unknown" else min(1.0, (item.score or 0.0) + 0.1)
        if any(token in criterion_text for token in ("项目/实验/笔记类型匹配", "类型匹配")):
            return 1.0 if self._repo_type_matches_intent(item.repo_type, query_intent) else 0.25
        if any(token in criterion_text for token in ("风险等级", "代码复用风险", "风险")):
            return risk_score
        if course_profile is not None and any(
            token in criterion_text
            for token in [criterion.lower(), *(item.reference_utility or []), *(course_profile.reference_criteria or [])]
        ):
            return 0.85
        if any(token in " ".join(item.reference_utility + item.suggested_usage) for token in (criterion, criterion_text)):
            return 0.85
        return 0.45

    def _reference_utility_match(
        self,
        item: InspectCourseProjectOutput,
        *,
        criteria: list[str],
        query_intent: str,
        course_profile=None,
    ) -> float:
        if not criteria:
            return 0.0
        scores = [
            self._criterion_score(
                criterion,
                item,
                query_intent=query_intent,
                course_profile=course_profile,
            )
            for criterion in criteria
        ]
        return round(sum(scores) / len(scores), 4)

    def _best_for(
        self,
        item: InspectCourseProjectOutput,
        *,
        criteria: list[str],
        query_intent: str,
        course_profile=None,
    ) -> list[str]:
        best = [
            criterion
            for criterion in criteria
            if self._criterion_score(
                criterion,
                item,
                query_intent=query_intent,
                course_profile=course_profile,
            ) >= 0.8
        ]
        if best:
            return best[:3]

        fallbacks: list[str] = []
        detected_assets = item.detected_assets or {}
        course_assets = item.course_specific_assets or {}
        if detected_assets.get("has_sql_or_schema"):
            fallbacks.append("数据库设计")
        if course_assets.get("has_scheduler_hint"):
            fallbacks.append("调度器实现")
        if course_assets.get("has_memory_hint"):
            fallbacks.append("内存管理")
        if course_assets.get("has_parser"):
            fallbacks.append("语法分析")
        if course_assets.get("has_ast") or course_assets.get("has_ir"):
            fallbacks.append("AST/IR 组织")
        if detected_assets.get("has_src") or detected_assets.get("has_lab"):
            fallbacks.append("代码结构")
        if detected_assets.get("has_report"):
            fallbacks.append("报告结构")
        if item.reference_utility:
            fallbacks.extend(item.reference_utility[:2])
        return unique_preserve_order(fallbacks)[:3]

    def _weaknesses(
        self,
        item: InspectCourseProjectOutput,
        *,
        criteria: list[str],
        query_intent: str,
        course_profile=None,
    ) -> list[str]:
        weaknesses: list[str] = []
        detected_assets = item.detected_assets or {}
        course_assets = item.course_specific_assets or {}
        if item.fit_for_query == "low":
            weaknesses.append("与当前 query 匹配较弱")
        if any(
            any(token in criterion.lower() for token in ("数据库设计", "表设计", "表结构", "sql", "schema", "er图", "erd"))
            for criterion in criteria
        ) and not (detected_assets.get("has_sql_or_schema") or course_assets.get("has_er_diagram")):
            weaknesses.append("数据库设计证据不足")
        if any(any(token in criterion.lower() for token in ("调度器", "scheduler")) for criterion in criteria) and not course_assets.get("has_scheduler_hint"):
            weaknesses.append("缺少调度器相关实现线索")
        if any(any(token in criterion.lower() for token in ("内存管理", "memory")) for criterion in criteria) and not course_assets.get("has_memory_hint"):
            weaknesses.append("缺少内存管理相关实现线索")
        if any(any(token in criterion.lower() for token in ("词法", "lexer", "语法", "parser", "ast", "ir", "llvm", "codegen")) for criterion in criteria) and not any(
            course_assets.get(key)
            for key in ("has_lexer", "has_parser", "has_ast", "has_ir", "has_llvm", "has_codegen")
        ):
            weaknesses.append("缺少编译前端/中间表示相关线索")
        if any(
            any(token in criterion.lower() for token in ("报告结构", "实验报告", "报告", "文档"))
            for criterion in criteria
        ) and not detected_assets.get("has_report"):
            weaknesses.append("报告资料不足")
        if any(
            any(token in criterion.lower() for token in ("代码结构", "项目结构", "模块划分", "实验流程"))
            for criterion in criteria
        ) and not (detected_assets.get("has_src") or detected_assets.get("has_lab")):
            weaknesses.append("代码结构参考价值有限")
        if item.repo_type == "collection":
            weaknesses.append("更偏资料导航，不是单一项目实现")
        if item.repo_type == "org_meta":
            weaknesses.append("更像组织元仓库，不是项目本体")
        if item.repo_type == "exam_solution":
            weaknesses.append("更偏题解/答案，不适合直接作为项目参考")
        if item.repo_type == "generic_algorithm":
            weaknesses.append("课程专属性较弱")
        if item.risk_level == "high":
            weaknesses.append("直接参考风险较高")
        if not self._repo_type_matches_intent(item.repo_type, query_intent):
            weaknesses.append("仓库类型与当前任务意图不完全匹配")
        return unique_preserve_order(weaknesses)[:4]

    def _overall_fit_score(
        self,
        item: InspectCourseProjectOutput,
        *,
        criteria: list[str],
        query_intent: str,
        course_profile=None,
    ) -> float:
        inspect_score = item.score or 0.0
        query_fit_score = FIT_SCORE_MAP.get(item.fit_for_query, FIT_SCORE_MAP["unknown"])
        utility_match = self._reference_utility_match(
            item,
            criteria=criteria,
            query_intent=query_intent,
            course_profile=course_profile,
        )
        risk_adjusted_score = RISK_SCORE_MAP.get(item.risk_level, RISK_SCORE_MAP["medium"])
        return round(
            0.50 * inspect_score
            + 0.20 * query_fit_score
            + 0.15 * utility_match
            + 0.15 * risk_adjusted_score,
            4,
        )

    def _eligible_for_best_overall(
        self,
        item: InspectCourseProjectOutput,
        *,
        query_present: bool,
    ) -> bool:
        if item.repo_type == "org_meta":
            return False
        if item.risk_level == "high":
            return False
        if not query_present:
            return True
        if item.repo_type in {"collection", "exam_solution", "generic_algorithm"} and item.fit_for_query != "high":
            return False
        return True

    def _compare_summary(self, comparison: list[CompareCourseProjectsItem]) -> str:
        if not comparison:
            return "未能获取有效仓库对比结果。"
        if len(comparison) == 1:
            best_for = "、".join(comparison[0].best_for[:2]) or "课程项目调研"
            return f"当前仅有一个可比较仓库，{comparison[0].repo} 更适合参考 {best_for}。"

        first = comparison[0]
        second = comparison[1]
        first_best = "、".join(first.best_for[:2]) or "课程结构"
        second_best = "、".join(second.best_for[:2]) or "补充参考"
        if len(comparison) >= 3 and comparison[2].fit_for_query == "low":
            return (
                f"综合来看，{first.repo} 更适合参考 {first_best}，"
                f"{second.repo} 更适合补充 {second_best}，"
                f"{comparison[2].repo} 与当前任务匹配较弱。"
            )
        return f"综合来看，{first.repo} 更适合参考 {first_best}，{second.repo} 更适合作为补充参考。"

    def _compare_recommendation(self, comparison: list[CompareCourseProjectsItem]) -> str:
        if not comparison:
            return "仅用于课程项目调研和学习参考，不支持直接代写、复制或提交。"
        first = comparison[0]
        first_best = "、".join(first.best_for[:2]) or "项目结构"
        if len(comparison) == 1:
            return f"优先参考 {first.repo} 的 {first_best}；不要直接复制任何仓库的代码或报告。"

        second = comparison[1]
        second_best = "、".join(second.best_for[:2]) or "补充说明"
        return (
            f"优先参考 {first.repo} 的 {first_best}；"
            f"{second.repo} 可用于补充 {second_best}；"
            "不要直接复制任何仓库的代码或报告。"
        )

    async def search_course_projects(
        self,
        payload: SearchCourseProjectsInput,
    ) -> SearchCourseProjectsOutput:
        top_k = max(1, min(payload.top_k, self.settings.max_top_k))
        query_text = " ".join([payload.query or "", payload.freshness or ""]).strip()
        analysis = analyze_query(
            query_text,
            school=payload.school,
            course=payload.course,
            source_types=payload.source_types,
        )

        providers = self.registry.select_search_providers(payload.source_types or analysis.source_types)
        broad_plan = plan_broad_school_retrieval(
            analysis,
            requested_top_k=top_k,
            config=self._broad_school_planner_config(),
        )
        collected = []
        warnings: list[str] = []
        provider_status: dict[str, Any] = {}

        if not providers:
            warnings.append("未启用或未匹配到可用 provider，请检查 source_types 与 ENABLE_* 配置。")

        for provider in providers:
            if provider.name == "gitee":
                warnings.append("Gitee provider 当前仍是 MVP 占位，搜索接口尚未完整实现。")
            try:
                if broad_plan is not None and self._provider_supports_broad_school_fanout(provider):
                    items, provider_status[provider.name] = await self._search_provider_with_broad_plan(
                        provider,
                        plan=broad_plan,
                        allow_domains=payload.allow_domains or None,
                        deny_domains=payload.deny_domains or None,
                    )
                else:
                    items = await provider.search(
                        analysis,
                        top_k=top_k,
                        allow_domains=payload.allow_domains or None,
                        deny_domains=payload.deny_domains or None,
                    )
                    provider_status[provider.name] = {
                        "ok": True,
                        "result_count": len(items),
                        "source_type": provider.source_type,
                    }
            except Exception as exc:
                logger.warning("Provider %s search failed: %s", provider.name, exc)
                warnings.append(f"Provider `{provider.name}` 检索失败：{exc}")
                provider_status[provider.name] = {
                    "ok": False,
                    "error": str(exc),
                    "source_type": provider.source_type,
                }
                items = []

            for item in items:
                evidence_obj = explain_score(analysis, item)
                evidence = evidence_obj.as_dict()
                normalized = normalize_provider_result(
                    item,
                    school=analysis.school,
                    course=analysis.course,
                    confidence=evidence_obj.final_score,
                    explanation=evidence_obj.summary(),
                    evidence=evidence,
                )
                collected.append(normalized)

        deduped = dedupe_results(collected)
        deduped.sort(key=lambda x: (x.score or x.confidence, x.year or 0), reverse=True)
        deduped = self._demote_org_meta_results(deduped, analysis=analysis)
        if broad_plan is not None:
            seed_diversified = self._diversify_search_results(deduped, top_k=max(len(deduped), 1))
            diversified = self._diversify_broad_scope_results(
                seed_diversified,
                analysis=analysis,
                top_k=top_k,
            )
        else:
            diversified = self._diversify_search_results(deduped, top_k=top_k)

        if not deduped:
            warnings.append("未找到稳定匹配结果；可以补充课程英文名、技术栈、年份，或放宽 query。")

        scope_coverage = self._build_scope_coverage(
            plan=broad_plan,
            visible_items=diversified[:top_k],
            provider_status=provider_status,
        )

        return SearchCourseProjectsOutput(
            query_analysis=analysis.model_dump(),
            total_found=len(deduped),
            results=diversified[:top_k],
            provider_status=provider_status,
            school_scope=analysis.school_scope if analysis.school_scope != "none" else None,
            school_group=broad_plan.school_group if broad_plan is not None else None,
            scope_note=broad_plan.scope_note if broad_plan is not None else None,
            scope_coverage=scope_coverage,
            warnings=unique_preserve_order(warnings),
            safety_note=SAFETY_NOTE_TEXT,
        )

    def _infer_project_type(self, title: str, summary: str) -> str:
        text = f"{title} {summary}".lower()
        if "lab" in text or "实验" in text:
            return "lab"
        if "课程设计" in text or "大作业" in text or "course project" in text or "final project" in text:
            return "course_project"
        if "report" in text or "报告" in text:
            return "report_or_material"
        if "资料" in text or "教程" in text or "guide" in text:
            return "resource"
        return "public_project"

    def _build_brief_summary(self, result: ProviderSearchResult, tech_stack: list[str]) -> str:
        metadata = result.metadata or {}
        source_type = result.source_type or result.source
        snippet = truncate_text(result.snippet or result.title, 650)
        parts = [snippet]
        if metadata.get("full_name"):
            parts.append(f"来源仓库：{metadata['full_name']}")
        if tech_stack:
            parts.append(f"可见技术栈：{', '.join(tech_stack[:6])}")
        if metadata.get("stargazers_count") is not None and source_type == "github":
            parts.append(
                f"公开可见信号：stars={metadata.get('stargazers_count', 0)}, "
                f"forks={metadata.get('forks_count', 0)}"
            )
        return truncate_text("；".join([part for part in parts if part]), 900)

    def _infer_key_points(self, title: str, summary: str, tech_stack: list[str]) -> list[str]:
        points = []
        keywords = extract_keywords(f"{title} {summary}", top_k=8)
        if tech_stack:
            points.append(f"可能涉及的技术栈：{', '.join(tech_stack[:6])}")
        if keywords:
            points.append(f"高频关键词：{', '.join(keywords[:6])}")
        if "github.com" in summary or "仓库" in summary:
            points.append("可用于分析项目目录结构、README 组织方式和模块拆分。")
        if "readme" in summary.lower():
            points.append("README 可用于确认运行方式、模块边界和依赖范围。")
        points.append("建议优先参考公开项目思路和结构，不要直接复用为可提交作业。")
        return unique_preserve_order(points)[:5]

    async def get_project_brief(
        self,
        payload: GetProjectBriefInput,
    ) -> GetProjectBriefOutput:
        provider = self.registry.provider_for_url(payload.url)
        result = await provider.get_project_brief(payload.url)
        if result is None and provider is not self.web_seed:
            result = await self.web_seed.get_project_brief(payload.url)

        if result is None:
            result = ProviderSearchResult(
                title=payload.url,
                url=payload.url,
                source="web",
                source_type="web",
                snippet="Unable to extract detailed brief from the target URL.",
                metadata={},
            )

        analysis = analyze_query(f"{result.title} {result.snippet}")
        tech_stack = infer_tech_tags(result.title, result.snippet, result.metadata or {})
        summary = self._build_brief_summary(result, tech_stack)
        project_type = self._infer_project_type(result.title, summary)
        key_points = self._infer_key_points(result.title, summary, tech_stack)

        return GetProjectBriefOutput(
            title=result.title,
            summary=summary,
            inferred_course=analysis.course,
            inferred_school=analysis.school,
            tech_stack=tech_stack,
            project_type=project_type,
            key_points=key_points,
            risk_note=SAFETY_NOTE_TEXT,
            citations=[
                CitationItem(
                    title=result.title,
                    url=result.url,
                    note=f"direct source via {result.source_type}",
                )
            ],
        )

    def _infer_modules_from_brief(self, item: GetProjectBriefOutput) -> list[str]:
        text = " ".join(
            [item.title, item.summary, item.project_type, " ".join(item.tech_stack), " ".join(item.key_points)]
        ).lower()
        modules: list[str] = []
        if any(tag in item.tech_stack for tag in ["react", "vue", "web", "javascript", "typescript"]):
            modules.append("前端界面与交互层")
        if any(tag in item.tech_stack for tag in ["flask", "fastapi", "django", "spring", "node.js"]):
            modules.append("后端 API 与业务逻辑层")
        if any(tag in item.tech_stack for tag in ["mysql", "postgresql", "sqlite", "redis"]):
            modules.append("数据建模与持久化")
        if any(tag in item.tech_stack for tag in ["pytorch", "tensorflow", "opencv", "深度学习"]):
            modules.append("数据集、模型训练与评测")
        if any(tag in item.tech_stack for tag in ["图算法", "可视化", "检索"]):
            modules.append("算法建模、结果解释与可视化")
        if "report" in text or "报告" in text:
            modules.append("实验报告与复现实验记录")
        modules.append("README、运行说明与依赖管理")
        return unique_preserve_order(modules)

    def _summarize_common_modules(self, items: list[GetProjectBriefOutput]) -> list[str]:
        module_counts: dict[str, int] = {}
        for item in items:
            for module in self._infer_modules_from_brief(item):
                module_counts[module] = module_counts.get(module, 0) + 1
        threshold = 2 if len(items) >= 2 else 1
        common = [module for module, count in module_counts.items() if count >= threshold]
        if common:
            return common[:8]
        pool: list[str] = []
        for item in items:
            pool.extend(item.tech_stack)
            pool.extend(extract_keywords(" ".join(item.key_points), top_k=5))
        return unique_preserve_order(pool)[:8]

    def _summarize_differences(self, items: list[GetProjectBriefOutput]) -> list[str]:
        differences = []
        for item in items:
            modules = self._infer_modules_from_brief(item)
            if item.tech_stack:
                differences.append(
                    f"{item.title}: {item.project_type or 'public_project'}，技术路线偏向"
                    f"{', '.join(item.tech_stack[:4])}，重点模块包括 {', '.join(modules[:3])}"
                )
            else:
                differences.append(f"{item.title}: 更偏资料/经验型页面而非明确代码仓库")
        return differences[:8]

    def _recommended_learning_path(self, items: list[GetProjectBriefOutput]) -> list[str]:
        steps = [
            "先看课程要求与评分点，明确是实验型、课程设计型还是综合大作业。",
            "优先阅读公开项目的 README、模块划分和运行说明。",
            "对比 2~3 个项目的共通模块，再决定自己的最小可行实现范围。",
            "先补前置知识，再独立实现核心模块。",
            "最后只把公开项目当作验证思路和查漏补缺的参考。",
        ]
        if any("web" in x.tech_stack or "react" in x.tech_stack or "vue" in x.tech_stack for x in items):
            steps.insert(2, "如果题目偏系统平台类项目，先区分前端、后端、数据库三层职责。")
        if any("pytorch" in x.tech_stack or "tensorflow" in x.tech_stack for x in items):
            steps.insert(2, "如果题目偏 AI/视觉方向，先确认数据集、训练流程和评测指标。")
        return unique_preserve_order(steps)[:6]

    async def compare_project_routes(
        self,
        payload: CompareProjectRoutesInput,
    ) -> CompareProjectRoutesOutput:
        briefs: list[GetProjectBriefOutput] = []
        citations: list[CitationItem] = []
        urls = list(payload.urls or [])
        if not urls:
            search_result = await self.search_course_projects(
                SearchCourseProjectsInput(
                    query=payload.query,
                    top_k=payload.top_k,
                )
            )
            urls = [item.url for item in search_result.results[: payload.top_k]]

        for url in urls[: payload.top_k]:
            brief = await self.get_project_brief(GetProjectBriefInput(url=url))
            briefs.append(brief)
            citations.extend(brief.citations)

        compared_items = [
            ComparedItem(
                title=brief.title,
                url=brief.citations[0].url if brief.citations else "",
                project_type=brief.project_type,
                inferred_stack=brief.tech_stack,
                highlights=brief.key_points,
            )
            for brief in briefs
        ]

        return CompareProjectRoutesOutput(
            compared_items=compared_items,
            common_modules=self._summarize_common_modules(briefs),
            differing_routes=self._summarize_differences(briefs),
            typical_stack_choices=unique_preserve_order([tag for brief in briefs for tag in brief.tech_stack])[:10],
            recommended_learning_path=self._recommended_learning_path(briefs),
            citations=citations[:10],
        )

    def _categorize_resource(self, title: str, url: str, note: str) -> str:
        text = f"{title} {url} {note}".lower()
        if "github.com" in text or "gitee.com" in text:
            return "repository"
        if "blog" in text or "csdn" in text or "cnblogs" in text:
            return "blog"
        if "实验" in text or "lab" in text:
            return "lab_material"
        if "报告" in text or "slides" in text:
            return "report_or_slides"
        return "general_resource"

    async def list_course_resources(
        self,
        payload: ListCourseResourcesInput,
    ) -> ListCourseResourcesOutput:
        query = f"{payload.school or ''} {payload.course} 资料 教程 实验 大作业 github"
        search_result = await self.search_course_projects(
            SearchCourseProjectsInput(
                query=query.strip(),
                school=payload.school,
                course=payload.course,
                top_k=payload.top_k,
            )
        )

        resources: list[CourseResourceItem] = []
        categories: list[str] = []
        citations: list[CitationItem] = []
        for item in search_result.results:
            category = self._categorize_resource(item.title, item.url, item.snippet)
            categories.append(category)
            resources.append(
                CourseResourceItem(
                    title=item.title,
                    url=item.url,
                    category=category,
                    note=item.use_case or item.snippet,
                    source_type=item.source_type,
                    tags=item.tech_tags,
                )
            )
            citations.append(CitationItem(title=item.title, url=item.url, note=category))

        notes = [
            "结果为公开资料入口与学习线索，不等同于课程官方答案。",
            "建议优先阅读 README、项目结构、实验报告框架和经验总结。",
            "若课程每年题目变化较大，请重点参考方法路线而不是具体实现细节。",
        ]
        return ListCourseResourcesOutput(
            school=payload.school,
            course=payload.course,
            resources=resources,
            categories=unique_preserve_order(categories),
            notes=notes,
            citations=citations[:10],
        )

    async def inspect_course_project(
        self,
        payload: InspectCourseProjectInput,
    ) -> InspectCourseProjectOutput:
        provider = self.github
        if not hasattr(provider, "inspect_repository"):
            return InspectCourseProjectOutput(
                repo=payload.repo,
                error="GitHub provider is unavailable for inspect_course_project.",
            )
        try:
            inspect_kwargs = {
                "include_readme": payload.include_readme,
                "include_tree": payload.include_tree,
            }
            if payload.query and self._provider_supports_query_inspect(provider):
                inspect_kwargs["query"] = payload.query
            return await provider.inspect_repository(payload.repo, **inspect_kwargs)
        except Exception as exc:
            logger.warning("inspect_course_project failed for %s: %s", payload.repo, exc)
            return InspectCourseProjectOutput(
                repo=payload.repo,
                url=f"https://github.com/{payload.repo}" if "/" in payload.repo else None,
                source_provider="github",
                error=f"Failed to inspect repository `{payload.repo}`: {exc}",
                fit_for_query="unknown",
                task_fit_reason="仓库分析失败，无法判断当前任务匹配度。",
                not_suitable_for=["不适合作为当前任务的主要参考对象"],
                suggested_usage=[],
                risk_level="high",
                risk_note=SAFETY_NOTE_TEXT,
            )

    async def compare_course_projects(
        self,
        payload: CompareCourseProjectsInput,
    ) -> CompareCourseProjectsOutput:
        repos = unique_preserve_order(payload.repos)[:5]
        criteria = self._normalize_compare_criteria(payload.criteria)
        query_context = " ".join([payload.query or "", *criteria]).strip()
        query_analysis = analyze_query(query_context, source_types=["github"]) if query_context else None
        query_intent = classify_query_intent(query_analysis) if query_analysis else "generic"
        course_profile = (
            get_course_profile(query_analysis.course_profile_id or query_analysis.course)
            if query_analysis
            else None
        )

        inspect_tasks = [
            self.inspect_course_project(
                InspectCourseProjectInput(
                    repo=repo,
                    query=payload.query,
                    include_readme=True,
                    include_tree=True,
                )
            )
            for repo in repos
        ]
        inspected = await asyncio.gather(*inspect_tasks, return_exceptions=True)

        ranked: list[tuple[float, CompareCourseProjectsItem]] = []
        failed_repos: list[FailedRepoItem] = []
        query_present = bool(payload.query and payload.query.strip())

        for repo, result in zip(repos, inspected, strict=False):
            if isinstance(result, Exception):
                failed_repos.append(FailedRepoItem(repo=repo, error=str(result)))
                continue
            if result.error:
                failed_repos.append(FailedRepoItem(repo=repo, error=result.error))
                continue

            best_for = self._best_for(
                result,
                criteria=criteria,
                query_intent=query_intent,
                course_profile=course_profile,
            )
            weaknesses = self._weaknesses(
                result,
                criteria=criteria,
                query_intent=query_intent,
                course_profile=course_profile,
            )
            reason = result.task_fit_reason or result.why_recommended or result.risk_note or ""
            comparison_item = CompareCourseProjectsItem(
                repo=result.repo,
                url=result.url,
                repo_type=result.repo_type,
                school=result.school,
                course=result.course,
                course_profile_id=result.course_profile_id,
                intent=result.intent,
                score=result.score,
                value_level=result.value_level,
                confidence_level=result.confidence_level,
                fit_for_query=result.fit_for_query,
                best_for=best_for,
                weaknesses=weaknesses,
                risk_level=result.risk_level,
                reason=reason,
                reference_utility=result.reference_utility if payload.include_details else [],
                suggested_usage=result.suggested_usage if payload.include_details else [],
                not_suitable_for=result.not_suitable_for if payload.include_details else [],
                detected_assets=result.detected_assets if payload.include_details else {},
                course_specific_assets=result.course_specific_assets if payload.include_details else {},
            )
            overall_fit = self._overall_fit_score(
                result,
                criteria=criteria,
                query_intent=query_intent,
                course_profile=course_profile,
            )
            ranked.append((overall_fit, comparison_item))

        ranked.sort(
            key=lambda entry: (
                -FIT_SCORE_MAP.get(entry[1].fit_for_query, FIT_SCORE_MAP["unknown"]),
                -entry[0],
                entry[1].risk_level == "high",
            )
        )

        comparison = [item for _, item in ranked]
        eligible = [
            (score, item)
            for score, item in ranked
            if self._eligible_for_best_overall(item, query_present=query_present)
        ]
        best_overall = eligible[0][1].repo if eligible else (comparison[0].repo if comparison else None)

        return CompareCourseProjectsOutput(
            query=payload.query,
            criteria=criteria,
            best_overall=best_overall,
            summary=self._compare_summary(comparison),
            comparison=comparison,
            failed_repos=failed_repos,
            recommendation=self._compare_recommendation(comparison),
            safety_note=SAFETY_NOTE_TEXT,
        )
