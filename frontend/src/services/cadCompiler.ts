import * as THREE from 'three';

export interface GeometricFeature {
  type:
    | 'box'
    | 'cylinder'
    | 'sphere'
    | 'cone'
    | 'torus'
    | 'tube'
    | 'plate'
    | 'bolt'
    | 'gear'
    | 'bracket'
    | 'hole'
    | 'ring'
    | 'rectangle_2d'
    | 'circle_2d'
    | 'polygon_2d'
    | 'slot_2d'
    | 'line_2d'
    | 'arc_2d'
    | 'sketch';
  operation?: 'add' | 'cut' | 'subtract' | 'intersect';
  params: Record<string, number | string | boolean>;
  position?: [number, number, number];
  rotation?: [number, number, number];
}

export interface ModelSpecification {
  name: string;
  description: string;
  cadCode: string;
  dimensions?: { width: number; height: number; depth: number };
  features: GeometricFeature[];
  is2D?: boolean;
  rawStl?: string;
}

/**
 * Builds a complete 3D CAD or 2D Technical Drawing Group containing meshes, edges, and annotations.
 * Automatically centers all geometry at (0, 0, 0)
 */
export function buildCadModel(
  features: GeometricFeature[],
  cadCode?: string,
  viewMode: '3d' | '2d' = '3d',
  wireframe: boolean = false,
  showEdges: boolean = true,
  is2DOverride?: boolean,
  originalPrompt?: string
): {
  group: THREE.Group;
  primaryGeometry: THREE.BufferGeometry;
  dimensions: { width: number; height: number; depth: number };
  is2D: boolean;
} {
  // 1. Resolve features: prioritize parsing Python code directly so complex AST arrays (polar, brackets) are faithfully rendered
  let resolvedFeatures = parseFeaturesFromCode(cadCode || '', originalPrompt);
  if (resolvedFeatures.length === 0 && features && features.length > 0) {
    resolvedFeatures = features;
  }

  // 2. Determine if this is a 2D technical drawing
  const is2D =
    is2DOverride === true ||
    resolvedFeatures.some((f) => f.type.includes('_2d') || f.type === 'sketch') ||
    (!!cadCode && /BuildSketch/i.test(cadCode) && !/extrude|revolve/i.test(cadCode));

  if (is2D) {
    const result2D = build2dCadDrawing(resolvedFeatures, cadCode, wireframe);
    return { ...result2D, is2D: true };
  }

  // 3. 3D Solid Part Assembly
  const group = new THREE.Group();
  const lowerCode = (cadCode || '').toLowerCase();
  const lowerPrompt = (originalPrompt || '').toLowerCase();

  const isBracket =
    lowerCode.includes('mount') ||
    lowerCode.includes('bracket') ||
    lowerCode.includes('stepper') ||
    lowerCode.includes('nema') ||
    lowerPrompt.includes('bracket') ||
    lowerPrompt.includes('mount') ||
    lowerPrompt.includes('stepper') ||
    lowerPrompt.includes('nema');

  const isFlange =
    lowerCode.includes('flange') ||
    lowerPrompt.includes('flange') ||
    (lowerCode.includes('polarlocations') && resolvedFeatures.some((f) => f.type === 'cylinder'));

  const isEnclosure =
    lowerCode.includes('enclosure') ||
    lowerPrompt.includes('enclosure') ||
    lowerPrompt.includes('split-body') ||
    (resolvedFeatures.some((f) => f.type === 'box' && f.operation === 'cut') &&
      resolvedFeatures.some((f) => f.type === 'cylinder'));

  const isGear = lowerCode.includes('gear') || lowerPrompt.includes('gear') || lowerPrompt.includes('pinion') || lowerPrompt.includes('cog');

  let primaryGeom: THREE.BufferGeometry | null = null;

  if (isBracket) {
    // Heavy-duty L-bracket / NEMA Stepper Motor Mount
    primaryGeom = buildBracketGeometry(resolvedFeatures, cadCode, originalPrompt);
  } else if (isFlange) {
    // Stepped Circular Flange with central bore and polar bolt circle
    primaryGeom = buildFlangeGeometry(resolvedFeatures, cadCode);
  } else if (isEnclosure) {
    // Electronics Enclosure with hollow cavity & corner screw bosses
    primaryGeom = buildEnclosureGeometry(resolvedFeatures, cadCode, originalPrompt);
  } else if (isGear) {
    // Spur Gear with teeth and hub bore
    primaryGeom = buildGearGeometry(resolvedFeatures, cadCode, originalPrompt);
  } else {
    // Universal Composite Assembly
    primaryGeom = buildUniversalCompositeGeometry(resolvedFeatures);
  }

  // Create standard solid CAD mesh
  const material = new THREE.MeshStandardMaterial({
    color: viewMode === '2d' ? 0x38bdf8 : 0x2563eb, // Precision vibrant CAD blue
    roughness: 0.35,
    metalness: 0.45,
    wireframe: wireframe,
    flatShading: false,
  });

  const mesh = new THREE.Mesh(primaryGeom, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  group.add(mesh);

  // Add sharp CAD outline edges
  if (showEdges && !wireframe) {
    const edges = new THREE.EdgesGeometry(primaryGeom, 25);
    const lineMat = new THREE.LineBasicMaterial({
      color: viewMode === '2d' ? 0x0369a1 : 0x1e3a8a,
      linewidth: 1.5,
    });
    const lineSegments = new THREE.LineSegments(edges, lineMat);
    group.add(lineSegments);
  }

  // Center group and compute bounding box
  const bbox = new THREE.Box3().setFromObject(group);
  const center = bbox.getCenter(new THREE.Vector3());
  const size = bbox.getSize(new THREE.Vector3());

  group.position.set(-center.x, -center.y, -center.z);

  return {
    group,
    primaryGeometry: primaryGeom,
    dimensions: {
      width: Math.round(size.x * 10) / 10 || 10,
      height: Math.round(size.y * 10) / 10 || 10,
      depth: Math.round(size.z * 10) / 10 || 10,
    },
    is2D: false,
  };
}

/**
 * Builds a true 2D CAD Technical Drawing / Blueprint on the X-Z ground plane (Z=0 in 2D Top View)
 * Supports multiple composite shapes (e.g. flower central hub + ALL surrounding petals)!
 */
function build2dCadDrawing(
  features: GeometricFeature[],
  cadCode?: string,
  wireframe: boolean = false
): { group: THREE.Group; primaryGeometry: THREE.BufferGeometry; dimensions: { width: number; height: number; depth: number } } {
  const group = new THREE.Group();

  const additiveFeats = features.filter((f) => f.operation !== 'cut' && f.operation !== 'subtract');
  const subtractiveFeats = features.filter((f) => f.operation === 'cut' || f.operation === 'subtract' || f.type === 'hole');

  if (additiveFeats.length === 0) {
    additiveFeats.push({ type: 'rectangle_2d', params: { width: 60, height: 40 }, position: [0, 0, 0] });
  }

  const sheetMat = new THREE.MeshBasicMaterial({
    color: 0x0284c7,
    transparent: true,
    opacity: wireframe ? 0.05 : 0.22,
    side: THREE.DoubleSide,
    depthWrite: false,
  });

  const lineMat = new THREE.LineBasicMaterial({
    color: 0x38bdf8, // Vibrant CAD cyan
    linewidth: 2,
  });

  const centerMat = new THREE.LineBasicMaterial({
    color: 0x0ea5e9,
    transparent: true,
    opacity: 0.85,
  });

  const componentGeometries: THREE.BufferGeometry[] = [];
  let minX = Infinity;
  let maxX = -Infinity;
  let minZ = Infinity;
  let maxZ = -Infinity;

  // Render EACH additive 2D shape (e.g. central disc AND all 6 petals for flower!)
  for (const feat of additiveFeats) {
    const p = feat.params || {};
    const posX = feat.position ? feat.position[0] : 0;
    const posZ = feat.position ? (feat.position[2] ?? feat.position[1] ?? 0) : 0;

    const shape = new THREE.Shape();
    let r = 15;

    if (feat.type === 'circle_2d' || feat.type === 'cylinder') {
      r = Number(p.radius ?? (Number(p.diameter ?? 30) / 2));
      shape.absarc(0, 0, r, 0, Math.PI * 2, false);

      minX = Math.min(minX, posX - r);
      maxX = Math.max(maxX, posX + r);
      minZ = Math.min(minZ, posZ - r);
      maxZ = Math.max(maxZ, posZ + r);

      // Center crosshairs for each circular feature
      const crossArm = r * 1.35;
      const crossPts = [
        new THREE.Vector3(posX - crossArm, 0.03, posZ),
        new THREE.Vector3(posX + crossArm, 0.03, posZ),
        new THREE.Vector3(posX, 0.03, posZ - crossArm),
        new THREE.Vector3(posX, 0.03, posZ + crossArm),
      ];
      const crossGeom = new THREE.BufferGeometry().setFromPoints(crossPts);
      group.add(new THREE.LineSegments(crossGeom, centerMat));
    } else {
      // Rectangle / Plate
      const w = Number(p.width ?? p.x ?? 60);
      const h = Number(p.height ?? p.y ?? p.length ?? 40);
      const hw = w / 2;
      const hh = h / 2;

      shape.moveTo(-hw, -hh);
      shape.lineTo(hw, -hh);
      shape.lineTo(hw, hh);
      shape.lineTo(-hw, hh);
      shape.closePath();

      minX = Math.min(minX, posX - hw);
      maxX = Math.max(maxX, posX + hw);
      minZ = Math.min(minZ, posZ - hh);
      maxZ = Math.max(maxZ, posZ + hh);
    }

    // Subtract internal holes if only 1 base shape
    if (additiveFeats.length === 1) {
      for (const sub of subtractiveFeats) {
        const sp = sub.params || {};
        const sr = Number(sp.radius ?? (Number(sp.diameter ?? 8) / 2));
        const shx = (sub.position ? sub.position[0] : 0) - posX;
        const shz = (sub.position ? (sub.position[2] ?? sub.position[1] ?? 0) : 0) - posZ;

        const holePath = new THREE.Path();
        holePath.absarc(shx, shz, sr, 0, Math.PI * 2, true);
        shape.holes.push(holePath);
      }
    }

    // Create planar sheet mesh
    const shapeGeom = new THREE.ShapeGeometry(shape, 48);
    shapeGeom.rotateX(-Math.PI / 2);
    shapeGeom.translate(posX, 0, posZ);
    componentGeometries.push(shapeGeom);

    const mesh = new THREE.Mesh(shapeGeom, sheetMat);
    group.add(mesh);

    // Create contour outline loop
    const outerPoints = shape.getPoints(48).map((pt) => new THREE.Vector3(pt.x + posX, 0.02, -pt.y + posZ));
    const outerGeom = new THREE.BufferGeometry().setFromPoints(outerPoints);
    group.add(new THREE.LineLoop(outerGeom, lineMat));

    // Hole contours
    for (const hole of shape.holes) {
      const holePoints = hole.getPoints(36).map((pt) => new THREE.Vector3(pt.x + posX, 0.02, -pt.y + posZ));
      const holeGeom = new THREE.BufferGeometry().setFromPoints(holePoints);
      group.add(new THREE.LineLoop(holeGeom, lineMat));
    }
  }

  // Draw standalone subtractive holes (e.g. if multiple base shapes)
  if (additiveFeats.length > 1) {
    for (const sub of subtractiveFeats) {
      const sp = sub.params || {};
      const sr = Number(sp.radius ?? (Number(sp.diameter ?? 8) / 2));
      const shx = sub.position ? sub.position[0] : 0;
      const shz = sub.position ? (sub.position[2] ?? sub.position[1] ?? 0) : 0;

      const holeCircle = new THREE.Shape();
      holeCircle.absarc(0, 0, sr, 0, Math.PI * 2, false);
      const holePoints = holeCircle.getPoints(36).map((pt) => new THREE.Vector3(pt.x + shx, 0.02, -pt.y + shz));
      const holeGeom = new THREE.BufferGeometry().setFromPoints(holePoints);
      group.add(new THREE.LineLoop(holeGeom, lineMat));

      const crossArm = sr * 1.35;
      const crossPts = [
        new THREE.Vector3(shx - crossArm, 0.03, shz),
        new THREE.Vector3(shx + crossArm, 0.03, shz),
        new THREE.Vector3(shx, 0.03, shz - crossArm),
        new THREE.Vector3(shx, 0.03, shz + crossArm),
      ];
      group.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(crossPts), centerMat));
    }
  }

  // Calculate composite width and height
  const totalWidth = Math.max(20, Math.round((maxX - minX) * 10) / 10);
  const totalHeight = Math.max(20, Math.round((maxZ - minZ) * 10) / 10);

  // Technical Dimension Callouts spanning entire composite geometry
  const dimColor = 0x93c5fd;
  const dimMat = new THREE.LineBasicMaterial({ color: dimColor, transparent: true, opacity: 0.8 });
  const dimOffset = Math.max(8, Math.min(totalWidth, totalHeight) * 0.15);

  const dimPoints: THREE.Vector3[] = [];

  // Horizontal Dimension (Width)
  const bottomZ = maxZ + dimOffset;
  dimPoints.push(new THREE.Vector3(minX, 0.03, maxZ + 1));
  dimPoints.push(new THREE.Vector3(minX, 0.03, bottomZ + 3));
  dimPoints.push(new THREE.Vector3(maxX, 0.03, maxZ + 1));
  dimPoints.push(new THREE.Vector3(maxX, 0.03, bottomZ + 3));
  dimPoints.push(new THREE.Vector3(minX, 0.03, bottomZ));
  dimPoints.push(new THREE.Vector3(maxX, 0.03, bottomZ));
  dimPoints.push(new THREE.Vector3(minX - 1.5, 0.03, bottomZ - 1.5));
  dimPoints.push(new THREE.Vector3(minX + 1.5, 0.03, bottomZ + 1.5));
  dimPoints.push(new THREE.Vector3(maxX - 1.5, 0.03, bottomZ - 1.5));
  dimPoints.push(new THREE.Vector3(maxX + 1.5, 0.03, bottomZ + 1.5));

  // Vertical Dimension (Height)
  const rightX = maxX + dimOffset;
  dimPoints.push(new THREE.Vector3(maxX + 1, 0.03, minZ));
  dimPoints.push(new THREE.Vector3(rightX + 3, 0.03, minZ));
  dimPoints.push(new THREE.Vector3(maxX + 1, 0.03, maxZ));
  dimPoints.push(new THREE.Vector3(rightX + 3, 0.03, maxZ));
  dimPoints.push(new THREE.Vector3(rightX, 0.03, minZ));
  dimPoints.push(new THREE.Vector3(rightX, 0.03, maxZ));
  dimPoints.push(new THREE.Vector3(rightX - 1.5, 0.03, minZ - 1.5));
  dimPoints.push(new THREE.Vector3(rightX + 1.5, 0.03, minZ + 1.5));
  dimPoints.push(new THREE.Vector3(rightX - 1.5, 0.03, maxZ - 1.5));
  dimPoints.push(new THREE.Vector3(rightX + 1.5, 0.03, maxZ + 1.5));

  group.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(dimPoints), dimMat));

  // Datum Origin Marker
  const datumPts = [
    new THREE.Vector3(-2.5, 0.03, 0),
    new THREE.Vector3(2.5, 0.03, 0),
    new THREE.Vector3(0, 0.03, -2.5),
    new THREE.Vector3(0, 0.03, 2.5),
  ];
  group.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(datumPts), new THREE.LineBasicMaterial({ color: 0xef4444 })));

  const primaryGeom = componentGeometries.length > 0 ? mergeGeometriesSafely(componentGeometries) : new THREE.PlaneGeometry(60, 40);

  return {
    group,
    primaryGeometry: primaryGeom,
    dimensions: {
      width: totalWidth,
      height: totalHeight,
      depth: 0,
    },
  };
}

