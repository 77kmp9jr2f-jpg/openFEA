"""Layer-contour perimeter/skin volumes; geometric envelopes, not toolpaths.

Internal holes and local top/bottom surfaces participate. The resulting global
fractions still feed a homogeneous equivalent material, not a spatial shell FE
model. Coordinates and areas are in mm and mm².
"""
from functools import lru_cache
import math
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize_full, unary_union

from .schemas import PrintSettings
from .storage import resource, read_json

METHOD = 'layer-contours-v1'
PRECISION_MM = 1e-6


def section(triangles, height):
    a, b = triangles, np.roll(triangles, -1, axis=1)
    crosses = (a[:, :, 2] < height) != (b[:, :, 2] < height)
    starts, ends = a[crosses], b[crosses]
    if not len(starts):
        return Polygon()
    points = starts + (ends-starts)*((height-starts[:, 2])/(ends[:, 2]-starts[:, 2]))[:, None]
    segments = np.round(points[:, :2].reshape(-1, 2, 2)/PRECISION_MM)*PRECISION_MM
    segments = segments[np.linalg.norm(segments[:, 1]-segments[:, 0], axis=1) > PRECISION_MM/2]
    polygons, cuts, dangles, invalid = polygonize_full(unary_union([LineString(s) for s in segments]))
    if cuts.length+dangles.length+invalid.length > 10*PRECISION_MM:
        raise ValueError('Print-layer contours are not closed. Repair the surface mesh before estimating print usage.')
    cells = list(polygons.geoms)
    # polygonize yields both the annular cell and its hole. Keep odd nesting
    # depth, including disconnected islands; never fill an internal cavity.
    envelopes = [Polygon(p.exterior) for p in cells]
    filled = [p for p in cells if sum(e.covers(p.representative_point()) for e in envelopes) % 2]
    return unary_union(filled) if filled else Polygon()


def measure_regions(triangles, settings: PrintSettings) -> dict:
    triangles = np.asarray(triangles, dtype=float)
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or not np.isfinite(triangles).all():
        raise ValueError('Print geometry needs finite surface triangles.')
    rotation = Rotation.from_euler('xyz', settings.rotation_deg, degrees=True).as_matrix()
    local = triangles @ rotation
    lo = local.min(axis=(0, 1))
    local = local-lo
    extent = local.max(axis=(0, 1))
    step = settings.layer_height_mm
    count = max(1, math.ceil((extent[2]-1e-9)/step))
    if count > 10000 or count*len(local) > 200_000_000:
        raise ValueError('Print contour calculation is too large for the local workspace. Increase layer height or use a coarser surface mesh.')
    zlo, zhi = local[:, :, 2].min(axis=1), local[:, :, 2].max(axis=1)
    layers, thicknesses = [], []
    for i in range(count):
        thickness = min(step, extent[2]-i*step)
        z = i*step+thickness/2
        layers.append(section(local[(zlo < z) & (zhi >= z)], z))
        thicknesses.append(thickness)
    wall = settings.wall_count*settings.line_width_mm
    total = perimeter = skins = core_volume = 0.0
    for i, (polygon, thickness) in enumerate(zip(layers, thicknesses)):
        inner = polygon.buffer(-wall, join_style=2)
        core = inner
        # A core column needs material through the requested top/bottom skin
        # depth. This handles local ledges and cavities, not only global ends.
        if i < settings.bottom_layers or i+settings.top_layers >= count:
            core = Polygon()
        else:
            for j in range(i-settings.bottom_layers, i+settings.top_layers+1):
                if core.is_empty:
                    break
                if j != i:
                    core = core.intersection(layers[j])
        total += polygon.area*thickness
        perimeter += max(0, polygon.area-inner.area)*thickness
        skins += max(0, inner.area-core.area)*thickness
        core_volume += core.area*thickness
    if total <= 0:
        raise ValueError('No closed material contours were found for the print geometry.')
    return {'geometry_method': METHOD, 'layer_count': count,
            'section_precision_mm': PRECISION_MM, 'print_extents_mm': extent.tolist(),
            'sampled_solid_volume_mm3': total, 'perimeter_volume_mm3': perimeter,
            'skin_volume_mm3': skins, 'core_volume_mm3': core_volume,
            'shell_volume_fraction': min(1.0, max(0.0, 1-core_volume/total))}


@lru_cache(maxsize=32)
def _model_regions(model_path, mesh_hash, geometry_settings):
    model = read_json(Path(model_path))
    settings = PrintSettings.model_validate_json(geometry_settings)
    points = np.asarray(model['nodes'])
    faces = np.asarray([t for f in model['faces'] for t in f['triangles']])
    regions = measure_regions(points[faces], settings)
    regions['volume_discretization_relative_error'] = abs(regions['sampled_solid_volume_mm3']/model['volume_mm3']-1)
    return regions


def model_regions(model: dict, settings: PrintSettings) -> dict:
    # Infill/material changes do not change geometry. Cache small scalar
    # summaries only, keyed to the immutable mesh and perimeter/skin settings.
    geometry_settings = settings.model_copy(update={'infill_density': .2, 'infill_pattern': 'gyroid'})
    return dict(_model_regions(str(resource('models', model['id'])/'model.json'),
                               model['mesh_sha256'], geometry_settings.model_dump_json()))
