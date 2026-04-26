from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from app.utils.text import safe_lower, unique_preserve_order


INTENT_PROJECT = "project"
INTENT_LAB = "lab"
INTENT_NOTES = "notes"
INTENT_EXAM = "exam"
INTENT_COLLECTION = "collection"


@dataclass(frozen=True)
class CourseProfile:
    id: str
    canonical_name: str
    english_name: str
    aliases: list[str]
    project_keywords: list[str]
    lab_keywords: list[str]
    notes_keywords: list[str]
    structure_signals: list[str]
    reference_criteria: list[str]
    negative_signals: list[str]
    weak_aliases: list[str] = field(default_factory=list)
    abbreviations: list[str] = field(default_factory=list)
    intent_structure_hints: dict[str, list[str]] = field(default_factory=dict)
    asset_signals: dict[str, list[str]] = field(default_factory=dict)
    reference_guidance: list[str] = field(default_factory=list)
    suggested_usage: list[str] = field(default_factory=list)

    def all_aliases(self) -> list[str]:
        return unique_preserve_order(
            [
                self.canonical_name,
                self.english_name,
                *self.aliases,
                *self.abbreviations,
                *self.weak_aliases,
            ]
        )

    def weak_alias_set(self) -> set[str]:
        return {safe_lower(alias) for alias in self.weak_aliases}

    def abbreviation_set(self) -> set[str]:
        return {safe_lower(alias) for alias in self.abbreviations}


@dataclass(frozen=True)
class CourseMatch:
    profile: CourseProfile
    matched_aliases: list[str]
    alias_score: float
    score: float
    structure_hits: list[str] = field(default_factory=list)
    intent_hits: list[str] = field(default_factory=list)


def _profile(
    *,
    id: str,
    canonical_name: str,
    english_name: str,
    aliases: list[str],
    project_keywords: list[str],
    lab_keywords: list[str],
    notes_keywords: list[str],
    structure_signals: list[str],
    reference_criteria: list[str],
    negative_signals: list[str],
    weak_aliases: list[str] | None = None,
    abbreviations: list[str] | None = None,
    intent_structure_hints: dict[str, list[str]] | None = None,
    asset_signals: dict[str, list[str]] | None = None,
    reference_guidance: list[str] | None = None,
    suggested_usage: list[str] | None = None,
) -> CourseProfile:
    return CourseProfile(
        id=id,
        canonical_name=canonical_name,
        english_name=english_name,
        aliases=aliases,
        project_keywords=project_keywords,
        lab_keywords=lab_keywords,
        notes_keywords=notes_keywords,
        structure_signals=structure_signals,
        reference_criteria=reference_criteria,
        negative_signals=negative_signals,
        weak_aliases=weak_aliases or [],
        abbreviations=abbreviations or [],
        intent_structure_hints=intent_structure_hints or {},
        asset_signals=asset_signals or {},
        reference_guidance=reference_guidance or [],
        suggested_usage=suggested_usage or [],
    )


