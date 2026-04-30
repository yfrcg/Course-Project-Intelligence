from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "course-project-intelligence-mcp-server"
    app_env: str = "dev"
    log_level: str = "INFO"

    github_token: str | None = None
    github_api_base: str = "https://api.github.com"
    github_timeout_seconds: float = 20.0

    # Current release scope is GitHub-only.
    enable_github: bool = True
    enable_gitee: bool = False
    enable_web_seed: bool = False

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
        "(education-use; public-github-repositories; contact=local-dev)"
    )
    seed_sites: List[str] = Field(
        default_factory=lambda: [
            "https://github.com/topics/course-project",
            "https://github.com/topics/education",
            "https://github.com/topics/computer-science",
        ]
    )
    trusted_domains: List[str] = Field(default_factory=lambda: ["github.com"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
