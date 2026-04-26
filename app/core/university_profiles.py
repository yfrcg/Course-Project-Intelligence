from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from app.utils.text import safe_lower, unique_preserve_order


SchoolGroup = Literal["985", "211", "c9", "double_first_class"]
SchoolScopeKind = Literal[
    "specific_school",
    "multiple_schools",
    "project_985",
    "project_211",
    "c9",
    "double_first_class",
    "broad_university",
    "none",
]

BROAD_SCHOOL_SCOPE_KINDS: set[str] = {
    "project_985",
    "project_211",
    "c9",
    "double_first_class",
    "broad_university",
}

SCOPE_TO_GROUP: dict[str, SchoolGroup] = {
    "project_985": "985",
    "project_211": "211",
    "c9": "c9",
    "double_first_class": "double_first_class",
}

UNIVERSITY_PRIORITY_ORDER = [
    "nankai",
    "thu",
    "pku",
    "zju",
    "sjtu",
    "fdu",
    "nju",
    "ustc",
    "hit",
    "xjtu",
    "buaa",
    "bit",
    "seu",
    "hust",
    "whu",
    "tongji",
    "sysu",
    "scu",
    "uestc",
    "npu",
]


@dataclass
class UniversityProfile:
    id: str
    canonical_name: str
    english_name: str
    aliases: list[str]
    github_keywords: list[str]
    groups: list[str] = field(default_factory=list)
    ambiguous_aliases: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)
    official_domains: list[str] = field(default_factory=list)
    computer_ecosystem_seeds: dict[str, str] = field(default_factory=dict)
    computer_ecosystem_intent_order: list[str] = field(default_factory=list)
    computer_ecosystem_intent_keywords: dict[str, list[str]] = field(default_factory=dict)
    computer_context_terms: list[str] = field(default_factory=list)
    computer_expansion_terms: list[str] = field(default_factory=list)

    def all_aliases(self) -> list[str]:
        return unique_preserve_order([self.canonical_name, self.english_name, *self.aliases])

    def ambiguous_alias_set(self) -> set[str]:
        return {safe_lower(alias) for alias in self.ambiguous_aliases}

    def group_set(self) -> set[str]:
        return {safe_lower(group) for group in self.groups}


@dataclass
class UniversityMatch:
    profile: UniversityProfile
    matched_aliases: list[str]
    evidence: list[str]
    ambiguous_aliases: list[str] = field(default_factory=list)
    has_canonical_name: bool = False
    has_english_name: bool = False

    @property
    def ambiguous(self) -> bool:
        return bool(self.matched_aliases) and len(self.ambiguous_aliases) == len(self.matched_aliases)

    def score(self) -> int:
        value = 0
        if self.has_canonical_name:
            value += 100
        if self.has_english_name:
            value += 80
        value += 20 * len([alias for alias in self.matched_aliases if alias not in self.ambiguous_aliases])
        value += 10 * len(self.ambiguous_aliases)
        return value

    def as_dict(self) -> dict[str, Any]:
        return {
            "school": self.profile.canonical_name,
            "school_id": self.profile.id,
            "matched_aliases": list(self.matched_aliases),
            "ambiguous_aliases": list(self.ambiguous_aliases),
            "ambiguous": self.ambiguous,
            "groups": list(self.profile.groups),
            "risk_notes": list(self.profile.risk_notes),
            "evidence": list(self.evidence),
        }


@dataclass
class SchoolScope:
    kind: SchoolScopeKind
    evidence: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "evidence": list(self.evidence)}