def _build_profiles() -> list[CourseProfile]:
    return [
        _profile(
            id="database_system",
            canonical_name="数据库系统",
            english_name="Database System",
            aliases=[
                "数据库系统",
                "数据库",
                "Database System",
                "Database Systems",
                "Database",
                "DBMS",
            ],
            project_keywords=[
                "大作业",
                "课程项目",
                "选课系统",
                "图书管理系统",
                "教务系统",
                "管理系统",
                "course selection",
                "library management",
            ],
            lab_keywords=["实验", "lab", "experiment", "sql lab"],
            notes_keywords=["笔记", "notes", "lecture", "chapter", "sql notes"],
            structure_signals=[
                "sql",
                "schema",
                "models",
                "database",
                "migrations",
                "erd",
                "er diagram",
                "transaction",
                "index",
                "table",
            ],
            reference_criteria=["数据库设计", "表结构", "ER图", "事务", "索引", "SQL"],
            negative_signals=["408", "考研", "题解", "答案"],
            weak_aliases=["database", "db", "sql"],
            abbreviations=["DB", "DBMS"],
            intent_structure_hints={
                INTENT_PROJECT: ["sql", "schema", "models"],
                INTENT_LAB: ["schema", "sql"],
                INTENT_NOTES: ["chapter", "sql"],
            },
            asset_signals={
                "has_sql_or_schema": ["sql", "schema", ".sql", "migrations"],
                "has_er_diagram": ["erd", "er diagram", "erd.png", "erd.drawio"],
                "has_models": ["models", "model", "entity", "entities", "migration", "migrations"],
            },
            reference_guidance=[
                "适合参考数据库设计",
                "适合参考表结构与 SQL 组织",
                "适合参考 ER 图、事务和索引设计",
            ],
            suggested_usage=[
                "优先看 sql/schema/models 梳理数据库设计",
                "只参考表结构、事务和索引思路，不直接复用实现",
            ],
        ),
        _profile(
            id="operating_system",
            canonical_name="操作系统",
            english_name="Operating System",
            aliases=["操作系统", "Operating System", "Operating Systems"],
            project_keywords=["大作业", "课程项目", "kernel project", "os project"],
            lab_keywords=["实验", "lab", "experiment", "os lab", "kernel lab"],
            notes_keywords=["笔记", "notes", "lecture", "chapter"],
            structure_signals=[
                "lab",
                "kernel",
                "ucore",
                "syscall",
                "scheduler",
                "memory",
                "file system",
                "filesystem",
                "paging",
            ],
            reference_criteria=["实验流程", "内核模块", "调度", "内存管理", "文件系统", "syscall"],
            negative_signals=["408", "考研", "题解", "答案"],
            weak_aliases=["operating system"],
            abbreviations=["OS"],
            intent_structure_hints={
                INTENT_LAB: ["kernel", "ucore"],
                INTENT_PROJECT: ["kernel", "scheduler"],
                INTENT_NOTES: ["scheduler", "memory"],
            },
            asset_signals={
                "has_kernel_dir": ["kernel"],
                "has_ucore": ["ucore"],
                "has_scheduler_hint": ["scheduler", "sched"],
                "has_memory_hint": ["memory", "mm", "paging"],
                "has_file_system_hint": ["file system", "filesystem", "fs"],
            },
            reference_guidance=[
                "适合参考实验流程与目录组织",
                "适合参考内核模块、调度和内存管理实现",
                "适合参考 syscall 与文件系统相关结构",
            ],
            suggested_usage=[
                "先看 lab/kernel 目录理解实验切分方式",
                "关注 scheduler、memory、file system 线索，不直接复用代码提交",
            ],
        ),
        _profile(
            id="algorithms",
            canonical_name="算法导论",
            english_name="Introduction to Algorithms",
            aliases=[
                "算法导论",
                "算法设计",
                "算法分析",
                "Introduction to Algorithms",
                "Algorithms",
            ],
            project_keywords=["作业", "assignment", "exercise", "project"],
            lab_keywords=["实验", "lab", "programming assignment"],
            notes_keywords=["笔记", "notes", "lecture", "chapter", "markdown"],
            structure_signals=[
                "notes",
                "chapter",
                "dp",
                "dynamic programming",
                "graph",
                "greedy",
                "complexity",
                "sort",
            ],
            reference_criteria=["章节笔记", "动态规划", "图算法", "贪心", "复杂度", "题型整理"],
            negative_signals=["408", "考研", "题解", "答案", "leetcode"],
            weak_aliases=["algorithm", "algorithms", "算法"],
            intent_structure_hints={
                INTENT_NOTES: ["chapter", "dp", "graph"],
                INTENT_PROJECT: ["graph", "greedy", "complexity"],
            },
            asset_signals={
                "has_chapter_notes": ["chapter", "lecture", "章节"],
                "has_dp_notes": ["dp", "dynamic programming", "动态规划"],
                "has_graph_notes": ["graph", "图"],
                "has_complexity_notes": ["complexity", "复杂度"],
            },
            reference_guidance=[
                "适合参考章节化课程笔记",
                "适合参考动态规划、图算法和贪心专题整理",
                "适合参考复杂度分析与题型归纳",
            ],
            suggested_usage=[
                "优先看 chapter/notes/markdown 的组织方式",
                "只参考知识点拆分和复杂度分析，不直接套用题解",
            ],
        ),
        _profile(
            id="data_structure",
            canonical_name="数据结构",
            english_name="Data Structure",
            aliases=["数据结构", "Data Structure", "Data Structures"],
            project_keywords=["作业", "assignment", "course project"],
            lab_keywords=["实验", "lab", "programming assignment"],
            notes_keywords=["笔记", "notes", "lecture", "chapter"],
            structure_signals=["list", "stack", "queue", "tree", "graph", "sort", "search"],
            reference_criteria=["线性表", "栈与队列", "树", "图", "查找", "排序"],
            negative_signals=["408", "考研", "题解", "答案", "leetcode"],
            weak_aliases=["data structure", "data structures"],
            reference_guidance=["适合参考基础数据结构实现与笔记整理"],
            suggested_usage=["优先看 list/tree/graph 等核心模块的拆分方式"],
        ),
        _profile(
            id="computer_networks",
            canonical_name="计算机网络",
            english_name="Computer Networks",
            aliases=["计算机网络", "Computer Network", "Computer Networks", "Networking"],
            project_keywords=["课程项目", "network project", "socket project"],
            lab_keywords=["实验", "lab", "socket lab", "network lab"],
            notes_keywords=["笔记", "notes", "lecture", "chapter"],
            structure_signals=["socket", "tcp", "udp", "http", "client", "server", "router", "wireshark"],
            reference_criteria=["socket 编程", "TCP/UDP", "协议实现", "client/server", "抓包分析"],
            negative_signals=["408", "考研", "题解", "答案"],
            weak_aliases=["network", "networks"],
            abbreviations=["CN"],
            intent_structure_hints={
                INTENT_LAB: ["socket", "tcp", "client", "server"],
                INTENT_PROJECT: ["tcp", "udp", "http"],
                INTENT_NOTES: ["chapter", "tcp"],
            },
            asset_signals={
                "has_socket_code": ["socket"],
                "has_tcp_hint": ["tcp"],
                "has_udp_hint": ["udp"],
                "has_client_server_split": ["client", "server"],
            },
            reference_guidance=[
                "适合参考 socket 与 TCP/UDP 实验结构",
                "适合参考 client/server 模块划分与协议实现",
            ],
            suggested_usage=[
                "优先看 socket、tcp、client/server 相关目录和文件",
            ],
        ),
        _profile(
            id="compiler",
            canonical_name="编译原理",
            english_name="Compiler",
            aliases=["编译原理", "编译器", "Compiler", "Compilers"],
            project_keywords=["课程项目", "project", "compiler project"],
            lab_keywords=["实验", "lab", "compiler lab"],
            notes_keywords=["笔记", "notes", "lecture", "chapter"],
            structure_signals=["lexer", "parser", "ast", "ir", "llvm", "codegen", "semantic", "token"],
            reference_criteria=["词法分析", "语法分析", "AST", "IR", "LLVM", "codegen"],
            negative_signals=["408", "考研", "题解", "答案"],
            weak_aliases=["compiler"],
            intent_structure_hints={
                INTENT_LAB: ["lexer", "parser", "ast"],
                INTENT_PROJECT: ["parser", "ir", "codegen"],
                INTENT_NOTES: ["chapter", "ast"],
            },
            asset_signals={
                "has_lexer": ["lexer", "lex", "token"],
                "has_parser": ["parser", "yacc", "grammar"],
                "has_ast": ["ast", "syntax tree"],
                "has_ir": ["ir", "intermediate representation"],
                "has_llvm": ["llvm"],
                "has_codegen": ["codegen", "code generation"],
            },
            reference_guidance=[
                "适合参考词法分析、语法分析与 AST 组织",
                "适合参考 IR/LLVM/codegen 管线",
            ],
            suggested_usage=[
                "先看 lexer/parser/ast 的目录和入口文件",
                "优先参考编译流程拆分，不直接复用实现细节",
            ],
        ),
        _profile(
            id="computer_organization",
            canonical_name="计算机组成原理",
            english_name="Computer Organization",
            aliases=[
                "计算机组成原理",
                "计算机组成",
                "Computer Organization",
                "Computer Architecture",
            ],
            project_keywords=["课程项目", "cpu project", "architecture project"],
            lab_keywords=["实验", "lab", "verilog lab", "logisim lab"],
            notes_keywords=["笔记", "notes", "lecture", "chapter"],
            structure_signals=["cpu", "alu", "pipeline", "cache", "verilog", "logisim", "risc", "instruction"],
            reference_criteria=["CPU 设计", "流水线", "Cache", "指令系统", "仿真"],
            negative_signals=["408", "考研", "题解", "答案"],
            weak_aliases=["computer architecture"],
            abbreviations=["CO"],
            reference_guidance=["适合参考 CPU、流水线和 Cache 相关实验实现"],
            suggested_usage=["优先看 verilog/logisim/cpu 等核心目录"],
        ),
        _profile(
            id="machine_learning",
            canonical_name="机器学习",
            english_name="Machine Learning",
            aliases=["机器学习", "Machine Learning"],
            project_keywords=["课程项目", "project", "ml project", "competition"],
            lab_keywords=["实验", "lab", "experiment", "training lab"],
            notes_keywords=["笔记", "notes", "lecture", "chapter"],
            structure_signals=[
                "notebook",
                "model",
                "dataset",
                "train",
                "eval",
                "evaluate",
                "inference",
                "checkpoint",
            ],
            reference_criteria=["数据处理", "模型训练", "实验评估", "特征工程", "结果分析"],
            negative_signals=["408", "考研", "题解", "答案"],
            weak_aliases=["ml"],
            abbreviations=["ML"],
            intent_structure_hints={
                INTENT_PROJECT: ["dataset", "train", "eval"],
                INTENT_LAB: ["dataset", "train", "eval"],
                INTENT_NOTES: ["model", "dataset"],
            },
            asset_signals={
                "has_notebook": ["notebook", ".ipynb", "jupyter"],
                "has_dataset": ["dataset", "data", "csv"],
                "has_train_script": ["train", "trainer"],
                "has_eval_script": ["eval", "evaluate", "validation"],
                "has_model_dir": ["model", "models", "checkpoint"],
            },
            reference_guidance=[
                "适合参考数据处理、训练脚本和评估流程",
                "适合参考 notebook/model/dataset 的组织方式",
            ],
            suggested_usage=[
                "优先看 dataset、train、eval 和 model 相关目录",
            ],
        ),
        _profile(
            id="software_engineering",
            canonical_name="软件工程",
            english_name="Software Engineering",
            aliases=["软件工程", "Software Engineering"],
            project_keywords=["课程项目", "大作业", "software project"],
            lab_keywords=["实验", "lab", "testing lab"],
            notes_keywords=["笔记", "notes", "lecture", "chapter"],
            structure_signals=["requirements", "design", "architecture", "uml", "test", "srs", "sdd", "use case"],
            reference_criteria=["需求分析", "架构设计", "测试", "UML", "文档组织"],
            negative_signals=["408", "考研", "题解", "答案"],
            weak_aliases=["se"],
            abbreviations=["SE"],
            reference_guidance=["适合参考需求、设计、测试和文档结构"],
            suggested_usage=["优先看 requirements/design/test 文档和模块边界"],
        ),
        _profile(
            id="artificial_intelligence",
            canonical_name="人工智能导论",
            english_name="Artificial Intelligence",
            aliases=["人工智能导论", "人工智能", "Artificial Intelligence"],
            project_keywords=["课程项目", "ai project", "search project"],
            lab_keywords=["实验", "lab", "ai lab"],
            notes_keywords=["笔记", "notes", "lecture", "chapter"],
            structure_signals=["search", "planning", "knowledge", "logic", "agent", "reasoning"],
            reference_criteria=["搜索问题", "知识表示", "推理", "规划", "Agent 设计"],
            negative_signals=["408", "考研", "题解", "答案"],
            weak_aliases=["ai"],
            abbreviations=["AI"],
            reference_guidance=["适合参考搜索、推理和知识表示相关结构"],
            suggested_usage=["优先看 search/planning/knowledge 等模块"],
        ),
    ]


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _term_in_text(text: str, term: str) -> bool:
    normalized = safe_lower(text)
    target = safe_lower(term)
    if not normalized or not target:
        return False
    if _has_cjk(target):
        return target in normalized
    pattern = re.compile(
        rf"(?<![a-z0-9_+#.]){re.escape(target)}(?![a-z0-9_+#.])",
        re.IGNORECASE,
    )
    return bool(pattern.search(normalized))


