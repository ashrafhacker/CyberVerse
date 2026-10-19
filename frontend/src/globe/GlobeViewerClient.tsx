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
  const { registerComponents } = useGlobe();
  const { loadCesium, isReady: cesiumReady, isLoading: cesiumLoading, error: cesiumError } = useCesium();

  // Keep the latest callbacks/props in refs so the Cesium init effect below can
  // run exactly once. Depending on these directly re-ran initialisation whenever
  // a parent re-rendered — which now happens on every shared-context update and
  // would tear down and rebuild the viewer in a loop.
  const onReadyRef = useRef(onReady);
  const onErrorRef = useRef(onError);
  const initialLayersRef = useRef(initialLayers);

  useEffect(() => {
    onReadyRef.current = onReady;
    onErrorRef.current = onError;
  });

  useEffect(() => {
    preloadCesiumAssets();
  }, []);

  useEffect(() => {
    if (!containerRef.current || !creditRef.current) return;

    const googleApiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    const cesiumToken = process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN;

    let mounted = true;
    // Real application-lifetime signal. The gods-eye-view core requires an
    // AbortSignal (it calls `signal.addEventListener` / `AbortSignal.any`), so a
    // plain stub object is not sufficient. Aborting on unmount lets the stack
    // dispose its listeners.
    const controller = new AbortController();

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
          onChange: (state: unknown) => {
            window.dispatchEvent(
              new CustomEvent('gev:map-stack-changed', { detail: state }),
            );
          },
          onError: (message: string) => console.warn('[MapStack]', message),
        });

        await mapStackController.setStack(tileset ? 'photoreal' : 'esri-imagery', { silent: true });

        // Initialize operations
        const { createApplicationOperations } = await import('./gods-eye-view/app/operations.js');
        const { createApplicationRequestServices } = await import('./gods-eye-view/services/requests.js');
        const operations = createApplicationOperations({
          requests: createApplicationRequestServices(),
          signal: controller.signal,
          eventTarget: globalThis.window,
        });

        // Initialize catalog and place search
        const { createStandaloneCatalog } = await import('./gods-eye-view/standalone/catalog.js');
        const { createStandalonePlaceSearch } = await import('./gods-eye-view/standalone/placeSearch.js');
        const { CITY_POIS } = await import('./gods-eye-view/locations.js');

        const placeSearch = createStandalonePlaceSearch({
          presets: CITY_POIS,
          resolveApiKey: () => googleApiKey,
          signal: controller.signal,
        } as any);

        const catalog = createStandaloneCatalog({
          nepalBoundaryResolver: (signal: AbortSignal) =>
            operations.annotationResolver.resolveRegionRingForQuery(
              'Nepal',
              signal,
              placeSearch,
              { budgetMs: Infinity },
            ),
          signal: controller.signal,
          surface: operations.surface,
        } as any);

        // The gods-eye-view controls (StyleManager + its ~150-node HUD shell) are
        // intentionally NOT mounted inside the CyberVerse page: this globe is a
        // custom integration that drives its layers through useCyberverseLayers
        // (see CyberverseLayers), and no gods-eye-view HUD CSS is loaded here.
        // The rest of the app only needs `controls` as a handle onto the viewer.
        const controls = {
          getViewer: () => viewer,
          getScene: () => viewer.scene,
        };

        registerComponents({ viewer, scene: { viewer, tileset, operations }, controls, catalog, placeSearch });
        
        setError(null);
        onReadyRef.current?.(viewer);

        const layersToEnable = initialLayersRef.current;
        if (layersToEnable.length > 0) {
          layersToEnable.forEach((layer) => {
            (controls as any).toggleLayer?.(layer, true);
          });
        }
      } catch (err) {
        if (!mounted) return;
        const describedError = new Error(describeError(err));
        setError(describedError);
        onErrorRef.current?.(describedError);
      }
    };

    initializeGlobe();

    return () => {
      mounted = false;
      controller.abort();
      applicationRef.current?.viewer?.destroy?.().catch(console.error);
    };
  }, [loadCesium, registerComponents]);

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