from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.core.vocabulary import find_course_mentions, find_school_mentions, term_in_text
from app.schemas import ProviderSearchResult
from app.utils.text import safe_lower


REPO_TYPE_LAB_CODE = "lab_code"
REPO_TYPE_COURSE_PROJECT = "course_project"
REPO_TYPE_REPORT_ONLY = "report_only"
REPO_TYPE_NOTES = "notes"
REPO_TYPE_EXAM_SOLUTION = "exam_solution"
REPO_TYPE_COLLECTION = "collection"
REPO_TYPE_ORG_META = "org_meta"
REPO_TYPE_GENERIC_ALGORITHM = "generic_algorithm"
REPO_TYPE_UNKNOWN = "unknown"

REPO_TYPE_PRIORITY = [
    REPO_TYPE_LAB_CODE,
    REPO_TYPE_COURSE_PROJECT,
    REPO_TYPE_NOTES,
    REPO_TYPE_REPORT_ONLY,
    REPO_TYPE_EXAM_SOLUTION,
    REPO_TYPE_COLLECTION,
    REPO_TYPE_GENERIC_ALGORITHM,
    REPO_TYPE_UNKNOWN,
]

LAB_TERMS = [
    "lab",
    "labs",
    "experiment",
    "experiments",
    "实验",
    "kernel",
    "ucore",
    "oslab",
    "os lab",
]
PROJECT_TERMS = [
    "course project",
    "project",
    "final project",
    "term project",
    "final assignment",
    "final-assignment",
    "assignment project",
    "大作业",
    "课程设计",
    "课程项目",
]
REPORT_TERMS = ["report", "reports", "报告", ".pdf", ".doc", ".docx"]
NOTES_TERMS = [
    "notes",
    "note",
    "lecture",
    "lectures",
    "lecture notes",
    "笔记",
    "docs",
    "markdown",
]
EXAM_TERMS = ["exam", "exams", "midterm", "final exam", "final", "quiz", "期末", "期中", "真题", "试题"]
SOLUTION_TERMS = ["answer", "answers", "solution", "solutions", "答案", "题解", "解答"]
COLLECTION_TERMS = [
    "408",
    "collection",
    "collections",
    "resources",
    "resource",
    "awesome",
    "archive",
    "archives",
    "courses",
    "course materials",
    "course resources",
    "课程资料",
    "课程资源",
    "资料合集",
    "多门课程",
    "合集",
    "汇总",
    "nku-courses",
    "408 资料",
]
GENERIC_ALGORITHM_TERMS = [
    "algorithm",
    "algorithms",
    "data structure",
    "data structures",
    "leetcode",
    "oj",
]
ORG_META_TERMS = [
    ".github",
    "profile",
    "organization profile",
    "github profile",
    "community health",
]
CODE_HINT_DIRS = ["src", "code", "kernel", "ucore", "labs", "lab", "project", "projects"]
DOC_HINT_DIRS = ["docs", "doc", "notes", "lecture", "lectures", "report", "reports"]
CODE_EXTENSIONS = (".c", ".h", ".cpp", ".hpp", ".py", ".rs", ".go", ".java", ".ts", ".js", ".sql")
DOC_EXTENSIONS = (".md", ".markdown", ".mdx", ".pdf", ".doc", ".docx")
CODE_LANGUAGES = {"c", "c++", "cpp", "rust", "go", "java", "python", "typescript", "javascript"}


@dataclass
class RepoClassification:
    repo_type: str
    positive_evidence: list[str] = field(default_factory=list)
    negative_evidence: list[str] = field(default_factory=list)
    signals: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _identifier_variant(text: str) -> str:
    return safe_lower(
        (text or "")
        .replace("_", " ")
        .replace("-", " ")
        .replace("/", " ")
        .replace(".", " ")
    )


def _metadata_values(metadata: dict[str, Any], key: str) -> list[str]:
    value = metadata.get(key)
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if value:
        return [str(value)]
    return []


def _root_signal(metadata: dict[str, Any]) -> dict[str, Any]:
    signal = metadata.get("root_signal")
    if isinstance(signal, dict):
        return signal
    return {}


def _repo_name(title: str, metadata: dict[str, Any]) -> str:
    full_name = str(metadata.get("full_name") or "")
    source = full_name or title
    if "/" in source:
        return source.rsplit("/", 1)[-1]
    return source


def _count_hits(text: str, terms: list[str]) -> int:
    return sum(1 for term in terms if term_in_text(text, term))


def _has_any(text: str, terms: list[str]) -> bool:
    return any(term_in_text(text, term) for term in terms)


