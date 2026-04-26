# Provider Development

本文说明如何在当前项目中新增一个 provider，而不破坏已有 MCP tools。

## 目标

新增 provider 时，应满足以下约束：

- 不改现有 4 个 MCP tools 的名称和输入输出
- 不移除已有 provider
- 不引入重依赖
- 输出仍然以学习参考和公开资料情报为边界

## 1. 实现 `BaseProvider`

在 `app/providers/` 下新增文件，例如 `my_provider.py`。

最小接口：

```python
from __future__ import annotations

from typing import Optional

from app.providers.base import BaseProvider
from app.schemas import ProviderSearchResult, QueryAnalysis


class MyProvider(BaseProvider):
    name = "my_provider"
    source_type = "web"

    async def search(
        self,
        analysis: QueryAnalysis,
        *,
        top_k: int = 5,
        allow_domains: Optional[list[str]] = None,
        deny_domains: Optional[list[str]] = None,
    ) -> list[ProviderSearchResult]:
        return []
```

可选实现：

```python
    async def get_project_brief(self, url: str) -> ProviderSearchResult | None:
        return None
```

## 2. 返回统一的 `ProviderSearchResult`

provider 不需要直接生成最终 MCP 输出，而是返回统一中间结构：

- `title`
- `url`
- `source`
- `source_type`
- `snippet`
- `metadata`

建议：

- `metadata` 放原始来源中的补充字段，如 stars、forks、topics、languages、更新时间。
- 不要在 provider 中直接拼最终 `risk_note` 或最终 `explanation`，这些由 core/ranking 统一生成。

## 3. 在 registry 中注册

将 provider 接入 `app/providers/registry.py`。

当前硬化版本中，registry 负责：

- 创建 provider 实例
- 按 `ENABLE_*` 开关过滤可用 provider
- 按 `source_types` 选择 provider
- 按 URL host 路由 brief provider

新增 provider 时应同步：

- 给 provider 一个稳定的 `name`
- 给 provider 一个明确的 `source_type`
- 在 registry 的构造逻辑中注册
- 在需要时补充配置开关

## 4. 配置项

如果 provider 需要新环境变量：

- 在 `app/config.py` 中新增设置项
- 在 `.env.example` 和 README 中补充说明
- 仅在确有必要时增加，不要堆积 provider 专属复杂配置

## 5. 失败处理

provider 是外部边界，必须按“失败可恢复”设计：

- 搜索失败时抛出异常是允许的，但 service/registry 上层必须能接住
- 不要因为单个 provider 失败导致整个 tool 失败
- 超时、限流、结构变化应尽量转成 warning 或空结果
- 如果 provider 还不完整，可以像 `GiteeProvider` 一样保留 MVP placeholder，但要明确 limitations

## 6. 测试建议

至少补以下测试之一：

- provider 单测：验证搜索结果映射到 `ProviderSearchResult`
- service 单测：验证该 provider 被 registry 选中并参与结果汇总
- brief 单测：验证 URL 能正确路由到对应 provider

推荐做法：

- 用 fake provider 替代真实网络请求
- 聚焦结构和行为，不依赖外部站点实时结果

## 7. 安全边界

新增 provider 时不要做这些事：

- 聚合“标准答案”
- 输出可直接提交的作业文本
- 绕过课程限制或平台访问限制
- 把项目定位成代写工具

provider 的职责是帮助发现公开资料、项目路线和学习线索，而不是帮助提交课程作业。
