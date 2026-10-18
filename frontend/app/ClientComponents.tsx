'use client';

import { useEffect } from 'react';
import { initPerformanceMonitoring, cleanupPerformanceMonitoring } from '@/lib/performance';

export function PerformanceMonitor() {
  useEffect(() => {
    initPerformanceMonitoring();
    return cleanupPerformanceMonitoring;
  }, []);
  return null;
}