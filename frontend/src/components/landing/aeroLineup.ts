export interface LineupItem {
  id: string;
  keyBadge: string;
  name: string;
  code: string;
  subtitle: string;
  category: string;
  specs: { label: string; value: string }[];
  modelPath: string;
  fileSizeBytes?: number;
  imagePath: string;
  camDist: number;
  camElevation: number;
  camAngle: number;
  isDrone?: boolean;
}

export const AERO_LINEUP: LineupItem[] = [
  {
    id: 'rotax_912is',
    keyBadge: 'F1',
    name: 'Rotax 912 iS Sport',
    code: 'ROTAX 912 iS',
    subtitle: '100 HP Naturally Aspirated Aero-EFI · Dual FADEC (Primary Ref)',
    category: 'MALE UAV PRIMARY PROPULSION',
    specs: [
      { label: 'RATED POWER', value: '100 HP @ 5800 RPM' },
      { label: 'DISPLACEMENT', value: '1,352 cc (4-Cyl Flat)' },
      { label: 'MANAGEMENT', value: 'Redundant Dual FADEC' },
      { label: 'FUEL INJECTION', value: 'Multi-Point Port EFI' },
    ],
    modelPath: '/models/rotax_912is.glb',
    fileSizeBytes: 16779456,
    imagePath: '/images/lineup/render_912is_beauty.png',
    camDist: 2.4,
    camElevation: 0.36,
    camAngle: -1.2,
  },
  {
    id: 'rotax_914',
    keyBadge: 'F2',
    name: 'Rotax 914 F Turbo',
    code: 'ROTAX 914 F',
    subtitle: '115 HP Turbocharged Powerplant · Automatic Wastegate TCU',
    category: 'HIGH-ALTITUDE CRUISE EXTENSION',
    specs: [
      { label: 'TAKE-OFF POWER', value: '115 HP (5 min limit)' },
      { label: 'TURBOCHARGING', value: 'Exhaust Wastegate TCU' },
      { label: 'CRITICAL ALTITUDE', value: '16,000 ft ceiling' },
      { label: 'DRY WEIGHT', value: '78.5 kg with turbo' },
    ],
    modelPath: '/models/rotax_914.glb',
    fileSizeBytes: 6081344,
    imagePath: '/images/lineup/render_914_solid.png',
    camDist: 2.4,
    camElevation: 0.36,
    camAngle: -1.2,
  },
  {
    id: 'rotax_915is',
    keyBadge: 'F3',
    name: 'Rotax 915 iS Turbo',
    code: 'ROTAX 915 iS',
    subtitle: '141 HP Turbocharged & Intercooled · Full Altitude FADEC',
    category: 'ADVANCED PAYLOAD MALE ENVELOPE',
    specs: [
      { label: 'CONTINUOUS POWER', value: '135 HP to FL150' },
      { label: 'ASPIRATION', value: 'Turbo + Charge-Air Cooler' },
      { label: 'TIME BETWEEN OVERHAUL', value: '1,200 hrs TBO' },
      { label: 'TATTVA RESIDUALS', value: '27-channel telemetry' },
    ],
    modelPath: '/models/rotax_915is.glb',
    fileSizeBytes: 19146632,
    imagePath: '/images/lineup/render_915is_framing.png',
    camDist: 2.4,
    camElevation: 0.36,
    camAngle: -1.2,
  },
  {
    id: 'austro_ae300',
    keyBadge: 'F4',
    name: 'Austro Engine AE300',
    code: 'AUSTRO AE300',
    subtitle: '2.0L Turbo Diesel · 168 HP · Common-Rail Heavy Fuel Injection',
    category: 'COMMON-RAIL DIESEL UAV PROPULSION',
    specs: [
      { label: 'MAX POWER', value: '168 HP @ 3880 RPM' },
      { label: 'FUEL COMPATIBILITY', value: 'Jet-A1 / Diesel Fuel' },
      { label: 'INJECTION SYSTEM', value: '1800-bar Common Rail' },
      { label: 'EFFICIENCY', value: '214 g/kWh Low BSFC' },
    ],
    modelPath: '/models/austro_ae300.glb',
    fileSizeBytes: 1989584,
    imagePath: '/images/lineup/render_austro_ae300.png',
    camDist: 2.4,
    camElevation: 0.36,
    camAngle: -1.2,
  },
  {
    id: 'vrde_jayem',
    keyBadge: 'F5',
    name: 'VRDE Jayem 2.2L',
    code: 'VRDE 2.2L',
    subtitle: '2.2L CI Turbocharged · 180 HP · DRDO Indigenized Heavy Fuel',
    category: 'DRDO INDIGENOUS AERO-ENGINE (VRDE)',
    specs: [
      { label: 'MAX POWER', value: '180 HP @ 4000 RPM' },
      { label: 'ASPIRATION', value: 'VGT Turbo + Intercooler' },
      { label: 'INDIGENOUS CONTENT', value: '100% Indian Manufacture' },
      { label: 'DEFENCE APPLICATION', value: 'Tactical Long-Range UAV' },
    ],
    modelPath: '/models/vrde_jayem_2_2l.glb',
    fileSizeBytes: 901828,
    imagePath: '/images/lineup/render_vrde_jayem.png',
    camDist: 2.4,
    camElevation: 0.36,
    camAngle: -1.2,
  },
  {
    id: 'uav_predator',
    keyBadge: 'F6',
    name: 'Predator-Class MALE UAV',
    code: 'MALE AIRFRAME',
    subtitle: 'Medium-Altitude Long-Endurance · Pusher Propulsion Configuration',
    category: 'TACTICAL MALE STRATEGIC DRONE (32H+ LOITER)',
    specs: [
      { label: 'PROPULSION', value: 'Rotax 914 / 915 iS Pusher' },
      { label: 'ENDURANCE', value: '32+ Hours SATCOM Loiter' },
      { label: 'SERVICE CEILING', value: '30,000 ft MSL' },
      { label: 'PAYLOAD / MTOW', value: '350 kg / 1,450 kg MTOW' },
    ],
    modelPath: '/models/uav_predator.glb',
    fileSizeBytes: 6639304,
    imagePath: '/images/lineup/sc_bayraktar_tb3.png',
    camDist: 3.2,
    camElevation: 0.38,
    camAngle: -1.2,
    isDrone: true,
  },
];

