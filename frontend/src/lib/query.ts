import {
  QueryClient,
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { api, ApiError } from "./api";
import type { Page } from "../types/api";
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 20000,
      retry: (count, error) =>
        !(error instanceof ApiError && error.status < 500) && count < 1,
      refetchOnWindowFocus: true,
    },
  },
});
export function usePages<T>(path: string, enabled = true) {
  return useInfiniteQuery({
    queryKey: ["page", path],
    initialPageParam: "",
    enabled,
    queryFn: ({ pageParam }) =>
      api<Page<T>>(
        path +
          (path.includes("?") ? "&" : "?") +
          "cursor=" +
          encodeURIComponent(pageParam),
      ),
    getNextPageParam: (last) => last.next_cursor || undefined,
  });
}
export function useAction<TVariables, TData = unknown>(
  fn: (variables: TVariables) => Promise<TData>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => qc.invalidateQueries(),
  });
}
