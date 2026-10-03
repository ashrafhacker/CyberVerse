'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { useCesium, createOptimizedViewer, preloadCesiumAssets } from './cesium-loader';
import { describeError } from './gods-eye-view/standalone/errors';
import { useGlobe } from './useGlobe';

interface GlobeViewerClientProps {
  initialLayers?: string[];
  onReady?: (viewer: any) => void;
  onError?: (error: Error) => void;
}

export function GlobeViewerClient({
  initialLayers = [],
  onReady,
  onError,
}: GlobeViewerClientProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const creditRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<Error | null>(null);
  const applicationRef = useRef<any>(null);
  const { registerComponents, ready } = useGlobe();
  const { loadCesium, isReady: cesiumReady, isLoading: cesiumLoading, error: cesiumError } = useCesium();

  useEffect(() => {
    preloadCesiumAssets();
  }, []);

  useEffect(() => {
    if (!containerRef.current || !creditRef.current) return;

    const googleApiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    const cesiumToken = process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN;

    let mounted = true;

    const initializeGlobe = async () => {
      try {
        const cesium = await loadCesium();
        
        if (!mounted || !containerRef.current || !creditRef.current) return;

        const createViewer = createOptimizedViewer(containerRef.current, creditRef.current);
        const viewer = await createViewer(cesium);

        // Store viewer globally for other components
        applicationRef.current = { viewer, cesium };

        // Load Google 3D Tiles
        const { loadPhotorealisticTileset } = await import('./gods-eye-view/mapStartup.js');
        const photoreal = await loadPhotorealisticTileset(cesium, {
          googleApiKey,
          cesiumToken,
        });

        if (!mounted) {
          viewer.destroy();
          return;
        }

        const tileset = photoreal.tileset;
        if (tileset) {
          viewer.scene.primitives.add(tileset);
          viewer.scene.globe.show = false;
        } else {
          viewer.scene.globe.show = true;
        }

        // Initialize map stack controller
        const { MapStackController } = await import('./gods-eye-view/mapStackController.js');
        const { governorRequestRender } = await import('./gods-eye-view/renderGovernor.js');
        
        const mapStackController = new MapStackController(viewer, {
          requestRender: governorRequestRender,
          googleTileset: tileset,
          cesiumToken,
          initialStack: tileset ? 'photoreal' : 'esri-imagery',
          onChange: (state) => {
            window.dispatchEvent(
              new CustomEvent('gev:map-stack-changed', { detail: state }),
            );
          },
          onError: (message) => console.warn('[MapStack]', message),
        });

        await mapStackController.setStack(tileset ? 'photoreal' : 'esri-imagery', { silent: true });

        // Initialize operations
        const { createApplicationOperations } = await import('./gods-eye-view/app/operations.js');
        const { createApplicationRequestServices } = await import('./gods-eye-view/services/requests.js');
        const operations = createApplicationOperations({
          requests: createApplicationRequestServices(),
          signal: { throwIfAborted: () => {}, aborted: false } as any,
        });

        // Initialize catalog and controls
        const { createStandaloneCatalog } = await import('./gods-eye-view/standalone/catalog.js');
        const { createStandaloneControls } = await import('./gods-eye-view/standalone/controls.js');
        const { createStandalonePlaceSearch } = await import('./gods-eye-view/standalone/placeSearch.js');
        const { CITY_POIS } = await import('./gods-eye-view/locations.js');

        const placeSearch = createStandalonePlaceSearch({
          presets: CITY_POIS,
          resolveApiKey: () => googleApiKey,
          signal: { throwIfAborted: () => {}, aborted: false } as any,
        });

        const catalog = createStandaloneCatalog({
          nepalBoundaryResolver: (signal) =>
            operations.annotationResolver.resolveRegionRingForQuery(
              'Nepal',
              signal,
              placeSearch,
              { budgetMs: Infinity },
            ),
          signal: { throwIfAborted: () => {}, aborted: false } as any,
          surface: operations.surface,
        });

        const controls = createStandaloneControls({
          viewer,
          scene: operations,
          loaderStatus: null,
          placeSearch,
          catalog,
        });

        registerComponents({ scene: { viewer, tileset, operations }, controls, catalog, placeSearch });
        
        setError(null);
        if (onReady) {
          onReady(viewer);
        }

        if (initialLayers.length > 0 && controls) {
          initialLayers.forEach((layer) => {
            controls.toggleLayer?.(layer, true);
          });
        }
      } catch (err) {
        if (!mounted) return;
        const describedError = new Error(describeError(err));
        setError(describedError);
        onError?.(describedError);
      }
    };

    initializeGlobe();

    return () => {
      mounted = false;
      applicationRef.current?.viewer?.destroy?.().catch(console.error);
    };
  }, [initialLayers, onReady, onError, loadCesium, registerComponents]);

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-900 text-red-400 p-4">
        <div className="text-center">
          <h3 className="text-lg font-mono mb-2">Globe Initialization Failed</h3>
          <p className="text-sm opacity-75">{error.message}</p>
        </div>
      </div>
    );
  }

  const isInitializing = cesiumLoading || !cesiumReady;

  return (
    <div className="w-full h-full relative">
      <div
        id="loading-screen"
        className="absolute inset-0 bg-gray-950 flex items-center justify-center z-50 transition-opacity duration-500"
        style={{ opacity: isInitializing ? 1 : 0, pointerEvents: isInitializing ? 'auto' : 'none' }}
      >
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-cyan-400 font-mono text-sm loader-status">
            {cesiumLoading ? 'Loading Cesium...' : 'Initializing Cyberverse Globe...'}
          </p>
        </div>
      </div>
      <div
        ref={containerRef}
        id="cesiumContainer"
        className="w-full h-full"
        style={{ zIndex: 0 }}
      />
      <div
        ref={creditRef}
        id="cesium-credits"
        className="absolute bottom-0 left-0 right-0 z-40"
      />
    </div>
  );
}

export default GlobeViewerClient;