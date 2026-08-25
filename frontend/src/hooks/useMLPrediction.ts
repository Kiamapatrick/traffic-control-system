import { useState, useEffect, useCallback } from 'react';
import { mlApi } from '@/lib/api';

export function useModels() {
  const [models, setModels] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchModels = useCallback(async () => {
    setLoading(true);
    try {
      const response = await mlApi.listModels();
      setModels(response.data);
    } catch (err) {
      console.error('Failed to fetch models:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  return { models, loading, refetch: fetchModels };
}

export function usePrediction(modelId: string | null, features: Record<string, number> | null) {
  const [prediction, setPrediction] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const predict = useCallback(async () => {
    if (!modelId || !features) return;
    setLoading(true);
    setError(null);
    try {
      const response = await mlApi.predict({ model_id: modelId, features });
      setPrediction(response.data);
      return response.data;
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [modelId, features]);

  return { prediction, loading, error, predict, setPrediction };
}