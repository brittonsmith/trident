"""
Absorption line generating functions.



"""

#-----------------------------------------------------------------------------
# Copyright (c) 2013-2017, yt Development Team.
# Copyright (c) 2017, Trident Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
#-----------------------------------------------------------------------------

import numpy as np
from yt.utilities.physical_constants import \
    charge_proton_cgs, \
    mass_electron_cgs, \
    speed_of_light_cgs
from yt.utilities.on_demand_imports import _scipy, NotAModule

special = _scipy.special
tau_factor = None
_cs = None


def voigt(a, u):
    """
    Calculate the numerical Voigt line profile for absorption features.

    This code uses a SciPy routine to numerically calculate the Voigt Profile
    for deposition as absorption features into spectra.

    This method employs the real part of the Fadeeva function, w(z),
    shown here as special.wofz.  It operates on a and u, unitless variables
    representing the frequency/wavelength range and the damping parameter for
    the line.

    Included are notes from a previous implementation:
    a = Voigt "A" parameter.
    u = Frequency in units of the Doppler frequency.

    The line profile "Phi(v)", the doppler width
    "Delv", the voigt parameter "a", and the frequency "u"
    are given by:

    Phi(v) =  Voigt(a,u)/[ Delv * sqrt(pi) ]
    Delv   =  Vo/c * sqrt[ 2kT/m ]
    u      =  V - Vo / Delv
    a      =  GAMMA / [ Delv * 4pi ]
    Gamma  =  Gu + Gl + 2*Vcol
    "Gu" and "Gl" are the widths of the upper and lower states
    "Vcol" is the collisions per unit time
    "Vo" is the line center frequency

    **Parameters**

    :a: float

        Damping parameter or Voigt "A" parameter describing the width of the
        profile. This is the gamma value divided by the b parameter (thermal
        broadening) in the unitless frame of the u array.

    :u: array

        The region over which the voigt profile will be calculated. This too
        is unitless and represents the normalized frequency space over which
        to calculate the Voigt profile.

    """
    x = np.asarray(u).astype(np.float64)
    y = np.asarray(a).astype(np.float64)
    return special.wofz(x + 1j * y).real

def tau_profile(lambda_0, f_value, gamma, v_doppler, column_density,
                delta_v=None, delta_lambda=None,
                lambda_bins=None, n_lambda=12000, dlambda=0.01):
    r"""
    Create an optical depth vs. wavelength profile for an
    absorption line using a voigt profile.

    Parameters
    ----------

    lambda_0 : float in angstroms
       central wavelength.
    f_value : float
       absorption line f-value.
    gamma : float
       absorption line gamma value.
    v_doppler : float in cm/s
       doppler b-parameter.
    column_density : float in cm^-2
       column density.
    delta_v : float in cm/s
       velocity offset from lambda_0.
       Default: None (no shift).
    delta_lambda : float in angstroms
        wavelength offset.
        Default: None (no shift).
    lambda_bins : array in angstroms
        wavelength array for line deposition.  If None, one will be
        created using n_lambda and dlambda.
        Default: None.
    n_lambda : int
        size of lambda bins to create if lambda_bins is None.
        Default: 12000.
    dlambda : float in angstroms
        lambda bin width in angstroms if lambda_bins is None.
        Default: 0.01.

    """
    global tau_factor
    if tau_factor is None:
        tau_factor = (
            np.sqrt(np.pi) * charge_proton_cgs ** 2 /
            (mass_electron_cgs * speed_of_light_cgs)
        ).in_cgs().d

    global _cs
    if _cs is None:
        _cs = speed_of_light_cgs.d[()]

    # shift lambda_0 by delta_v
    if delta_v is not None:
        lam1 = lambda_0 * (1 + delta_v / _cs)
    elif delta_lambda is not None:
        lam1 = lambda_0 + delta_lambda
    else:
        lam1 = lambda_0

    # conversions
    nudop = 1e8 * v_doppler / lam1   # doppler width in Hz

    # create wavelength
    if lambda_bins is None:
        lambda_bins = lam1 + \
            np.arange(n_lambda, dtype=np.float) * dlambda - \
            n_lambda * dlambda / 2  # wavelength vector (angstroms)

    # tau_0
    tau_X = tau_factor * column_density * f_value / v_doppler
    tau0 = tau_X * lambda_0 * 1e-8

    # dimensionless frequency offset in units of doppler freq
    u = _cs / v_doppler * (lam1 / lambda_bins - 1.0)
    a = gamma / (4.0 * np.pi * nudop)               # damping parameter
    phi = voigt(a, u)                               # line profile
    tauphi = tau0 * phi              # profile scaled with tau0

    return (lambda_bins, tauphi)