def _collect_root_names(metadata: dict[str, Any], key: str) -> list[str]:
    values = _metadata_values(metadata, key)
    if values:
        return values
    signal = _root_signal(metadata)
    fallback = signal.get(key)
    if isinstance(fallback, list):
        return [str(item) for item in fallback if item]
    return []


def _infer_has_code_structure(root_dirs: list[str], root_files: list[str]) -> bool:
    lowered_dirs = [_identifier_variant(path) for path in root_dirs]
    lowered_files = [safe_lower(path) for path in root_files]
    if any(any(term_in_text(path, hint) for hint in CODE_HINT_DIRS) for path in lowered_dirs):
        return True
    return any(path.endswith(CODE_EXTENSIONS) for path in lowered_files)


def _infer_document_count(root_files: list[str]) -> int:
    return sum(1 for name in root_files if safe_lower(name).endswith(DOC_EXTENSIONS))


def classify_repository(
    *,
    title: str,
    description: str = "",
    readme_text: str = "",
    metadata: dict[str, Any] | None = None,
) -> RepoClassification:
    metadata = dict(metadata or {})
    signal = _root_signal(metadata)
    root_dir_names = _collect_root_names(metadata, "root_dir_names") or _collect_root_names(metadata, "root_dirs")
    root_file_names = _collect_root_names(metadata, "root_file_names") or _collect_root_names(metadata, "root_files")
    root_paths = _metadata_values(metadata, "root_paths")
    topics = _metadata_values(metadata, "topics")
    languages = [safe_lower(language) for language in _metadata_values(metadata, "languages")]

    repo_name = _repo_name(title, metadata)
    repo_name_variant = _identifier_variant(repo_name)
    full_name = str(metadata.get("full_name") or title or "")
    description = description or str(metadata.get("description") or "")
    readme_text = readme_text or str(metadata.get("readme_excerpt") or "")

    base_text = safe_lower(
        " ".join(
            [
                title,
                description,
                repo_name,
                repo_name_variant,
                " ".join(root_paths),
                " ".join(root_dir_names),
                " ".join(root_file_names),
                " ".join(topics),
                " ".join(languages),
            ]
        )
    )
    readme_lower = safe_lower(readme_text)
    combined = safe_lower(f"{base_text} {readme_lower}")
    root_text = safe_lower(" ".join([*root_paths, *root_dir_names, *root_file_names]))

    school_mentions = find_school_mentions(combined)
    course_mentions = find_course_mentions(combined)
    markdown_count = int(signal.get("markdown_file_count") or 0)
    if not markdown_count:
        markdown_count = sum(
            1 for name in root_file_names if safe_lower(name).endswith((".md", ".markdown", ".mdx"))
        )
    has_readme = bool(signal.get("has_readme")) or any(
        safe_lower(name).startswith("readme") for name in root_file_names
    )
    has_lab_dir = bool(signal.get("has_lab_dir")) or _has_any(root_text, ["lab", "labs", "experiment", "实验"])
    has_src_dir = bool(signal.get("has_src_dir")) or _has_any(root_text, ["src"])
    has_report_dir = bool(signal.get("has_report_dir")) or _has_any(root_text, ["report", "报告", "pdf", "docx"])
    has_notes_dir = bool(signal.get("has_notes_dir")) or _has_any(root_text, ["notes", "docs", "lecture", "笔记"])
    has_exam_dir = bool(signal.get("has_exam_dir")) or _has_any(root_text, ["exam", "quiz", "试题", "真题", "408"])
    has_multiple_course_dirs = bool(signal.get("has_multiple_course_dirs")) or int(
        signal.get("course_directory_count") or 0
    ) >= 2 or len(course_mentions) >= 2
    likely_org_meta = bool(signal.get("likely_org_meta"))
    likely_collection = bool(signal.get("likely_collection")) or has_multiple_course_dirs
    document_count = _infer_document_count(root_file_names)
    code_language = any(language in CODE_LANGUAGES for language in languages)
    code_like_dirs = [
        name
        for name in root_dir_names
        if not _has_any(_identifier_variant(name), [*DOC_HINT_DIRS, ".github", "profile"])
    ]
    code_structure = (
        _infer_has_code_structure(root_dir_names, root_file_names)
        or has_lab_dir
        or has_src_dir
        or bool(code_like_dirs and (code_language or any(safe_lower(name).endswith(CODE_EXTENSIONS) for name in root_file_names)))
    )
    exam_term_hits = _count_hits(combined, EXAM_TERMS)
    solution_term_hits = _count_hits(combined, SOLUTION_TERMS)
    notes_term_hits = _count_hits(base_text, NOTES_TERMS)
    notes_readme_hits = _count_hits(readme_lower, NOTES_TERMS)
    report_term_hits = _count_hits(combined, REPORT_TERMS)
    lab_term_hits = _count_hits(combined, LAB_TERMS)
    project_term_hits = _count_hits(combined, PROJECT_TERMS)
    collection_term_hits = _count_hits(combined, COLLECTION_TERMS)
    generic_algorithm_hits = _count_hits(f"{repo_name_variant} {combined}", GENERIC_ALGORITHM_TERMS)
    strong_school_or_course = bool(school_mentions or course_mentions)

    org_meta_text = safe_lower(" ".join([title, full_name, description, repo_name, repo_name_variant, " ".join(topics)]))
    meta_only_structure = bool(root_dir_names) and all(
        safe_lower(name) in {".github", "profile"} for name in root_dir_names
    )

    if (
        repo_name == ".github"
        or full_name.endswith("/.github")
        or repo_name_variant == "profile"
        or likely_org_meta
        or meta_only_structure
        or _has_any(org_meta_text, ORG_META_TERMS)
    ):
        positive = ["repo appears to be organization profile or .github metadata"]
        if repo_name == ".github":
            positive.append("repo name is .github")
        if _has_any(root_text, [".github", "profile"]):
            positive.append("root contains .github/profile metadata structure")
        return RepoClassification(
            repo_type=REPO_TYPE_ORG_META,
            positive_evidence=positive[:4],
            negative_evidence=[],
            signals={
                "repo_name": repo_name,
                "root_dir_names": root_dir_names,
                "root_file_names": root_file_names,
                "markdown_file_count": markdown_count,
                "has_readme": has_readme,
                "has_lab_dir": has_lab_dir,
                "has_src_dir": has_src_dir,
                "has_report_dir": has_report_dir,
                "has_notes_dir": has_notes_dir,
                "has_exam_dir": has_exam_dir,
                "has_multiple_course_dirs": has_multiple_course_dirs,
                "likely_org_meta": True,
                "likely_collection": likely_collection,
                "school_mentions": school_mentions,
                "course_mentions": course_mentions,
                "code_structure": code_structure,
                "code_language": code_language,
            },
        )

    scores = {
        REPO_TYPE_LAB_CODE: 0,
        REPO_TYPE_COURSE_PROJECT: 0,
        REPO_TYPE_NOTES: 0,
        REPO_TYPE_REPORT_ONLY: 0,
        REPO_TYPE_EXAM_SOLUTION: 0,
        REPO_TYPE_COLLECTION: 0,
        REPO_TYPE_GENERIC_ALGORITHM: 0,
    }
    reasons: dict[str, list[str]] = {key: [] for key in scores}

    def bump(repo_type: str, amount: int, reason: str) -> None:
        scores[repo_type] += amount
        if reason not in reasons[repo_type]:
            reasons[repo_type].append(reason)

    if lab_term_hits:
        bump(REPO_TYPE_LAB_CODE, 3, "name/description/readme mentions lab or experiment")
    if has_lab_dir:
        bump(REPO_TYPE_LAB_CODE, 3, "root contains lab directory")
    if has_src_dir:
        bump(REPO_TYPE_LAB_CODE, 2, "root contains src directory")
    if _has_any(combined, ["kernel", "ucore"]):
        bump(REPO_TYPE_LAB_CODE, 2, "OS-style kernel or ucore structure detected")
    if code_language:
        bump(REPO_TYPE_LAB_CODE, 1, "primary language suggests executable code")

    if project_term_hits:
        bump(REPO_TYPE_COURSE_PROJECT, 3, "name/description/readme mentions course project")
    if _has_any(combined, ["final assignment", "final-assignment", "大作业", "课程设计"]):
        bump(REPO_TYPE_COURSE_PROJECT, 2, "final assignment wording detected")
    if has_src_dir:
        bump(REPO_TYPE_COURSE_PROJECT, 1, "project-like src structure detected")
    if has_report_dir:
        bump(REPO_TYPE_COURSE_PROJECT, 1, "project/report mixed structure detected")
    if code_structure and has_report_dir:
        bump(REPO_TYPE_COURSE_PROJECT, 1, "code and report coexist")

    if notes_term_hits:
        bump(REPO_TYPE_NOTES, 3, "notes or lecture wording detected")
    elif notes_readme_hits:
        bump(REPO_TYPE_NOTES, 1, "README mentions notes or lecture wording")
    if has_notes_dir:
        bump(REPO_TYPE_NOTES, 2, "root contains notes/docs directory")
    if markdown_count >= 2:
        bump(REPO_TYPE_NOTES, 1, "multiple markdown files detected")

    if report_term_hits:
        bump(REPO_TYPE_REPORT_ONLY, 3, "report-oriented files or wording detected")
    if document_count >= 2:
        bump(REPO_TYPE_REPORT_ONLY, 1, "multiple document files detected")
    if not code_structure and (has_report_dir or report_term_hits):
        bump(REPO_TYPE_REPORT_ONLY, 2, "documentation dominates over code structure")

    if exam_term_hits:
        bump(REPO_TYPE_EXAM_SOLUTION, 3, "exam-like wording detected")
    if solution_term_hits:
        bump(REPO_TYPE_EXAM_SOLUTION, 2, "answer/solution wording detected")
    if has_exam_dir:
        bump(REPO_TYPE_EXAM_SOLUTION, 2, "root contains exam directory")

    if collection_term_hits:
        bump(REPO_TYPE_COLLECTION, 3, "collection/resource wording detected")
    if has_multiple_course_dirs:
        bump(REPO_TYPE_COLLECTION, 2, "multiple course directories detected")
    if likely_collection:
        bump(REPO_TYPE_COLLECTION, 1, "repository looks like a multi-course collection")

    if generic_algorithm_hits:
        bump(REPO_TYPE_GENERIC_ALGORITHM, 3, "generic algorithm or leetcode wording detected")
    if repo_name_variant in {"algorithm", "algorithms", "leetcode", "data structure", "data structures"}:
        bump(REPO_TYPE_GENERIC_ALGORITHM, 2, "repo name is a generic algorithm keyword")
    if not strong_school_or_course and generic_algorithm_hits:
        bump(REPO_TYPE_GENERIC_ALGORITHM, 1, "generic algorithm repo lacks strong school/course evidence")

    if code_structure:
        scores[REPO_TYPE_REPORT_ONLY] -= 2
    if code_structure and has_lab_dir:
        scores[REPO_TYPE_NOTES] -= 1
        scores[REPO_TYPE_EXAM_SOLUTION] -= 1
    if strong_school_or_course:
        scores[REPO_TYPE_GENERIC_ALGORITHM] -= 1
    if notes_readme_hits and not notes_term_hits and not has_notes_dir and markdown_count < 2:
        scores[REPO_TYPE_NOTES] -= 1
    if document_count >= 2 and not code_structure:
        scores[REPO_TYPE_COURSE_PROJECT] -= 1

    best_type = REPO_TYPE_UNKNOWN
    best_score = 0
    for repo_type in REPO_TYPE_PRIORITY:
        if repo_type == REPO_TYPE_UNKNOWN:
            continue
        score = scores[repo_type]
        if score > best_score:
            best_type = repo_type
            best_score = score

    if best_score < 2:
        best_type = REPO_TYPE_UNKNOWN

    signals = {
        "repo_name": repo_name,
        "root_dir_names": root_dir_names,
        "root_file_names": root_file_names,
        "markdown_file_count": markdown_count,
        "has_readme": has_readme,
        "has_lab_dir": has_lab_dir,
        "has_src_dir": has_src_dir,
        "has_report_dir": has_report_dir,
        "has_notes_dir": has_notes_dir,
        "has_exam_dir": has_exam_dir,
        "has_multiple_course_dirs": has_multiple_course_dirs,
        "likely_org_meta": likely_org_meta,
        "likely_collection": likely_collection,
        "school_mentions": school_mentions,
        "course_mentions": course_mentions,
        "code_structure": code_structure,
        "code_language": code_language,
    }

    positive_evidence = reasons.get(best_type, [])[:4]
    negative_evidence: list[str] = []
    if best_type != REPO_TYPE_LAB_CODE and has_lab_dir and has_src_dir:
        negative_evidence.append("code structure is present but another pattern is stronger")
    if best_type != REPO_TYPE_COLLECTION and has_multiple_course_dirs:
        negative_evidence.append("multiple course directories also suggest a collection-like repo")
    if best_type != REPO_TYPE_REPORT_ONLY and report_term_hits and not code_structure:
        negative_evidence.append("report-heavy content is present")
    if best_type != REPO_TYPE_EXAM_SOLUTION and (exam_term_hits or solution_term_hits):
        negative_evidence.append("exam or solution terms also appear")

    return RepoClassification(
        repo_type=best_type,
        positive_evidence=positive_evidence[:4],
        negative_evidence=negative_evidence[:3],
        signals=signals,
    )


def classify_repo_item(item: ProviderSearchResult) -> RepoClassification:
    metadata = dict(item.metadata or {})
    return classify_repository(
        title=item.title or "",
        description=" ".join(
            part for part in [str(metadata.get("description") or ""), item.snippet or ""] if part
        ),
        readme_text=str(metadata.get("readme_excerpt") or ""),
        metadata=metadata,
    )
