import Util


class SolverSetting:
    def __init__(self):
        self.name = "default"
        self.runtime = 10 * 3600
        self.gap = 0
        self.setstart = True
        self.fixsol = False
        self.nodelimit = None
        self.method = 1
        # https://www.gurobi.com/documentation/9.1/refman/method.html
        self.focus = 1
        # https://www.gurobi.com/documentation/9.1/refman/mipfocus.html
        self.presolve = None
        # https://www.gurobi.com/documentation/9.1/refman/presolve.html#parameter:Presolve
        self.threads = 1
        # https://www.gurobi.com/documentation/9.1/refman/threads.html


class Setting:
    def __init__(self):
        self.name = "default"
        self.solver = SolverSetting()
        self.algorithm = 7 if self.solver.setstart else 12
        self.phase = 2
        self.use_multiple_scenarios = True
        self.use_real_data = False
        self.use_utc_time = True if self.phase == 2 else False
        self.start_date = "20-10-01" if self.phase == 1 else "20-11-01"
        self.end_date = "20-10-31" if self.phase == 1 else "20-11-30"
        self.slot_minutes = 15
        self.main_dir = self._get_main_dir()
        self.startsol_dir = Util.joinpath(self.main_dir, "startsol")
        self.input_dir = Util.joinpath(self.main_dir, "COMPETITION DATASET FILES")
        self.dataset_keys = [f"phase_{self.phase}"]
        self.summary_file_name = "summary"

    @property
    def output_dir(self):
        return Util.joinpath(self.main_dir, "output", f"{self.name}_{self.algorithm}")

    @property
    def summary_file(self):
        return Util.joinpath(self.output_dir, f"{self.summary_file_name}.csv")

    def _get_main_dir(self):
        home_dir = Util.homedir()
        main_dir = Util.joinpath(home_dir, "Desktop", "IEEE-CIS Predict+Optimize")
        return main_dir
