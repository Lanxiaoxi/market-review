"""可选写接口鉴权：配置 API_TOKEN 后，写操作需携带 X-API-Token 头"""

from fastapi import Header, HTTPException

from app.config import get_settings


def require_api_token(x_api_token: str | None = Header(default=None)):
    """写接口保护依赖。

    - 未配置 API_TOKEN（默认）→ 免鉴权（个人单用户）；
    - 已配置 → 请求必须携带 X-API-Token: <token>，否则 401。
    读取类接口不做限制。
    """
    settings = get_settings()
    if not settings.has_api_token:
        return
    if not x_api_token or x_api_token != settings.api_token:
        raise HTTPException(401, "无效或缺失的 API Token")
