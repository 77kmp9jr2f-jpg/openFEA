"""Plain-language result guidance for a first analysis.

These sentences are stored on the result so the workspace and reports say the
same thing. They interpret software evidence, not printed-part strength.
"""


def result_guidance(result: dict) -> dict:
    residual = result['relative_residual']
    print_info = result.get('print') or {}
    print_on = bool(print_info.get('enabled'))
    trust = [
        (
            f"Maximum displacement {result['max_displacement_mm']:.4g} mm is the "
            "number to compare when you change print settings or loads."
        ),
        (
            f"The solve residual is {residual:.2e}. Below 1e-7 means the algebra "
            "finished; it does not mean the mesh or material is right."
        ),
    ]
    if print_on:
        mass = print_info.get('filament_mass_g', result['mass_g'])
        fraction = print_info.get('volume_fraction')
        extra = (
            f" ({100 * fraction:.3g}% solid equivalent)" if fraction is not None else ''
        )
        trust.append(
            f"Estimated filament mass {mass:.4g} g{extra} tracks walls, skins and "
            "infill. It is not a weighed print."
        )
    else:
        trust.append(
            f"Solid mass {result['mass_g']:.4g} g uses the supplied density and the "
            "meshed volume."
        )
    caution = [
        (
            "Peak von Mises is the highest unaveraged integration-point stress. "
            "Fixture edges and sharp corners are often singular — that peak will "
            "not settle with a finer mesh."
        ),
        (
            "Yield ratio uses that peak and the supplied yield. It is not a safety "
            "factor and not printed-part strength."
        ),
    ]
    if print_on:
        caution.append(
            "The print model is a homogenized equivalent solid, not a sliced "
            "toolpath and not a calibration against printed coupons."
        )
    nxt = (
        "Pin this run, change infill, walls or orientation, and solve again. "
        "Trust the displacement and mass trend, not the peak stress."
        if print_on
        else "If you change geometry or material, rebuild, confirm, and compare a second run."
    )
    return {'trust': trust, 'caution': caution, 'next': nxt}
