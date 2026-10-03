import { Entity, Viewer, Cartesian3, Color, PinBuilder, LabelStyle, HeightReference } from 'cesium';

export interface CyberEntityOptions {
  id: string;
  position: { lat: number; lng: number; altitude?: number };
  name: string;
  description?: string;
  type: 'threat' | 'asset' | 'attack' | 'honeypot' | 'vulnerability' | 'incident';
  severity?: 'critical' | 'high' | 'medium' | 'low' | 'info';
  metadata?: Record<string, any>;
}

const SEVERITY_COLORS = {
  critical: Color.RED,
  high: Color.ORANGE,
  medium: Color.YELLOW,
  low: Color.LIME,
  info: Color.CYAN,
};

const TYPE_ICONS = {
  threat: '🎯',
  asset: '🖥️',
  attack: '⚡',
  honeypot: '🍯',
  vulnerability: '🔓',
  incident: '🚨',
};

export class CyberverseLayers {
  private viewer: Viewer;
  private entities: Map<string, Entity> = new Map();
  private pinBuilder: PinBuilder;

  constructor(viewer: Viewer) {
    this.viewer = viewer;
    this.pinBuilder = new PinBuilder();
  }

  addEntity(options: CyberEntityOptions): Entity {
    const { id, position, name, description, type, severity = 'info', metadata = {} } = options;
    
    const color = SEVERITY_COLORS[severity];
    const icon = TYPE_ICONS[type];

    const entity = this.viewer.entities.add({
      id,
      name,
      description: this.formatDescription(description, metadata),
      position: Cartesian3.fromDegrees(position.lng, position.lat, position.altitude || 0),
      billboard: {
        image: this.pinBuilder.fromText(icon, color, 48).toDataURL(),
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        heightReference: HeightReference.CLAMP_TO_GROUND,
        scale: 1.0,
        show: true,
      },
      label: {
        text: name,
        font: '14px "JetBrains Mono", monospace',
        style: LabelStyle.FILL_AND_OUTLINE,
        outlineWidth: 2,
        outlineColor: Color.BLACK,
        pixelOffset: new Cesium.Cartesian2(0, -40),
        heightReference: HeightReference.CLAMP_TO_GROUND,
        show: true,
      },
      properties: {
        type,
        severity,
        ...metadata,
      },
    });

    this.entities.set(id, entity);
    return entity;
  }

  addAttackPath(source: { lat: number; lng: number }, destination: { lat: number; lng: number }, options: { id: string; attackType: string; timestamp: string; severity: string }): Entity {
    const { id, attackType, timestamp, severity } = options;
    const color = SEVERITY_COLORS[severity as keyof typeof SEVERITY_COLORS] || Color.RED;

    const entity = this.viewer.entities.add({
      id,
      name: `Attack: ${attackType}`,
      description: `Type: ${attackType}<br/>Time: ${timestamp}<br/>Severity: ${severity}`,
      polyline: {
        positions: [
          Cartesian3.fromDegrees(source.lng, source.lat, 100000),
          Cartesian3.fromDegrees(destination.lng, destination.lat, 100000),
        ],
        width: 3,
        material: new Cesium.PolylineGlowMaterialProperty({
          glowPower: 0.2,
          color: color.withAlpha(0.8),
        }),
        clampToGround: false,
      },
      properties: {
        type: 'attack_path',
        attackType,
        timestamp,
        severity,
      },
    });

    this.entities.set(id, entity);
    return entity;
  }

  addNetworkLink(source: { lat: number; lng: number }, destination: { lat: number; lng: number }, options: { id: string; linkType: string; status: string }): Entity {
    const { id, linkType, status } = options;
    const color = status === 'active' ? Color.CYAN : status === 'suspicious' ? Color.ORANGE : Color.GRAY;

    const entity = this.viewer.entities.add({
      id,
      name: `Network Link: ${linkType}`,
      description: `Type: ${linkType}<br/>Status: ${status}`,
      polyline: {
        positions: [
          Cartesian3.fromDegrees(source.lng, source.lat, 1000),
          Cartesian3.fromDegrees(destination.lng, destination.lat, 1000),
        ],
        width: 2,
        material: color.withAlpha(0.6),
        clampToGround: true,
      },
      properties: {
        type: 'network_link',
        linkType,
        status,
      },
    });

    this.entities.set(id, entity);
    return entity;
  }

  addHeatmap(data: Array<{ lat: number; lng: number; weight: number }>, options: { id: string; radius?: number; maxIntensity?: number }): Entity {
    // For heatmap, we'll create a custom primitive or use entities with varying sizes
    // This is a simplified version using entities
    const { id, radius = 50000, maxIntensity = 100 } = options;

    const entity = this.viewer.entities.add({
      id,
      name: 'Heatmap',
      description: 'Security event heatmap',
      // Heatmap would typically use a custom Primitive or ImageryLayer
      // For now, we'll create a placeholder
    });

    this.entities.set(id, entity);
    return entity;
  }

  removeEntity(id: string): boolean {
    const entity = this.entities.get(id);
    if (entity) {
      this.viewer.entities.remove(entity);
      this.entities.delete(id);
      return true;
    }
    return false;
  }

  clearAll(): void {
    this.entities.forEach((entity) => {
      this.viewer.entities.remove(entity);
    });
    this.entities.clear();
  }

  getEntity(id: string): Entity | undefined {
    return this.entities.get(id);
  }

  getAllEntities(): Entity[] {
    return Array.from(this.entities.values());
  }

  flyToEntity(id: string): void {
    const entity = this.entities.get(id);
    if (entity) {
      this.viewer.camera.flyTo(entity);
    }
  }

  private formatDescription(baseDescription: string | undefined, metadata: Record<string, any>): string {
    let desc = baseDescription || '';
    if (Object.keys(metadata).length > 0) {
      desc += '<br/><br/><b>Metadata:</b><br/>';
      desc += Object.entries(metadata)
        .map(([key, value]) => `${key}: ${typeof value === 'object' ? JSON.stringify(value) : value}`)
        .join('<br/>');
    }
    return desc;
  }

  destroy(): void {
    this.clearAll();
  }
}

export default CyberverseLayers;