def _identifier_variant(text: str) -> str:
    return (
        (text or "")
        .replace("_", " ")
        .replace("-", " ")
        .replace("/", " ")
        .replace(".", " ")
    )


COURSE_PROFILES = _build_profiles()
COURSE_PROFILE_BY_ID = {profile.id: profile for profile in COURSE_PROFILES}

_COURSE_LOOKUP: dict[str, CourseProfile] = {}
for _profile_item in COURSE_PROFILES:
    for _token in [_profile_item.id, *_profile_item.all_aliases()]:
        _COURSE_LOOKUP[safe_lower(_token)] = _profile_item


def list_course_profiles() -> list[CourseProfile]:
    return list(COURSE_PROFILES)


def course_alias_map() -> dict[str, list[str]]:
    return {profile.canonical_name: profile.all_aliases() for profile in COURSE_PROFILES}


def get_course_profile(value: str | None) -> CourseProfile | None:
    if not value:
        return None
    return _COURSE_LOOKUP.get(safe_lower(value))


def _alias_weight(profile: CourseProfile, alias: str) -> float:
    normalized = safe_lower(alias)
    if normalized == safe_lower(profile.canonical_name):
        return 1.0
    if normalized == safe_lower(profile.english_name):
        return 0.92
    if normalized in profile.abbreviation_set():
        return 0.76
    if normalized in profile.weak_alias_set():
        return 0.58
    if _has_cjk(alias):
        return 0.90
    if " " in alias:
        return 0.84
    return 0.80


