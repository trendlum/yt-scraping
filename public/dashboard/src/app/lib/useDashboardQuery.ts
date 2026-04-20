import { useEffect, useState } from "react";
import { dashboardRequest } from "./dashboard";

interface QueryState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function useDashboardQuery<T>(path: string, query: string) {
  const [state, setState] = useState<QueryState<T>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    const controller = new AbortController();

    setState({ data: null, loading: true, error: null });

    dashboardRequest<T>(path, query, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setState({ data, loading: false, error: null });
        }
      })
      .catch((error: Error) => {
        if (!controller.signal.aborted) {
          setState({
            data: null,
            loading: false,
            error: error.message || "Unable to load dashboard data",
          });
        }
      });

    return () => controller.abort();
  }, [path, query]);

  return state;
}
