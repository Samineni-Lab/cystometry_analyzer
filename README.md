# Cystometry Analyzer

A program that analyzes cystometry data.

## Environment Setup

Create a new virtual environment using your preferred method. Python versions 3.9 and 3.10 have been tested 
successfully. (Example setup using [Anaconda3](https://www.anaconda.com) shown below.)
```shell
conda create -n cysto_analzyer python=3.9
conda activate cysto_analzyer
```

In your new Python environment, download requirements with `pip`:

```shell
pip install -r requirements.txt
```

This should install the necessary dependencies to use the cystometry analyzer.

## Use

Analysis of cystometry data is done via the `CystometryAnalyzer` class defined in `analyzer.py`.
To see how its used, you can review the code in `example.py`. For a more detailed description on how to use it,
continue reading.

### Loading Data

There are two methods of loading raw data: loading data from a file and directly
supplying the raw data.

#### Loading from a File

Firstly, only csv files can be loaded by the `CystometryAnalyzer` and must
include time and bladder pressure values. If your data is not in this
format, you must extract the raw data manually and provide it with the `set_data` method.

To load raw data from a file, you must first select a file. There are two ways of doing this.
The first is via the `CystometryAnalyzer` constructor:

```python
analyzer = CystometryAnalyzer("path/to/data.csv")
```

The second is via the `set_file` method:

```python
analyzer = CystometryAnalyzer().set_file("path/to/data.csv")
```

The `set_file` method exists primarily for chaining different analyses together, which will
be touched upon later.

After a file is selected, raw data must be extracted. This is done with the `load` method:

```python
analyzer.load(0, 1, 20, ',')
```

The `load` method takes four arguments, two of which are optional:
* `analyzer.load(time_col, pressure_col, [row_skip], [delim])`
  * `time_col` - *required* - zero-based column index corresponding to the time values of your data
  * `pressure_col` - *required* - zero-based column index corresponding to the bladder pressure values of your data
  * `row_skip` - *optional, default = 0* - The number of rows to skip when loading data
    * useful for skipping headers and unusable initial data
  * `delim` - *optional, default = ','* - The delimiter of your csv file. Typically, it is either tab or comma.


#### Direct

If you'd like to extract your data from a file yourself or receive it from another source, then
you can directly supply raw data to the `CystometryAnalyzer`. This is done through the 
`set_data` method:

```python
analyzer.set_data(time_data, pressure_data)
```

`set_data` takes two arguments, both of which are required:
* `time_data` - *required* - A list or ndarray of time values in seconds.
* `pressure_data` - *required* - A list or ndarray of pressure values.
* **Note:** data is interpreted as corresponding pairs of the form 
   `[(time_data[0], pressure_data[0]), (time_data[1], pressure_data[1]), ...]`

### Analysis

After your raw data is loaded, you can move on to analysis. Analysis is done through the
`CystometryAnalyzer`'s `analyze` method:

```python
analyzer.analyze(moving_avg_window=10, peak_finding_sensitivity=0.333,
                pressure_threshold_percentile=91., volume_empty_percent=10.,
                flow_volume=1)
```

The `analyze` method takes 5 positional arguments, none of which are required. However,
it is recommended you specify most of them as these are the parameters you'll curate
to your data.
* `moving_avg_window` - *optional, default = 10* - The window or size of the moving average taken of the pressure data. 
    The higher the number, the smoother and flatter data is. The moving average is used for most
    analysis calculations and algorithms.
* `peak_finding_sensitivity` - *optional, default = 0.333* - Value that modifies the number of peaks
    detected. Higher values yield fewer peaks with greater prominence, lower results in more peaks 
    with lesser prominence. This value should mostly remain between 0 and 1.
* `pressure_threshhold_percentile` - *optional, default = 91.* - The percentile used to locate pressure threshold 
    times. Should be within `[0, 100]` and stay near `90`-`96`. Generally, higher values result it thresholds closer to
    peaks, and lower values result in thresholds closer to baselines.
  * A pressure threshold is found when 
      `P''(t) >= xth percentile of P''` where `P` is the bladder pressures within a certain section of time,
      `x` is the `pressure_threshhold_percentile`, and `t` is time. 
      The sections are defined as the region between neighboring baseline pressures.
* `volume_empty_percent` - *optional, default = 10* - The percentage of the max pressure of a contraction at which the
    bladder is considered empty. Value should be within `[0, 100]`.
* `flow_volume` - *optional, default = 1* - The volume flow rate of fluid entering the mouse's bladder. Units are
    milliliters per minute (mL/min).

### Using Analyzed Data

After analyzing your raw cystometry data, you can retrieve the analyzed data using the `get_data` method:

```python
analyzer.get_data()
```

Data is returned as a `dataclass` called `CystometryData`. Its declaration is located in `data.py` and contains
the following attributes:
* `time` - *1d array of floats* - An array of time values.
* `values` - *1d array of floats* - An array of the pressure values.
* `derivative2` - *1d array of floats* - An array containing the second derivitive of `moving_avg_vals`
* `moving_avg_vals` - *1d array of floats* - The moving average of `values`
* `peaks` - *1d array of ints* - The indexes of the peaks in bladder pressure.
* `baselines` - *1d array of ints* - The indexes of the baselines
* `pressure_threshold_idx` - *1d array of ints* - The indexes of the pressure thresholds in bladder pressure.
* `volume_empty_idx` - *1d array of ints* - The indexes of where the mouse's bladder is deemed empty.
* `volume` - *1d array of floats* - The volume values over time.
* `baseline_bounds` - *1d array of slices* - Bounds that can divide `values`, `moving_avg_vals`, `derivative2`, `time`, 
    and `volume` into sections split at the `baselines`
* `slope_thresholds` - *1d array of floats* - The threshold which `derivative2` must cross for a pressure threshold to
    be detected. Only useful when trying to visualize how pressure thresholds were determined.
* **Note:** all attributes correspond to each other. 
  * For example: to get the bladder pressures at every peak, use `peak_pressures = data.values[data.peaks]` using
      numpy's indexing.

### Visualizing Data

For particular and customized visualization of analyzed data, it is recommended that you use the attributes of 
`CystometryData` to create your own visualization. For a simple visualization, however, the following can be used:

```python
analyzer.get_data().visualize(show_labels=True, show_markers=True, show_legend=True)
# OR
analyzer.visualize_data(show_labels=True, show_markers=True, show_legend=True)
```

Both create the same visualization and have the same three optional positional arguments:
* `show_labels` - *optional, default = True* - Whether to show axis/title labels in the visualization.
* `show_markers` - *optional, default = True* - Whether to mark pressure thresholds, peaks, baselines, etc.
* `show_legend` - *optional, default = True* - Whether to show a legend 
    (a legend is recommended if `show_markers` is True)

The difference between these two methods is that `visualize_data` returns the `CystometryAnalyzer`, preserving method
chaining with the analyzer, while `visualize` returns `CystometryData`. Look at the **Method Chaining** section for a 
comparison.

### Exporting Data

For particular and customized exporting of analyzed data, it is recommended that you use the attributes of 
`CystometryData` to create your own export. For a standard export (seen in the example exports of the `exports` folder), 
however, the following can be used:

```python
analyzer.get_data().export(dir_path="path/to/export/folder", prefix="experiment1_")
# OR
analyzer.export_data(dir_path="path/to/export/folder", prefix="experiment1_")
```

Both export data in the same way, and both have the same required and optional position arguments:
* `dir_path` - *required* - The path to a folder to save exported data.
* `prefix` - *optional, default = ''* - A prefix prepended to file names to distinguish exports

Like with visualizing, `export_data` returns the `CystometryAnalyzer`, preserving method
chaining with the analyzer, while `export` returns `CystometryData`. Look at the **Method Chaining** section for a 
comparison.

## Method Chaining

The `CystometryAnalyzer` was built with method chaining in mind. Check `example.py` for a functional example of this.
Here's an extreme example of method chaining.

```python
from analyzer import CystometryAnalyzer

# analyze 3 sets of data in a row, each with different parameters
analyzer = CystometryAnalyzer("./data1.csv") \
    .load(0, 1, 20) \
    .analyze(peak_finding_sensitivity=0.5) \
    .export_data("./exports", 'd1_') \
    .set_file("./data2.csv") \
    .load(0, 2, 50) \
    .analyze(peak_finding_sensitivity=0.6, pressure_threshold_percentile=95) \
    .export_data("./exports", 'd2_') \
    .set_file("./data3.csv") \
    .load(1, 3, 10) \
    .analyze(peak_finding_sensitivity=0.2, moving_avg_window=20) \
    .export_data("./exports", 'd3_') \
    .visualize_data()

print(analyzer.get_data())  # can continue to use the analyzer
```

`CystometryData` also supports method chaining on a smaller scale:

```python
from analyzer import CystometryAnalyzer

data = CystometryAnalyzer("./data1.csv") \
    .load(0, 1, 20) \
    .analyze(peak_finding_sensitivity=0.5) \
    .get_data()

data.export("./exports", 'd1_').visualize()  # exports then visualizes the analyzed data

print(data)  # continue to do stuff with data
```

Note that `get_data` returns `CystometryData`, meaning that method chaining the `CystometryAnalyzer` indefinitely
stops when `get_data` is called. However, because `CystometryData` supports method chaining, 
the above can be simplified:

```python
from analyzer import CystometryAnalyzer

data = CystometryAnalyzer("./data1.csv") \
    .load(0, 1, 20) \
    .analyze(peak_finding_sensitivity=0.5) \
    .get_data() \
    .export("./exports", 'd1_') \
    .visualize()

print(data)  # continue to do stuff with data
```
