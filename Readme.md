This repository includes the standalone optimisation engine used for solving the optimisation problem introduced in the "predict+optimise" challenge,
IEEE CIS 3rd Technical Challenge. For more details of the competition, please see
https://ieee-dataport.org/competitions/ieee-cis-technical-challenge-predictoptimize-renewable-energy-scheduling

The optimisation engine reads problem data, solves the problem, and reports its solution together with additional results and statistics. This information is reported for every instance in its designated directory. The formats of the input/output files (input instance files, output solution files and the input forecast files) follows those of the competition.

The engine has been written in Python 3.9 and it uses Gurobi 9.1.2 as the MILP solver. It has been tested on Ubuntu 20.04, but should work on Windows too. The directory "IEEE-CIS Predict+Optimize" includes three folders as follows:

1. "codes": This folder includes the python source codes of the engine
2. "COMPETITION DATASET FILES": This folder includes the input data read by the engine. For example, "phase_2_instances" includes the problem instances of phase 2 of the competition, and "phase_2_scenarios" includes the price data as well as the input forecasts. The file name of each forecast file (i.e., each scenario) needs to include the term "submission" to be included in the problem as a scenario. At least one scenario is needed, but there is no upper bound on the number of scenarios that can be included. The existing scenarios have been obtained from the forecasting methodology described in https://github.com/mahdiabolghasemi/IEEE-predict_Optimise_Competitoin.
3. "startsol": this folder is used to warm-start the engine with an existing solution (if any).

Each engine solves every problem in the corresponding folder (e.g., "phase_2_instances") and writes the solution for each instance in "IEEE-CIS Predict+Optimize/output/" (the output folder will be created if it does not exist). By default, the engine assumes that the "IEEE-CIS Predict+Optimize" directory is located in the Desktop. This location can be changed in the "_get_main_dir" method in Setting.py file (if needed). To run the engine and solve all instances one by one, open a bash terminal, change dirctory to the location of Main.py, and run "python Main.py" (replace python with python3 or the path to your python 3.9+ if needed). Alternatively you can use your favorate IDE to run the code. To solve one instance only, use "python Main.py ?" where ? is the index of the problem in the list of all problem instances (sorted alphabetically). For instance, "python Main.py 9" will run "phase2_instance_small_4" using the existing data files.


The engine has multiple source files as follows:

1. Main.py: This is where the program starts.

2. Setting.py: The engine parameters can be set in this file. These settings are generally self explanatory, but we explain some of them here:
runtime: the time limit of the engine in seconds, the maximum time we would like to wait to obtain a solution for each instance
gap: The relative optimality gap of the solver
setstart: This setting indicates whether the solutions in the "startsol" folder be used as warm-start or not. If True, each solution in the "startsol" folder will be replaced with the final solution after the problem is solved.
fixsol: This setting indicates whether the solutions in the "startsol" folder be fixed or not. If True, it fixes the solution and reports in the summary.csv file the value of the solution in different scenarios. Note that summary.csv will include this information for all instances.
algorithm: The version of the algorithm that is used to solve the problem. For a list of possible algorithms, see Algorithm.py.
use_multiple_scenarios: This setting indicates whether multiple scenarios are used or not. If False, the first scenario is used. We suggest to set this parameter to True and instead modify the list of scenarios in the corresponding scenario directory.
main_dir: the full address of the "IEEE-CIS Predict+Optimize" directory.

3. Algorithm.py: This is where different algorithms can be designed based on the optimizer objects and their methods.

4. Optimizer.py: An object of this class receives a problem instance and creates the modelling objects (variables, constraints and the objective function) for that instance. It includes various methods for desiging different algorithms.

5. Instance.py: An object of this class includes the relevant data for the corresponding instance that is used to construct an Optimizer object.

6. Data.py: This is where the related problems are specified and each problem instance is constructed.

7. Solution.py: Extracts the solution from an Optimizer object and provides methods to export the solution.

8. Time.py: This module creates all time slots for a given planning horizon (as specified in the settings).

9. Util.py: Includes utilities for input/output etc used in other files.

