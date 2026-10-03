import { useCallback, useEffect, useRef, useState } from 'react';
import { CyberverseLayers, CyberEntityOptions } from './CyberverseLayers';
import { useGlobe } from './useGlobe';
import { GlobeAPI, ThreatIntelData, SOCData, NetworkTopologyData, LabEnvironmentData } from './api';

export interface LayerState {
  threatIntel: boolean;
  socAlerts: boolean;
  networkTopology: boolean;
  liveAttacks: boolean;
  honeypots: boolean;
  malwareDistribution: boolean;
  vulnerabilityHeatmap: boolean;
}

export function useCyberverseLayers() {
  const { controls, ready } = useGlobe();
  const layersRef = useRef<CyberverseLayers | null>(null);
  const [layerState, setLayerState] = useState<LayerState>({
    threatIntel: false,
    socAlerts: false,
    networkTopology: false,
    liveAttacks: false,
    honeypots: false,
    malwareDistribution: false,
    vulnerabilityHeatmap: false,
  });
  const [loading, setLoading] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (ready && controls) {
      const viewer = controls.getViewer();
      if (viewer && !layersRef.current) {
        layersRef.current = new CyberverseLayers(viewer);
      }
    }
  }, [ready, controls]);

  const toggleLayer = useCallback(async (layer: keyof LayerState, enabled?: boolean) => {
    const newState = enabled ?? !layerState[layer];
    setLayerState(prev => ({ ...prev, [layer]: newState }));

    if (!layersRef.current) return;

    if (newState) {
      setLoading(prev => ({ ...prev, [layer]: true }));
      try {
        await loadLayerData(layer);
      } catch (error) {
        console.error(`Failed to load ${layer}:`, error);
        setLayerState(prev => ({ ...prev, [layer]: false }));
      } finally {
        setLoading(prev => ({ ...prev, [layer]: false }));
      }
    } else {
      clearLayerData(layer);
    }
  }, [layerState]);

  const loadLayerData = useCallback(async (layer: keyof LayerState) => {
    if (!layersRef.current) return;

    switch (layer) {
      case 'threatIntel': {
        const data = await GlobeAPI.getThreatIntel();
        data.cves.forEach(cve => {
          if (cve.location) {
            layersRef.current!.addEntity({
              id: `cve-${cve.id}`,
              position: cve.location!,
              name: cve.cve_id,
              description: cve.description,
              type: 'vulnerability',
              severity: cve.severity.toLowerCase() as any,
              metadata: { cvss_score: cve.cvss_score, published_date: cve.published_date },
            });
          }
        });
        data.threat_indicators.forEach(indicator => {
          if (indicator.location) {
            layersRef.current!.addEntity({
              id: `indicator-${indicator.id}`,
              position: indicator.location!,
              name: `${indicator.indicator_type}: ${indicator.value}`,
              description: `Type: ${indicator.threat_type}<br/>Confidence: ${indicator.confidence}%`,
              type: 'threat',
              severity: indicator.confidence > 80 ? 'high' : indicator.confidence > 50 ? 'medium' : 'low',
              metadata: { indicator_type: indicator.indicator_type, value: indicator.value },
            });
          }
        });
        break;
      }
      case 'socAlerts': {
        const data = await GlobeAPI.getSOCData();
        data.alerts.forEach(alert => {
          if (alert.location) {
            layersRef.current!.addEntity({
              id: `alert-${alert.id}`,
              position: alert.location!,
              name: alert.title,
              description: alert.description,
              type: 'incident',
              severity: alert.severity.toLowerCase() as any,
              metadata: { source_ip: alert.source_ip, dest_ip: alert.dest_ip, mitre_techniques: alert.mitre_techniques },
            });
          }
        });
        break;
      }
      case 'liveAttacks': {
        const data = await GlobeAPI.getLiveAttacks();
        data.forEach(attack => {
          layersRef.current!.addAttackPath(
            attack.source_location,
            attack.dest_location,
            {
              id: `attack-${attack.id}`,
              attackType: attack.attack_type,
              timestamp: attack.timestamp,
              severity: attack.severity,
            }
          );
        });
        break;
      }
      case 'honeypots': {
        const data = await GlobeAPI.getHoneypotData();
        data.forEach(honeypot => {
          layersRef.current!.addEntity({
            id: `honeypot-${honeypot.id}`,
            position: honeypot.location,
            name: honeypot.name,
            description: `Attacks (24h): ${honeypot.attacks_24h}<br/>Top types: ${honeypot.top_attack_types.join(', ')}`,
            type: 'honeypot',
            severity: honeypot.status === 'compromised' ? 'critical' : honeypot.status === 'active' ? 'low' : 'info',
            metadata: { attacks_24h: honeypot.attacks_24h, top_attack_types: honeypot.top_attack_types },
          });
        });
        break;
      }
      case 'malwareDistribution': {
        const data = await GlobeAPI.getMalwareDistribution();
        data.forEach(family => {
          family.locations.forEach(loc => {
            layersRef.current!.addEntity({
              id: `malware-${family.family}-${loc.lat}-${loc.lng}`,
              position: loc,
              name: `${family.family} (${loc.count})`,
              description: `Malware family: ${family.family}<br/>Total sightings: ${family.count}`,
              type: 'threat',
              severity: loc.count > 100 ? 'high' : loc.count > 10 ? 'medium' : 'low',
              metadata: { family: family.family, total_count: family.count },
            });
          });
        });
        break;
      }
      case 'vulnerabilityHeatmap': {
        const data = await GlobeAPI.getVulnerabilityHeatmap();
        data.forEach(vuln => {
          vuln.locations.forEach(loc => {
            layersRef.current!.addEntity({
              id: `vuln-${vuln.cve_id}-${loc.lat}-${loc.lng}`,
              position: loc,
              name: `${vuln.cve_id} (${loc.count})`,
              description: `CVE: ${vuln.cve_id}<br/>Severity: ${vuln.severity}<br/>Affected systems: ${loc.count}`,
              type: 'vulnerability',
              severity: vuln.severity.toLowerCase() as any,
              metadata: { cve_id: vuln.cve_id, total_count: vuln.count },
            });
          });
        });
        break;
      }
      case 'networkTopology': {
        // This would be loaded for a specific lab
        break;
      }
    }
  }, []);

  const clearLayerData = useCallback((layer: keyof LayerState) => {
    if (!layersRef.current) return;

    const prefixes: Record<keyof LayerState, string> = {
      threatIntel: 'cve-',
      socAlerts: 'alert-',
      networkTopology: 'network-',
      liveAttacks: 'attack-',
      honeypots: 'honeypot-',
      malwareDistribution: 'malware-',
      vulnerabilityHeatmap: 'vuln-',
    };

    const prefix = prefixes[layer];
    layersRef.current.getAllEntities().forEach(entity => {
      if (entity.id.startsWith(prefix)) {
        layersRef.current!.removeEntity(entity.id);
      }
    });
  }, []);

  const loadNetworkTopology = useCallback(async (labId: string) => {
    if (!layersRef.current) return;
    setLoading(prev => ({ ...prev, networkTopology: true }));
    try {
      const data = await GlobeAPI.getNetworkTopology(labId);
      
      // Add nodes
      data.nodes.forEach(node => {
        layersRef.current!.addEntity({
          id: `network-node-${node.id}`,
          position: node.location,
          name: node.name,
          description: `Type: ${node.type}<br/>IP: ${node.ip}<br/>Status: ${node.status}`,
          type: 'asset',
          severity: node.status === 'compromised' ? 'critical' : node.status === 'suspicious' ? 'high' : 'low',
          metadata: { node_type: node.type, ip: node.ip, status: node.status, ...node.metadata },
        });
      });

      // Add edges
      data.edges.forEach(edge => {
        const source = data.nodes.find(n => n.id === edge.source);
        const target = data.nodes.find(n => n.id === edge.target);
        if (source && target) {
          layersRef.current!.addNetworkLink(source.location, target.location, {
            id: `network-edge-${edge.source}-${edge.target}`,
            linkType: edge.type,
            status: edge.status,
          });
        }
      });

      setLayerState(prev => ({ ...prev, networkTopology: true }));
    } catch (error) {
      console.error('Failed to load network topology:', error);
    } finally {
      setLoading(prev => ({ ...prev, networkTopology: false }));
    }
  }, []);

  const loadLabEnvironment = useCallback(async (labId: string) => {
    if (!layersRef.current) return;
    setLoading(prev => ({ ...prev, networkTopology: true }));
    try {
      const data = await GlobeAPI.getLabEnvironment(labId);
      
      // Add topology
      data.topology.nodes.forEach(node => {
        layersRef.current!.addEntity({
          id: `lab-node-${node.id}`,
          position: node.location,
          name: node.name,
          description: `Type: ${node.type}<br/>IP: ${node.ip}<br/>Status: ${node.status}`,
          type: 'asset',
          severity: node.status === 'compromised' ? 'critical' : node.status === 'suspicious' ? 'high' : 'low',
          metadata: { node_type: node.type, ip: node.ip, status: node.status, ...node.metadata },
        });
      });

      data.topology.edges.forEach(edge => {
        const source = data.topology.nodes.find(n => n.id === edge.source);
        const target = data.topology.nodes.find(n => n.id === edge.target);
        if (source && target) {
          layersRef.current!.addNetworkLink(source.location, target.location, {
            id: `lab-edge-${edge.source}-${edge.target}`,
            linkType: edge.type,
            status: edge.status,
          });
        }
      });

      // Add objectives
      data.scenario.objectives.forEach((obj, index) => {
        if (obj.location) {
          layersRef.current!.addEntity({
            id: `lab-objective-${obj.id}`,
            position: obj.location,
            name: `Objective ${index + 1}`,
            description: obj.description,
            type: 'incident',
            severity: 'medium',
            metadata: { objective_id: obj.id },
          });
        }
      });

      setLayerState(prev => ({ ...prev, networkTopology: true }));
    } catch (error) {
      console.error('Failed to load lab environment:', error);
    } finally {
      setLoading(prev => ({ ...prev, networkTopology: false }));
    }
  }, []);

  const clearAll = useCallback(() => {
    layersRef.current?.clearAll();
    setLayerState({
      threatIntel: false,
      socAlerts: false,
      networkTopology: false,
      liveAttacks: false,
      honeypots: false,
      malwareDistribution: false,
      vulnerabilityHeatmap: false,
    });
  }, []);

  return {
    layers: layersRef.current,
    layerState,
    loading,
    toggleLayer,
    loadNetworkTopology,
    loadLabEnvironment,
    clearAll,
    ready: ready && !!layersRef.current,
  };
}