def _profile(
    *,
    id: str,
    canonical_name: str,
    english_name: str,
    aliases: list[str],
    github_keywords: list[str],
    groups: list[str],
    ambiguous_aliases: list[str] | None = None,
    risk_notes: list[str] | None = None,
    official_domains: list[str] | None = None,
    computer_ecosystem_seeds: dict[str, str] | None = None,
    computer_ecosystem_intent_order: list[str] | None = None,
    computer_ecosystem_intent_keywords: dict[str, list[str]] | None = None,
    computer_context_terms: list[str] | None = None,
    computer_expansion_terms: list[str] | None = None,
) -> UniversityProfile:
    return UniversityProfile(
        id=id,
        canonical_name=canonical_name,
        english_name=english_name,
        aliases=aliases,
        github_keywords=github_keywords,
        groups=groups,
        ambiguous_aliases=ambiguous_aliases or [],
        risk_notes=risk_notes or [],
        official_domains=official_domains or [],
        computer_ecosystem_seeds=computer_ecosystem_seeds or {},
        computer_ecosystem_intent_order=computer_ecosystem_intent_order or [],
        computer_ecosystem_intent_keywords=computer_ecosystem_intent_keywords or {},
        computer_context_terms=computer_context_terms or [],
        computer_expansion_terms=computer_expansion_terms or [],
    )