def _matched_aliases(text: str, profile: CourseProfile) -> tuple[list[str], float]:
    search_text = " ".join([text or "", _identifier_variant(text or "")]).strip()
    matched: list[str] = []
    score = 0.0
    for alias in profile.all_aliases():
        if _term_in_text(search_text, alias):
            matched.append(alias)
            score = max(score, _alias_weight(profile, alias))
    return unique_preserve_order(matched), score


def _intent_context_hits(text: str, profile: CourseProfile) -> list[str]:
    hits: list[str] = []
    if any(_term_in_text(text, keyword) for keyword in profile.project_keywords):
        hits.append(INTENT_PROJECT)
    if any(_term_in_text(text, keyword) for keyword in profile.lab_keywords):
        hits.append(INTENT_LAB)
    if any(_term_in_text(text, keyword) for keyword in profile.notes_keywords):
        hits.append(INTENT_NOTES)
    if any(_term_in_text(text, keyword) for keyword in profile.negative_signals):
        hits.append(INTENT_EXAM)
    return unique_preserve_order(hits)


def course_structure_hits(
    profile: CourseProfile,
    text: str,
    *,
    limit: int | None = None,
) -> list[str]:
    search_text = " ".join([text or "", _identifier_variant(text or "")]).strip()
    hits = [signal for signal in profile.structure_signals if _term_in_text(search_text, signal)]
    hits = unique_preserve_order(hits)
    if limit is not None:
        return hits[:limit]
    return hits


