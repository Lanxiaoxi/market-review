import axios from "axios";

const apiClient = axios.create({
  baseURL: "/api",
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

// 请求拦截：FormData（multipart 上传）必须移除全局默认的 Content-Type:
// application/json —— 否则请求以 JSON 头发出、无 boundary，
// 后端 request.form() 解析不到任何字段/文件（返回 7× Field required）。
// 删除后由浏览器自动生成带 boundary 的 multipart/form-data。
apiClient.interceptors.request.use((config) => {
  if (config.data instanceof FormData) {
    config.headers.delete("Content-Type");
  }
  return config;
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