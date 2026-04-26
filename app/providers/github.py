from __future__ import annotations

import asyncio
import base64
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.config import get_settings
from app.core.course_profiles import detect_course_specific_assets, get_course_profile
from app.core.query_analyzer import analyze_query
from app.core.repo_classifier import REPO_TYPE_ORG_META, classify_repository
from app.core.retrieval_profiles import build_github_search_queries
from app.core.retrieval_intents import classify_query_intent
from app.core.vocabulary import find_course_mentions, get_course_aliases, term_in_text
from app.providers.base import BaseProvider
from app.ranking.scorer import explain_score, score_provider_result
from app.schemas import InspectCourseProjectOutput, ProviderSearchResult, QueryAnalysis, SAFETY_NOTE_TEXT
from app.utils.http import fetch_json
from app.utils.logging import get_logger
from app.utils.text import safe_lower, truncate_text


logger = get_logger(__name__)

NOTE_STRUCTURE_HINTS = ["notes", "note", "笔记", "docs", "lecture", "lectures"]
LAB_STRUCTURE_HINTS = ["lab", "labs", "实验", "src", "kernel", "ucore"]
REPORT_STRUCTURE_HINTS = ["report", "reports", "报告", "pdf", "doc", "docx"]
EXAM_STRUCTURE_HINTS = ["exam", "exams", "quiz", "试题", "真题", "期末", "期中", "answer", "solution"]
COLLECTION_STRUCTURE_HINTS = ["courses", "resources", "archive", "awesome", "合集", "资料", "course"]
ORG_META_STRUCTURE_HINTS = [".github", "profile", "community", "contributing", "code_of_conduct"]
PACKAGE_REQUIREMENTS_HINTS = [
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "requirements.txt",
    "pyproject.toml",
    "pom.xml",
    "build.gradle",
    "cargo.toml",
    "go.mod",
]


