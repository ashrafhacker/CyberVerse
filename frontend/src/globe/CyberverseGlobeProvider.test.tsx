import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useEffect } from 'react';
import { describe, expect, it, vi } from 'vitest';

// The globe layer plumbing pulls in Cesium + the network API at module scope.
// None of that is needed to prove the context wiring, so stub it out.
vi.mock('cesium', () => ({
  Cartesian3: { fromDegrees: () => ({}) },
  ScreenSpaceEventType: { LEFT_CLICK: 2 },
}));

vi.mock('./CyberverseLayers', () => {
  class CyberverseLayers {
    entities: Array<{ id: string }> = [];
    constructor(public viewer: unknown) {}
    addEntity(entity: { id: string }) {
      this.entities.push(entity);
    }
    addAttackPath() {}
    addNetworkLink() {}
    getAllEntities() {
      return this.entities;
    }
    removeEntity(id: string) {
      this.entities = this.entities.filter((entity) => entity.id !== id);
    }
    clearAll() {
      this.entities = [];
    }
  }
  return { CyberverseLayers };
});

vi.mock('./api', () => ({
  GlobeAPI: {
    getThreatIntel: vi.fn(async () => ({
      cves: [
        {
          id: 1,
          cve_id: 'CVE-2024-0001',
          description: 'demo',
          severity: 'HIGH',
          cvss_score: 9.1,
          published_date: '2024-01-01',
          location: { lat: 1, lng: 2 },
        },
      ],
      threat_indicators: [],
    })),
    getSOCData: vi.fn(async () => ({ alerts: [] })),
    getLiveAttacks: vi.fn(async () => []),
    getHoneypotData: vi.fn(async () => []),
    getMalwareDistribution: vi.fn(async () => []),
    getVulnerabilityHeatmap: vi.fn(async () => []),
    getNetworkTopology: vi.fn(async () => ({ nodes: [], edges: [] })),
    getLabEnvironment: vi.fn(async () => ({
      topology: { nodes: [], edges: [] },
      scenario: { objectives: [] },
    })),
  },
}));

import { CyberverseGlobeProvider } from './CyberverseGlobeProvider';
import { useGlobe } from './useGlobe';
import { useCyberverseLayers } from './useCyberverseLayers';

const fakeViewer = { camera: {}, entities: { getById: () => undefined } };

// Stands in for GlobeViewerClient: registers the viewer into the shared store.
function Registrar() {
  const { ready, registerComponents } = useGlobe();
  useEffect(() => {
    registerComponents({
      viewer: fakeViewer,
      scene: {},
      controls: { getViewer: () => fakeViewer },
    });
  }, [registerComponents]);
  return <div data-testid="registrar">{ready ? 'live' : 'loading'}</div>;
}

// Stands in for GlobeViewerClient, which passes the viewer bundled inside
// `scene` (not at the top level). The store must still resolve it, otherwise the
// layer manager is never created and the header stays stuck on "○ LOADING".
function NestedRegistrar() {
  const { registerComponents } = useGlobe();
  useEffect(() => {
    registerComponents({
      scene: { viewer: fakeViewer, tileset: null, operations: {} },
      controls: { getViewer: () => fakeViewer },
    });
  }, [registerComponents]);
  return <div data-testid="nested-registrar" />;
}

// Stands in for the header badge and the layer panel: two independent consumers.
function LayersConsumer({ id }: { id: string }) {
  const { layerState, toggleLayer, ready } = useCyberverseLayers();
  return (
    <div>
      <div data-testid={`ready-${id}`}>{ready ? 'live' : 'loading'}</div>
      <div data-testid={`threatIntel-${id}`}>{layerState.threatIntel ? 'on' : 'off'}</div>
      <button type="button" onClick={() => toggleLayer('threatIntel', true)}>
        toggle-{id}
      </button>
    </div>
  );
}

describe('CyberverseGlobeProvider', () => {
  it('propagates globe readiness to a separate consumer', async () => {
    render(
      <CyberverseGlobeProvider>
        <Registrar />
        <LayersConsumer id="header" />
      </CyberverseGlobeProvider>,
    );

    await waitFor(() => expect(screen.getByTestId('registrar')).toHaveTextContent('live'));
    await waitFor(() => expect(screen.getByTestId('ready-header')).toHaveTextContent('live'));
  });

  it('shares one layer store between sibling consumers', async () => {
    render(
      <CyberverseGlobeProvider>
        <Registrar />
        <LayersConsumer id="a" />
        <LayersConsumer id="b" />
      </CyberverseGlobeProvider>,
    );

    await waitFor(() => expect(screen.getByTestId('ready-a')).toHaveTextContent('live'));

    fireEvent.click(screen.getByText('toggle-a'));

    await waitFor(() => expect(screen.getByTestId('threatIntel-a')).toHaveTextContent('on'));
    // The sibling observes the same store, not a private copy.
    expect(screen.getByTestId('threatIntel-b')).toHaveTextContent('on');
  });

  it('resolves a viewer supplied inside `scene` (GlobeViewerClient shape)', async () => {
    render(
      <CyberverseGlobeProvider>
        <NestedRegistrar />
        <LayersConsumer id="nested" />
      </CyberverseGlobeProvider>,
    );

    // Without the `scene.viewer` fallback this stays on 'loading' forever.
    await waitFor(() => expect(screen.getByTestId('ready-nested')).toHaveTextContent('live'));
  });
});
