"""
Interactive function and helper functions used to trace apertures.
"""
import numpy as np
from astropy import table

from gempy.library import astromodels, astrotools, config, tracing

from .fit1d import Fit1DVisualizer
from .. import server

__all__ = ["interactive_trace_apertures", ]


class TraceAperturesVisualizer(Fit1DVisualizer):
    pass


def interactive_trace_apertures(ext, _config, _fit1d_params):
    """
    Run traceApertures() interactively.

    Parameters
    ----------
    ext : AstroData
        Single extension extracted from an AstroData object.
    _config : dict
        Dictionary containing the parameters from traceApertures().
    _fit1d_params : dict
        Dictionary containing initial parameters for fitting a model.

    Returns
    -------
    """
    ap_table = ext.APERTURE
    fit_par_list = [_fit1d_params] * len(ap_table)
    domain_list = [[ap['domain_start'], ap['domain_end']] for ap in ap_table]

    # Create parameters to add to the UI
    reinit_extras = {
        "max_missed": config.RangeField(
            "Max Missed", int, 5, min=0),
        "max_shift": config.RangeField(
            "Max Shifted", float, 0.05, min=0.001, max=0.1),
        "nsum": config.RangeField(
            "Number of lines to sum", int, 10, min=1),
        "step": config.RangeField(
            "Tracing step: ", int, 10, min=1),
    }

    def data_provider(conf, extra):
        return trace_apertures_data_provider(ext, conf, extra)

    visualizer = TraceAperturesVisualizer(
        data_provider,
        config=_config,
        fitting_parameters=fit_par_list,
        tab_name_fmt="Aperture {}",
        xlabel='x',
        ylabel='y',
        reinit_extras=reinit_extras,
        domains=domain_list,
        template="trace_apertures.html",
        title="Trace Apertures")

    server.interactive_fitter(visualizer)
    models = visualizer.results()

    all_aperture_tables = []
    dispaxis = 2 - ext.dispersion_axis()  # python sense

    for final_model, ap in zip(models, ap_table):
        location = ap['c0']
        this_aptable = astromodels.model_to_table(final_model.model)

        # Recalculate aperture limits after rectification
        apcoords = final_model.evaluate(np.arange(ext.shape[dispaxis]))

        this_aptable["aper_lower"] = (
                ap["aper_lower"] + (location - apcoords.min()))

        this_aptable["aper_upper"] = (
                ap["aper_upper"] - (apcoords.max() - location))

        all_aperture_tables.append(this_aptable)

    new_aptable = table.vstack(all_aperture_tables, metadata_conflicts="silent")
    return new_aptable


def trace_apertures_data_provider(ext, conf, extra):
    """
    Function used by the interactive fitter to generate the a list with
    pairs of [x, y] data containing the knots used for tracing.

    Parameters
    ----------
    ext : AstroData
        Single extension of data containing an .APERTURE table.
    conf : dict
        Dictionary containing default traceApertures() parameters.
    extra : dict
        Dictionary containing extra parameters used to re-create the input data
        for fitting interactively.

    Returns
    -------
    list : pairs of (x, y) for each aperture center, where x is the
    spectral position of the knots, and y is the spacial position of the
    knots.
    """
    all_tracing_knots = []
    dispaxis = 2 - ext.dispersion_axis()  # python sense

    for _i, _loc in enumerate(ext.APERTURE['c0'].data):
        _c0 = int(_loc + 0.5)

        _spectrum = (ext.data[_c0] if dispaxis == 1
                     else ext.data[:, _c0])

        _start = np.argmax(astrotools.boxcar(_spectrum, size=3))

        _, _in_coords = tracing.trace_lines(
            ext, axis=dispaxis, cwidth=5,
            initial=[_loc], initial_tolerance=None,
            max_missed=extra['max_missed'], max_shift=extra['max_shift'],
            nsum=extra['nsum'], rwidth=None, start=_start,
            step=extra['step'])

        _in_coords = np.ma.masked_array(_in_coords)

        # ToDo: This should not be required
        _in_coords.mask = np.zeros_like(_in_coords)

        spectral_tracing_knots = _in_coords[1 - dispaxis]
        spatial_tracing_knots = _in_coords[dispaxis]

        all_tracing_knots.append(
            [spectral_tracing_knots, spatial_tracing_knots])

    return all_tracing_knots