def course_negative_signal_hits(
    profile: CourseProfile,
    text: str,
    *,
    limit: int | None = None,
) -> list[str]:
    search_text = " ".join([text or "", _identifier_variant(text or "")]).strip()
    hits = [signal for signal in profile.negative_signals if _term_in_text(search_text, signal)]
    hits = unique_preserve_order(hits)
    if limit is not None:
        return hits[:limit]
    return hits


def _match_score(
    *,
    alias_score: float,
    structure_hits: list[str],
    intent_hits: list[str],
) -> float:
    if alias_score <= 0:
        return 0.0
    score = alias_score
    if intent_hits:
        score += min(0.16, 0.08 * len(intent_hits))
    if structure_hits:
        score += min(0.18, 0.06 * min(3, len(structure_hits)))
    return min(1.0, score)


def _should_accept_match(
    *,
    alias_score: float,
    structure_hits: list[str],
    intent_hits: list[str],
) -> bool:
    if alias_score >= 0.88:
        return True
    if alias_score >= 0.76 and (intent_hits or structure_hits):
        return True
    if alias_score >= 0.58 and len(structure_hits) >= 2:
        return True
    if alias_score >= 0.58 and INTENT_LAB in intent_hits and structure_hits:
        return True
    if alias_score >= 0.58 and INTENT_NOTES in intent_hits and structure_hits:
        return True
    return False


