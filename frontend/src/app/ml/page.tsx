'use client';

import { useState } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Cell } from 'recharts';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export default function MLPage() {
  const [models, setModels] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [features, setFeatures] = useState<Record<string, number>>({
    hour: 8,
    time_of_day: 0.5,
    length: 200,
    capacity: 1000,
    cost: 1,
    utilization: 0.3,
    travel_time: 120,
  });
  const [predictions, setPredictions] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState<any>(null);

  const fetchModels = async () => {
    try {
      const response = await axios.get(`${API_BASE}/models`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
      });
      setModels(response.data);
      if (response.data.length > 0 && !selectedModel) {
        setSelectedModel(response.data[0].model_id);
      }
    } catch (err) {
      console.error('Failed to fetch models:', err);
    }
  };

  const handlePredict = async () => {
    if (!selectedModel) return;
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/predict`, {
        model_id: selectedModel,
        features,
      }, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
      });
      setPredictions(response.data);
    } catch (err) {
      console.error('Prediction failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTrain = async () => {
    setTraining(true);
    setTrainResult(null);
    try {
      // This would trigger a training job - for demo, we'll simulate
      await new Promise(r => setTimeout(r, 2000));
      setTrainResult({ message: 'Training completed (simulated)', models: ['linear', 'ridge', 'random_forest'] });
      await fetchModels();
    } catch (err) {
      console.error('Training failed:', err);
    } finally {
      setTraining(false);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4 shadow-sm">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">ML Prediction</h1>
          <button
            onClick={handleTrain}
            disabled={training}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            {training ? 'Training...' : 'Train Models'}
          </button>
        </div>
      </header>

      {trainResult && (
        <div className="mx-4 mt-4 p-4 bg-green-100 dark:bg-green-900 border border-green-400 dark:border-green-700 rounded-lg text-green-800 dark:text-green-200">
          {trainResult.message}
        </div>
      )}

      <div className="flex-1 flex max-w-7xl mx-auto w-full p-4 gap-8">
        <div className="flex-1 max-w-md">
          <section className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 mb-6 border border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold mb-4">Available Models</h2>
            {models.length === 0 ? (
              <p className="text-gray-500 dark:text-gray-400">No models trained yet. Click "Train Models" to start.</p>
            ) : (
              <div className="space-y-2">
                {models.map(model => (
                  <button
                    key={model.model_id}
                    onClick={() => setSelectedModel(model.model_id)}
                    className={`w-full p-3 rounded-lg text-left border transition-colors ${
                      selectedModel === model.model_id
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    <div className="font-medium">{model.model_id}</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      Type: {model.model_type} | MAE: {model.metrics?.mae?.toFixed(4) ?? 'N/A'}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </section>

          <section className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 border border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold mb-4">Input Features</h2>
            <div className="space-y-4">
              {Object.entries(features).map(([key, value]) => (
                <div key={key}>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {key.replace(/_/g, ' ')}
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={value}
                    onChange={e => setFeatures({ ...features, [key]: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
                  />
                </div>
              ))}
              <button
                onClick={handlePredict}
                disabled={loading || !selectedModel}
                className="w-full px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
              >
                {loading ? 'Predicting...' : 'Predict Flow'}
              </button>
            </div>
          </section>
        </div>

        <div className="flex-1 min-w-0">
          <section className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 border border-gray-200 dark:border-gray-700 h-full">
            <h2 className="text-lg font-semibold mb-4">Predictions</h2>
            {predictions ? (
              <div>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={Object.entries(predictions.predictions).map(([k, v]) => ({ name: k, value: v as number }))} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="name" width={80} />
                    <Tooltip formatter={(value: number) => [value.toFixed(2), 'veh/h']} />
                    <Bar dataKey="value">
                      {Object.entries(predictions.predictions).map((_, i) => (
                        <Cell key={i} fill="#3b82f6" />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div className="mt-4">
                  <h3 className="font-medium mb-2">Model Info</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Model: {predictions.model_id}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Version: {predictions.model_version}</p>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-500 dark:text-gray-400">
                Select a model and enter features to predict
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}