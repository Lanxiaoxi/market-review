"""
订单复盘接口测试（独立临时库 + 独立临时上传目录）
覆盖：CRUD 往返（含图片落盘/随删除清理）、图片必填与格式限制、
盈亏校验、统计汇总口径。
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

transport = ASGITransport(app=app)

# 1x1 红色 PNG 最小字节流（后端不校验真实图像内容，仅按扩展名/大小放行）
FAKE_PNG = (
    b"\x89PNG\r\n\x1a\n" + b"\x00" * 128
)


@pytest_asyncio.fixture(autouse=True)
async def _tmp_uploads(monkeypatch, tmp_path):
    """上传目录指向临时目录，避免测试污染开发环境 api/data/uploads"""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    import app.config as config_mod
    import app.routers.journal as journal_mod

    monkeypatch.setattr(config_mod, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(journal_mod, "UPLOAD_DIR", upload_dir)
    yield upload_dir


def _order_form(**overrides):
    data = {
        "symbol": "贵州茅台",
        "trade_date": "2026-09-08",
        "amount": "12500",          # 元
        "pnl_type": "win",
        "open_logic": "放量突破",
        "close_logic": "止盈离场",
        "note": "回踩均线企稳后放量突破前高，持有 3 天分批止盈。",
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_journal_crud_roundtrip(tmp_path, _tmp_uploads):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 创建（带必填图片）
        resp = await client.post(
            "/api/orders",
            data=_order_form(),
            files={"image": ("kline.png", FAKE_PNG, "image/png")},
        )
        assert resp.status_code == 201, resp.text
        created = resp.json()
        assert created["symbol"] == "贵州茅台"
        assert created["pnl"] == 12500
        assert created["imageUrl"].startswith("/uploads/orders/")

        # 图片确实落盘
        rel = created["imageUrl"].replace("/uploads/", "")
        stored = (_tmp_uploads / rel)
        assert stored.exists() and stored.stat().st_size > 0

        order_id = created["id"]

        # 列表 + 汇总（1 笔盈利）
        listed = (await client.get("/api/orders")).json()
        assert any(i["id"] == order_id for i in listed["items"])
        summary = listed["summary"]
        assert summary["total"] == 1
        assert summary["winCount"] == 1
        assert summary["winRate"] == 100.0
        assert summary["totalPnl"] == 12500

        # 更新：换字段不换图（表单不带 image 字段）
        up = await client.put(
            f"/api/orders/{order_id}",
            data=_order_form(symbol="五粮液", amount="8000", pnl_type="loss", note="更新后的笔记"),
        )
        assert up.status_code == 200, up.text
        updated = up.json()
        assert updated["symbol"] == "五粮液"
        assert updated["pnl"] == -8000
        assert updated["imageUrl"] == created["imageUrl"]  # 图未动

        # 更新：换图 → 旧文件被清理、新文件落盘
        up2 = await client.put(
            f"/api/orders/{order_id}",
            data=_order_form(),
            files={"image": ("new.png", FAKE_PNG, "image/png")},
        )
        assert up2.status_code == 200, up2.text
        new_url = up2.json()["imageUrl"]
        assert new_url != created["imageUrl"]
        assert (_tmp_uploads / created["imageUrl"].replace("/uploads/", "")).exists() is False
        assert (_tmp_uploads / new_url.replace("/uploads/", "")).exists()

        # 删除 → 行与文件一起清理
        dele = await client.delete(f"/api/orders/{order_id}")
        assert dele.status_code == 204
        assert (_tmp_uploads / new_url.replace("/uploads/", "")).exists() is False
        after = (await client.get("/api/orders")).json()
        assert after["summary"]["total"] == 0
        assert all(i["id"] != order_id for i in after["items"])


@pytest.mark.asyncio
async def test_journal_image_required_and_validation():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 缺图片 → 422
        resp = await client.post("/api/orders", data=_order_form())
        assert resp.status_code == 422, resp.text

        # 非图片扩展名 → 422
        resp = await client.post(
            "/api/orders",
            data=_order_form(),
            files={"image": ("note.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 422, resp.text

        # 超过 5MB → 413
        big = b"\x89PNG" + b"\x00" * (5 * 1024 * 1024 + 64)
        resp = await client.post(
            "/api/orders",
            data=_order_form(),
            files={"image": ("big.png", big, "image/png")},
        )
        assert resp.status_code == 413, resp.text


@pytest.mark.asyncio
async def test_journal_pnl_validation():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 金额 ≤ 0 → 422
        resp = await client.post(
            "/api/orders",
            data=_order_form(amount="0"),
            files={"image": ("k.png", FAKE_PNG, "image/png")},
        )
        assert resp.status_code == 422, resp.text

        # 盈亏类型非法 → 422
        resp = await client.post(
            "/api/orders",
            data=_order_form(pnl_type="flat"),
            files={"image": ("k.png", FAKE_PNG, "image/png")},
        )
        assert resp.status_code == 422, resp.text

        # 必填文本缺失 → 422
        resp = await client.post(
            "/api/orders",
            data=_order_form(symbol="  "),
            files={"image": ("k.png", FAKE_PNG, "image/png")},
        )
        assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_journal_summary_counts_win_loss_flat():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rows = [
            ("win", "1.0"),
            ("loss", "0.5"),
            ("win", "2.0"),
        ]
        for i, (pt, amt) in enumerate(rows):
            resp = await client.post(
                "/api/orders",
                data=_order_form(symbol=f"标的{i}", amount=amt, pnl_type=pt),
                files={"image": (f"k{i}.png", FAKE_PNG, "image/png")},
            )
            assert resp.status_code == 201, resp.text

        summary = (await client.get("/api/orders")).json()["summary"]
        assert summary["total"] == 3
        assert summary["winCount"] == 2
        assert summary["lossCount"] == 1
        assert summary["winRate"] == 66.7
        assert summary["totalPnl"] == 2.5  # +1.0 -0.5 +2.0