class GitHubProvider(BaseProvider):
    name = "github"
    source_type = "github"

    def __init__(self) -> None:
        self.settings = get_settings()
        self._search_cache: dict[tuple[str, int], list[dict[str, Any]]] = {}
        self._repo_cache: dict[str, dict[str, Any] | None] = {}
        self._readme_cache: dict[str, str] = {}
        self._readme_error_cache: dict[str, bool] = {}
        self._root_entries_cache: dict[str, list[dict[str, str]]] = {}
        self._root_entries_error_cache: dict[str, bool] = {}

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        return headers

    def _domain_allowed(
        self,
        url: str,
        allow_domains: Optional[list[str]],
        deny_domains: Optional[list[str]],
    ) -> bool:
        host = urlparse(url).netloc.lower()
        if deny_domains:
            for domain in deny_domains:
                if domain.lower() in host:
                    return False
        if allow_domains:
            return any(domain.lower() in host for domain in allow_domains)
        return True

    def _repo_key(self, owner: str, repo: str) -> str:
        return f"{owner}/{repo}".lower()

    def _repo_to_result(self, repo: Dict[str, Any]) -> ProviderSearchResult:
        topics = repo.get("topics") or []
        language = repo.get("language")
        languages = [language] if language else []
        stars = repo.get("stargazers_count")
        forks = repo.get("forks_count")
        updated_at = repo.get("updated_at")
        metadata = {
            "full_name": repo.get("full_name"),
            "topics": topics,
            "languages": languages,
            "stargazers_count": stars,
            "forks_count": forks,
            "updated_at": updated_at,
            "pushed_at": repo.get("pushed_at"),
            "created_at": repo.get("created_at"),
            "default_branch": repo.get("default_branch"),
            "owner": (repo.get("owner") or {}).get("login"),
            "license": ((repo.get("license") or {}).get("spdx_id")),
            "archived": repo.get("archived", False),
            "visibility": repo.get("visibility"),
            "github_score": repo.get("score"),
            "homepage": repo.get("homepage"),
            "description": repo.get("description") or "",
            "year": None,
        }
        snippet_parts = [
            repo.get("description") or "",
            f"stars={stars}" if stars is not None else "",
            f"forks={forks}" if forks is not None else "",
            f"updated={updated_at}" if updated_at else "",
            f"language={language}" if language else "",
        ]
        return ProviderSearchResult(
            title=repo.get("full_name") or repo.get("name") or "GitHub Repository",
            url=repo.get("html_url") or "",
            source=self.name,
            source_type=self.source_type,
            snippet=truncate_text(" | ".join(part for part in snippet_parts if part), 320),
            metadata=metadata,
        )

    async def _search_repositories(self, query: str, per_page: int) -> list[dict[str, Any]]:
        cache_key = (query, per_page)
        if cache_key in self._search_cache:
            return list(self._search_cache[cache_key])

        url = f"{self.settings.github_api_base}/search/repositories"
        params = {
            "q": query,
            "sort": "best-match",
            "order": "desc",
            "per_page": max(1, min(per_page, 50)),
            "page": 1,
        }
        payload = await fetch_json(
            url,
            params=params,
            headers=self._build_headers(),
            timeout=self.settings.github_timeout_seconds,
        )
        items = payload.get("items") or []
        self._search_cache[cache_key] = list(items)
        return list(items)

    async def _fetch_repository(self, owner: str, repo: str) -> dict[str, Any] | None:
        cache_key = self._repo_key(owner, repo)
        if cache_key in self._repo_cache:
            cached = self._repo_cache[cache_key]
            return dict(cached) if isinstance(cached, dict) else None

        api_url = f"{self.settings.github_api_base}/repos/{owner}/{repo}"
        try:
            payload = await fetch_json(
                api_url,
                headers=self._build_headers(),
                timeout=self.settings.github_timeout_seconds,
            )
        except Exception as exc:
            logger.debug("GitHub repo fetch failed for %s: %s", cache_key, exc)
            self._repo_cache[cache_key] = None
            return None

        self._repo_cache[cache_key] = dict(payload)
        return dict(payload)

    async def _fetch_readme_excerpt(self, owner: str, repo: str) -> str:
        cache_key = self._repo_key(owner, repo)
        if cache_key in self._readme_cache:
            return self._readme_cache[cache_key]

        api_url = f"{self.settings.github_api_base}/repos/{owner}/{repo}/readme"
        self._readme_error_cache[cache_key] = False
        try:
            payload = await fetch_json(
                api_url,
                headers=self._build_headers(),
                timeout=self.settings.github_timeout_seconds,
            )
        except Exception as exc:
            logger.debug("GitHub README fetch failed for %s: %s", cache_key, exc)
            self._readme_error_cache[cache_key] = True
            self._readme_cache[cache_key] = ""
            return ""

        content = payload.get("content") or ""
        encoding = (payload.get("encoding") or "").lower()
        if encoding != "base64" or not content:
            self._readme_cache[cache_key] = ""
            return ""

        try:
            decoded = base64.b64decode(content).decode("utf-8", errors="replace")
        except Exception as exc:
            logger.debug("GitHub README decode failed for %s: %s", cache_key, exc)
            self._readme_error_cache[cache_key] = True
            self._readme_cache[cache_key] = ""
            return ""

        excerpt = truncate_text(decoded, 1600)
        self._readme_cache[cache_key] = excerpt
        return excerpt

    async def _fetch_root_entries(self, owner: str, repo: str) -> list[dict[str, str]]:
        cache_key = self._repo_key(owner, repo)
        if cache_key in self._root_entries_cache:
            return list(self._root_entries_cache[cache_key])

        api_url = f"{self.settings.github_api_base}/repos/{owner}/{repo}/contents"
        headers = self._build_headers()
        headers["Accept"] = "application/vnd.github.object+json"
        self._root_entries_error_cache[cache_key] = False
        try:
            payload = await fetch_json(
                api_url,
                headers=headers,
                timeout=self.settings.github_timeout_seconds,
            )
        except Exception as exc:
            logger.debug("GitHub contents fetch failed for %s: %s", cache_key, exc)
            self._root_entries_error_cache[cache_key] = True
            self._root_entries_cache[cache_key] = []
            return []

        entries_payload = payload.get("entries") if isinstance(payload, dict) else payload
        if not isinstance(entries_payload, list):
            self._root_entries_cache[cache_key] = []
            return []

        entries: list[dict[str, str]] = []
        for entry in entries_payload[:40]:
            if not isinstance(entry, dict):
                continue
            path = str(entry.get("path") or entry.get("name") or "").strip()
            if not path:
                continue
            entries.append(
                {
                    "name": str(entry.get("name") or path).strip(),
                    "path": path,
                    "type": str(entry.get("type") or "").strip(),
                }
            )
        self._root_entries_cache[cache_key] = list(entries)
        return list(entries)

    def _path_contains_term(self, path: str, term: str) -> bool:
        normalized_path = safe_lower(
            path.replace("_", " ").replace("-", " ").replace("/", " ").replace(".", " ")
        )
        normalized_term = safe_lower(term)
        compact_path = normalized_path.replace(" ", "")
        compact_term = normalized_term.replace(" ", "")
        return term_in_text(normalized_path, normalized_term) or (
            bool(compact_term) and compact_term in compact_path
        )

    def _extract_root_signals(
        self,
        entries: list[dict[str, str]],
        analysis: QueryAnalysis,
        *,
        repo_title: str,
        description: str,
        readme_excerpt: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        root_paths = [entry.get("path", "") for entry in entries if entry.get("path")]
        root_dir_names = [
            entry.get("name", "")
            for entry in entries
            if entry.get("type") == "dir" and entry.get("name")
        ]
        root_file_names = [
            entry.get("name", "")
            for entry in entries
            if entry.get("type") == "file" and entry.get("name")
        ]
        root_dirs = [
            entry.get("path", "")
            for entry in entries
            if entry.get("type") == "dir" and entry.get("path")
        ]
        root_files = [
            entry.get("path", "")
            for entry in entries
            if entry.get("type") == "file" and entry.get("path")
        ]
        lowered_dirs = [safe_lower(path) for path in root_dirs]
        lowered_files = [safe_lower(path) for path in root_files]
        markdown_files = [
            path for path in root_files if safe_lower(path).endswith((".md", ".markdown", ".mdx"))
        ]
        has_readme = any(name.lower().startswith("readme") for name in root_file_names)
        course_aliases = get_course_aliases(analysis.course)
        course_specific_paths = [
            path
            for path in root_paths
            if any(self._path_contains_term(path, alias) for alias in course_aliases)
        ]
        course_mentions = find_course_mentions(" ".join(root_paths))
        has_multiple_course_dirs = len(course_mentions) >= 2
        meta_dirs = {path for path in lowered_dirs if path in {".github", "profile"}}
        meta_only_structure = bool(meta_dirs) and len(meta_dirs) == len(lowered_dirs) and not any(
            path for path in lowered_dirs if path not in {".github", "profile"}
        )
        likely_org_meta = meta_only_structure or any(
            any(hint in name for hint in ORG_META_STRUCTURE_HINTS) for name in lowered_files
        )
        likely_collection = has_multiple_course_dirs or any(
            any(hint in path for hint in COLLECTION_STRUCTURE_HINTS) for path in lowered_dirs + lowered_files
        )

        preview_metadata = dict(metadata)
        preview_metadata.update(
            {
                "root_paths": root_paths,
                "root_entries": list(entries),
                "root_dir_names": root_dir_names,
                "root_file_names": root_file_names,
                "root_dirs": root_dirs,
                "root_files": root_files,
                "root_signal": {
                    "markdown_file_count": len(markdown_files),
                    "has_readme": has_readme,
                    "has_lab_dir": any(
                        any(hint in path for hint in LAB_STRUCTURE_HINTS) for path in lowered_dirs
                    ),
                    "has_src_dir": any(path == "src" or path.endswith("/src") for path in lowered_dirs),
                    "has_report_dir": any(
                        any(hint in path for hint in REPORT_STRUCTURE_HINTS) for path in lowered_dirs + lowered_files
                    ),
                    "has_notes_dir": any(
                        any(hint in path for hint in NOTE_STRUCTURE_HINTS) for path in lowered_dirs
                    ),
                    "has_exam_dir": any(
                        any(hint in path for hint in EXAM_STRUCTURE_HINTS) for path in lowered_dirs + lowered_files
                    ),
                    "has_sql_or_schema": any(
                        any(hint in path for hint in ("sql", "schema", "models", ".sql"))
                        for path in lowered_dirs + lowered_files
                    ),
                    "has_package_or_requirements": any(
                        any(hint in path for hint in PACKAGE_REQUIREMENTS_HINTS)
                        for path in lowered_files
                    ),
                    "has_multiple_course_dirs": has_multiple_course_dirs,
                    "likely_org_meta": likely_org_meta,
                    "likely_collection": likely_collection,
                    "course_directory_count": len(course_mentions),
                    "course_specific_paths": course_specific_paths[:8],
                },
            }
        )
        classification = classify_repository(
            title=repo_title,
            description=description,
            readme_text=readme_excerpt,
            metadata=preview_metadata,
        )

        return {
            "root_dir_names": root_dir_names,
            "root_file_names": root_file_names,
            "markdown_file_count": len(markdown_files),
            "has_readme": has_readme,
            "has_lab_dir": any(any(hint in path for hint in LAB_STRUCTURE_HINTS) for path in lowered_dirs),
            "has_src_dir": any(path == "src" or path.endswith("/src") for path in lowered_dirs),
            "has_report_dir": any(
                any(hint in path for hint in REPORT_STRUCTURE_HINTS) for path in lowered_dirs + lowered_files
            ),
            "has_notes_dir": any(any(hint in path for hint in NOTE_STRUCTURE_HINTS) for path in lowered_dirs),
            "has_exam_dir": any(
                any(hint in path for hint in EXAM_STRUCTURE_HINTS) for path in lowered_dirs + lowered_files
            ),
            "has_sql_or_schema": any(
                any(hint in path for hint in ("sql", "schema", "models", ".sql"))
                for path in lowered_dirs + lowered_files
            ),
            "has_package_or_requirements": any(
                any(hint in path for hint in PACKAGE_REQUIREMENTS_HINTS)
                for path in lowered_files
            ),
            "has_multiple_course_dirs": has_multiple_course_dirs,
            "likely_org_meta": likely_org_meta or bool(classification.signals.get("likely_org_meta")),
            "likely_collection": likely_collection or bool(classification.signals.get("likely_collection")),
            "course_specific_paths": course_specific_paths[:8],
            "course_directory_count": len(course_mentions),
            "root_path_count": len(root_paths),
        }

    def _build_inspect_analysis(
        self,
        *,
        repo: str,
        result: ProviderSearchResult,
        metadata: dict[str, Any],
        readme_excerpt: str,
    ) -> QueryAnalysis:
        analysis_text = " ".join(
            part
            for part in [
                repo,
                result.title or "",
                str(metadata.get("description") or ""),
                readme_excerpt or "",
                " ".join(metadata.get("root_paths", []) or []),
                " ".join(metadata.get("root_dir_names", []) or []),
                " ".join(metadata.get("root_file_names", []) or []),
            ]
            if part
        )
        return analyze_query(analysis_text, source_types=["github"])

    def _build_detected_assets(self, metadata: dict[str, Any]) -> dict[str, bool]:
        root_signal = metadata.get("root_signal") or {}
        return {
            "has_readme": bool(root_signal.get("has_readme")),
            "has_src": bool(root_signal.get("has_src_dir")),
            "has_lab": bool(root_signal.get("has_lab_dir")),
            "has_lab_code": bool(root_signal.get("has_lab_dir") or root_signal.get("has_src_dir")),
            "has_report": bool(root_signal.get("has_report_dir")),
            "has_notes": bool(root_signal.get("has_notes_dir")),
            "has_exam": bool(root_signal.get("has_exam_dir")),
            "has_sql_or_schema": bool(root_signal.get("has_sql_or_schema")),
            "has_package_or_requirements": bool(root_signal.get("has_package_or_requirements")),
        }

    def _build_inspect_next_steps(
        self,
        *,
        repo_type: str,
        readme_excerpt: str,
        detected_assets: dict[str, bool],
        course_profile=None,
        course_specific_assets: dict[str, bool] | None = None,
    ) -> list[str]:
        steps: list[str] = []
        if readme_excerpt:
            steps.append("优先查看 README 了解项目背景和运行方式")
        course_assets = dict(course_specific_assets or {})
        if course_profile is not None:
            if course_profile.id == "database_system":
                if course_assets.get("has_sql_or_schema") or course_assets.get("has_models"):
                    steps.append("查看 sql/schema/models 理解表结构和数据库设计")
                if course_assets.get("has_er_diagram"):
                    steps.append("查看 ER 图确认实体关系")
            elif course_profile.id == "operating_system":
                if course_assets.get("has_kernel_dir") or course_assets.get("has_ucore"):
                    steps.append("优先阅读 kernel/ucore 理解实验骨架")
                if course_assets.get("has_scheduler_hint"):
                    steps.append("重点查看 scheduler 相关实现")
                if course_assets.get("has_memory_hint"):
                    steps.append("重点查看 memory/mm/paging 相关实现")
            elif course_profile.id == "compiler":
                if course_assets.get("has_lexer") or course_assets.get("has_parser"):
                    steps.append("先看 lexer/parser 入口理解编译前端")
                if course_assets.get("has_ast") or course_assets.get("has_ir") or course_assets.get("has_codegen"):
                    steps.append("再看 AST/IR/codegen 梳理编译管线")
            elif course_profile.id == "algorithms":
                if course_assets.get("has_chapter_notes"):
                    steps.append("优先按 chapter/lecture 顺序阅读笔记")
                if course_assets.get("has_dp_notes") or course_assets.get("has_graph_notes"):
                    steps.append("重点查看 dp/graph/greedy 等专题整理")
            elif course_profile.id == "machine_learning":
                if course_assets.get("has_dataset") or course_assets.get("has_notebook"):
                    steps.append("先看 dataset/notebook 理解实验输入")
                if course_assets.get("has_train_script") or course_assets.get("has_eval_script"):
                    steps.append("再看 train/eval 流程理解训练与评估")
        if detected_assets.get("has_sql_or_schema"):
            steps.append("查看 sql/ 或 schema 文件理解数据库设计")
        if detected_assets.get("has_src"):
            steps.append("查看 src/ 理解模块划分")
        if detected_assets.get("has_lab"):
            steps.append("优先阅读 lab/ 目录理解实验组织方式")
        if detected_assets.get("has_report"):
            steps.append("如有 report/，只参考结构，不复制内容")
        if detected_assets.get("has_notes"):
            steps.append("结合 notes/ 或 docs/ 梳理课程知识点结构")
        if repo_type == REPO_TYPE_ORG_META:
            steps = ["这更像组织元仓库，不建议作为主要课程项目参考"]
        if not steps:
            steps.append("先核对 README、目录结构和课程证据，再决定是否深入阅读")
        return steps[:4]

    def _build_inspect_risk_note(self, *, repo_type: str, caveat: str) -> str:
        if repo_type == REPO_TYPE_ORG_META:
            return "这是组织元信息仓库，不适合作为主要参考，仅适合了解项目入口。"
        if repo_type == "exam_solution":
            return "内容更偏试题或题解，仅适合知识点核对，不建议直接复用答案或提交。"
        return caveat or SAFETY_NOTE_TEXT

    def _build_query_analysis(self, query: str | None) -> QueryAnalysis | None:
        query_text = (query or "").strip()
        if not query_text:
            return None
        return analyze_query(query_text, source_types=["github"])

    def _fit_for_query(
        self,
        *,
        query_analysis: QueryAnalysis | None,
        explain,
        repo_type: str,
    ) -> str:
        if query_analysis is None:
            return "unknown"
        if repo_type == REPO_TYPE_ORG_META:
            return "low"

        query_intent = classify_query_intent(query_analysis)
        intent_match = query_intent == "generic" or explain.matched_intent == query_intent
        school_match = not query_analysis.school or explain.school_match_strength in {"strong", "weak"}
        course_match = not query_analysis.course or bool(explain.matched_course)
        score = explain.final_score

        if score >= 0.78 and intent_match and school_match and course_match:
            return "high"
        if score >= 0.55 and (intent_match or school_match or course_match):
            return "medium"
        return "low"

    def _describe_structures(self, detected_assets: dict[str, bool]) -> list[str]:
        structures: list[str] = []
        if detected_assets.get("has_src"):
            structures.append("src")
        if detected_assets.get("has_lab"):
            structures.append("lab")
        if detected_assets.get("has_sql_or_schema"):
            structures.append("sql/schema")
        if detected_assets.get("has_report"):
            structures.append("report")
        if detected_assets.get("has_notes"):
            structures.append("notes/docs")
        return structures

    def _build_task_fit_reason(
        self,
        *,
        query_analysis: QueryAnalysis | None,
        fit_for_query: str,
        repo_type: str,
        detected_assets: dict[str, bool],
        explain,
    ) -> str:
        if query_analysis is None:
            return "未提供 query，上下文适配度未知；以下判断基于仓库自身的课程与结构证据。"

        matched_parts: list[str] = []
        if query_analysis.school and explain.school_match_strength in {"strong", "weak"}:
            matched_parts.append(query_analysis.school)
        if query_analysis.course and explain.matched_course:
            matched_parts.append(query_analysis.course)
        query_intent = classify_query_intent(query_analysis)
        if query_intent != "generic" and explain.matched_intent == query_intent:
            intent_label = {
                "project": "大作业/课程项目",
                "lab": "实验",
                "notes": "笔记",
                "exam": "题解/试题",
                "collection": "资料合集",
            }.get(query_intent, query_intent)
            matched_parts.append(intent_label)

        structure_text = "、".join(self._describe_structures(detected_assets))
        matched_text = "、".join(matched_parts) if matched_parts else "当前 query"

        if fit_for_query == "high":
            if structure_text:
                return (
                    f"该仓库明确命中 {matched_text}，并包含 {structure_text} 结构，"
                    "适合作为当前任务的公开参考。"
                )
            return f"该仓库明确命中 {matched_text}，适合作为当前任务的公开参考。"
        if fit_for_query == "medium":
            if structure_text:
                return (
                    f"该仓库与 {matched_text} 部分匹配，且包含 {structure_text} 结构，"
                    "适合交叉参考，但不宜作为唯一来源。"
                )
            return f"该仓库与 {matched_text} 部分匹配，可作辅助参考，但需要结合其他仓库交叉验证。"

        repo_label = {
            "org_meta": "组织元仓库",
            "collection": "资料合集",
            "exam_solution": "题解/答案仓库",
            "generic_algorithm": "通用算法仓库",
        }.get(repo_type, "当前仓库")
        if structure_text:
            return (
                f"该仓库与 {matched_text} 匹配较弱，更像 {repo_label}，"
                f"虽然包含 {structure_text} 等结构线索，但不建议作为当前任务的主要参考。"
            )
        return f"该仓库与 {matched_text} 匹配较弱，更像 {repo_label}，不建议作为当前任务的主要参考。"

    def _build_suggested_usage(
        self,
        *,
        repo_type: str,
        detected_assets: dict[str, bool],
        readme_excerpt: str,
        course_profile=None,
        course_specific_assets: dict[str, bool] | None = None,
    ) -> list[str]:
        usage: list[str] = []
        course_assets = dict(course_specific_assets or {})
        if course_profile is not None:
            if course_profile.id == "database_system":
                if course_assets.get("has_sql_or_schema"):
                    usage.append("参考 sql/schema 理解数据库表设计")
                if course_assets.get("has_models"):
                    usage.append("参考 models 和 migrations 理解实体映射")
                if course_assets.get("has_er_diagram"):
                    usage.append("参考 ER 图理解关系设计")
            elif course_profile.id == "operating_system":
                if course_assets.get("has_kernel_dir") or course_assets.get("has_ucore"):
                    usage.append("参考 kernel/ucore 的实验骨架")
                if course_assets.get("has_scheduler_hint"):
                    usage.append("参考 scheduler 的模块拆分")
                if course_assets.get("has_memory_hint"):
                    usage.append("参考内存管理实现路径")
            elif course_profile.id == "compiler":
                if course_assets.get("has_lexer"):
                    usage.append("参考 lexer 的 token 化流程")
                if course_assets.get("has_parser"):
                    usage.append("参考 parser 的语法分析流程")
                if course_assets.get("has_ast") or course_assets.get("has_ir"):
                    usage.append("参考 AST/IR 的中间表示组织")
            elif course_profile.id == "algorithms":
                if course_assets.get("has_chapter_notes"):
                    usage.append("参考章节化笔记结构")
                if course_assets.get("has_dp_notes") or course_assets.get("has_graph_notes"):
                    usage.append("参考 dp/graph 专题整理方式")
                if course_assets.get("has_complexity_notes"):
                    usage.append("参考复杂度分析写法")
            elif course_profile.id == "machine_learning":
                if course_assets.get("has_dataset"):
                    usage.append("参考数据处理与 dataset 组织")
                if course_assets.get("has_train_script"):
                    usage.append("参考 train 流程与实验参数组织")
                if course_assets.get("has_eval_script"):
                    usage.append("参考 eval 流程与指标评估")
        if repo_type == "course_project":
            usage.append("参考项目选题和模块划分")
        if detected_assets.get("has_lab"):
            usage.append("参考实验步骤和目录组织方式")
        if detected_assets.get("has_src"):
            usage.append("参考代码结构和模块边界")
        if detected_assets.get("has_sql_or_schema"):
            usage.append("参考 sql/schema 了解数据库设计")
        if readme_excerpt:
            usage.append("参考 README 的运行说明")
        if detected_assets.get("has_report"):
            usage.append("报告部分只参考结构，不复制内容")
        if detected_assets.get("has_notes"):
            usage.append("参考 notes/docs 梳理知识点和实验说明")
        if repo_type == "collection":
            usage.append("把它当作扩展检索入口，而不是单一项目模板")
        if repo_type == REPO_TYPE_ORG_META:
            usage = ["仅用于定位组织入口或关联仓库，不作为具体项目参考"]
        return usage[:4]

    def _build_not_suitable_for(
        self,
        *,
        repo_type: str,
        fit_for_query: str,
    ) -> list[str]:
        limitations = [
            "不适合直接复用代码提交",
            "不适合作为唯一参考来源",
        ]
        if repo_type == REPO_TYPE_ORG_META:
            limitations.insert(0, "不适合作为具体课程项目或实验主参考")
        if repo_type == "collection":
            limitations.insert(0, "不适合作为单一项目实现模板")
        if repo_type == "report_only":
            limitations.insert(0, "不适合作为完整代码结构参考")
        if repo_type == "exam_solution":
            limitations.insert(0, "不适合直接套用题解、答案或报告")
        if repo_type == "generic_algorithm":
            limitations.insert(0, "不适合作为特定学校课程项目直接参考")
        if fit_for_query == "low":
            limitations.insert(0, "不适合作为当前 query 的主要参考对象")
        deduped: list[str] = []
        seen: set[str] = set()
        for item in limitations:
            if item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped[:4]

    def _build_risk_level(
        self,
        *,
        repo_type: str,
        fit_for_query: str,
    ) -> str:
        if repo_type in {REPO_TYPE_ORG_META, "exam_solution", "generic_algorithm"}:
            return "high"
        if fit_for_query == "low":
            return "high"
        if repo_type == "notes":
            return "low"
        if repo_type == "collection" and fit_for_query != "high":
            return "high"
        return "medium"

    def _summarize_root_entries(self, entries: list[dict[str, str]]) -> str:
        if not entries:
            return ""
        picked: list[str] = []
        for entry in entries:
            path = entry.get("path") or entry.get("name") or ""
            if not path:
                continue
            if entry.get("type") == "dir" and not path.endswith("/"):
                path = f"{path}/"
            picked.append(path)
            if len(picked) >= 6:
                break
        return ", ".join(picked)

    async def _enrich_results_with_context(
        self,
        results: list[ProviderSearchResult],
        *,
        analysis: QueryAnalysis,
        limit: int,
    ) -> list[ProviderSearchResult]:
        async def enrich(result: ProviderSearchResult) -> ProviderSearchResult:
            metadata = dict(result.metadata or {})
            full_name = str(metadata.get("full_name") or "")
            if not full_name or "/" not in full_name:
                return result

            owner, repo = full_name.split("/", 1)
            readme_excerpt, root_entries = await asyncio.gather(
                self._fetch_readme_excerpt(owner, repo),
                self._fetch_root_entries(owner, repo),
            )
            cache_key = self._repo_key(owner, repo)
            readme_failed = self._readme_error_cache.get(cache_key, False)
            root_failed = self._root_entries_error_cache.get(cache_key, False)

            metadata["readme_excerpt"] = readme_excerpt or ""
            metadata["readme_text"] = readme_excerpt or ""
            metadata["readme_summary"] = truncate_text((readme_excerpt or "").replace("\n", " ").strip(), 480)
            metadata["root_entries"] = list(root_entries)
            metadata["root_paths"] = [entry["path"] for entry in root_entries if entry.get("path")]
            metadata["root_dirs"] = [
                entry["path"]
                for entry in root_entries
                if entry.get("type") == "dir" and entry.get("path")
            ]
            metadata["root_files"] = [
                entry["path"]
                for entry in root_entries
                if entry.get("type") == "file" and entry.get("path")
            ]
            metadata["root_dir_names"] = [
                entry["name"]
                for entry in root_entries
                if entry.get("type") == "dir" and entry.get("name")
            ]
            metadata["root_file_names"] = [
                entry["name"]
                for entry in root_entries
                if entry.get("type") == "file" and entry.get("name")
            ]

            root_signal = self._extract_root_signals(
                root_entries,
                analysis,
                repo_title=result.title,
                description=str(metadata.get("description") or ""),
                readme_excerpt=readme_excerpt,
                metadata=metadata,
            )
            metadata["root_signal"] = root_signal
            metadata["root_markdown_count"] = root_signal["markdown_file_count"]
            metadata["root_course_specific_paths"] = root_signal["course_specific_paths"]
            metadata["root_course_directory_count"] = root_signal["course_directory_count"]
            metadata["enrichment_failed"] = bool(readme_failed or root_failed)
            if metadata["enrichment_failed"]:
                metadata["enrichment_error"] = {
                    "readme_failed": readme_failed,
                    "root_entries_failed": root_failed,
                }

            snippet_parts = [result.snippet]
            if readme_excerpt:
                snippet_parts.append(f"README: {truncate_text(readme_excerpt, 360)}")
            root_summary = self._summarize_root_entries(root_entries)
            if root_summary:
                snippet_parts.append(f"ROOT: {root_summary}")
            if metadata["enrichment_failed"]:
                snippet_parts.append("ENRICHMENT_FAILED")
            result.metadata = metadata
            result.snippet = truncate_text(" | ".join(part for part in snippet_parts if part), 1400)
            return result

        if limit <= 0 or not results:
            return results
        head = results[:limit]
        tail = results[limit:]
        enriched_head = await asyncio.gather(*(enrich(result) for result in head))
        return [*enriched_head, *tail]

    def _rerank_results(
        self,
        analysis: QueryAnalysis,
        results: list[ProviderSearchResult],
    ) -> list[ProviderSearchResult]:
        ranked: list[tuple[float, int, ProviderSearchResult]] = []
        for index, result in enumerate(results):
            score, _ = score_provider_result(analysis, result)
            ranked.append((score, index, result))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [result for _, _, result in ranked]

    def _diversify_by_owner(
        self,
        results: list[ProviderSearchResult],
        *,
        top_k: int,
    ) -> list[ProviderSearchResult]:
        if len(results) <= 1:
            return results

        selected: list[ProviderSearchResult] = []
        overflow: list[ProviderSearchResult] = []
        seen_owners: set[str] = set()

        for result in results:
            owner = str((result.metadata or {}).get("owner") or "").lower()
            if owner and owner in seen_owners:
                overflow.append(result)
                continue
            selected.append(result)
            if owner:
                seen_owners.add(owner)
            if len(selected) >= top_k:
                return selected

        for result in overflow:
            selected.append(result)
            if len(selected) >= top_k:
                break
        return selected

    async def search(
        self,
        analysis: QueryAnalysis,
        *,
        top_k: int = 5,
        allow_domains: Optional[list[str]] = None,
        deny_domains: Optional[list[str]] = None,
    ) -> List[ProviderSearchResult]:
        if not self.settings.enable_github:
            return []

        planner_hints = dict(analysis.planner_hints or {})
        candidate_target = int(planner_hints.get("github_candidate_target") or min(50, max(top_k * 5, 15)))
        candidate_target = max(top_k, min(50, candidate_target))
        per_query = int(planner_hints.get("github_per_query") or min(12, max(top_k * 2, 6)))
        per_query = max(1, min(12, per_query))
        query_limit = int(planner_hints.get("github_query_limit") or 20)
        query_limit = max(1, min(20, query_limit))
        search_queries = build_github_search_queries(analysis)[:query_limit]
        items: list[dict[str, Any]] = []
        seen_items: set[str] = set()

        for search_query in search_queries:
            try:
                query_items = await self._search_repositories(search_query, per_page=per_query)
            except Exception as exc:
                logger.warning("GitHub search failed for query %r: %s", search_query, exc)
                continue
            for repo in query_items:
                key = (repo.get("full_name") or repo.get("html_url") or repo.get("url") or "").lower()
                if not key or key in seen_items:
                    continue
                seen_items.add(key)
                items.append(repo)
            if len(items) >= candidate_target:
                break

        results: List[ProviderSearchResult] = []
        for repo in items:
            result = self._repo_to_result(repo)
            if not result.url:
                continue
            if not self._domain_allowed(result.url, allow_domains, deny_domains):
                continue
            results.append(result)

        should_enrich = bool(
            analysis.school
            or analysis.course
            or analysis.project_keywords
            or analysis.resource_keywords
            or analysis.tech_keywords
        )
        if should_enrich:
            results = await self._enrich_results_with_context(
                results,
                analysis=analysis,
                limit=min(len(results), max(top_k + 3, 6)),
            )

        results = self._rerank_results(analysis, results)
        if classify_query_intent(analysis) not in {"collection"} and not any(
            term in safe_lower(analysis.raw_query or "") for term in (".github", "profile", "组织主页", "community health")
        ):
            non_meta: list[ProviderSearchResult] = []
            org_meta: list[ProviderSearchResult] = []
            for result in results:
                if explain_score(analysis, result).repo_type == REPO_TYPE_ORG_META:
                    org_meta.append(result)
                else:
                    non_meta.append(result)
            if non_meta:
                results = [*non_meta, *org_meta]
        results = self._diversify_by_owner(results, top_k=top_k)
        return results[:top_k]

    async def get_project_brief(self, url: str) -> ProviderSearchResult | None:
        parsed = urlparse(url)
        if "github.com" not in parsed.netloc.lower():
            return None
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            return None
        owner, repo = parts[0], parts[1]
        payload = await self._fetch_repository(owner, repo)
        if payload is None:
            return None

        result = self._repo_to_result(payload)
        readme_excerpt = await self._fetch_readme_excerpt(owner, repo)
        if readme_excerpt:
            result.metadata["readme_excerpt"] = readme_excerpt
            result.metadata["readme_text"] = readme_excerpt
            result.metadata["readme_summary"] = truncate_text(readme_excerpt.replace("\n", " ").strip(), 480)
            result.snippet = truncate_text(f"{result.snippet} | README: {readme_excerpt}", 1200)
        return result

    async def inspect_repository(
        self,
        repo: str,
        *,
        query: str | None = None,
        include_readme: bool = True,
        include_tree: bool = True,
    ) -> InspectCourseProjectOutput:
        if "/" not in repo:
            return InspectCourseProjectOutput(
                repo=repo,
                source_provider=self.name,
                error="`repo` must be in `owner/name` form.",
                fit_for_query="unknown",
                task_fit_reason="仓库标识不合法，无法判断任务匹配度。",
                not_suitable_for=["不适合作为当前任务的主要参考对象"],
                risk_level="high",
            )

        owner, name = repo.split("/", 1)
        payload = await self._fetch_repository(owner, name)
        if payload is None:
            return InspectCourseProjectOutput(
                repo=repo,
                url=f"https://github.com/{repo}",
                source_provider=self.name,
                error=f"Failed to fetch GitHub repository `{repo}`.",
                fit_for_query="unknown",
                task_fit_reason="仓库获取失败，无法判断任务匹配度。",
                not_suitable_for=["不适合作为当前任务的主要参考对象"],
                risk_level="high",
            )

        result = self._repo_to_result(payload)
        readme_excerpt = ""
        root_entries: list[dict[str, str]] = []
        if include_readme or include_tree:
            fetches = []
            if include_readme:
                fetches.append(self._fetch_readme_excerpt(owner, name))
            if include_tree:
                fetches.append(self._fetch_root_entries(owner, name))
            fetched = await asyncio.gather(*fetches)
            cursor = 0
            if include_readme:
                readme_excerpt = fetched[cursor] or ""
                cursor += 1
            if include_tree:
                root_entries = fetched[cursor] or []

        cache_key = self._repo_key(owner, name)
        metadata = dict(result.metadata or {})
        query_analysis = self._build_query_analysis(query)
        metadata["readme_excerpt"] = readme_excerpt or ""
        metadata["readme_text"] = readme_excerpt or ""
        metadata["readme_summary"] = (
            truncate_text(readme_excerpt.replace("\n", " ").strip(), 480) if readme_excerpt else None
        )
        metadata["root_entries"] = list(root_entries)
        if root_entries:
            root_signal = self._extract_root_signals(
                root_entries,
                query_analysis or QueryAnalysis(raw_query=repo),
                repo_title=result.title,
                description=str(metadata.get("description") or ""),
                readme_excerpt=readme_excerpt,
                metadata=metadata,
            )
            metadata["root_signal"] = root_signal
            metadata["root_paths"] = [entry["path"] for entry in root_entries if entry.get("path")]
            metadata["root_dir_names"] = root_signal["root_dir_names"]
            metadata["root_file_names"] = root_signal["root_file_names"]
            metadata["root_dirs"] = [
                entry["path"]
                for entry in root_entries
                if entry.get("type") == "dir" and entry.get("path")
            ]
            metadata["root_files"] = [
                entry["path"]
                for entry in root_entries
                if entry.get("type") == "file" and entry.get("path")
            ]
        metadata["enrichment_failed"] = bool(
            self._readme_error_cache.get(cache_key, False)
            or self._root_entries_error_cache.get(cache_key, False)
        )
        if metadata["enrichment_failed"]:
            metadata["enrichment_error"] = {
                "readme_failed": self._readme_error_cache.get(cache_key, False),
                "root_entries_failed": self._root_entries_error_cache.get(cache_key, False),
            }

        result.metadata = metadata
        classification = classify_repository(
            title=result.title,
            description=str(metadata.get("description") or ""),
            readme_text=readme_excerpt,
            metadata=metadata,
        )
        repo_analysis = self._build_inspect_analysis(
            repo=repo,
            result=result,
            metadata=metadata,
            readme_excerpt=readme_excerpt,
        )
        scoring_analysis = query_analysis or repo_analysis
        repo_explain = explain_score(repo_analysis, result)
        explain = explain_score(scoring_analysis, result)
        course_profile = get_course_profile(
            (query_analysis.course_profile_id if query_analysis is not None else None)
            or repo_analysis.course_profile_id
            or repo_explain.matched_course
            or explain.matched_course
        )

        root_tree: list[str] = []
        if include_tree:
            for entry in root_entries[:20]:
                path = entry.get("path") or entry.get("name") or ""
                if not path:
                    continue
                if entry.get("type") == "dir" and not path.endswith("/"):
                    path = f"{path}/"
                root_tree.append(path)

        detected_assets = self._build_detected_assets(metadata)
        course_specific_assets = detect_course_specific_assets(
            course_profile,
            title=result.title,
            description=str(metadata.get("description") or ""),
            readme_text=readme_excerpt,
            root_paths=metadata.get("root_paths") or [],
            root_dir_names=metadata.get("root_dir_names") or [],
            root_file_names=metadata.get("root_file_names") or [],
            root_signal=metadata.get("root_signal") or {},
        )
        fit_for_query = self._fit_for_query(
            query_analysis=query_analysis,
            explain=explain,
            repo_type=classification.repo_type,
        )
        suggested_next_steps = self._build_inspect_next_steps(
            repo_type=classification.repo_type,
            readme_excerpt=readme_excerpt,
            detected_assets=detected_assets,
            course_profile=course_profile,
            course_specific_assets=course_specific_assets,
        )
        risk_note = self._build_inspect_risk_note(
            repo_type=classification.repo_type,
            caveat=explain.caveat,
        )
        suggested_usage = self._build_suggested_usage(
            repo_type=classification.repo_type,
            detected_assets=detected_assets,
            readme_excerpt=readme_excerpt,
            course_profile=course_profile,
            course_specific_assets=course_specific_assets,
        )
        not_suitable_for = self._build_not_suitable_for(
            repo_type=classification.repo_type,
            fit_for_query=fit_for_query,
        )
        risk_level = self._build_risk_level(
            repo_type=classification.repo_type,
            fit_for_query=fit_for_query,
        )
        task_fit_reason = self._build_task_fit_reason(
            query_analysis=query_analysis,
            fit_for_query=fit_for_query,
            repo_type=classification.repo_type,
            detected_assets=detected_assets,
            explain=explain,
        )

        return InspectCourseProjectOutput(
            repo=repo,
            url=result.url,
            source_provider=self.name,
            repo_type=classification.repo_type,
            school=repo_explain.detected_school,
            school_id=repo_explain.detected_school_id,
            course=repo_explain.matched_course or repo_analysis.course,
            course_profile_id=course_profile.id if course_profile is not None else None,
            intent=repo_explain.matched_intent
            or (repo_explain.candidate_intents[0] if repo_explain.candidate_intents else None),
            score=explain.final_score,
            value_level=explain.value_level,
            confidence_level=explain.confidence,
            fit_for_query=fit_for_query,
            task_fit_reason=task_fit_reason,
            not_suitable_for=not_suitable_for,
            suggested_usage=suggested_usage,
            risk_level=risk_level,
            language=(metadata.get("languages") or [None])[0],
            updated_at=metadata.get("updated_at"),
            stars=metadata.get("stargazers_count"),
            readme_summary=metadata.get("readme_summary"),
            root_tree=root_tree,
            detected_assets=detected_assets,
            course_specific_assets=course_specific_assets,
            reference_utility=explain.reference_utility[:4],
            risk_note=risk_note,
            suggested_next_steps=suggested_next_steps,
            reference_suggestions=suggested_next_steps,
            safety_note=SAFETY_NOTE_TEXT,
            why_recommended=explain.why_recommended or None,
            positive_evidence=explain.positive_evidence[:5],
            negative_evidence=explain.negative_evidence[:3],
            debug={
                "score": explain.final_score,
                "analysis": scoring_analysis.model_dump(),
                "repo_analysis": repo_analysis.model_dump(),
                "query": query,
                "repo_type_signals": classification.signals,
                "enrichment_failed": bool(metadata.get("enrichment_failed")),
            },
        )