def _build_profiles() -> list[UniversityProfile]:
    return [
        _profile(
            id="nankai",
            canonical_name="南开大学",
            english_name="Nankai University",
            aliases=["南开", "南开大学", "nankai", "Nankai University", "NKU", "nku"],
            github_keywords=["南开大学", "南开", "nku", "nankai"],
            groups=["985", "211", "double_first_class"],
            official_domains=["nankai.edu.cn", "cc.nankai.edu.cn"],
            computer_ecosystem_seeds={
                "overview": "https://cc.nankai.edu.cn/",
                "faculty": "https://cc.nankai.edu.cn/jswyjy/list.htm",
                "undergraduate": "https://cc.nankai.edu.cn/13272/list.htm",
                "postgraduate": "https://cc.nankai.edu.cn/13273/list.htm",
                "research": "https://cc.nankai.edu.cn/13280/list.htm",
                "lab": "https://cc.nankai.edu.cn/13284/list.htm",
                "notice": "https://cc.nankai.edu.cn/13292/list.htm",
                "undergraduate_teaching": "https://cc.nankai.edu.cn/13295/list.htm",
                "postgraduate_admission": "https://cc.nankai.edu.cn/13297/list.htm",
            },
            computer_ecosystem_intent_order=[
                "undergraduate",
                "postgraduate",
                "faculty",
                "research",
                "lab",
                "notice",
                "undergraduate_teaching",
                "postgraduate_admission",
            ],
            computer_ecosystem_intent_keywords={
                "faculty": ["教师", "老师", "教授", "研究员", "导师", "师资"],
                "undergraduate": ["本科", "本科教育", "培养方案", "专业信息", "课程体系"],
                "postgraduate": ["研究生", "研究生教育", "硕士", "博士"],
                "postgraduate_admission": ["招生", "考研", "推免", "调剂", "申请考核", "博士招生"],
                "undergraduate_teaching": ["本科生教学", "教学安排", "课程安排", "期末考试", "创新项目"],
                "notice": ["公告", "通知", "公示", "news", "notice"],
                "lab": ["实验", "实验室", "实验教学", "实验中心", "虚拟仿真"],
                "research": ["研究所", "研究中心", "团队", "科研", "实验平台", "学术"],
            },
            computer_context_terms=[
                "计算机",
                "计算机专业",
                "计算机学院",
                "计算机科学与技术",
                "软件工程",
                "网络空间安全",
                "computer science",
                "software engineering",
                "cybersecurity",
            ],
            computer_expansion_terms=[
                "计算机学院",
                "计算机科学与技术",
                "本科教育",
                "研究生教育",
                "师资队伍",
                "实验教学",
                "学院公告",
                "本科生教学",
                "研究生招生",
            ],
        ),
        _profile(
            id="thu",
            canonical_name="清华大学",
            english_name="Tsinghua University",
            aliases=["清华", "清华大学", "tsinghua", "Tsinghua University", "THU", "thu"],
            github_keywords=["清华大学", "清华", "thu", "tsinghua"],
            groups=["985", "211", "c9", "double_first_class"],
            ambiguous_aliases=["THU", "thu"],
            risk_notes=["THU is an ambiguous abbreviation and needs repository-level school evidence."],
        ),
        _profile(
            id="pku",
            canonical_name="北京大学",
            english_name="Peking University",
            aliases=["北大", "北京大学", "peking", "Peking University", "PKU", "pku"],
            github_keywords=["北京大学", "北大", "pku", "peking"],
            groups=["985", "211", "c9", "double_first_class"],
        ),
        _profile(
            id="zju",
            canonical_name="浙江大学",
            english_name="Zhejiang University",
            aliases=["浙大", "浙江大学", "zhejiang", "Zhejiang University", "ZJU", "zju"],
            github_keywords=["浙江大学", "浙大", "zju", "zhejiang"],
            groups=["985", "211", "c9", "double_first_class"],
        ),
        _profile(
            id="sjtu",
            canonical_name="上海交通大学",
            english_name="Shanghai Jiao Tong University",
            aliases=[
                "上交",
                "上海交大",
                "上海交通大学",
                "shanghai jiao tong",
                "Shanghai Jiao Tong University",
                "SJTU",
                "sjtu",
            ],
            github_keywords=["上海交通大学", "上海交大", "sjtu", "shanghai jiao tong"],
            groups=["985", "211", "c9", "double_first_class"],
        ),
        _profile(
            id="fdu",
            canonical_name="复旦大学",
            english_name="Fudan University",
            aliases=["复旦", "复旦大学", "fudan", "Fudan University", "FDU", "fdu"],
            github_keywords=["复旦大学", "复旦", "fdu", "fudan"],
            groups=["985", "211", "c9", "double_first_class"],
        ),
        _profile(
            id="nju",
            canonical_name="南京大学",
            english_name="Nanjing University",
            aliases=["南大", "南京大学", "nanjing", "Nanjing University", "NJU", "nju"],
            github_keywords=["南京大学", "南大", "nju", "nanjing"],
            groups=["985", "211", "c9", "double_first_class"],
            ambiguous_aliases=["NJU", "nju"],
            risk_notes=["NJU is ambiguous and should not drive high confidence by itself."],
        ),
        _profile(
            id="ustc",
            canonical_name="中国科学技术大学",
            english_name="University of Science and Technology of China",
            aliases=[
                "中科大",
                "中国科学技术大学",
                "ustc",
                "USTC",
                "University of Science and Technology of China",
            ],
            github_keywords=["中国科学技术大学", "中科大", "ustc"],
            groups=["985", "211", "c9", "double_first_class"],
        ),
        _profile(
            id="hit",
            canonical_name="哈尔滨工业大学",
            english_name="Harbin Institute of Technology",
            aliases=["哈工大", "哈尔滨工业大学", "hit", "HIT", "Harbin Institute of Technology"],
            github_keywords=["哈尔滨工业大学", "哈工大", "hit", "harbin institute of technology"],
            groups=["985", "211", "c9", "double_first_class"],
            ambiguous_aliases=["HIT", "hit"],
            risk_notes=["HIT is ambiguous and needs full-name or repository context support."],
        ),
        _profile(
            id="xjtu",
            canonical_name="西安交通大学",
            english_name="Xi'an Jiaotong University",
            aliases=[
                "西交",
                "西安交大",
                "西安交通大学",
                "Xi'an Jiaotong University",
                "XJTU",
                "xjtu",
            ],
            github_keywords=["西安交通大学", "西安交大", "xjtu", "xi'an jiaotong"],
            groups=["985", "211", "c9", "double_first_class"],
        ),
        _profile(
            id="buaa",
            canonical_name="北京航空航天大学",
            english_name="Beihang University",
            aliases=["北航", "北京航空航天大学", "beihang", "Beihang University", "BUAA", "buaa"],
            github_keywords=["北京航空航天大学", "北航", "buaa", "beihang"],
            groups=["985", "211", "double_first_class"],
        ),
        _profile(
            id="bit",
            canonical_name="北京理工大学",
            english_name="Beijing Institute of Technology",
            aliases=["北理工", "北京理工大学", "bit", "BIT", "Beijing Institute of Technology"],
            github_keywords=["北京理工大学", "北理工", "bit", "beijing institute of technology"],
            groups=["985", "211", "double_first_class"],
            ambiguous_aliases=["BIT", "bit"],
            risk_notes=["BIT is ambiguous and should not be treated as strong school evidence alone."],
        ),
        _profile(
            id="seu",
            canonical_name="东南大学",
            english_name="Southeast University",
            aliases=["东南大学", "southeast", "Southeast University", "SEU", "seu"],
            github_keywords=["东南大学", "seu", "southeast university"],
            groups=["985", "211", "double_first_class"],
            ambiguous_aliases=["SEU", "seu"],
            risk_notes=["SEU is ambiguous and requires repository-level school evidence."],
        ),
        _profile(
            id="hust",
            canonical_name="华中科技大学",
            english_name="Huazhong University of Science and Technology",
            aliases=[
                "华科",
                "华中科技大学",
                "hust",
                "HUST",
                "Huazhong University of Science and Technology",
            ],
            github_keywords=["华中科技大学", "华科", "hust", "huazhong university of science and technology"],
            groups=["985", "211", "double_first_class"],
        ),
        _profile(
            id="whu",
            canonical_name="武汉大学",
            english_name="Wuhan University",
            aliases=["武大", "武汉大学", "whu", "WHU", "Wuhan University"],
            github_keywords=["武汉大学", "武大", "whu", "wuhan university"],
            groups=["985", "211", "double_first_class"],
            ambiguous_aliases=["WHU", "whu"],
            risk_notes=["WHU is ambiguous and should not be high confidence without stronger evidence."],
        ),
        _profile(
            id="tongji",
            canonical_name="同济大学",
            english_name="Tongji University",
            aliases=["同济", "同济大学", "tongji", "Tongji University"],
            github_keywords=["同济大学", "同济", "tongji"],
            groups=["985", "211", "double_first_class"],
        ),
        _profile(
            id="sysu",
            canonical_name="中山大学",
            english_name="Sun Yat-sen University",
            aliases=["中山大学", "中大", "sysu", "SYSU", "Sun Yat-sen University"],
            github_keywords=["中山大学", "sysu", "sun yat-sen university"],
            groups=["985", "211", "double_first_class"],
            ambiguous_aliases=["中大"],
            risk_notes=["中大 is ambiguous and should rely on stronger repository context."],
        ),
        _profile(
            id="scu",
            canonical_name="四川大学",
            english_name="Sichuan University",
            aliases=["川大", "四川大学", "scu", "SCU", "Sichuan University"],
            github_keywords=["四川大学", "川大", "scu", "sichuan university"],
            groups=["985", "211", "double_first_class"],
            ambiguous_aliases=["SCU", "scu"],
            risk_notes=["SCU is ambiguous and needs non-abbreviation school evidence."],
        ),
        _profile(
            id="uestc",
            canonical_name="电子科技大学",
            english_name="University of Electronic Science and Technology of China",
            aliases=[
                "电子科技大学",
                "成电",
                "UESTC",
                "uestc",
                "University of Electronic Science and Technology of China",
            ],
            github_keywords=["电子科技大学", "uestc", "university of electronic science and technology of china"],
            groups=["985", "211", "double_first_class"],
        ),
        _profile(
            id="npu",
            canonical_name="西北工业大学",
            english_name="Northwestern Polytechnical University",
            aliases=[
                "西工大",
                "西北工业大学",
                "NPU",
                "npu",
                "Northwestern Polytechnical University",
            ],
            github_keywords=["西北工业大学", "西工大", "npu", "northwestern polytechnical university"],
            groups=["985", "211", "double_first_class"],
            ambiguous_aliases=["NPU", "npu"],
            risk_notes=["NPU can be ambiguous in repository abbreviations."],
        ),
    ]


