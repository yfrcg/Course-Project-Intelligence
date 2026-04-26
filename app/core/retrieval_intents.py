from __future__ import annotations

import re

from app.core.vocabulary import term_in_text
from app.schemas import QueryAnalysis
from app.utils.text import safe_lower, unique_preserve_order

"""
这个文件负责识别“用户到底想找什么类型的资料”。
项目、实验、笔记、试题这些意图会直接影响搜索词扩展和后续排序惩罚规则。
"""


# 这些常量把检索意图收敛成一个稳定集合，避免后续逻辑到处写裸字符串。
INTENT_NOTES = "notes"
INTENT_PROJECT = "project"
INTENT_LAB = "lab"
INTENT_EXAM = "exam"
INTENT_SOLUTION = "solution"
INTENT_COLLECTION = "collection"
INTENT_GENERIC = "generic"

KNOWN_INTENTS = [
    INTENT_NOTES,
    INTENT_PROJECT,
    INTENT_LAB,
    INTENT_EXAM,
    INTENT_SOLUTION,
    INTENT_COLLECTION,
    INTENT_GENERIC,
]

INTENT_TERMS: dict[str, list[str]] = {
    INTENT_NOTES: [
        "笔记",
        "课程笔记",
        "复习笔记",
        "学习笔记",
        "notes",
        "note",
        "lecture notes",
        "markdown",
        "md",
        "obsidian",
        "lecture",
        "lectures",
    ],
    INTENT_PROJECT: [
        "大作业",
        "课程项目",
        "课程设计",
        "course project",
        "final project",
        "term project",
        "project",
        "big homework",
    ],
    INTENT_LAB: [
        "实验",
        "实验报告",
        "实验代码",
        "lab",
        "labs",
        "lab report",
        "src/lab",
        "experiment",
    ],
    INTENT_EXAM: [
        "试题",
        "往年题",
        "真题",
        "期末",
        "期中",
        "考试",
        "quiz",
        "exam",
        "exams",
        "midterm",
        "final exam",
    ],
    INTENT_SOLUTION: [
        "答案",
        "题解",
        "解答",
        "作业答案",
        "answer",
        "answers",
        "solution",
        "solutions",
    ],
    INTENT_COLLECTION: [
        "合集",
        "汇总",
        "资料汇总",
        "课程资料",
        "课程资源",
        "多门课程",
        "awesome",
        "resources",
        "course archive",
        "course-archive",
        "course collection",
        "courses",
        "nku-courses",
        "408",
        "考研",
        "王道",
    ],
}

QUERY_INTENT_PRIORITY = [
    INTENT_SOLUTION,
    INTENT_EXAM,
    INTENT_COLLECTION,
    INTENT_PROJECT,
    INTENT_LAB,
    INTENT_NOTES,
]


def _analysis_text(value: QueryAnalysis | str) -> str:
    # QueryAnalysis 里有不少拆好的字段，拼回去后比只看 raw_query 更利于意图识别。
    if isinstance(value, QueryAnalysis):
        return " ".join(
            [
                value.raw_query or "",
                value.school or "",
                value.course or "",
                " ".join(value.project_keywords),
                " ".join(value.resource_keywords),
                " ".join(value.tech_keywords),
            ]
        )
    return value or ""


def _is_negated_term(text: str, term: str) -> bool:
    lowered_text = safe_lower(text)
    lowered_term = safe_lower(term).strip()
    if not lowered_term:
        return False

    compact_text = lowered_text.replace(" ", "")
    compact_term = lowered_term.replace(" ", "")
    zh_negated_prefixes = [
        "不要",
        "别",
        "不看",
        "不想要",
        "不需要",
        "不是",
        "排除",
        "不含",
    ]
    en_negated_prefixes = ["without", "no", "not"]

    if any(prefix + lowered_term in lowered_text for prefix in [*zh_negated_prefixes, *[f"{prefix} " for prefix in en_negated_prefixes]]):
        return True
    if compact_term and any(prefix + compact_term in compact_text for prefix in zh_negated_prefixes):
        return True
    if compact_term:
        zh_gap_patterns = [
            re.compile(rf"{re.escape(prefix)}[^，。；、,.!?！？\s]{{0,8}}{re.escape(compact_term)}")
            for prefix in zh_negated_prefixes
        ]
        if any(pattern.search(compact_text) for pattern in zh_gap_patterns):
            return True

    escaped_term = re.escape(lowered_term)
    en_gap_patterns = [
        re.compile(rf"\b{re.escape(prefix)}\b[\w\s/#-]{{0,16}}\b{escaped_term}\b", re.IGNORECASE)
        for prefix in en_negated_prefixes
    ]
    if any(pattern.search(lowered_text) for pattern in en_gap_patterns):
        return True
    return False


def score_intents(value: QueryAnalysis | str) -> dict[str, int]:
    text = _analysis_text(value)
    scores = {intent: 0 for intent in KNOWN_INTENTS if intent != INTENT_GENERIC}

    # 先做一轮普通词项计分，再用下面的规则给一些强信号额外加权。
    for intent, terms in INTENT_TERMS.items():
        for term in terms:
            if term_in_text(text, term) and not _is_negated_term(text, term):
                scores[intent] += 1

    lowered = safe_lower(text)
    if "大作业" in text:
        scores[INTENT_PROJECT] += 2
    if "实验报告" in text or " lab " in f" {lowered} ":
        scores[INTENT_LAB] += 2
    if "期末题" in text or "往年题" in text:
        scores[INTENT_EXAM] += 2
    if "课程资料合集" in text or "nku-courses" in lowered:
        scores[INTENT_COLLECTION] += 3

    return scores


def classify_query_intent(value: QueryAnalysis | str) -> str:
    scores = score_intents(value)
    if not any(scores.values()):
        return INTENT_GENERIC

    # 这里按固定优先级挑 intent，而不是单纯取最大分。
    # 原因是“答案”和“试题”一类风险更高，需要优先被识别出来。
    for intent in QUERY_INTENT_PRIORITY:
        if scores[intent] > 0:
            return intent

    return INTENT_GENERIC


def classify_text_intents(text: str) -> list[str]:
    scores = score_intents(text)
    intents = [
        intent
        for intent, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        if score > 0
    ]
    return unique_preserve_order(intents) or [INTENT_GENERIC]


def intent_terms(intent: str) -> list[str]:
    return INTENT_TERMS.get(intent, [])
