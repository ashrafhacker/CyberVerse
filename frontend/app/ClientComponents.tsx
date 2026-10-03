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

export function CesiumPreloader() {
  useEffect(() => {
    const timer = setTimeout(() => {
      import('@/src/globe/cesium-loader').then(({ preloadCesium, preloadCesiumAssets }) => {
        preloadCesiumAssets();
        preloadCesium();
      }).catch(() => {});
    }, 3000);
    return () => clearTimeout(timer);
  }, []);
  return null;
}