UNIVERSITY_PROFILES = _build_profiles()
UNIVERSITY_PROFILE_BY_ID = {profile.id: profile for profile in UNIVERSITY_PROFILES}
UNIVERSITY_PROFILE_ORDER = {profile_id: index for index, profile_id in enumerate(UNIVERSITY_PRIORITY_ORDER)}
UNIVERSITY_ALIAS_TO_ID = {
    safe_lower(alias): profile.id
    for profile in UNIVERSITY_PROFILES
    for alias in [profile.id, profile.canonical_name, profile.english_name, *profile.aliases]
}


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def university_term_in_text(text: str, term: str) -> bool:
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


def count_university_term_occurrences(text: str, term: str) -> int:
    normalized = safe_lower(text)
    target = safe_lower(term)
    if not normalized or not target:
        return 0
    if _has_cjk(target):
        return normalized.count(target)
    pattern = re.compile(
        rf"(?<![a-z0-9_+#.]){re.escape(target)}(?![a-z0-9_+#.])",
        re.IGNORECASE,
    )
    return len(pattern.findall(normalized))


def _profile_sort_key(profile: UniversityProfile) -> tuple[int, str]:
    return (UNIVERSITY_PROFILE_ORDER.get(profile.id, len(UNIVERSITY_PROFILE_ORDER)), profile.id)


