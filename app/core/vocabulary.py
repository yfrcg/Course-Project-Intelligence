from __future__ import annotations

import re
from typing import Iterable

from app.core.course_profiles import (
    course_alias_map,
    detect_courses,
    find_course_mentions_loose,
    get_course_profile,
)
from app.core.university_profiles import (
    find_university,
    find_university_mentions,
    get_university_aliases,
    list_university_profiles,
)
from app.utils.text import extract_keywords, safe_lower, tokenize, unique_preserve_order

"""
这个文件维护项目里最基础的词表和别名映射。
查询分析、意图识别、排序解释都会复用这里的学校、课程、技术栈和资源类型词典。
"""


# 学校 profile registry 已迁移到 `university_profiles.py`，这里保留兼容读接口。
SCHOOL_ALIASES: dict[str, list[str]] = {
    profile.canonical_name: profile.all_aliases()
    for profile in list_university_profiles()
}


COURSE_ALIASES: dict[str, list[str]] = course_alias_map()


COMPUTING_TOPIC_ALIASES: dict[str, list[str]] = {
    "计算机科学与技术": [
        "计算机",
        "计算机专业",
        "计算机学院",
        "计算机科学与技术",
        "computer science",
        "cs",
    ],
    "软件工程": ["软件工程", "software engineering"],
    "网络空间安全": ["网络空间安全", "cyber security", "cybersecurity"],
    "人工智能": ["人工智能", "ai", "machine learning", "deep learning"],
    "信息检索": ["信息检索", "检索", "retrieval", "search"],
    "数据与数据库": ["数据库", "数据工程", "data engineering", "database systems"],
}


