from __future__ import annotations

import csv
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

import utils


@dataclass
class CystometryData:
    time: NDArray[float]
    values: NDArray[float]
    derivative2: NDArray[float]
    moving_avg_vals: NDArray[float]
    peaks: NDArray[int]
    baselines: NDArray[int]
    pressure_threshold_idx: NDArray[int]
    volume_empty_idx: NDArray[int]
    volume: NDArray[float]
    baseline_bounds: NDArray[slice]
    slope_thresholds: NDArray[float]

    def _export_from_indexes(self, path: str, indexes: NDArray[int]) -> None:
        """Exports a csv with the columns "time" and "bladder_p" with the values specified by indexes.

        Args:
            path (str): The file path the csv will be written.
            indexes (np.ndarray[int]): An array of the indexes corresponding to the values to be saved.
        """
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=',')
            rows = [('time', 'bladder_p')]

            rows.extend((t, p) for t, p in zip(self.time[indexes], self.values[indexes]))

            writer.writerows(rows)

    def export(self, dir_path: str, prefix: str = '') -> CystometryData:
        """
        Exports the data the specified directory/folder in the form of three files:

        baselines.csv
        threshold_pressures.csv
        peaks.csv
        volume.csv

        Each file stores 2 columns: time and some pressure value depending on the kind of data being exported.
        `peaks.csv` also stores the inter-contractile interval (ici) and contractile duration (cd) alongside peak
        pressure values. Intervals are stored as the time between the previous peak and current peak (thus, the first
        ici value is None).

        volume.csv will have time and volume values rather than time and pressure.

        Args:
            dir_path: A path to a directory for data to be saved to.
            prefix: An optional string prefix to be prepended to each exported file name.

        Returns:
            self, to allow for method chaining
        """

        if dir_path[-1] not in {'/', '\\'}:
            # make sure the directory path ends with a slash
            dir_path += '/'

        def make_path(filename: str):
            return f"{dir_path}{prefix}{filename}"

        self._export_from_indexes(make_path('baselines.csv'), self.baselines)
        self._export_from_indexes(make_path('threshold_pressures.csv'), self.pressure_threshold_idx)

        # can't use self._export_from_indexes here as volume is saved in a different way
        # newline='' is something required on Windows machines because of how Windows interprets newlines
        with open(make_path("volume.csv"), 'w', newline='') as f:
            cw = csv.writer(f, delimiter=',')

            rows = [('time', 'volume')]

            rows.extend((t, v) for t, v in zip(self.time, self.volume))

            cw.writerows(rows)

        # also can't use self._export_from_indexes here as peaks are saved in a different way
        with open(make_path("peaks.csv"), 'w', newline='') as f:
            intervals = np.diff(self.time[self.peaks])
            valleys, pthresh_indexes = utils.normalize_len(self.baselines, self.pressure_threshold_idx)

            contractile_durations = self.time[valleys] - self.time[pthresh_indexes]
            cw = csv.writer(f, delimiter=',')
            rows = [('time', 'bladder_p', 'ici', 'cd')]

            rows.extend((t, p, i, cd) for t, p, i, cd in
                        zip(self.time[self.peaks], self.values[self.peaks],
                            [None, *intervals], contractile_durations))

            cw.writerows(rows)

        return self

    def visualize(self, show_labels: bool = True, show_markers: bool = True,
                  show_legend: bool = True) -> CystometryData:
        """
        Creates a basic visualization of the data, including bladder pressure and estimated bladder volume.

        Args:
            show_labels: If True, then axis labels and titles will be drawn
            show_markers: If True, then markers for peaks, baselines, pressure thresholds, and volume empty points will
                be drawn
            show_legend: If True, a legend will be drawn for the bladder pressure figure. This is only really necessary
                when show_markers is True

        Returns:
            self, to allow for method chaining
        """

        bp_fig, bp_ax = plt.subplots()
        bp_fig.canvas.manager.set_window_title('Bladder Pressure')

        bp_ax.plot(self.time, self.moving_avg_vals, color='C0', label='Bladder P')

        if show_markers:
            bp_ax.scatter(self.time[self.peaks], self.moving_avg_vals[self.peaks], color="C1", marker="x",
                          label="Peaks")
            bp_ax.scatter(self.time[self.baselines], self.moving_avg_vals[self.baselines], color="C2", marker="x",
                          label="Baselines")
            bp_ax.scatter(self.time[self.pressure_threshold_idx], self.moving_avg_vals[self.pressure_threshold_idx],
                          color="C3", marker="x", label="P Thresholds")
            bp_ax.scatter(self.time[self.volume_empty_idx], self.moving_avg_vals[self.volume_empty_idx], marker='x',
                          color='magenta', label="Volume Empty")

        if show_legend:
            bp_ax.legend()

        vol_fig, vol_ax = plt.subplots()
        vol_fig.canvas.manager.set_window_title('Volume')

        vol_ax.plot(self.time, self.volume)

        if show_labels:
            bp_ax.set_title("Bladder Pressure vs. Time")
            bp_ax.set_ylabel("Bladder P")
            bp_ax.set_xlabel("Time")

            vol_ax.set_title("Volume vs. Time")
            vol_ax.set_ylabel("Volume")
            vol_ax.set_xlabel("Time")

        plt.show()

        return self