/**
 * Builds realistic heavy-duty L-bracket / NEMA Stepper Motor Mount
 */
function buildBracketGeometry(features: GeometricFeature[], code?: string, prompt?: string): THREE.BufferGeometry {
  const geometries: THREE.BufferGeometry[] = [];

  let width = 42;
  let height = 50;
  let depth = 40;
  const thickness = 5;

  const dimMatch = (prompt || '').match(/(\d+)\s*x\s*(\d+)/i);
  if (dimMatch) {
    width = parseFloat(dimMatch[1]) || 42;
    height = parseFloat(dimMatch[2]) || 50;
  }

  // 1. Vertical motor mounting plate with central pilot hole & 4x M3 holes
  const vertShape = new THREE.Shape();
  const halfW = width / 2;
  vertShape.moveTo(-halfW, 0);
  vertShape.lineTo(halfW, 0);
  vertShape.lineTo(halfW, height);
  vertShape.lineTo(-halfW, height);
  vertShape.closePath();

  // Central pilot hole (22mm diameter)
  const centerY = height / 2 + 2;
  const pilotHole = new THREE.Path();
  pilotHole.absarc(0, centerY, 11, 0, Math.PI * 2, true);
  vertShape.holes.push(pilotHole);

  // 4x M3 motor mounting holes on 31mm pattern
  const spacing = 15.5;
  const m3Radius = 1.6;
  [
    [-spacing, centerY - spacing],
    [spacing, centerY - spacing],
    [-spacing, centerY + spacing],
    [spacing, centerY + spacing],
  ].forEach(([hx, hy]) => {
    const hp = new THREE.Path();
    hp.absarc(hx, hy, m3Radius, 0, Math.PI * 2, true);
    vertShape.holes.push(hp);
  });

  const vertExtrude = new THREE.ExtrudeGeometry(vertShape, {
    depth: thickness,
    bevelEnabled: true,
    bevelSegments: 2,
    bevelSize: 0.5,
    bevelThickness: 0.5,
    curveSegments: 32,
  });
  geometries.push(vertExtrude);

  // 2. Horizontal base mounting plate with 4x M4 mounting holes
  const baseShape = new THREE.Shape();
  baseShape.moveTo(-halfW, 0);
  baseShape.lineTo(halfW, 0);
  baseShape.lineTo(halfW, depth);
  baseShape.lineTo(-halfW, depth);
  baseShape.closePath();

  // 4x M4 holes
  const m4Radius = 2.2;
  const bxOffset = 13;
  [
    [-bxOffset, 10],
    [bxOffset, 10],
    [-bxOffset, depth - 10],
    [bxOffset, depth - 10],
  ].forEach(([bx, bz]) => {
    const hp = new THREE.Path();
    hp.absarc(bx, bz, m4Radius, 0, Math.PI * 2, true);
    baseShape.holes.push(hp);
  });

  const baseExtrude = new THREE.ExtrudeGeometry(baseShape, {
    depth: thickness,
    bevelEnabled: true,
    bevelSegments: 2,
    bevelSize: 0.5,
    bevelThickness: 0.5,
    curveSegments: 32,
  });
  baseExtrude.rotateX(Math.PI / 2);
  geometries.push(baseExtrude);

  // 3. Dual triangular stiffener ribs / gussets
  const ribThickness = 4;
  const ribHeight = height * 0.55;
  const ribDepth = depth * 0.75;

  const ribShape = new THREE.Shape();
  ribShape.moveTo(0, 0);
  ribShape.lineTo(ribDepth, 0);
  ribShape.lineTo(0, ribHeight);
  ribShape.closePath();

  const ribLeft = new THREE.ExtrudeGeometry(ribShape, { depth: ribThickness });
  ribLeft.rotateY(-Math.PI / 2);
  ribLeft.translate(-halfW + ribThickness, 0, 0);
  geometries.push(ribLeft);

  const ribRight = new THREE.ExtrudeGeometry(ribShape, { depth: ribThickness });
  ribRight.rotateY(-Math.PI / 2);
  ribRight.translate(halfW, 0, 0);
  geometries.push(ribRight);

  const merged = mergeGeometriesSafely(geometries);
  merged.center();
  return merged;
}

