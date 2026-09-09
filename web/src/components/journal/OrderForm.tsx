import {
  useRef,
  useState,
  type ClipboardEvent as ReactClipboardEvent,
} from "react";
import { isAxiosError } from "axios";
import Segmented from "@/components/common/Segmented";
import PillButton from "@/components/common/PillButton";
import {
  CLOSE_LOGIC_OPTIONS,
  OPEN_LOGIC_OPTIONS,
  PNL_TYPE_OPTIONS,
  type PnlType,
} from "@/constants/journal";
import { useCreateOrder, useUpdateOrder } from "@/hooks/useJournal";
import type { OrderFormValues, TradeOrder } from "@/types/journal";
import { buildOrderFormData } from "@/api/journal";
import styles from "./OrderReview.module.css";

interface OrderFormProps {
  /** 编辑模式传订单；新建为 null */
  initial?: TradeOrder | null;
  /** 保存成功回调（编辑模式会带回最新订单） */
  onDone?: (order?: TradeOrder) => void;
  onCancel: () => void;
}

function todayStr(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function errText(e: unknown): string {
  if (isAxiosError(e)) {
    const detail = (e.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const msgs = detail
        .map((x) => (x && typeof x === "object" && "msg" in x ? String((x as { msg: unknown }).msg) : ""))
        .filter(Boolean);
      if (msgs.length) return msgs.join("；");
    }
    return e.message || "保存失败";
  }
  return "保存失败";
}

const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
/** 剪贴板 MIME → 扩展名（后端按扩展名白名单校验） */
const MIME_TO_EXT: Record<string, string> = {
  "image/png": "png",
  "image/jpeg": "jpg",
  "image/webp": "webp",
  "image/gif": "gif",
  "image/bmp": "bmp",
};

export default function OrderForm({ initial, onDone, onCancel }: OrderFormProps) {
  const isEdit = Boolean(initial);
  const createMut = useCreateOrder();
  const updateMut = useUpdateOrder();
  const busy = createMut.isPending || updateMut.isPending;

  const [symbol, setSymbol] = useState(initial?.symbol ?? "");
  const [tradeDate, setTradeDate] = useState(initial?.tradeDate ?? todayStr());
  const [pnlType, setPnlType] = useState<PnlType>(
    initial && initial.pnl < 0 ? "loss" : "win"
  );
  const [amount, setAmount] = useState(
    initial ? String(Math.abs(initial.pnl)) : ""
  );
  const [openLogic, setOpenLogic] = useState(
    initial?.openLogic || OPEN_LOGIC_OPTIONS[0]
  );
  const [closeLogic, setCloseLogic] = useState(
    initial?.closeLogic || CLOSE_LOGIC_OPTIONS[0]
  );
  const [note, setNote] = useState(initial?.note ?? "");
  // file：新建/换图时携带的新文件；preview：当前展示图（edit 初始为原图 URL）
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(initial?.imageUrl ?? null);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const pickFile = (f: File | undefined | null) => {
    if (!f) return;
    if (f.size > MAX_IMAGE_BYTES) {
      setError("图片不能超过 5MB");
      return;
    }
    if (!f.type.startsWith("image/")) {
      setError("请选择图片文件（jpg / png / webp / gif / bmp）");
      return;
    }
    setError(null);
    if (preview?.startsWith("blob:")) URL.revokeObjectURL(preview);
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  /** 截图后直接在表单内 Ctrl+V 粘贴（剪贴板图片自动填入） */
  const handlePaste = (e: ReactClipboardEvent<HTMLDivElement>) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    let imageItem: DataTransferItem | null = null;
    for (const item of Array.from(items)) {
      if (item.kind === "file" && item.type.startsWith("image/")) {
        imageItem = item;
        break;
      }
    }
    if (!imageItem) return;
    const pasted = imageItem.getAsFile();
    if (!pasted) return;
    e.preventDefault(); // 阻止把图片当文本插入（如在笔记框内粘贴）
    // 剪贴板文件常无合法文件名，按 MIME 补名，保证扩展名校验通过
    const mime = pasted.type.toLowerCase();
    const ext = MIME_TO_EXT[mime] ?? "png";
    const named = new File([pasted], `paste_${Date.now()}.${ext}`, { type: mime });
    pickFile(named);
  };

  const clearImage = () => {
    if (preview?.startsWith("blob:")) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview(initial?.imageUrl ?? null);
  };

  const submit = async () => {
    setError(null);
    if (!symbol.trim()) {
      setError("请填写标的名");
      return;
    }
    if (!tradeDate) {
      setError("请选择订单日期");
      return;
    }
    const amt = parseFloat(amount);
    if (!Number.isFinite(amt) || amt <= 0) {
      setError("盈亏金额需为大于 0 的数字（单位：元）");
      return;
    }
    if (!file && !preview) {
      setError("请上传订单截图");
      return;
    }

    const values: OrderFormValues = {
      symbol,
      tradeDate,
      amount: String(amt),
      pnlType,
      openLogic,
      closeLogic,
      note,
    };
    try {
      if (isEdit && initial) {
        const updated = await updateMut.mutateAsync({
          id: initial.id,
          formData: buildOrderFormData(values, file),
        });
        onDone?.(updated);
      } else {
        const created = await createMut.mutateAsync(buildOrderFormData(values, file));
        onDone?.(created);
      }
    } catch (e) {
      setError(errText(e));
    }
  };

  const selectStyle: React.CSSProperties = { width: 200 };
  const fullFieldStyle: React.CSSProperties = { flex: "1 1 100%" };

  return (
    <div
      style={{ display: "flex", flexDirection: "column", gap: 16 }}
      onPaste={handlePaste}
    >
      {/* 行 1：标的名 / 日期 */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "16px 20px" }}>
        <div className={styles.field}>
          <label className={styles.fieldLabel} htmlFor="jf-symbol">
            标的名 *
          </label>
          <input
            id="jf-symbol"
            className={styles.control}
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="如 600519 贵州茅台"
            style={{ width: 190 }}
            maxLength={32}
          />
        </div>

        <div className={styles.field}>
          <label className={styles.fieldLabel} htmlFor="jf-date">
            订单日期
          </label>
          <input
            id="jf-date"
            className={styles.control}
            type="date"
            value={tradeDate}
            onChange={(e) => setTradeDate(e.target.value)}
            style={{ width: 150 }}
          />
        </div>
      </div>

      {/* 行 2：盈亏金额 / 开仓逻辑 / 平仓逻辑 */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "16px 20px" }}>
        <div className={styles.field}>
          <label className={styles.fieldLabel} htmlFor="jf-amount">
            盈亏金额（元）*
          </label>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <input
              id="jf-amount"
              className={`${styles.control} ${styles.amountInput}`}
              inputMode="numeric"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="如 12500"
              style={{ width: 130 }}
            />
            <Segmented
              options={[...PNL_TYPE_OPTIONS]}
              value={pnlType}
              onChange={(v) => setPnlType(v as PnlType)}
              ariaLabel="盈亏类型"
            />
          </div>
        </div>

        <div className={styles.field}>
          <label className={styles.fieldLabel} htmlFor="jf-open">
            开仓逻辑 *
          </label>
          <select
            id="jf-open"
            className={styles.control}
            value={openLogic}
            onChange={(e) => setOpenLogic(e.target.value)}
            style={selectStyle}
          >
            {OPEN_LOGIC_OPTIONS.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.field}>
          <label className={styles.fieldLabel} htmlFor="jf-close">
            平仓逻辑 *
          </label>
          <select
            id="jf-close"
            className={styles.control}
            value={closeLogic}
            onChange={(e) => setCloseLogic(e.target.value)}
            style={selectStyle}
          >
            {CLOSE_LOGIC_OPTIONS.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 行 3：订单截图 */}
      <div className={styles.field} style={fullFieldStyle}>
        <span className={styles.fieldLabel}>
          订单截图 *（必填 1 张 · 点击选择，或截图后直接 Ctrl+V 粘贴 · ≤5MB）
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          {preview && (
            <img
              src={preview}
              alt="订单截图预览"
              className={styles.thumb}
              style={{ cursor: "zoom-in" }}
              onClick={() => fileInputRef.current?.click()}
            />
          )}
          <div
            className={styles.uploadBox}
            role="button"
            tabIndex={0}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
            }}
          >
            <svg width="14" height="14" viewBox="0 0 20 20" fill="none" aria-hidden>
              <rect x="2.5" y="4" width="15" height="12" rx="2" stroke="currentColor" strokeWidth="1.4" />
              <circle cx="7.5" cy="8.5" r="1.3" fill="currentColor" />
              <path d="M4 15 L8 10.5 L11 13 L14 9.5 L16 12" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {preview ? "更换图片" : "点击选择 / Ctrl+V 粘贴"}
          </div>
          {preview && (
            <button
              type="button"
              onClick={clearImage}
              style={{
                border: "none",
                background: "transparent",
                color: "var(--muted)",
                fontSize: 12,
                cursor: "pointer",
                fontFamily: "inherit",
                padding: 0,
              }}
            >
              {isEdit && !file ? "不更换" : "移除"}
            </button>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            style={{ display: "none" }}
            onChange={(e) => {
              pickFile(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
        </div>
      </div>

      {/* 行 4：订单笔记 */}
      <div className={styles.field} style={fullFieldStyle}>
        <label className={styles.fieldLabel} htmlFor="jf-note">
          订单笔记
        </label>
        <textarea
          id="jf-note"
          className={styles.control}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="记录这笔交易的思考：当时的判断依据、执行情况、可改进之处…"
          maxLength={2000}
        />
      </div>

      {/* 操作行 */}
      <div className={styles.formActions}>
        <PillButton onClick={submit} disabled={busy} style={{ opacity: busy ? 0.7 : 1 }}>
          {busy ? "提交中…" : isEdit ? "保存修改" : "确认新建"}
        </PillButton>
        <span
          role="button"
          tabIndex={0}
          onClick={onCancel}
          onKeyDown={(e) => e.key === "Enter" && onCancel()}
          style={{
            fontSize: 12,
            color: "var(--muted)",
            cursor: "pointer",
            fontFamily: "inherit",
            background: "none",
            border: "none",
            padding: "6px 2px",
          }}
        >
          取消
        </span>
        {error && <span className={styles.formError}>⚠ {error}</span>}
      </div>
    </div>
  );
}
