from typing import Dict, Callable

import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from constants import CALIBRATION_DATASET, CALIBRATION_GRAPH


def calculate_parameters():
    """
    Calculate the A and B parameters of the hyperbole that fits the low-light
    data points given in the calibration dataset.
    """
    # Load the dataset
    df = pd.read_csv(CALIBRATION_DATASET, header=None)
    df.columns=['in_lum','fin_lum', 'speed']
    df = df.sort_values(by='in_lum')

    # Solve system with two points five times and average the results
    a_value = 0
    b_value = 0
    for i in range(5):
        x1 = df.iat[i, 0]
        y1 = df.iat[i, 2]
        x2 = df.iat[df.shape[0]-i-1, 0]
        y2 = df.iat[df.shape[0]-i-1, 2]

        # Closed form solution of a hyperbole
        b = -(x1*y1 - x2*y2)/(x1+x2)
        a = x1 * (y1 - b)

        a_value += a
        b_value += b

    a_value = int(a_value / 5)
    b_value = int(b_value / 5)

    return a_value, b_value


def plot_curve_fit(a_value: int, b_value: int, old_a_value: int = None, old_b_value: int = None):
    """
    Plots the hyperbole that fits the low-light
    data points given in the calibration dataset along
    with the data points themselves.
    """
    # Load the dataset
    df = pd.read_csv(CALIBRATION_DATASET, header=None)
    df.columns=['in_lum','fin_lum', 'speed']
    df = df.sort_values(by='in_lum')

    # Plot source values
    df.plot.scatter(
        x='in_lum',
        y='speed',
        label="Valori reali",
        xlabel="Luminosita' iniziale",
        ylabel="Shutter speed",
    )

    # Plot new fitting curve
    x = np.array(df[['in_lum']])
    y = ((a_value/x) + b_value) 
    plt.plot(x,y,label="Nuova stima")

    # Plot old fitting curve
    if old_a_value and old_b_value:
        x = np.array(df[['in_lum']])
        y = ((old_a_value/x) + old_b_value) 
        plt.plot(x,y,label="Stima attuale")

    plt.legend(loc="upper right")

    plt.savefig(CALIBRATION_GRAPH)