def list_university_profiles() -> list[UniversityProfile]:
    return sorted(UNIVERSITY_PROFILES, key=_profile_sort_key)


def list_university_profiles_by_group(group: str) -> list[UniversityProfile]:
    normalized = safe_lower(group)
    profiles = [profile for profile in UNIVERSITY_PROFILES if normalized in profile.group_set()]
    return sorted(profiles, key=_profile_sort_key)


def get_university_profile(identifier: str | None) -> UniversityProfile | None:
    if not identifier:
        return None
    school_id = UNIVERSITY_ALIAS_TO_ID.get(safe_lower(identifier))
    if school_id:
        return UNIVERSITY_PROFILE_BY_ID.get(school_id)
    return None


def get_university_aliases(identifier: str | None) -> list[str]:
    profile = get_university_profile(identifier)
    if not profile:
        return [identifier] if identifier else []
    return profile.all_aliases()


def profile_in_group(profile: UniversityProfile | None, group: str | None) -> bool:
    if profile is None or not group:
        return False
    return safe_lower(group) in profile.group_set()


def group_for_school_scope(scope_kind: str | None) -> SchoolGroup | None:
    if not scope_kind:
        return None
    return SCOPE_TO_GROUP.get(scope_kind)


def is_broad_school_scope(scope_kind: str | None) -> bool:
    return bool(scope_kind and scope_kind in BROAD_SCHOOL_SCOPE_KINDS)


