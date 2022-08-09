from analyzer import CystometryAnalyzer

# Settings can be changed here if you'd like

IMPORT_FILE: str = "example.csv"

EXPORT_FOLDER: str = "./exports"
EXPORT_PREFIX: str = "example_"

TIME_COLUMN: int = 0
PRESSURE_COLUMN: int = 1
ROW_SKIP_COUNT: int = 20

# if there are any errors, then these settings are likely poorly configured
# mess around with them (particularly the peak finding, and pressure threshold ones) until
# errors cease.
ANALYSIS_SETTINGS = dict(
    moving_avg_window=2,  # keep greater than or equal to 2
    peak_finding_sensitivity=0.5,  # keep between 0 and 1 mostly and closer to 0.5 generally
    pressure_threshold_percentile=92.6,  # keep this around 90-99. higher values usually mean higher thresholds
    volume_empty_percent=10.,  # keep between 0 and 100
    flow_volume=1  # The volume flow rate of fluid into the mouse's bladder (mL/min).
)

if __name__ == "__main__":

    analyzer = CystometryAnalyzer("./data/example.csv")

    analyzer.load(TIME_COLUMN, PRESSURE_COLUMN, ROW_SKIP_COUNT)\
        .analyze(**ANALYSIS_SETTINGS)\
        .get_data()\
        .export(EXPORT_FOLDER, EXPORT_PREFIX)\
        .visualize()

    # this does the same thing as the above
    # analyzer.load(TIME_COLUMN, PRESSURE_COLUMN, ROW_SKIP_COUNT) \
    #     .analyze(**ANALYSIS_SETTINGS) \
    #     .export_data(EXPORT_FOLDER, EXPORT_PREFIX) \
    #     .visualize_data()

# Since our lab doesn't do anything involving lasers, laser analysis code was (mostly) untouched.
'''
f = open("data\cystometry\\" + export_file_path + ".csv", "w")

f.write("Normal Interval,Normal Mean \n") #Change this title to the data needed
lasti = -1
normalIntervalSum = 0
normalSum = 0
normalCount = 0

laserIntervalSum = 0
laserSum = 0
laserCount = 0

lastLaser = False
"""
for i in peaks: #Change this algorithm depending on the neccessary data. #This is for laser + interval
    if laserVal[i] > .5 : ##Laser is On and not first number
        if lasti != -1:
            laserIntervalSum += time[i] - time[lasti]
            laserSum += actualVal[i]
        else:
            laserCount -= 1
        laserCount += 1
        lastLaser = True
    else:
        if lasti != -1:
            normalIntervalSum += time[i] - time[lasti]
            normalSum += actualVal[i]
        else:
            normalCount -= 1
        normalCount += 1
        lastLaser = False
    lasti = i
"""

for i in peaks: #Change this algorithm depending on the neccessary data. #Just normal interval here
    if lasti != -1:
        normalIntervalSum += time[i] - time[lasti]
        normalSum += actual_vals[i]
    else:
        normalCount -= 1
    normalCount += 1
    lasti = i


if normalCount > 1:
    f.write(str(normalIntervalSum/normalCount) + "," + str(normalSum/normalCount) + ",")
else:
    f.write("No Normal,,")

""" #Use this if laser is a part of the measurements
if laserCount > 1:
    f.write(str(laserIntervalSum/laserCount) + "," + str(laserSum/laserCount) + "\n")
else:
    f.write("No Laser,\n")
"""

f.write("Peaks\n")

f.write("Time_Peak,Bladder_P_Peak,Laser_Peak\n")
for i in peaks:
    f.write(str(time[i]) + "," + str(actual_vals[i]) + "\n") #Change this based on the columns you want to output to CSV
f.close()
'''
