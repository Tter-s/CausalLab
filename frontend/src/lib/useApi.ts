"use client";
/** 轻量数据获取 hooks（SWR 风格，不引入额外依赖）。 */
import { useCallback, useEffect, useRef, useState } from "react";
import { api, get } from "./api";

export interface ApiState<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
  refresh: () => Promise<void>;
  setData: (v: T | null) => void;
}

export function useApi<T>(path: string | null, deps: unknown[] = []): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState<boolean>(!!path);
  const mounted = useRef(true);
  const pathRef = useRef(path);
  pathRef.current = path;

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const load = useCallback(async () => {
    const p = pathRef.current;
    if (!p) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const v = await get<T>(p);
      if (mounted.current) setData(v);
    } catch (e) {
      if (mounted.current) setError(e as Error);
    } finally {
      if (mounted.current) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path]);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps]);

  return { data, error, loading, refresh: load, setData };
}

/** 触发一次变更请求并自动刷新关联查询。 */
export function useMutation() {
  const [pending, setPending] = useState(false);
  const run = useCallback(async (fn: () => Promise<unknown>): Promise<boolean> => {
    setPending(true);
    try {
      await fn();
      return true;
    } finally {
      setPending(false);
    }
  }, []);
  return { run, pending };
}

export { api };
