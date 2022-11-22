#!/usr/bin/env python3
import numpy as np


def ptRTD_temperature(r_x, r_0=1000.0):
    """Quadratic equation for the temperature of platinum RTDs.
    This is the inversion of the H.L.Callendar polynomial for positive
    temperatures.
    
    Result is temperature in °C according to the ITS-90 scale.

    For negative temperatures, we are adding a correction term. This is
    a fifth-order polynomial fit of the deviation of the numerically
    inverted ITS-90 standard Callendar-Van Dusen equation, using coef-
    ficient "C" for T < 0, from the second-order equation without
    coefficient "C". Source for the ITS-90 standard polynomial:
    
    http://de-de.wika.de/upload/DS_IN0029_en_co_59667.pdf
    (Verified with DIN EN 60751:2009, 2017-02-21)

    Source for the correction term:
    https://github.com/ulikoehler/UliEngineering
    """
    PT_A =  3.9083E-3
    PT_B = -5.775E-7
    # Uncorrected solution which is exact for positive temperatures
    r_norm = r_x / r_0
    theta = (- PT_A + np.sqrt(PT_A**2 - 4*PT_B*(1 - r_norm))
            ) / (2*PT_B)
    if r_norm < 1.0:
        # Polynomial correction only for negative temperatures
        correction = np.poly1d(
            [1.51892983e+00, -2.85842067e+00, -5.34227299e+00,
             1.80282972e+01, -1.61875985e+01,  4.84112370e+00]
        )
        return theta + correction(r_norm)
    else:
        return theta


def wheatstone(ud, u0, nref, rs1):
    """ Return wheatstone bridge unknown resistance "r1".
    Arguments:
        ud:   Bridge voltage differential
        u0:   Reference bridge leg absolute voltage
        nref: Reference bridge leg resistance ratio
        rs1:  Measurement bridge leg series resistor
             _______
             |      |
            rs0    rs1       nref=rs0/r0
         u0..|<-ud--|
            r0     r1
             |      |
             _______ ..0V
    """
    return rs1 * (u0 + ud) / (u0*nref - ud)


def wheatstone_factor(ud, u0, nref):
    """ Return factor by which to scale known resistance "rs1"
    in order to get unknown resistance "r1".

    Arguments:
        ud:   Bridge voltage differential
        u0:   Reference bridge leg absolute voltage
        nref: Reference bridge leg resistance ratio
             _______
             |      |
            rs0    rs1       nref=rs0/r0
         u0..|<-ud--|
            r0     r1
             |      |
             _______ ..0V
    """
    return (u0 + ud) / (u0*nref - ud)
