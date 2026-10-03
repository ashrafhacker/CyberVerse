'use client';

import { useEffect } from 'react';
import { initPerformanceMonitoring, cleanupPerformanceMonitoring } from '@/lib/performance';

export default function PerformanceMonitorClient() {
  useEffect(() => {
    initPerformanceMonitoring();
    return cleanupPerformanceMonitoring;
  }, []);
  return null;
}