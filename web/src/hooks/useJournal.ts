import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createOrder,
  deleteOrder,
  fetchJournal,
  updateOrder,
} from "@/api/journal";
import type { JournalResponse } from "@/types/journal";

/** 订单复盘列表 + 汇总查询 */
export function useJournalQuery() {
  return useQuery<JournalResponse>({
    queryKey: ["journal"],
    queryFn: fetchJournal,
  });
}

function useInvalidateJournal() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["journal"] });
}

/** 新建订单 → 落库 + 刷新 */
export function useCreateOrder() {
  const invalidate = useInvalidateJournal();
  return useMutation({
    mutationFn: (formData: FormData) => createOrder(formData),
    onSuccess: invalidate,
  });
}

/** 编辑订单 → 落库 + 刷新 */
export function useUpdateOrder() {
  const invalidate = useInvalidateJournal();
  return useMutation({
    mutationFn: ({ id, formData }: { id: number; formData: FormData }) =>
      updateOrder(id, formData),
    onSuccess: invalidate,
  });
}

/** 删除订单（连带截图）→ 刷新 */
export function useDeleteOrder() {
  const invalidate = useInvalidateJournal();
  return useMutation({
    mutationFn: (id: number) => deleteOrder(id),
    onSuccess: invalidate,
  });
}