TECH_ALIASES: dict[str, list[str]] = {
    "python": ["python", "py"],
    "c": ["c", "c语言", "c language"],
    "c++": ["c++", "cpp", "cplusplus", "c plus plus"],
    "java": ["java"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "go": ["golang", "go"],
    "rust": ["rust"],
    "verilog": ["verilog", "systemverilog"],
    "matlab": ["matlab"],
    "pytorch": ["pytorch", "torch"],
    "tensorflow": ["tensorflow"],
    "vue": ["vue", "vue.js", "vuejs"],
    "react": ["react", "react.js", "reactjs"],
    "node.js": ["node", "node.js", "nodejs"],
    "flask": ["flask"],
    "fastapi": ["fastapi"],
    "django": ["django"],
    "spring": ["spring", "springboot", "spring boot"],
    "mysql": ["mysql"],
    "postgresql": ["postgresql", "postgres", "pgsql"],
    "sqlite": ["sqlite", "sqlite3"],
    "redis": ["redis"],
    "docker": ["docker"],
    "linux": ["linux"],
    "opencv": ["opencv"],
    "qt": ["qt", "pyqt"],
    "mpi": ["mpi"],
    "openmp": ["openmp"],
    "cuda": ["cuda"],
    "web": ["web", "webapp", "web app", "前端", "后端", "网站", "网页"],
    "可视化": ["可视化", "visualization", "visualisation"],
    "图算法": ["图算法", "graph algorithm", "graph algorithms", "graph search"],
    "检索": ["检索", "search", "retrieval"],
    "爬虫": ["爬虫", "crawler", "scraper", "scraping"],
    "推荐系统": ["推荐系统", "recommender", "recommendation"],
    "深度学习": ["深度学习", "deep learning"],
    "强化学习": ["强化学习", "reinforcement learning", "rl"],
}


PROJECT_KEYWORD_ALIASES: dict[str, list[str]] = {
    "课程项目": ["课程项目", "course project", "project"],
    "大作业": ["大作业", "final project", "term project", "big homework"],
    "实验": ["实验", "lab", "labs", "experiment"],
    "课程设计": ["课程设计", "course design"],
    "作业": ["作业", "homework", "assignment"],
    "报告": ["报告", "report"],
    "源码": ["源码", "source code", "code"],
    "经验帖": ["经验帖", "经验", "experience", "review"],
    "资料": ["资料", "material", "materials", "tutorial", "notes"],
}


RESOURCE_KEYWORD_ALIASES: dict[str, list[str]] = {
    "repository": ["github", "gitee", "gitlab", "仓库", "repo", "repository", "源码"],
    "blog": ["博客", "blog", "经验帖", "经验总结", "post"],
    "lab_material": ["实验", "lab", "实验指导", "实验报告"],
    "slides_or_report": ["课件", "slides", "ppt", "报告", "report"],
    "tutorial": ["教程", "tutorial", "notes", "笔记", "资料"],
}


INFO_SCOPE_ALIASES: dict[str, list[str]] = {
    "本科教育": ["本科", "本科教育", "本科生培养", "培养方案", "专业信息", "课程体系"],
    "研究生教育": ["研究生", "研究生教育", "硕士", "博士", "研究方向"],
    "研究生招生": ["研究生招生", "招生", "考研", "推免", "调剂", "博士招生"],
    "师资队伍": ["教师", "老师", "教授", "研究员", "导师", "师资"],
    "实验教学": ["实验教学", "实验中心", "实验室", "虚拟仿真", "上机"],
    "学院公告": ["公告", "通知", "公示", "news", "notice"],
    "本科生教学": ["本科生教学", "教学安排", "考试", "创新项目", "转专业"],
    "系所中心": ["系所中心", "研究所", "研究中心", "团队", "科研平台"],
}


SOURCE_HINTS: dict[str, list[str]] = {
    "github": ["github", "github.com", "repo", "repository"],
    "gitee": ["gitee", "gitee.com", "码云"],
    "web": ["博客", "网页", "站点", "网站", "教程", "经验帖", "资料站", "csdn", "cnblogs"],
}


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def term_in_text(text: str, term: str) -> bool:
    normalized = safe_lower(text)
    target = safe_lower(term)
    if not normalized or not target:
        return False

    # 中文直接做包含判断比较稳；英文要做词边界匹配，避免 `c` 误伤 `course` 这种情况。
    if _has_cjk(target):
        return target in normalized

    pattern = re.compile(
        rf"(?<![a-z0-9_+#.]){re.escape(target)}(?![a-z0-9_+#.])",
        re.IGNORECASE,
    )
    return bool(pattern.search(normalized))


def match_alias_map(text: str, alias_map: dict[str, list[str]]) -> str | None:
    for canonical, aliases in alias_map.items():
        if any(term_in_text(text, alias) for alias in aliases):
            return canonical
    return None


def find_alias_matches(text: str, alias_map: dict[str, list[str]]) -> list[str]:
    found: list[str] = []
    for canonical, aliases in alias_map.items():
        if any(term_in_text(text, alias) for alias in aliases):
            found.append(canonical)
    return unique_preserve_order(found)


def find_school(text: str) -> str | None:
    return find_university(text)


def find_school_mentions(text: str) -> list[str]:
    return find_university_mentions(text)


def find_course(text: str) -> str | None:
    matches = detect_courses(text)
    return matches[0].canonical_name if matches else None


def find_course_mentions(text: str) -> list[str]:
    return find_course_mentions_loose(text)


def _get_aliases_for_canonical(
    canonical: str | None,
    alias_map: dict[str, list[str]],
) -> list[str]:
    if not canonical:
        return []
    aliases = alias_map.get(canonical) or []
    # 把 canonical 本身放回结果里，避免上层还要额外手动补一遍标准名。
    return unique_preserve_order([canonical, *aliases])


def get_school_aliases(canonical: str | None) -> list[str]:
    return get_university_aliases(canonical)


def get_course_aliases(canonical: str | None) -> list[str]:
    profile = get_course_profile(canonical)
    if profile is not None:
        return profile.all_aliases()
    return _get_aliases_for_canonical(canonical, COURSE_ALIASES)


def find_tech_keywords(text: str) -> list[str]:
    return find_alias_matches(text, TECH_ALIASES)


def find_computing_topics(text: str) -> list[str]:
    return find_alias_matches(text, COMPUTING_TOPIC_ALIASES)


def find_project_keywords(text: str) -> list[str]:
    found = find_alias_matches(text, PROJECT_KEYWORD_ALIASES)
    if found:
        return found
    # 如果一个显式项目词都没识别出来，就退回关键词提取，尽量别让结果完全空掉。
    return extract_keywords(text, top_k=6)


def find_resource_keywords(text: str) -> list[str]:
    return find_alias_matches(text, RESOURCE_KEYWORD_ALIASES)


def find_info_scope_keywords(text: str) -> list[str]:
    return find_alias_matches(text, INFO_SCOPE_ALIASES)


def find_source_type_hints(text: str) -> list[tuple[str, str]]:
    hints: list[tuple[str, str]] = []
    for source_type, aliases in SOURCE_HINTS.items():
        for alias in aliases:
            if term_in_text(text, alias):
                hints.append((source_type, alias))
                break
    return hints


def count_term_hits(text: str, keywords: Iterable[str]) -> int:
    return sum(1 for keyword in keywords if term_in_text(text, keyword))


def tokenize_for_query(text: str) -> list[str]:
    return unique_preserve_order(tokenize(text))