def _match_profile(text: str, profile: UniversityProfile) -> UniversityMatch | None:
    def alias_priority(alias: str) -> tuple[int, int]:
        lowered = safe_lower(alias)
        if lowered == safe_lower(profile.canonical_name):
            return (0, -len(alias))
        if lowered == safe_lower(profile.english_name):
            return (1, -len(alias))
        return (2, -len(alias))

    matched_aliases: list[str] = []
    ambiguous_aliases: list[str] = []
    evidence: list[str] = []
    has_canonical_name = False
    has_english_name = False
    ambiguous_alias_set = profile.ambiguous_alias_set()

    for alias in sorted(profile.all_aliases(), key=alias_priority):
        count = count_university_term_occurrences(text, alias)
        if count <= 0:
            continue
        if any(
            not alias.isascii() and not matched_alias.isascii() and alias in matched_alias
            for matched_alias in matched_aliases
        ):
            continue
        matched_aliases.append(alias)
        if safe_lower(alias) == safe_lower(profile.canonical_name):
            has_canonical_name = True
        if safe_lower(alias) == safe_lower(profile.english_name):
            has_english_name = True
        if safe_lower(alias) in ambiguous_alias_set:
            ambiguous_aliases.append(alias)
        evidence.append(f"query contains `{alias}`")

    if not matched_aliases:
        return None

    return UniversityMatch(
        profile=profile,
        matched_aliases=unique_preserve_order(matched_aliases),
        ambiguous_aliases=unique_preserve_order(ambiguous_aliases),
        evidence=unique_preserve_order(evidence),
        has_canonical_name=has_canonical_name,
        has_english_name=has_english_name,
    )


def detect_university_matches(query: str) -> list[UniversityMatch]:
    matches = [
        match
        for profile in list_university_profiles()
        if (match := _match_profile(query, profile)) is not None
    ]
    matches.sort(key=lambda match: (-match.score(), _profile_sort_key(match.profile)))
    return matches


def detect_universities(query: str) -> list[UniversityProfile]:
    return [match.profile for match in detect_university_matches(query)]


def find_university(text: str) -> str | None:
    matches = detect_university_matches(text)
    if not matches:
        return None
    return matches[0].profile.canonical_name


def find_university_mentions(text: str) -> list[str]:
    return [match.profile.canonical_name for match in detect_university_matches(text)]


def detect_school_scope(query: str, matches: list[UniversityMatch] | None = None) -> SchoolScope:
    detected_matches = matches if matches is not None else detect_university_matches(query)
    if len(detected_matches) == 1:
        match = detected_matches[0]
        return SchoolScope(
            kind="specific_school",
            evidence=[f"query explicitly mentions {match.profile.canonical_name}"],
        )
    if len(detected_matches) > 1:
        return SchoolScope(
            kind="multiple_schools",
            evidence=[f"query mentions {len(detected_matches)} schools"],
        )

    lowered = safe_lower(query)
    if re.search(r"c\s*9", lowered) or "九校联盟" in query:
        return SchoolScope(kind="c9", evidence=["query mentions C9"])
    if "985" in lowered:
        return SchoolScope(kind="project_985", evidence=["query mentions 985"])
    if "211" in lowered:
        return SchoolScope(kind="project_211", evidence=["query mentions 211"])
    if "双一流" in query or "double first class" in lowered:
        return SchoolScope(kind="double_first_class", evidence=["query mentions 双一流"])
    broad_terms = [term for term in ("高校", "大学") if university_term_in_text(query, term)]
    if broad_terms:
        return SchoolScope(
            kind="broad_university",
            evidence=[f"query mentions broad university scope term `{broad_terms[0]}`"],
        )
    return SchoolScope(kind="none", evidence=[])


def school_query_terms(profile: UniversityProfile) -> dict[str, list[str]]:
    aliases = profile.all_aliases()
    ascii_abbreviations = [
        alias
        for alias in aliases
        if alias.isascii() and len(alias.replace(".", "")) <= 5 and " " not in alias
    ]
    chinese_short_aliases = [
        alias for alias in aliases if not alias.isascii() and alias != profile.canonical_name and len(alias) <= 4
    ]

    canonical_terms = [profile.canonical_name]
    abbreviation_terms = unique_preserve_order([*ascii_abbreviations, *chinese_short_aliases])
    english_terms = [profile.english_name]
    fallback_terms = unique_preserve_order(
        [*profile.github_keywords, *chinese_short_aliases, *ascii_abbreviations, *aliases]
    )

    return {
        "canonical": canonical_terms[:1],
        "abbreviation": abbreviation_terms[:2],
        "english": english_terms[:1],
        "fallback": fallback_terms[:3],
    }
