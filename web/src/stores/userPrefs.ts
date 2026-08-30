import { create } from "zustand";
import { persist } from "zustand/middleware";
import { DEFAULT_SELECTED } from "@/constants/indices";

interface UserPrefs {
  /** 侧边栏昵称（头像取首字） */
  nickname: string;
  /** 首页分时对比默认勾选的指数 */
  selectedIndices: string[];
  setNickname: (name: string) => void;
  setSelectedIndices: (codes: string[]) => void;
}

/** 用户偏好（localStorage 持久化，单机自用，无需后端用户系统） */
export const useUserPrefs = create<UserPrefs>()(
  persist(
    (set) => ({
      nickname: "李复盘",
      selectedIndices: DEFAULT_SELECTED,
      setNickname: (name) => set({ nickname: name.trim() || "李复盘" }),
      setSelectedIndices: (codes) =>
        set({ selectedIndices: codes.length ? codes : DEFAULT_SELECTED }),
    }),
    { name: "market-review-user-prefs" }
  )
);
