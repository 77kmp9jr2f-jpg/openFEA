"""Homogenized FDM stiffness and material usage from print settings.

This is a documented equivalent-solid model, not a sliced toolpath and not a
calibration against printed coupons. Shells and skins are treated as solid
filament; the core uses pattern factors. Layering is transversely isotropic
about the print Z axis after the user rotation.
"""
from __future__ import annotations
import math
import numpy as np
from scipy.spatial.transform import Rotation
from .schemas import Material, PrintSettings

PATTERN = {
    'rectilinear': {'xy': 0.95, 'z': 0.32},
    'grid': {'xy': 1.00, 'z': 0.40},
    'triangles': {'xy': 1.05, 'z': 0.45},
    'gyroid': {'xy': 0.82, 'z': 0.72},
}


def rotation_matrix(rotation_deg) -> np.ndarray:
    return Rotation.from_euler('xyz', rotation_deg, degrees=True).as_matrix()


def homogenize(bounds, material: Material, settings: PrintSettings, *, regions=None) -> dict:
    lo, hi = np.asarray(bounds[0], float), np.asarray(bounds[1], float)
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    local = corners @ rotation_matrix(settings.rotation_deg)
    extent = local.max(axis=0) - local.min(axis=0)
    lx, ly, lz = (float(max(v, 1e-9)) for v in extent)
    wall = settings.wall_count * settings.line_width_mm
    skin = (settings.top_layers + settings.bottom_layers) * settings.layer_height_mm
    inner_x = max(lx - 2 * wall, 0.0)
    inner_y = max(ly - 2 * wall, 0.0)
    box = lx * ly * lz
    walls = box - inner_x * inner_y * lz
    skins = inner_x * inner_y * min(skin, lz)
    core = max(box - walls - skins, 0.0)
    solid_shell = walls + skins
    if regions is not None:
        lx, ly, lz = regions['print_extents_mm']
        box = regions['sampled_solid_volume_mm3']
        core = regions['core_volume_mm3']
        solid_shell = box-core
    if settings.infill_density >= 1 - 1e-12:
        filament = box
        eta_xy = eta_z = 1.0
        pattern_note = '100% infill is treated as a solid isotropic equivalent of the filament.'
    else:
        filament = solid_shell + settings.infill_density * core
        vf_shell = solid_shell / box
        vf_core = (settings.infill_density * core) / box
        coeff = PATTERN[settings.infill_pattern]
        eta_xy = min(1.0, vf_shell + vf_core * coeff['xy'])
        eta_z = min(1.0, vf_shell + vf_core * coeff['z'])
        pattern_note = (
            f"{settings.infill_pattern} core factors are illustrative "
            f"(in-plane {coeff['xy']}, layer {coeff['z']}), not coupon-calibrated."
        )
    vf = filament / box
    young_xy = material.young_mpa * eta_xy
    young_z = material.young_mpa * eta_z
    poisson = material.poisson
    shear_xy = young_xy / (2 * (1 + poisson))
    shear_z = math.sqrt(max(young_xy * young_z, 1e-12)) / (2 * (1 + poisson))
    assumptions = [
        'Print stiffness is a homogenized equivalent solid, not an explicit infill mesh or sliced toolpath.',
        ('Perimeter and skin volumes use actual layer contours, including internal holes and local top/bottom surfaces.'
         if regions is not None else
         'Walls and top/bottom skins are estimated from the axis-aligned box of the oriented part.'),
        'Shell and core fractions are homogenized throughout the body; the spatial stiffness of individual walls and infill is not resolved.',
        'Layering is transversely isotropic: print Z is the weak/layer direction after the supplied rotation.',
        pattern_note,
        'Filament modulus, strength and density remain user inputs. No printed-specimen calibration is claimed.',
        'Additional raster-scale anisotropy, local voids, bonding defects and moisture are not modelled.',
        'Estimated filament covers the part only; supports, adhesion and purge are excluded. Check usage and orientation trends in your slicer.',
        'Print orientation defines the material frame; it does not check bed contact, overhangs or whether the part can be printed in that orientation.',
    ]
    if regions is not None:
        assumptions.append('Layer contours use nominal line width and layer height; bead overlap, variable extrusion widths, gap fill and toolpaths are not modeled.')
        first_layer = regions.get('first_layer_nominal_footprint', {})
        if first_layer.get('has_centerline_area') is False:
            assumptions.append('No interior margin for a nominal-width line was found in the first model layer at this orientation. Check first-layer extrusion, bed contact and supports in your slicer; exact-width and variable-width paths may behave differently.')
        error = regions.get('volume_discretization_relative_error', 0)
        if error > .01:
            assumptions.append(f'Layer-sampled volume differs from the input solid by {100*error:.3g}%; refine the surface mesh or reduce layer height before interpreting material usage.')
    return {
        **(regions or {'geometry_method': 'bounding-box-v1'}),
        'enabled': True,
        'settings': settings.model_dump(mode='json'),
        'print_extents_mm': [lx, ly, lz],
        'volume_fraction': vf,
        'shell_volume_fraction': solid_shell / box,
        'filament_volume_ratio': vf,
        'young_xy_mpa': young_xy,
        'young_z_mpa': young_z,
        'shear_xy_mpa': shear_xy,
        'shear_z_mpa': shear_z,
        'poisson': poisson,
        'eta_xy': eta_xy,
        'eta_z': eta_z,
        'assumptions': assumptions,
    }


