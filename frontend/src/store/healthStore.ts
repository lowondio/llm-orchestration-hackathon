import { create } from 'zustand';

interface HealthState {
  isHealthy: boolean;
  lastChecked: string | null;
  setHealth: (isHealthy: boolean, timestamp: string) => void;
}

export const useHealthStore = create<HealthState>((set) => ({
  isHealthy: false,
  lastChecked: null,
  setHealth: (isHealthy, timestamp) => set({ isHealthy, lastChecked: timestamp }),
}));
