from __future__ import annotations  # 让类型标注延后解析，减少模块互相引用时的导入压力。

from functools import lru_cache  # 用缓存保留同一份配置对象，避免重复读取环境变量。
from typing import List

from pydantic import Field  # 列表字段要用 Field 包装默认工厂，避免多个实例共享同一个列表。
from pydantic_settings import BaseSettings, SettingsConfigDict  # 负责把 .env 和环境变量映射成配置类。

"""
这段代码是项目的配置管理模块。
它集中定义了运行时会用到的开关、超时、种子站点和 provider 配置。
"""


class Settings(BaseSettings):  # 继承 BaseSettings 后，字段值会优先从 .env 和环境变量里读取。
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )  # 这里定义配置读取规则：忽略未知字段，且大小写不敏感。

    # 这些字段是应用本身的基础配置。
    app_name: str = "course-project-intelligence-mcp-server"
    app_env: str = "dev"
    log_level: str = "INFO"

    # 这组字段只服务于 GitHub provider。
    github_token: str | None = None
    github_api_base: str = "https://api.github.com"
    github_timeout_seconds: float = 20.0

    # 这三个开关控制不同 provider 是否参与检索。
    enable_github: bool = True
    enable_gitee: bool = True
    enable_web_seed: bool = True

    # 这组参数控制默认返回量和抓取范围，避免一次请求扫得太重。
    default_top_k: int = 5
    max_top_k: int = 20
    request_timeout_seconds: float = 15.0
    max_seed_sites: int = 8
    max_links_per_seed: int = 30
    max_schools_per_broad_query: int = 10
    per_school_candidate_budget: int = 2
    max_total_candidates: int = 30
    max_results_per_school_in_top: int = 2
    user_agent: str = (
        "CourseProjectIntelligenceMCP/1.0.0rc1 "
        "(education-use; public-web-indexing; contact=local-dev)"
    )  # 所有对外 HTTP 请求都会带这个 User-Agent，方便对方站点识别来源。

    seed_sites: List[str] = Field(
        default_factory=lambda: [
            "https://cc.nankai.edu.cn/",
            "https://github.com/topics/course-project",
            "https://github.com/topics/nankai",
            "https://gitee.com/explore",
        ]
    )  # 这些站点是 Web seed provider 做公开资源发现时的默认起点。

    trusted_domains: List[str] = Field(
        default_factory=lambda: [
            "nankai.edu.cn",
            "cc.nankai.edu.cn",
            "github.com",
            "gitee.com",
            "gitlab.com",
            "csdn.net",
            "cnblogs.com",
        ]
    )  # 这里保留一份可信域名名单，便于后续扩展白名单策略。


@lru_cache(maxsize=1)  # 进程内只保留一份 Settings，调用方拿到的始终是同一个配置实例。
def get_settings() -> Settings:
    return Settings()
