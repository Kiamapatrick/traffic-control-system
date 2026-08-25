import { useState, useCallback } from 'react';
import { solveApi } from '@/lib/api';

export function useSolver() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  const solve = useCallback(async (request: any) => {
    setLoading(true);
    setError(null);
    try {
      const response = await solveApi.solve(request);
      setResult(response.data);
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { solve, loading, error, result, setResult };
}