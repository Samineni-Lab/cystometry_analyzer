from __future__ import annotations

import csv
from functools import wraps

import numpy as np
from numpy.typing import NDArray
from scipy.signal import savgol_filter, find_peaks

import utils
from data import CystometryData


# custom errors for more precisely named exceptions
class MissingFileError(Exception):
    """Exception for when a path is missing when it's required."""
    pass


class FileNotLoadedError(Exception):
    """Exception for when data is not loaded when it needs to be."""
    pass


class MissingDataError(Exception):
    """Exception for when data is needed but is missing."""
    pass


class CystometryAnalyzer:
    """
    Class used to analyze cystometry data.

    This class was designed with method chaining in mind. This allows methods to be called easily.

    Example:

        CystometryAnalyzer()\
            .set_file("path/to/data.csv")\
            .load(0, 1, 50)\
            .analyze(pressure_threshold_percentile=94)\
            .get_data()\
            .export("path/to/export/folder/", "exp1_")

        If you wanted to do multiple analyses of the same data, you could do:

        CystometryAnalyzer()\
            .set_file("path/to/data.csv")\
            .load(0, 1, 50)\
            .analyze(pressure_threshold_percentile=94)\
            .export_data("path/to/export/folder/", "a1_")\
            .analyze(pressure_threshold_percentile=96)\
            .export_data("path/to/export/folder/", "a2_")\
            .analyze(pressure_threshold_percentile=97, moving_avg_window=20)\
            .export_data("path/to/export/folder/", "a3_")\


    """

    def __init__(self, path: str | None = None) -> None:
        """
        Instantiates a CystometryAnalyzer.

        Args:
            path: The file path to raw cystometry data. This does not have to be provided, such as if
                `analyzer.set_data` is to be used.
        """
        self._data_path: str | None = path
        self._data: CystometryData | None = None
        self._raw_data: tuple[list[float], list[float]] | None = None

    def set_data(self, time_data: list[float] | NDArray[float],
                 pressure_data: list[float] | NDArray[float]) -> CystometryAnalyzer:
        """
        Sets the raw data to be analyzed directly rather than loading it from a file. Data will not be validated
        automatically.

        Args:
            time_data: The time data that corresponds with the provided pressure data.
            pressure_data: The raw bladder pressure data.

        Returns:
            self, allowing for method chaining
        """
        self._raw_data = time_data, pressure_data

        return self

    def set_file(self, path: str) -> CystometryAnalyzer:
        """
        Sets the file containing the raw cystometry data.

        Args:
            path: the file path to the raw data.

        Returns:
            self, allowing for method chaining
        """

        self._data = None
        self._raw_data = None
        self._data_path = path

        return self

    def load(self, time_col: int, pressure_col: int, skip_rows: int = 0, delim: str = ',') -> CystometryAnalyzer:
        """
        Loads the raw data from the selected file.

        Args:
            time_col: The column index (starting at 0) of time data.
            pressure_col: The column index of pressure data.
            skip_rows: The number of rows to skip before collecting data. Recommended for excluding headers and
                unusable data typically found near the beginning of files.
            delim: The delimiter separating values in the loaded csv file. Defaults to ','.

        Returns:
            self, allowing for method chaining
        """
        if not self.has_file():
            raise MissingFileError("Raw data cannot be loaded before selecting a file. Either provide a path in "
                                   "the constructor or use analyzer.set_file('path/to/file.csv')")

        with open(self._data_path) as file:
            vals = []
            time = []

            csv_reader = csv.reader(file, delimiter=delim)

            for line_num, row in enumerate(csv_reader):
                if line_num < skip_rows:
                    continue
                vals.append(float(row[pressure_col]))
                time.append(float(row[time_col]))

        self._raw_data = time, vals

        return self

    def analyze(self, moving_avg_window: int = 10, peak_finding_sensitivity: float = 0.333,
                pressure_threshold_percentile: float = 91., volume_empty_percent: float = 10.,
                flow_volume: float = 1) -> CystometryAnalyzer:
        """
        Analyzes the provided cystometry data.

        Args:
            moving_avg_window: The window or size of the moving average taken of the bladder pressure.
            peak_finding_sensitivity: Value that affects the sensitivity of finding peaks. Higher generally mean less
                peaks (more strict), lower means more peaks (less strict). Mostly, keep between 0 and 1
            pressure_threshold_percentile: percentile used to generate pressure thresholds.
                A pressure threshold is found when P''(t) >= xth percentile of P'' where P is bladder pressure and x is
                this value. Keep this value between 0 and 100 at all times, but stay in the 85-98 range for accuracy.
            volume_empty_percent: The percent of peak pressure at which the bladder is considered empty.
            flow_volume: The volume flow rate used when collecting data. Units are milliliters per minute (mL/min)

        Returns:
            self, allowing for method chaining
        """
        if not self.is_loaded():
            raise FileNotLoadedError("Cannot analyze data before it is loaded. Either use analyzer.set_data or "
                                     "analyser.load before this")

        time, actual_vals = self._raw_data

        moving_avg_vals = np.array(utils.moving_average(actual_vals, moving_avg_window))

        time = np.array(time[:-moving_avg_window + 1])

        # convert from python list to np.array for convenience
        actual_vals = np.array(actual_vals)

        # assumes that the intervals between individual times is constant
        time_step = time[1] - time[0]
        prominence = (max(moving_avg_vals) - min(moving_avg_vals)) * peak_finding_sensitivity

        peaks, _ = find_peaks(moving_avg_vals, prominence=prominence)  # find peaks
        valleys, _ = find_peaks(-1 * moving_avg_vals, prominence=prominence, distance=min(np.diff(peaks)) // 2)

        # calculate the first and second derivatives
        slopes = np.insert(np.diff(moving_avg_vals), 0, 0)
        slopes2 = np.insert(np.diff(slopes), 0, 0)

        # smooth the second derivative to reduce noise
        slopes2 = savgol_filter(slopes2, 9, 4)

        # create section of the data based on the baseline pressures
        # a 'section' in this case is the data between two neighboring baseline pressures
        baseline_bounds = utils.to_slices([None, *valleys], [*valleys, None])

        slope_thresholds = []  # will house the slope thresholds for each section
        # p-thresh refers to pressure threshold
        pthresh_indexes = []  # will house the indexes of found pressure thresholds
        # vethresh refers to volume empty threshold
        vethresh_indexes = []  # will house the indexes of found volume empty points

        # Threshold Pressure Finding

        # This algorithm is far from perfect, but it's the most accurate way I've found so far

        for section in utils.sections(slopes2, baseline_bounds):
            # the 1.618 * ... part is an attempt to correct inaccuracies caused by variation in section size
            # correction = 1.618 * (max(section) / abs(max(section) - min(section)))
            # pthresh = np.percentile(section, pressure_threshold_percentile + correction)

            pthresh = np.percentile(section, pressure_threshold_percentile)
            slope_thresholds.append(pthresh)

        # The index bounds between baselines (valleys) and peaks.
        baseline_peak_bounds = utils.to_slices([None, *valleys], peaks)
        bounded_slopes = (utils.sections(sl, baseline_peak_bounds) for sl in (slopes, slopes2))
        zipped_data = zip(*bounded_slopes, slope_thresholds, peaks, baseline_peak_bounds)

        for i, (dx, dx2, pthresh, peak, bound) in enumerate(zipped_data):

            allow_hit = True
            hits = []

            while len(hits) == 0 and pthresh > 0:

                # need to keep track of the index with respect to the data as a whole
                abs_idx = bound.start if bound.start is not None else 0

                for slope, slope2 in zip(dx, dx2):

                    if slope < 0.01:
                        # allow another hit if bladder pressure decreases
                        allow_hit = True

                    if slope2 >= pthresh and slope > 0 and allow_hit:
                        # add a potential p-thresh if the 2nd derivative
                        # is above the threshold and the pressure is increasing
                        hits.append(abs_idx)
                        allow_hit = False

                    abs_idx += 1

                slope_thresholds[i] = pthresh

                # there must be a pressure threshold before a peak, so the threshold to find one will be
                #   lowered repeatedly until one is found
                # most of the time, a hit is found on the first pass
                pthresh -= 0.001

            # the last potential threshold pressure is likely the most accurate one
            # other hits could be false positives where the pressure spikes a little
            if len(hits) > 0:
                pthresh_indexes.append(hits[-1])
            else:
                pthresh_indexes.append(bound.start if bound.start is not None else 0)

        # Find Volume Empty Points

        # first divide moving_avg vals into sections
        # each section contains the data between a peak and the next baseline
        for i, section in zip(peaks, utils.sections(moving_avg_vals, utils.to_slices(peaks, valleys + 1))):
            if len(section) == 0: continue
            diff = section[0] - section[-1]
            for val in section:
                if val < ((volume_empty_percent / 100) * diff) + section[-1]:
                    vethresh_indexes.append(i)
                    # the first point to meet the criteria of volume empty is the correct one, so just end the loop now
                    break

                i += 1  # keeps track of the index in the context of all data rather than just the section.

        vethresh_indexes = np.array(vethresh_indexes)

        # Volume Calculations

        peaks, pthresh_indexes = utils.normalize_len(peaks, pthresh_indexes)

        volume = []

        filling_sections = set(utils.flatten(utils.sections(time, utils.to_slices(pthresh_indexes, peaks + 1))))
        voiding_sections = []
        volume_down_slopes = []

        for section in utils.sections(time, utils.to_slices(peaks, vethresh_indexes + 1)):
            voiding_sections.extend(section)
            volume_down_slopes.append(section[-1] - section[0])
        voiding_sections = set(voiding_sections)

        curr_vol = 0
        max_vol = 0

        slope_index = 0
        for i, t in enumerate(time):

            if t in filling_sections:
                curr_vol += flow_volume / 60 * time_step
                max_vol = curr_vol
            elif t in voiding_sections and curr_vol > 0:
                curr_vol -= max_vol / (volume_down_slopes[slope_index]) * time_step

            if i in valleys:
                slope_index += 1

            volume.append(curr_vol)

        # Generate CystometryData

        self._data = CystometryData(
            time=time,
            values=actual_vals,
            moving_avg_vals=moving_avg_vals,
            peaks=peaks,
            baselines=valleys,
            pressure_threshold_idx=pthresh_indexes,
            volume_empty_idx=vethresh_indexes,
            baseline_bounds=np.array(baseline_bounds),
            derivative2=slopes2,
            volume=np.array(volume),
            slope_thresholds=np.array(slope_thresholds)
        )

        return self

    @wraps(CystometryData.visualize)
    def visualize_data(self, *args, **kwargs) -> CystometryAnalyzer:
        """
        A wrapper function for ``CystometryData.visualize`` that preserves method chaining if desired.

        Args:
            args: Arguments that will be passed to `CystometryData.visualize`.
            kwargs: Keyword arguments that will be passed to `CystometryData.visualize`.

        Return:
            self, allowing for method chaining
        """

        if not self.has_data():
            raise MissingDataError("Cannot visualize data when there is None! "
                                   "Make sure to run analyzer.analyze before using this.")

        self._data.visualize(*args, **kwargs)

        return self

    @wraps(CystometryData.export)
    def export_data(self, *args, **kwargs) -> CystometryAnalyzer:
        """
        A wrapper function for ``CystometryData.visualize`` that preserves method chaining if desired.

        Args:
            args: Arguments that will be passed to `CystometryData.export`.
            kwargs: Keyword arguments that will be passed to `CystometryData.export`.

        Return:
            self, allowing for method chaining
        """

        if not self.has_data():
            raise MissingDataError("Cannot export data when there is None. "
                                   "Make sure to run analyzer.analyze before using this.")

        self._data.export(*args, **kwargs)

        return self

    def has_file(self) -> bool:
        """
        Returns:
            True if a file has been selected, False otherwise
        """

        return self._data_path is not None and self._data_path != ''

    def has_data(self) -> bool:
        """
        Returns:
            True if analyzed data is present, False otherwise
        """

        return self._data is not None

    def is_loaded(self) -> bool:
        """
        Returns:
            True if raw data is present, False otherwise
        """
        return self._raw_data is not None

    def get_data(self) -> CystometryData | None:
        """
        Retrieves analyzed data in the form of the CystometryData dataclass.

        Returns:
            The analyzed data if there is any or None.
        """
        return self._data

    def get_file_path(self) -> str | None:
        """
        Retrieves the file path to the selected raw data.

        Returns:
            The file path if it's present or None
        """
        return self._data_path
