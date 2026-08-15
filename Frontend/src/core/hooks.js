import { useCallback, useEffect, useState } from './view.js';

export function useAsyncData(loader, dependencies = []) {
  const [state, setState] = useState({ status: 'loading', data: null, error: null });
  const load = useCallback(async signal => {
    setState(previous => ({ ...previous, status: 'loading', error: null }));
    try {
      const data = await loader(signal);
      if (signal?.aborted) return;
      setState({ status: 'success', data, error: null });
    } catch (error) {
      if (!signal?.aborted && error?.code !== 'request_cancelled') setState({ status: 'error', data: null, error });
    }
  }, dependencies);
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);
  const reload = useCallback(() => load(new AbortController().signal), [load]);
  return { ...state, reload };
}
