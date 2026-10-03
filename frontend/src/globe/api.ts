import { api } from '@/lib/api';

export interface ThreatIntelData {
  cves: Array<{
    id: string;
    cve_id: string;
    description: string;
    severity: string;
    cvss_score: number;
    published_date: string;
    location?: { lat: number; lng: number };
  }>;
  attack_techniques: Array<{
    id: string;
    technique_id: string;
    name: string;
    tactic: string;
    description: string;
  }>;
  threat_indicators: Array<{
    id: string;
    indicator_type: string;
    value: string;
    threat_type: string;
    confidence: number;
    location?: { lat: number; lng: number };
  }>;
}

export interface SOCData {
  alerts: Array<{
    id: string;
    severity: string;
    title: string;
    description: string;
    source_ip: string;
    dest_ip: string;
    timestamp: string;
    mitre_techniques: string[];
    location?: { lat: number; lng: number };
  }>;
  incidents: Array<{
    id: string;
    title: string;
    status: string;
    severity: string;
    created_at: string;
    location?: { lat: number; lng: number };
  }>;
}

export interface NetworkTopologyData {
  nodes: Array<{
    id: string;
    name: string;
    type: 'server' | 'router' | 'switch' | 'firewall' | 'workstation' | 'database' | 'web_server';
    ip: string;
    location: { lat: number; lng: number };
    status: 'online' | 'offline' | 'compromised' | 'suspicious';
    metadata?: Record<string, any>;
  }>;
  edges: Array<{
    source: string;
    target: string;
    type: 'ethernet' | 'wifi' | 'vpn' | 'internet';
    status: 'active' | 'inactive' | 'suspicious';
  }>;
}

export interface LabEnvironmentData {
  id: string;
  name: string;
  facility_type: string;
  topology: NetworkTopologyData;
  scenario: {
    seed: string;
    objectives: Array<{
      id: string;
      description: string;
      location?: { lat: number; lng: number };
    }>;
  };
}

export class GlobeAPI {
  static async getThreatIntel(bounds?: { north: number; south: number; east: number; west: number }): Promise<ThreatIntelData> {
    const params = new URLSearchParams();
    if (bounds) {
      params.set('north', bounds.north.toString());
      params.set('south', bounds.south.toString());
      params.set('east', bounds.east.toString());
      params.set('west', bounds.west.toString());
    }
    const response = await api.get(`/threat-intel/map?${params.toString()}`);
    return response.data;
  }

  static async getSOCData(bounds?: { north: number; south: number; east: number; west: number }): Promise<SOCData> {
    const params = new URLSearchParams();
    if (bounds) {
      params.set('north', bounds.north.toString());
      params.set('south', bounds.south.toString());
      params.set('east', bounds.east.toString());
      params.set('west', bounds.west.toString());
    }
    const response = await api.get(`/soc/map?${params.toString()}`);
    return response.data;
  }

  static async getNetworkTopology(labId: string): Promise<NetworkTopologyData> {
    const response = await api.get(`/labs/${labId}/topology`);
    return response.data;
  }

  static async getLabEnvironment(labId: string): Promise<LabEnvironmentData> {
    const response = await api.get(`/labs/${labId}/environment`);
    return response.data;
  }

  static async getLiveAttacks(): Promise<Array<{
    id: string;
    source_ip: string;
    dest_ip: string;
    attack_type: string;
    severity: string;
    timestamp: string;
    source_location: { lat: number; lng: number };
    dest_location: { lat: number; lng: number };
  }>> {
    const response = await api.get('/analytics/live-attacks');
    return response.data;
  }

  static async getHoneypotData(): Promise<Array<{
    id: string;
    name: string;
    location: { lat: number; lng: number };
    attacks_24h: number;
    top_attack_types: string[];
    status: 'active' | 'inactive' | 'compromised';
  }>> {
    const response = await api.get('/analytics/honeypots');
    return response.data;
  }

  static async getMalwareDistribution(): Promise<Array<{
    family: string;
    count: number;
    locations: Array<{ lat: number; lng: number; count: number }>;
  }>> {
    const response = await api.get('/analytics/malware-distribution');
    return response.data;
  }

  static async getVulnerabilityHeatmap(): Promise<Array<{
    cve_id: string;
    severity: string;
    count: number;
    locations: Array<{ lat: number; lng: number; count: number }>;
  }>> {
    const response = await api.get('/analytics/vulnerability-heatmap');
    return response.data;
  }
}

export default GlobeAPI;