def stiffness(material: Material, settings: PrintSettings, bounds, *, regions=None) -> tuple[np.ndarray, dict]:
    if not settings.enabled:
        return _isotropic(material.young_mpa, material.poisson), {'enabled': False}
    model = homogenize(bounds, material, settings, regions=regions)
    C_print = _transverse(model['young_xy_mpa'], model['young_z_mpa'], model['poisson'],
                          model['shear_xy_mpa'], model['shear_z_mpa'])
    C = _rotate_voigt(C_print, rotation_matrix(settings.rotation_deg))
    return C, model


def apply_usage(homogenized: dict, solid_volume_mm3: float, density_kg_m3: float) -> dict:
    if not homogenized.get('enabled'):
        mass = solid_volume_mm3 * density_kg_m3 * 1e-6
        return {'filament_volume_mm3': solid_volume_mm3, 'filament_mass_g': mass, 'mass_g': mass}
    vf = homogenized['volume_fraction']
    # Use the measured section volume for new contour models, and preserve the
    # historical box-fraction calculation for archived runs.
    volume = homogenized.get('sampled_solid_volume_mm3', solid_volume_mm3) * vf
    mass = volume * density_kg_m3 * 1e-6
    return {'filament_volume_mm3': volume, 'filament_mass_g': mass, 'mass_g': mass}


def _isotropic(young, poisson) -> np.ndarray:
    lam = young * poisson / ((1 + poisson) * (1 - 2 * poisson))
    mu = young / (2 * (1 + poisson))
    c11 = lam + 2 * mu
    C = np.zeros((6, 6))
    C[0, 0] = C[1, 1] = C[2, 2] = c11
    C[0, 1] = C[1, 0] = C[0, 2] = C[2, 0] = C[1, 2] = C[2, 1] = lam
    C[3, 3] = C[4, 4] = C[5, 5] = mu
    return C


def _transverse(ep, et, nu, gp, gt) -> np.ndarray:
    # Compliance in print axes: 1-2 in-plane, 3 layer normal. Engineering Voigt.
    nup = nu
    nupt = nu * math.sqrt(et / ep) if ep > 0 else nu
    nutp = nupt * et / ep if ep > 0 else nu
    S = np.zeros((6, 6))
    S[0, 0] = S[1, 1] = 1 / ep
    S[2, 2] = 1 / et
    S[0, 1] = S[1, 0] = -nup / ep
    S[0, 2] = S[2, 0] = -nutp / et
    S[1, 2] = S[2, 1] = -nutp / et
    S[3, 3] = 1 / gt
    S[4, 4] = 1 / gt
    S[5, 5] = 1 / gp
    try:
        C = np.linalg.inv(S)
    except np.linalg.LinAlgError as exc:
        raise ValueError('Print stiffness is not positive definite. Reduce Poisson ratio or raise infill.') from exc
    if np.min(np.linalg.eigvalsh((C + C.T) / 2)) <= 0:
        raise ValueError('Print stiffness is not positive definite. Reduce Poisson ratio or raise infill.')
    return C


def _rotate_voigt(C, R) -> np.ndarray:
    """R maps print-frame vectors to global: v_g = R @ v_p."""
    q = R
    t = np.zeros((6, 6))
    for a, (i, j) in enumerate(((0, 0), (1, 1), (2, 2), (1, 2), (0, 2), (0, 1))):
        for b, (k, l) in enumerate(((0, 0), (1, 1), (2, 2), (1, 2), (0, 2), (0, 1))):
            if a < 3 and b < 3:
                t[a, b] = q[i, k] * q[j, l]
            elif a < 3 <= b:
                t[a, b] = q[i, k] * q[j, l] + q[i, l] * q[j, k]
            elif a >= 3 > b:
                t[a, b] = q[i, k] * q[j, l]
            else:
                t[a, b] = q[i, k] * q[j, l] + q[i, l] * q[j, k]
    return t @ C @ t.T


def compare_results(a: dict, b: dict) -> dict:
    keys = ('max_displacement_mm', 'peak_von_mises_mpa', 'mass_g', 'filament_mass_g',
            'relative_residual', 'force_balance_error_n')
    def pack(result):
        print_info = result.get('print') or {}
        return {
            'id': result['id'],
            'model_id': result['model_id'],
            'max_displacement_mm': result['max_displacement_mm'],
            'peak_von_mises_mpa': result['peak_von_mises_mpa'],
            'mass_g': result['mass_g'],
            'filament_mass_g': print_info.get('filament_mass_g', result['mass_g']),
            'volume_fraction': print_info.get('volume_fraction'),
            'young_xy_mpa': print_info.get('young_xy_mpa'),
            'young_z_mpa': print_info.get('young_z_mpa'),
            'geometry_method': print_info.get('geometry_method', 'bounding-box-v1') if print_info.get('enabled') else None,
            'print': print_info.get('settings'),
            'relative_residual': result['relative_residual'],
            'force_balance_error_n': result['force_balance_error_n'],
            'setup': result.get('setup'),
        }
    left, right = pack(a), pack(b)
    delta = {k: right[k] - left[k] for k in keys if left.get(k) is not None and right.get(k) is not None}
    differences = []
    if left['geometry_method'] and right['geometry_method'] and left['geometry_method'] != right['geometry_method']:
        differences.append('print_geometry_method')
    for key in ('model_id', 'mesh_sha256', 'element_order'):
        if a.get(key) != b.get(key):
            differences.append(key)
    for key in ('material', 'fixed_faces', 'loads'):
        av, bv = (r.get('setup', {}).get(key) for r in (a, b))
        if av is None or bv is None or av != bv:
            differences.append(key)
    return {'same_model': a['model_id'] == b['model_id'],
            'same_analysis_context': not differences, 'context_differences': differences,
            'a': left, 'b': right, 'delta': delta}
