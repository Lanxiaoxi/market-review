import apiClient from "./client";
import type {
  JournalResponse,
  OrderFormValues,
  TradeOrder,
} from "@/types/journal";

/** 组装订单 multipart 表单（注意：后端 Form 字段为 snake_case） */
export function buildOrderFormData(
  values: OrderFormValues,
  image?: File | null
): FormData {
  const fd = new FormData();
  fd.append("symbol", values.symbol.trim());
  fd.append("trade_date", values.tradeDate);
  fd.append("amount", values.amount);
  fd.append("pnl_type", values.pnlType);
  fd.append("open_logic", values.openLogic);
  fd.append("close_logic", values.closeLogic);
  fd.append("note", values.note);
  if (image) fd.append("image", image);
  return fd;
}

export async function fetchJournal(): Promise<JournalResponse> {
  const { data } = await apiClient.get<JournalResponse>("/orders");
  return data;
}

export async function createOrder(formData: FormData): Promise<TradeOrder> {
  const { data } = await apiClient.post<TradeOrder>("/orders", formData);
  return data;
}

export async function updateOrder(
  id: number,
  formData: FormData
): Promise<TradeOrder> {
  const { data } = await apiClient.put<TradeOrder>(`/orders/${id}`, formData);
  return data;
}

export async function deleteOrder(id: number): Promise<void> {
  await apiClient.delete(`/orders/${id}`);
}
