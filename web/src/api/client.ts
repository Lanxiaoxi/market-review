import axios from "axios";

const apiClient = axios.create({
  baseURL: "/api",
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

// 响应拦截：统一错误处理
apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response) {
      console.warn(
        `[API] ${error.response.status} ${error.response.config?.url}`
      );
    } else if (error.request) {
      console.warn("[API] 无响应", error.config?.url);
    }
    return Promise.reject(error);
  }
);

export default apiClient;