/**
 * Builds Stepped Circular Flange with central bore and polar bolt circle
 */
function buildFlangeGeometry(features: GeometricFeature[], code?: string): THREE.BufferGeometry {
  const cyls = features.filter((f) => f.type === 'cylinder' && f.operation !== 'cut');

  let od = 120;
  let baseH = 15;
  let totalH = 35;
  let boreD = 40;
  let boltD = 90;
  const boltHoleD = 8;
  let numBoltHoles = 6;

  if (cyls.length > 0) {
    const baseP = cyls[0].params || {};
    od = Number(baseP.diameter ?? (Number(baseP.radius ?? 60) * 2));
    baseH = Number(baseP.height ?? 15);
  }
  if (cyls.length > 1) {
    const stepP = cyls[1].params || {};
    totalH = baseH + Number(stepP.height ?? 20);
  }

  if (code) {
    const polarMatch = code.match(/PolarLocations\s*\(\s*(?:radius\s*=\s*)?([\d.]+)\s*,\s*(?:count\s*=\s*)?(\d+)/i);
    if (polarMatch) {
      boltD = parseFloat(polarMatch[1]) * 2;
      numBoltHoles = parseInt(polarMatch[2], 10);
    }
  }

  const flangeShape = new THREE.Shape();
  flangeShape.absarc(0, 0, od / 2, 0, Math.PI * 2, false);

  // Central bore hole
  const borePath = new THREE.Path();
  borePath.absarc(0, 0, boreD / 2, 0, Math.PI * 2, true);
  flangeShape.holes.push(borePath);

  // Polar bolt circle holes
  const boltR = boltD / 2;
  for (let i = 0; i < numBoltHoles; i++) {
    const angle = (i * (360 / numBoltHoles) * Math.PI) / 180;
    const bx = boltR * Math.cos(angle);
    const bz = boltR * Math.sin(angle);
    const holeP = new THREE.Path();
    holeP.absarc(bx, bz, boltHoleD / 2, 0, Math.PI * 2, true);
    flangeShape.holes.push(holeP);
  }

  const baseExtrude = new THREE.ExtrudeGeometry(flangeShape, {
    depth: baseH,
    bevelEnabled: true,
    bevelSegments: 2,
    bevelSize: 0.8,
    bevelThickness: 0.8,
    curveSegments: 48,
  });
  baseExtrude.rotateX(-Math.PI / 2);

  // Stepped upper neck cylinder
  const neckH = totalH - baseH;
  const neckShape = new THREE.Shape();
  neckShape.absarc(0, 0, (od * 0.65) / 2, 0, Math.PI * 2, false);
  const neckBore = new THREE.Path();
  neckBore.absarc(0, 0, boreD / 2, 0, Math.PI * 2, true);
  neckShape.holes.push(neckBore);

  const neckExtrude = new THREE.ExtrudeGeometry(neckShape, {
    depth: neckH,
    bevelEnabled: true,
    bevelSegments: 2,
    bevelSize: 0.5,
    bevelThickness: 0.5,
    curveSegments: 48,
  });
  neckExtrude.rotateX(-Math.PI / 2);
  neckExtrude.translate(0, baseH, 0);

  const merged = mergeGeometriesSafely([baseExtrude, neckExtrude]);
  merged.center();
  return merged;
}

/**
 * Builds Electronics Enclosure with hollow cavity & corner screw bosses
 */
function buildEnclosureGeometry(features: GeometricFeature[], code?: string, prompt?: string): THREE.BufferGeometry {
  const geometries: THREE.BufferGeometry[] = [];

  let width = 100;
  let depth = 60;
  let height = 30;
  const wall = 2.5;

  const dimMatch = (prompt || '').match(/(\d+)\s*x\s*(\d+)\s*x\s*(\d+)/i);
  if (dimMatch) {
    width = parseFloat(dimMatch[1]) || 100;
    depth = parseFloat(dimMatch[2]) || 60;
    height = parseFloat(dimMatch[3]) || 30;
  }

  // 1. Outer Box with Cavity via Shape Extrusion
  const outerShape = new THREE.Shape();
  const hw = width / 2;
  const hd = depth / 2;
  outerShape.moveTo(-hw, -hd);
  outerShape.lineTo(hw, -hd);
  outerShape.lineTo(hw, hd);
  outerShape.lineTo(-hw, hd);
  outerShape.closePath();

  // Hollow internal cavity
  const innerPath = new THREE.Path();
  const inHw = hw - wall;
  const inHd = hd - wall;
  innerPath.moveTo(-inHw, -inHd);
  innerPath.lineTo(inHw, -inHd);
  innerPath.lineTo(inHw, inHd);
  innerPath.lineTo(-inHw, inHd);
  innerPath.closePath();
  outerShape.holes.push(innerPath);

  // Extrude walls
  const wallGeom = new THREE.ExtrudeGeometry(outerShape, { depth: height - wall });
  wallGeom.rotateX(-Math.PI / 2);
  wallGeom.translate(0, wall, 0);
  geometries.push(wallGeom);

  // Solid base plate
  const baseGeom = new THREE.BoxGeometry(width, wall, depth);
  baseGeom.translate(0, wall / 2, 0);
  geometries.push(baseGeom);

  // 4 corner screw bosses (OD 7mm, ID 3mm, height 20mm)
  const bossOD = 7;
  const bossID = 3;
  const bossH = 20;
  const bx = hw - wall - bossOD / 2;
  const bz = hd - wall - bossOD / 2;

  [
    [-bx, -bz],
    [bx, -bz],
    [-bx, bz],
    [bx, bz],
  ].forEach(([cx, cz]) => {
    const bossShape = new THREE.Shape();
    bossShape.absarc(0, 0, bossOD / 2, 0, Math.PI * 2, false);
    const holeP = new THREE.Path();
    holeP.absarc(0, 0, bossID / 2, 0, Math.PI * 2, true);
    bossShape.holes.push(holeP);

    const bossExtrude = new THREE.ExtrudeGeometry(bossShape, { depth: bossH, curveSegments: 32 });
    bossExtrude.rotateX(-Math.PI / 2);
    bossExtrude.translate(cx, wall, cz);
    geometries.push(bossExtrude);
  });

  const merged = mergeGeometriesSafely(geometries);
  merged.center();
  return merged;
}

/**
 * Builds precision 3D Spur Gear with teeth, hub, and shaft bore
 */
function buildGearGeometry(features: GeometricFeature[], code?: string, prompt?: string): THREE.BufferGeometry {
  const numTeeth = 18;
  const pitchRadius = 35;
  const toothDepth = 6;
  const gearThickness = 12;
  const boreRadius = 6;

  const shape = new THREE.Shape();
  const totalSteps = numTeeth * 4;

  for (let i = 0; i <= totalSteps; i++) {
    const angle = (i * 2 * Math.PI) / totalSteps;
    const stepInTooth = i % 4;
    const r = stepInTooth === 1 || stepInTooth === 2 ? pitchRadius + toothDepth / 2 : pitchRadius - toothDepth / 2;
    const x = r * Math.cos(angle);
    const y = r * Math.sin(angle);

    if (i === 0) shape.moveTo(x, y);
    else shape.lineTo(x, y);
  }
  shape.closePath();

  // Central shaft bore
  const bore = new THREE.Path();
  bore.absarc(0, 0, boreRadius, 0, Math.PI * 2, true);
  shape.holes.push(bore);

  const extrude = new THREE.ExtrudeGeometry(shape, {
    depth: gearThickness,
    bevelEnabled: true,
    bevelSegments: 2,
    bevelSize: 0.5,
    bevelThickness: 0.5,
    curveSegments: 32,
  });
  extrude.rotateX(-Math.PI / 2);
  extrude.center();
  return extrude;
}

/**
 * Universal Composite Assembly for general multi-primitive models
 */
function buildUniversalCompositeGeometry(features: GeometricFeature[]): THREE.BufferGeometry {
  const geometries: THREE.BufferGeometry[] = [];

  for (const feat of features) {
    if (feat.operation === 'cut' || feat.operation === 'subtract') continue;

    const geom = createPrimitiveGeometry(feat);
    if (geom) {
      if (feat.position) {
        geom.translate(feat.position[0], feat.position[1], feat.position[2]);
      }
      if (feat.rotation) {
        geom.rotateX(feat.rotation[0]);
        geom.rotateY(feat.rotation[1]);
        geom.rotateZ(feat.rotation[2]);
      }
      geometries.push(geom);
    }
  }

  if (geometries.length === 0) {
    const box = new THREE.BoxGeometry(20, 20, 20);
    box.center();
    return box;
  }

  const merged = mergeGeometriesSafely(geometries);
  merged.center();
  return merged;
}

/**
 * Creates individual primitive Three.js geometries from a feature definition
 */
function createPrimitiveGeometry(feat: GeometricFeature): THREE.BufferGeometry {
  const p = feat.params || {};

  switch (feat.type) {
    case 'box':
    case 'plate': {
      const w = Number(p.width ?? p.x ?? 20);
      const h = Number(p.height ?? p.y ?? 20);
      const d = Number(p.depth ?? p.length ?? p.z ?? 20);
      return new THREE.BoxGeometry(w, h, d);
    }
    case 'cylinder':
    case 'tube':
    case 'bolt': {
      const rTop = Number(p.radiusTop ?? p.radius ?? (Number(p.diameter ?? 20) / 2));
      const rBottom = Number(p.radiusBottom ?? p.radius ?? (Number(p.diameter ?? 20) / 2));
      const h = Number(p.height ?? p.length ?? 30);
      const segments = Math.max(24, Number(p.segments ?? 48));
      return new THREE.CylinderGeometry(rTop, rBottom, h, segments);
    }
    case 'sphere': {
      const r = Number(p.radius ?? (Number(p.diameter ?? 20) / 2));
      return new THREE.SphereGeometry(r, 36, 36);
    }
    case 'cone': {
      const r = Number(p.radius ?? (Number(p.diameter ?? 20) / 2));
      const h = Number(p.height ?? 30);
      return new THREE.ConeGeometry(r, h, 36);
    }
    case 'torus':
    case 'ring': {
      const r = Number(p.radius ?? (Number(p.diameter ?? 30) / 2));
      const tube = Number(p.tubeRadius ?? p.thickness ?? 4);
      return new THREE.TorusGeometry(r, tube, 24, 60);
    }
    case 'hole': {
      const r = Number(p.radius ?? (Number(p.diameter ?? 6) / 2));
      const h = Number(p.height ?? p.depth ?? 25);
      return new THREE.CylinderGeometry(r, r, h, 32);
    }
    default:
      return new THREE.BoxGeometry(15, 15, 15);
  }
}

/**
 * Intelligent CAD Feature & Dimension Parser:
 * Evaluates Build123d / CadQuery code AST (including PolarLocations and coordinate arrays)
 */
export function parseFeaturesFromCode(code: string, originalPrompt?: string): GeometricFeature[] {
  const lowerPrompt = (originalPrompt || '').toLowerCase();
  const lowerCode = (code || '').toLowerCase();

  const is2D =
    /\b(2d|sketch|drawing|flat|planar|profile)\b/.test(lowerPrompt) ||
    (/\b(rectangle|circle|square|polygon|slot)\b/.test(lowerPrompt) &&
      !/\b(3d|extrude|depth|height|box|cube|enclosure|flange|bracket|mount)\b/.test(lowerPrompt)) ||
    (code && /BuildSketch/i.test(code) && !/extrude/i.test(code));

  const features: GeometricFeature[] = [];
  const lines = (code || '').split('\n');

  let currentContext: { type: 'polar'; radius: number; count: number } | { type: 'locations'; points: [number, number][] } | null = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line || line.startsWith('#')) continue;

    // Detect PolarLocations(radius=..., count=...)
    const polarMatch = line.match(/PolarLocations\s*\(\s*(?:radius\s*=\s*)?([\d.]+)\s*,\s*(?:count\s*=\s*)?(\d+)/i);
    if (polarMatch) {
      currentContext = {
        type: 'polar',
        radius: parseFloat(polarMatch[1]),
        count: parseInt(polarMatch[2], 10),
      };
      continue;
    }

    // Detect Locations((x, y), (x, y), ...)
    const locMatch = line.match(/Locations\s*\(\s*(\([^)]+\)(?:\s*,\s*\([^)]+\))*)\s*\)/i);
    if (locMatch && !polarMatch) {
      const rawPts = locMatch[1];
      const ptMatches = Array.from(rawPts.matchAll(/\(\s*([-\d.]+)\s*,\s*([-\d.]+)(?:\s*,\s*([-\d.]+))?\s*\)/g));
      if (ptMatches.length > 0) {
        currentContext = {
          type: 'locations',
          points: ptMatches.map((m) => [parseFloat(m[1]), parseFloat(m[2])]),
        };
        continue;
      }
    }

    // Circle(radius=...) or Circle(r)
    const circMatch = line.match(/Circle\s*\(\s*(?:radius\s*=\s*)?([\d.]+)/i);
    if (circMatch) {
      const radius = parseFloat(circMatch[1]);
      const isSub = line.includes('SUBTRACT') || line.includes('subtract');

      if (currentContext && currentContext.type === 'polar') {
        const { radius: pR, count } = currentContext;
        for (let j = 0; j < count; j++) {
          const angle = (j * (360 / count) * Math.PI) / 180;
          features.push({
            type: 'circle_2d',
            operation: isSub ? 'subtract' : 'add',
            params: { radius },
            position: [pR * Math.cos(angle), 0, pR * Math.sin(angle)],
          });
        }
        currentContext = null;
      } else if (currentContext && currentContext.type === 'locations') {
        for (const pt of currentContext.points) {
          features.push({
            type: 'circle_2d',
            operation: isSub ? 'subtract' : 'add',
            params: { radius },
            position: [pt[0], 0, pt[1]],
          });
        }
        currentContext = null;
      } else {
        features.push({
          type: 'circle_2d',
          operation: isSub ? 'subtract' : 'add',
          params: { radius },
          position: [0, 0, 0],
        });
      }
      continue;
    }

    // Rectangle(w, h)
    const rectMatch = line.match(/Rectangle\s*\(\s*(?:width\s*=\s*)?([\d.]+)\s*,\s*(?:height\s*=\s*)?([\d.]+)/i);
    if (rectMatch) {
      const w = parseFloat(rectMatch[1]);
      const h = parseFloat(rectMatch[2]);
      const isSub = line.includes('SUBTRACT') || line.includes('subtract');
      features.push({
        type: 'rectangle_2d',
        operation: isSub ? 'subtract' : 'add',
        params: { width: w, height: h },
        position: [0, 0, 0],
      });
      continue;
    }

    // Box(w, h, d)
    const boxMatch = line.match(/Box\s*\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)/i);
    if (boxMatch) {
      const w = parseFloat(boxMatch[1]);
      const h = parseFloat(boxMatch[2]);
      const d = parseFloat(boxMatch[3]);
      const isSub = line.includes('SUBTRACT') || line.includes('subtract');
      features.push({
        type: 'box',
        operation: isSub ? 'subtract' : 'add',
        params: { width: w, height: h, depth: d },
        position: [0, h / 2, 0],
      });
      continue;
    }

    // Hole(radius=r, depth=d)
    const holeMatch = line.match(/Hole\s*\(\s*(?:radius\s*=\s*)?([\d.]+)/i);
    if (holeMatch) {
      const radius = parseFloat(holeMatch[1]);
      if (currentContext && currentContext.type === 'polar') {
        const { radius: pR, count } = currentContext;
        for (let j = 0; j < count; j++) {
          const angle = (j * (360 / count) * Math.PI) / 180;
          features.push({
            type: 'hole',
            operation: 'cut',
            params: { diameter: radius * 2, height: 25 },
            position: [pR * Math.cos(angle), 0, pR * Math.sin(angle)],
          });
        }
        currentContext = null;
      } else {
        features.push({
          type: 'hole',
          operation: 'cut',
          params: { diameter: radius * 2, height: 25 },
          position: [0, 0, 0],
        });
      }
      continue;
    }

    // Cylinder(radius=r, height=h)
    const cylMatch = line.match(/Cylinder\s*\(\s*(?:radius\s*=\s*)?([\d.]+)\s*,\s*(?:height\s*=\s*)?([\d.]+)/i);
    if (cylMatch) {
      const r = parseFloat(cylMatch[1]);
      const h = parseFloat(cylMatch[2]);
      const isSub = line.includes('SUBTRACT') || line.includes('subtract');
      features.push({
        type: 'cylinder',
        operation: isSub ? 'subtract' : 'add',
        params: { diameter: r * 2, height: h },
        position: [0, h / 2, 0],
      });
      continue;
    }
  }

  if (features.length > 0) return features;

  // Fallback heuristics based on prompt if code was not standard
  if (is2D) {
    if (lowerPrompt.includes('flower')) {
      // 1 central disc + 6 surrounding petals
      features.push({ type: 'circle_2d', params: { radius: 15 }, position: [0, 0, 0] });
      for (let j = 0; j < 6; j++) {
        const angle = (j * 60 * Math.PI) / 180;
        features.push({
          type: 'circle_2d',
          params: { radius: 12 },
          position: [20 * Math.cos(angle), 0, 20 * Math.sin(angle)],
        });
      }
      return features;
    }

    const pRect = lowerPrompt.match(/(\d+)\s*(?:x|by|\*|\s+)\s*(\d+)/i);
    if (pRect) {
      features.push({
        type: 'rectangle_2d',
        params: { width: parseFloat(pRect[1]), height: parseFloat(pRect[2]) },
        position: [0, 0, 0],
      });
      return features;
    }

    features.push({ type: 'circle_2d', params: { radius: 25 }, position: [0, 0, 0] });
    return features;
  }

  // 3D Bracket prompt fallback
  if (lowerPrompt.includes('bracket') || lowerPrompt.includes('stepper') || lowerPrompt.includes('nema')) {
    features.push({ type: 'bracket', params: { width: 42, height: 50, depth: 40 }, position: [0, 0, 0] });
    return features;
  }

  features.push({ type: 'box', params: { width: 40, height: 40, depth: 40 }, position: [0, 0, 0] });
  return features;
}

/**
 * Merges multiple BufferGeometries safely without buffer allocation errors
 */
function mergeGeometriesSafely(geometries: THREE.BufferGeometry[]): THREE.BufferGeometry {
  const nonIndexed = geometries.map((g) => (g.index ? g.toNonIndexed() : g.clone()));

  let totalFloats = 0;
  for (const g of nonIndexed) {
    const pos = g.getAttribute('position');
    if (pos) totalFloats += pos.array.length;
  }

  const mergedPositions = new Float32Array(totalFloats);
  let offset = 0;

  for (const g of nonIndexed) {
    const pos = g.getAttribute('position');
    if (pos) {
      mergedPositions.set(pos.array as Float32Array, offset);
      offset += pos.array.length;
    }
  }

  const merged = new THREE.BufferGeometry();
  merged.setAttribute('position', new THREE.BufferAttribute(mergedPositions, 3));
  merged.computeVertexNormals();
  return merged;
}

/**
 * Parses binary or ASCII STL data into a Three.js BufferGeometry
 */
export function parseSTL(stlData: string | ArrayBuffer): THREE.BufferGeometry {
  if (typeof stlData === 'string') {
    let cleaned = stlData.trim();
    if (cleaned.startsWith('data:')) {
      cleaned = cleaned.substring(cleaned.indexOf(',') + 1);
    }

    const isBase64 = !cleaned.startsWith('solid ') && /^[A-Za-z0-9+/=\s]+$/.test(cleaned.substring(0, 100));
    if (isBase64) {
      try {
        const binaryString = atob(cleaned.replace(/\s/g, ''));
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        return parseBinarySTL(bytes.buffer);
      } catch (e) {
        console.warn('Base64 decode fallback to ASCII', e);
      }
    }

    if (cleaned.startsWith('solid')) {
      return parseAsciiSTL(cleaned);
    }

    const encoder = new TextEncoder();
    return parseBinarySTL(encoder.encode(cleaned).buffer);
  }

  return parseBinarySTL(stlData);
}

function parseAsciiSTL(text: string): THREE.BufferGeometry {
  const vertexRegex =
    /vertex\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)/g;
  const vertices: number[] = [];
  let vertexMatch;
  while ((vertexMatch = vertexRegex.exec(text)) !== null) {
    vertices.push(parseFloat(vertexMatch[1]), parseFloat(vertexMatch[2]), parseFloat(vertexMatch[3]));
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  geometry.center();
  return geometry;
}

function parseBinarySTL(buffer: ArrayBuffer): THREE.BufferGeometry {
  const reader = new DataView(buffer);
  const faces = reader.getUint32(80, true);

  const vertices = new Float32Array(faces * 9);
  let offset = 84;
  for (let face = 0; face < faces; face++) {
    if (offset + 50 > buffer.byteLength) break;
    for (let v = 0; v < 3; v++) {
      const vIndex = (face * 3 + v) * 3;
      vertices[vIndex] = reader.getFloat32(offset + 12 + v * 12, true);
      vertices[vIndex + 1] = reader.getFloat32(offset + 16 + v * 12, true);
      vertices[vIndex + 2] = reader.getFloat32(offset + 20 + v * 12, true);
    }
    offset += 50;
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  geometry.center();
  return geometry;
}

/**
 * Exports a Three.js BufferGeometry to an ASCII STL string for download
 */
export function exportToSTL(geometry: THREE.BufferGeometry, modelName: string = 'TextCAD_Model'): string {
  const nonIndexed = geometry.index ? geometry.toNonIndexed() : geometry;
  const positions = nonIndexed.getAttribute('position');
  if (!positions) return '';

  let stl = `solid ${modelName.replace(/\s+/g, '_')}\n`;
  const count = positions.count;

  for (let i = 0; i < count; i += 3) {
    const ax = positions.getX(i);
    const ay = positions.getY(i);
    const az = positions.getZ(i);

    const bx = positions.getX(i + 1);
    const by = positions.getY(i + 1);
    const bz = positions.getZ(i + 1);

    const cx = positions.getX(i + 2);
    const cy = positions.getY(i + 2);
    const cz = positions.getZ(i + 2);

    const vA = new THREE.Vector3(ax, ay, az);
    const vB = new THREE.Vector3(bx, by, bz);
    const vC = new THREE.Vector3(cx, cy, cz);
    const normal = new THREE.Vector3().crossVectors(new THREE.Vector3().subVectors(vC, vB), new THREE.Vector3().subVectors(vA, vB)).normalize();

    stl += `  facet normal ${normal.x.toFixed(6)} ${normal.y.toFixed(6)} ${normal.z.toFixed(6)}\n`;
    stl += `    outer loop\n`;
    stl += `      vertex ${ax.toFixed(4)} ${ay.toFixed(4)} ${az.toFixed(4)}\n`;
    stl += `      vertex ${bx.toFixed(4)} ${by.toFixed(4)} ${bz.toFixed(4)}\n`;
    stl += `      vertex ${cx.toFixed(4)} ${cy.toFixed(4)} ${cz.toFixed(4)}\n`;
    stl += `    endloop\n`;
    stl += `  endfacet\n`;
  }

  stl += `endsolid ${modelName.replace(/\s+/g, '_')}\n`;
  return stl;
}

/**
 * Calculates bounding box dimensions
 */
export function getModelDimensions(geometry: THREE.BufferGeometry): { width: number; height: number; depth: number } {
  geometry.computeBoundingBox();
  if (!geometry.boundingBox) return { width: 10, height: 10, depth: 10 };
  const size = new THREE.Vector3();
  geometry.boundingBox.getSize(size);
  return {
    width: Math.round(size.x * 10) / 10 || 10,
    height: Math.round(size.y * 10) / 10 || 10,
    depth: Math.round(size.z * 10) / 10 || 10,
  };
}
