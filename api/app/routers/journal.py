"""CRUD /api/orders —— 订单复盘（写接口受 API Token 保护）

创建/编辑走 multipart/form-data：文本字段 + 1 张必填截图。
图片落盘到 UPLOAD_DIR/orders/YYYYMM/，DB 只存相对路径，经 /uploads 静态服务访问。
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import require_api_token
from app.config import UPLOAD_DIR
from app.models.db import get_session
from app.models.journal import TradeOrder
from app.schemas.journal import JournalResponse, JournalSummaryOut, OrderOut

logger = logging.getLogger(__name__)

router = APIRouter(tags=["订单复盘"])

# 图片约束：单张、≤5MB、常见位图格式
MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
PNL_TYPES = {"win", "loss"}
TRADE_DATE_PATTERN = "YYYY-MM-DD"
_MAX_TEXT_LEN = {
    "symbol": 32,
    "open_logic": 32,
    "close_logic": 32,
    "note": 2000,
}


def _safe_ext(filename: str | None) -> str:
    ext = Path(filename or "").suffix.lower()
    return ext if ext in ALLOWED_EXT else ""


def _clean_text(value: str | None, field: str, required: bool = False) -> str:
    """去空白 + 长度上限校验（用于 Form 字段）"""
    text = (value or "").strip()
    if required and not text:
        raise HTTPException(422, f"{field} 不能为空")
    if len(text) > _MAX_TEXT_LEN[field]:
        raise HTTPException(422, f"{field} 过长（最多 {_MAX_TEXT_LEN[field]} 字）")
    return text


def _valid_trade_date(value: str) -> str:
    """校验 YYYY-MM-DD（宽松按长度+分隔符，具体日期合法性交给前端 date 控件）"""
    if len(value) != 10 or value[4] != "-" or value[7] != "-":
        raise HTTPException(422, f"订单日期格式应为 {TRADE_DATE_PATTERN}")
    return value


def _parse_pnl(amount: str | None, pnl_type: str | None) -> float:
    """正数金额（元）+ 盈亏类型 → 带符号盈亏（元，正盈负亏）"""
    if amount is None or pnl_type is None:
        raise HTTPException(422, "盈亏金额与类型必须一起提交")
    try:
        value = float(amount)
    except (TypeError, ValueError):
        raise HTTPException(422, "盈亏金额必须是数字") from None
    if value <= 0:
        raise HTTPException(422, "盈亏金额必须大于 0")
    if pnl_type not in PNL_TYPES:
        raise HTTPException(422, "盈亏类型必须为 win（盈利）或 loss（亏损）")
    return round(value, 2) if pnl_type == "win" else round(-value, 2)


async def _save_image(file: UploadFile, trade_date: str) -> str:
    """校验图片并落盘，返回相对 UPLOAD_DIR 的路径（如 orders/202609/xxx.png）"""
    ext = _safe_ext(file.filename)
    if not ext:
        raise HTTPException(422, "仅支持 jpg / png / webp / gif / bmp 图片")
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "图片不能超过 5MB")
    if not content:
        raise HTTPException(422, "图片内容为空")

    # 由订单日期取 YYYYMM 作分目录（如 2026-09-08 → orders/202609/）
    month = (trade_date or datetime.now().strftime("%Y%m%d")).replace("-", "")[:6]
    rel_dir = f"orders/{month}"
    (UPLOAD_DIR / rel_dir).mkdir(parents=True, exist_ok=True)
    name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}{ext}"
    (UPLOAD_DIR / rel_dir / name).write_bytes(content)
    return f"{rel_dir}/{name}"


def _delete_image(rel_path: str) -> None:
    """删除订单截图（仅限 UPLOAD_DIR 内，防路径穿越）"""
    if not rel_path:
        return
    target = (UPLOAD_DIR / rel_path).resolve()
    if not target.is_relative_to(UPLOAD_DIR.resolve()):
        logger.warning("[Journal] 拒绝删除越界路径: %s", rel_path)
        return
    try:
        target.unlink(missing_ok=True)
    except OSError as e:  # 文件删除失败不应阻塞主流程
        logger.warning("[Journal] 删除图片失败 %s: %s", rel_path, e)


def _to_out(order: TradeOrder) -> OrderOut:
    return OrderOut(
        id=order.id,
        symbol=order.symbol,
        trade_date=order.trade_date,
        pnl=round(order.pnl, 2),
        open_logic=order.open_logic,
        close_logic=order.close_logic,
        note=order.note,
        image_url=f"/uploads/{order.image_path}" if order.image_path else "",
    )


async def _build_response(session: AsyncSession) -> JournalResponse:
    stmt = select(TradeOrder).order_by(
        TradeOrder.trade_date.desc(), TradeOrder.id.desc()
    )
    rows = (await session.execute(stmt)).scalars().all()

    total = len(rows)
    win = sum(1 for r in rows if r.pnl > 0)
    loss = sum(1 for r in rows if r.pnl < 0)
    summary = JournalSummaryOut(
        total=total,
        win_count=win,
        loss_count=loss,
        win_rate=round(win / total * 100, 1) if total else 0.0,
        total_pnl=round(sum(r.pnl for r in rows), 2),
    )
    return JournalResponse(items=[_to_out(r) for r in rows], summary=summary)


@router.get("/orders", response_model=JournalResponse)
async def list_orders(session: AsyncSession = Depends(get_session)):
    return await _build_response(session)


@router.post(
    "/orders",
    response_model=OrderOut,
    status_code=201,
    dependencies=[Depends(require_api_token)],
)
async def create_order(
    symbol: str = Form(...),
    trade_date: str = Form(...),
    amount: str = Form(...),          # 正数（元）
    pnl_type: str = Form(...),        # win | loss
    open_logic: str = Form(...),
    close_logic: str = Form(...),
    note: str = Form(""),
    image: UploadFile = File(...),    # 必填截图
    session: AsyncSession = Depends(get_session),
):
    order = TradeOrder(
        symbol=_clean_text(symbol, "symbol", required=True),
        trade_date=_valid_trade_date(trade_date),
        pnl=_parse_pnl(amount, pnl_type),
        open_logic=_clean_text(open_logic, "open_logic", required=True),
        close_logic=_clean_text(close_logic, "close_logic", required=True),
        note=_clean_text(note, "note"),
        image_path=await _save_image(image, trade_date),
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return _to_out(order)


@router.put(
    "/orders/{order_id}",
    response_model=OrderOut,
    dependencies=[Depends(require_api_token)],
)
async def update_order(
    order_id: int,
    symbol: Optional[str] = Form(None),
    trade_date: Optional[str] = Form(None),
    amount: Optional[str] = Form(None),
    pnl_type: Optional[str] = Form(None),
    open_logic: Optional[str] = Form(None),
    close_logic: Optional[str] = Form(None),
    note: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),  # 不传 = 保留原图
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(TradeOrder).where(TradeOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(404, "订单不存在")

    # 换图：先落新图成功，再删旧图（避免新图失败时旧图已丢）
    if image is not None and image.filename:
        new_path = await _save_image(image, trade_date or order.trade_date)
        old_path = order.image_path
        order.image_path = new_path
        _delete_image(old_path)

    if symbol is not None:
        order.symbol = _clean_text(symbol, "symbol", required=True)
    if trade_date is not None:
        order.trade_date = _valid_trade_date(trade_date)
    if amount is not None or pnl_type is not None:
        order.pnl = _parse_pnl(amount, pnl_type)
    if open_logic is not None:
        order.open_logic = _clean_text(open_logic, "open_logic", required=True)
    if close_logic is not None:
        order.close_logic = _clean_text(close_logic, "close_logic", required=True)
    if note is not None:
        order.note = _clean_text(note, "note")

    session.add(order)
    await session.commit()
    await session.refresh(order)
    return _to_out(order)


@router.delete(
    "/orders/{order_id}",
    status_code=204,
    dependencies=[Depends(require_api_token)],
)
async def delete_order(
    order_id: int,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(TradeOrder).where(TradeOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(404, "订单不存在")
    image_path = order.image_path
    await session.delete(order)
    await session.commit()
    _delete_image(image_path)