def detect_course_matches(query: str) -> list[CourseMatch]:
    text = query or ""
    matches: list[CourseMatch] = []
    for profile in COURSE_PROFILES:
        matched_aliases, alias_score = _matched_aliases(text, profile)
        if alias_score <= 0:
            continue
        structure_hits = course_structure_hits(profile, text, limit=4)
        intent_hits = _intent_context_hits(text, profile)
        if not _should_accept_match(
            alias_score=alias_score,
            structure_hits=structure_hits,
            intent_hits=intent_hits,
        ):
            continue
        matches.append(
            CourseMatch(
                profile=profile,
                matched_aliases=matched_aliases,
                alias_score=alias_score,
                score=_match_score(
                    alias_score=alias_score,
                    structure_hits=structure_hits,
                    intent_hits=intent_hits,
                ),
                structure_hits=structure_hits,
                intent_hits=intent_hits,
            )
        )
    ranked = sorted(
        matches,
        key=lambda match: (
            -match.score,
            -match.alias_score,
            -len(match.matched_aliases[0]) if match.matched_aliases else 0,
            match.profile.canonical_name,
        ),
    )
    return ranked


def detect_courses(query: str) -> list[CourseProfile]:
    return [match.profile for match in detect_course_matches(query)]


def find_course_mentions_loose(text: str) -> list[str]:
    search_text = " ".join([text or "", _identifier_variant(text or "")]).strip()
    matched: list[str] = []
    for profile in COURSE_PROFILES:
        if any(_term_in_text(search_text, alias) for alias in profile.all_aliases()):
            matched.append(profile.canonical_name)
    return unique_preserve_order(matched)


def pick_course_query_aliases(profile: CourseProfile | None) -> dict[str, list[str]]:
    if profile is None:
        return {"canonical": [], "english": [], "short": [], "fallback": []}

    fallback = [
        alias
        for alias in profile.aliases
        if safe_lower(alias) not in profile.weak_alias_set()
        and safe_lower(alias) not in profile.abbreviation_set()
        and safe_lower(alias) not in {safe_lower(profile.canonical_name), safe_lower(profile.english_name)}
    ]
    weak_english = [alias for alias in profile.weak_aliases if alias.isascii() and len(alias) > 2]
    return {
        "canonical": [profile.canonical_name],
        "english": [profile.english_name] if profile.english_name else [],
        "short": profile.abbreviations[:1],
        "fallback": (fallback[:1] or weak_english[:1]),
    }


def pick_course_intent_keywords(profile: CourseProfile | None, intent: str) -> list[str]:
    if profile is None:
        return []
    if intent == INTENT_PROJECT:
        return profile.project_keywords[:2]
    if intent == INTENT_LAB:
        return profile.lab_keywords[:2]
    if intent == INTENT_NOTES:
        return profile.notes_keywords[:2]
    return profile.project_keywords[:1] or profile.lab_keywords[:1] or profile.notes_keywords[:1]


def pick_course_structure_terms(profile: CourseProfile | None, intent: str) -> list[str]:
    if profile is None:
        return []
    terms = profile.intent_structure_hints.get(intent) or profile.structure_signals
    return unique_preserve_order([term for term in terms if term])[:2]


def detect_course_specific_assets(
    profile: CourseProfile | None,
    *,
    title: str = "",
    description: str = "",
    readme_text: str = "",
    root_paths: Iterable[str] | None = None,
    root_dir_names: Iterable[str] | None = None,
    root_file_names: Iterable[str] | None = None,
    root_signal: dict[str, object] | None = None,
) -> dict[str, bool]:
    if profile is None:
        return {}

    signal = dict(root_signal or {})
    path_parts = [
        *(list(root_paths or [])),
        *(list(root_dir_names or [])),
        *(list(root_file_names or [])),
    ]
    combined = " ".join(
        part
        for part in [
            title,
            description,
            readme_text,
            " ".join(path_parts),
        ]
        if part
    )

    assets: dict[str, bool] = {}
    for asset_name, terms in profile.asset_signals.items():
        if asset_name in signal:
            assets[asset_name] = bool(signal.get(asset_name))
            continue
        assets[asset_name] = any(_term_in_text(combined, term) for term in terms)

    if "has_sql_or_schema" in profile.asset_signals:
        assets["has_sql_or_schema"] = bool(
            assets.get("has_sql_or_schema") or signal.get("has_sql_or_schema")
        )
    return assets
