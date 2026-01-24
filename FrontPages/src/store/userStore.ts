import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/types';

// 用户状态接口
interface UserState {
  user: User | null; // 当前用户信息
  token: string | null; // 认证token
  isAuthenticated: boolean; // 是否已认证
  setUser: (user: User | null) => void; // 设置用户信息
  setToken: (token: string | null) => void; // 设置token
  logout: () => void; // 登出
}

// 创建用户状态store
export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      // 设置用户信息
      setUser: (user) => set({ user, isAuthenticated: !!user }),

      // 设置token
      setToken: (token) => {
        if (token) {
          localStorage.setItem('token', token);
        } else {
          localStorage.removeItem('token');
        }
        set({ token, isAuthenticated: !!token });
      },

      // 登出
      logout: () => {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        set({ user: null, token: null, isAuthenticated: false });
      },
    }),
    {
      name: 'user-storage', // localStorage中的key名称
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);