"""Conservative distance measurements at declared surface samples.

Each sample is tested against actual target triangles, not target vertices.
Searching a subset can overestimate the nearest-surface distance, never
underestimate it. This is not a full-surface Hausdorff certificate.
"""
import numpy as np
from scipy.spatial import cKDTree

SURFACE_RELATIVE_LIMIT = 1e-4
VOLUME_RELATIVE_LIMIT = .01


def _distance_squared(points, triangles):
    """Distance from each point to each supplied triangle, including its edges."""
    p = points[:, None, :]
    a, b, c = triangles[:, :, 0], triangles[:, :, 1], triangles[:, :, 2]
    ab, ac, ap = b-a, c-a, p-a
    normal = np.cross(ab, ac)
    n2 = np.einsum('...i,...i->...', normal, normal)
    dot = lambda x, y: np.einsum('...i,...i->...', x, y)
    # Oriented edge half-planes avoid a subtractive Gram determinant on thin
    # triangles. The normal component of the point drops out of these signs.
    inside = ((dot(np.cross(ab, ap), normal) >= 0) &
              (dot(np.cross(c-b, p-b), normal) >= 0) &
              (dot(np.cross(a-c, p-c), normal) >= 0) & (n2 > 0))
    plane = np.divide(dot(ap, normal)**2, n2, out=np.full_like(n2, np.inf), where=n2>0)
    best = np.where(inside, plane, np.inf)
    for x, y in ((a, b), (b, c), (c, a)):
        edge = y-x
        length2 = dot(edge, edge)
        t = np.divide(dot(p-x, edge), length2, out=np.zeros_like(length2), where=length2>0)
        delta = p - (x + np.clip(t, 0, 1)[..., None]*edge)
        best = np.minimum(best, dot(delta, delta))
    return np.maximum(best, 0)


def _sample_bound(source, target, limit):
    # Separate triangle sizes so many small nearby centers cannot obscure a
    # large face containing the point. Only unresolved samples need expansion.
    centers = target.mean(axis=1)
    radii = np.linalg.norm(target-centers[:, None, :], axis=2).max(axis=1)
    sizes = np.floor(np.log2(np.maximum(radii, 1e-18))).astype(int)
    groups = []
    for size in np.unique(sizes)[::-1]:
        ids = np.flatnonzero(sizes == size)
        groups.append((ids, cKDTree(centers[ids]), float(radii[ids].max())))
    maximum, count = 0., 0
    for start in range(0, len(source), 1024):
        t = source[start:start+1024]
        samples = np.concatenate([t.reshape(-1, 3), ((t+np.roll(t, -1, axis=1))/2).reshape(-1, 3),
                                  t.mean(axis=1)])
        distances2 = np.full(len(samples), np.inf)
        for target_ids, tree, radius in groups:
            unresolved = np.flatnonzero(distances2 > limit**2)
            if not len(unresolved):
                break
            k = min(16, len(target_ids))
            near = tree.query(samples[unresolved], k=k)[1].reshape(len(unresolved), k)
            distances2[unresolved] = np.minimum(distances2[unresolved],
                _distance_squared(samples[unresolved], target[target_ids[near]]).min(axis=1))
        # If a triangle is within limit of p, its center is within radius+limit
        # of p. These ball queries cover every possible passing triangle; they
        # avoid sorting or allocating all triangles for each unresolved sample.
        for index in np.flatnonzero(distances2 > limit**2):
            point = samples[index:index+1]
            for target_ids, tree, radius in groups:
                near = tree.query_ball_point(point[0], radius+limit)
                for offset in range(0, len(near), 8192):
                    triangles = target[target_ids[np.asarray(near[offset:offset+8192], dtype=int)]]
                    d2 = float(_distance_squared(point, triangles[None]).min())
                    distances2[index] = min(distances2[index], d2)
                    if distances2[index] <= limit**2:
                        break
                if distances2[index] <= limit**2:
                    break
            if distances2[index] > limit**2:
                # A failing sample is enough to reject; no coverage claim for
                # the remaining samples is made for a rejected candidate.
                return float(np.sqrt(distances2[index])), count+index+1
        maximum = max(maximum, float(np.sqrt(distances2.max())))
        count += len(samples)
    return maximum, count


def measure_surface(source, working):
    extent = float(np.ptp(source.reshape(-1, 3), axis=0).max())
    limit = extent * SURFACE_RELATIVE_LIMIT
    forward, source_samples = _sample_bound(source, working, limit)
    reverse, working_samples = _sample_bound(working, source, limit)
    bound = max(forward, reverse)
    return {
        'max_sample_distance_source_units': bound,
        'max_sample_distance_mm': bound,
        'limit_source_units': extent * SURFACE_RELATIVE_LIMIT,
        'limit_mm': extent * SURFACE_RELATIVE_LIMIT,
        'source_to_working_source_units': forward,
        'working_to_source_source_units': reverse,
        'source_samples': source_samples,
        'working_samples': working_samples,
        'relative_to_longest_extent': bound / max(extent, 1e-18),
        'relative_limit': SURFACE_RELATIVE_LIMIT,
        'scope': 'Upper bound on nearest-triangle distance at vertices, edge midpoints and face centroids in both directions; accepted reductions sample every face. Triangle-size groups and enclosing-radius queries bound the candidate search. Unsampled surface regions and small-feature preservation are not certified.',
    }
