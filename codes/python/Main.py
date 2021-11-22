import pandas as pd
import sys
import traceback
from Setting import Setting
from Data import Data
from Algorithm import Algorithm
import Util


Util.clearTerminal()

if len(sys.argv) > 1:
    i = sys.argv[1]
    cli = True
    print(f"\nSolving Instance {i}\n")
else:
    cli = False


setting = Setting()
data = Data(setting)
for key in data.datasets:
    instances = (
        [data.get_instance_by_index(key, int(i))] if cli else data.get_instances(key)
    )
    for instance in instances:
        algorithm = Algorithm(instance)
        summary, solution = algorithm.run()
        print(f"\n\nSolved {instance.name}\n\n")
        if setting.solver.fixsol:
            if not Util.exists(setting.summary_file):
                solution.csv_header(setting.summary_file)
            solution.add2csv(setting.summary_file)
        else:
            if not Util.exists(setting.summary_file):
                summary.csv_header(setting.summary_file)
            summary.add2csv(instance.name, setting.summary_file)
        solution.export_ppoi(setting.startsol_dir, tag=False)

if setting.solver.fixsol:
    Util.writeln(setting.summary_file)
    df = pd.read_csv(setting.summary_file)
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
    df.describe().loc[["mean", "std", "min", "50%", "max", "count"]].to_csv(
        setting.summary_file, mode="a", header=True
    )
