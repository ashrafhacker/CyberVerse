'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

// Configure Cesium base URL for assets
if (typeof window !== 'undefined') {
  (window as any).CESIUM_BASE_URL = '/cesium/';
}

interface CesiumLoaderState {
  isLoading: boolean;
  isReady: boolean;
  error: Error | null;
}

let cesiumPromise: Promise<typeof import('cesium')> | null = null;
let cesiumLoaded = false;
const cesiumLoadCallbacks: Array<(cesium: typeof import('cesium')) => void> = [];

/**
 * Preload Cesium asynchronously to avoid blocking the main thread.
 * Call this early (e.g., in _app.tsx or layout.tsx) to start loading Cesium
 * before the user navigates to the globe page.
 */
export function preloadCesium(): Promise<typeof import('cesium')> {
  if (cesiumLoaded && cesiumPromise) {
    return cesiumPromise;
  }
  
  if (!cesiumPromise) {
    cesiumPromise = import('cesium').then((cesium) => {
      cesiumLoaded = true;
      cesiumLoadCallbacks.forEach((cb) => cb(cesium));
      cesiumLoadCallbacks.length = 0;
      return cesium;
    });
  }
  
  return cesiumPromise;
}

/**
 * Subscribe to Cesium load completion
 */
export function onCesiumLoaded(callback: (cesium: typeof import('cesium')) => void): () => void {
  if (cesiumLoaded && cesiumPromise) {
    cesiumPromise.then(callback);
    return () => {};
  }
  
  cesiumLoadCallbacks.push(callback);
  return () => {
    const index = cesiumLoadCallbacks.indexOf(callback);
    if (index !== -1) cesiumLoadCallbacks.splice(index, 1);
  };
}

/**
 * Hook to use Cesium with loading state management
 */
export function useCesium() {
  const [state, setState] = useState<CesiumLoaderState>({
    isLoading: false,
    isReady: false,
    error: null,
  });
  const cesiumRef = useRef<typeof import('cesium') | null>(null);

  const loadCesium = useCallback(async () => {
    if (cesiumRef.current) {
      setState({ isLoading: false, isReady: true, error: null });
      return cesiumRef.current;
    }

    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const cesium = await preloadCesium();
      cesiumRef.current = cesium;
      setState({ isLoading: false, isReady: true, error: null });
      return cesium;
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to load Cesium');
      setState({ isLoading: false, isReady: false, error: err });
      throw err;
    }
  }, []);

  return { ...state, loadCesium, cesium: cesiumRef.current };
}

/**
 * Optimized Cesium Viewer creation with performance settings
 */
export function createOptimizedViewer(container: HTMLDivElement, creditContainer: HTMLElement) {
  return async function(cesium: typeof import('cesium')): Promise<cesium.Viewer> {
    const viewer = new cesium.Viewer(container, {
      timeline: false,
      animation: false,
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      fullscreenButton: false,
      vrButton: false,
      selectionIndicator: false,
      infoBox: false,
      baseLayer: false,
      creditContainer,
      msaaSamples: 2, // Reduced from 4 for better performance
      contextOptions: { 
        webgl: { 
          preserveDrawingBuffer: false, // Disable for better performance
          alpha: false, // Disable alpha for better performance
          antialias: true,
          depth: true,
          stencil: false,
          premultipliedAlpha: false,
        } 
      },
      requestRenderMode: true, // Only render when scene changes
      maximumRenderTimeChange: 0.1,
    });

    // Performance optimizations
    viewer.targetFrameRate = 60;
    viewer.scene.globe.show = false;
    viewer.scene.skyAtmosphere.show = true;
    viewer.scene.skyAtmosphere.atmosphereLightIntensity = 18;
    viewer.scene.skyAtmosphere.saturationShift = -0.12;
    viewer.scene.skyAtmosphere.brightnessShift = -0.08;
    
    // Disable depth test against terrain for better performance
    viewer.scene.globe.depthTestAgainstTerrain = false;
    
    // Optimize terrain
    viewer.scene.globe.enableLighting = false;
    
    // Reduce logo fade time
    viewer.cesiumWidget.creditContainer.style.display = 'none';
    
    return viewer;
  };
}

/**
 * Preload critical Cesium assets
 */
export async function preloadCesiumAssets(): Promise<void> {
  try {
    // Preload CSS
    const cssLink = document.createElement('link');
    cssLink.rel = 'preload';
    cssLink.href = '/cesium/Widgets/widgets.css';
    cssLink.as = 'style';
    document.head.appendChild(cssLink);
    
    // Preload Cesium worker
    const workerLink = document.createElement('link');
    workerLink.rel = 'preload';
    workerLink.href = '/cesium/Workers/cesiumWorkerBootstrapper.js';
    workerLink.as = 'script';
    workerLink.crossOrigin = 'anonymous';
    document.head.appendChild(workerLink);
  } catch {
    // Ignore preload errors
  }
}