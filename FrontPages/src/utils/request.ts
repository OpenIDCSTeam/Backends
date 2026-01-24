import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { message } from 'antd';
import type { ApiResponse } from '@/types';

// 创建axios实例
const request: AxiosInstance = axios.create({
  baseURL: '', // 不设置baseURL，直接使用完整路径（/api会被Vite代理处理）
  timeout: 30000, // 请求超时时间30秒
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 从localStorage获取token并添加到请求头
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    console.error('请求错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
request.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const res = response.data;

    // 如果返回的状态码不是200，则认为是错误
    if (res.code !== 200) {
      // 显示错误消息
      message.error(res.msg || '请求失败');

      // 401: 未授权，跳转到登录页
      if (res.code === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }

      // 403: 权限不足
      if (res.code === 403) {
        message.error('权限不足，无法执行此操作');
      }

      return Promise.reject(new Error(res.msg || '请求失败'));
    }

    // 返回数据
    return response;
  },
  (error: AxiosError<ApiResponse>) => {
    console.error('响应错误:', error);

    // 处理网络错误
    if (!error.response) {
      message.error('网络连接失败，请检查网络设置');
      return Promise.reject(error);
    }

    // 处理HTTP错误状态码
    const { status, data } = error.response;
    
    switch (status) {
      case 400:
        message.error(data?.msg || '请求参数错误');
        break;
      case 401:
        message.error('未授权，请重新登录');
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        break;
      case 403:
        message.error('权限不足');
        break;
      case 404:
        message.error('请求的资源不存在');
        break;
      case 500:
        message.error(data?.msg || '服务器内部错误');
        break;
      case 502:
        message.error('网关错误');
        break;
      case 503:
        message.error('服务暂时不可用');
        break;
      default:
        message.error(data?.msg || `请求失败 (${status})`);
    }

    return Promise.reject(error);
  }
);

// 导出请求方法
export default request;

// 封装常用的请求方法
export const http = {
  // GET请求
  get: <T = any>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> => {
    return request.get<ApiResponse<T>>(url, config).then(res => res.data);
  },

  // POST请求
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> => {
    return request.post<ApiResponse<T>>(url, data, config).then(res => res.data);
  },

  // PUT请求
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> => {
    return request.put<ApiResponse<T>>(url, data, config).then(res => res.data);
  },

  // DELETE请求
  delete: <T = any>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> => {
    return request.delete<ApiResponse<T>>(url, config).then(res => res.data);
  },

  // PATCH请求
  patch: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> => {
    return request.patch<ApiResponse<T>>(url, data, config).then(res => res.data);
  },
};
