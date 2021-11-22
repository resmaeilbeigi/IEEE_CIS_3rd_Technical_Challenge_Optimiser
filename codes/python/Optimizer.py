import json
import math
from collections import OrderedDict
import numpy as np
import gurobipy as gp
from gurobipy import GRB
from Instance import Instance, Type
import Util


class SolutionInfo:
    def __init__(self):
        self.CPU = np.nan
        self.ITR = np.nan
        self.GAP = np.nan
        self.LB = np.nan
        self.UB = np.nan
        self.NOD = np.nan
        self.NNZ = np.nan
        self.VARs = np.nan
        self.CONs = np.nan
        self.STATUS = None

    def write(self, filepath):
        with open(filepath, "w") as f:
            json.dump(vars(self), f, indent=4, sort_keys=True)

    def add2csv(self, key, filepath):
        writer = Util.Writer(filepath, sep=",", empty=False)
        values = [
            f"{key}",
            self.LB,
            self.UB,
            self.GAP,
            self.CPU,
            self.NOD,
            self.ITR,
            self.NNZ,
            self.VARs,
            self.CONs,
        ]
        writer.pretty_out(values, len(values))

    def csv_header(self, filepath):
        writer = Util.Writer(filepath, sep=",")
        fields = [
            "KEY",
            "LB",
            "UB",
            "GAP",
            "CPU",
            "NOD",
            "ITR",
            "NNZ",
            "VARs",
            "CONs",
        ]
        writer.pretty_out(fields, len(fields))


class Optimizer:
    def __init__(self, instance: Instance) -> None:
        self.solve_count = 0
        self.setting = instance.setting
        self.instance = instance
        self.slots_per_hour = instance.time.slots_per_hour
        self.load_indices = range(1, instance.max_load_ub + 1)
        self.slot_indices = self.instance.planning_horizon
        self.scenarios = OrderedDict((i, s) for i, s in enumerate(instance.scenarios))
        self.batteries = OrderedDict(
            (i, instance.batteries[i]) for i in range(len(instance.batteries))
        )
        self.activities = OrderedDict(
            (i, instance.activities[i]) for i in range(len(instance.activities))
        )
        self.activities_r = OrderedDict(
            (i, a) for i, a in self.activities.items() if a.type == Type.R
        )
        self.activities_o = OrderedDict(
            (i, a) for i, a in self.activities.items() if a.type == Type.O
        )
        self.lp_file = Util.joinpath(instance.folder, "model.lp")
        self.log_file = Util.joinpath(instance.folder, "gurobi.log")
        self.info_file = Util.joinpath(instance.folder, "summary.json")
        Util.empty_file(self.log_file)
        # Util.empty_file(self.lp_file)
        Util.writeln(
            self.log_file,
            f"Instance={instance.name} Algorithm={self.setting.algorithm} ScenarioCount={len(self.scenarios)}",
        )
        Util.writeln(
            self.log_file,
            f'Scenarios: {" ".join(s.name for s in self.instance.scenarios)}',
        )
        Util.writeln(self.log_file, Util.SEPARATOR)
        self.start_vars = []
        self.total_runtime = 0
        self.temporary_constraints = []
        self.model = gp.Model()
        self.model.setParam(GRB.Param.LogToConsole, 1)
        self.model.setParam(GRB.Param.LogFile, self.log_file)
        self.model.setParam(GRB.Param.MIPGap, self.setting.solver.gap)
        self.model.setParam(GRB.Param.TimeLimit, self.setting.solver.runtime)
        if self.setting.solver.nodelimit:
            self.model.setParam(GRB.Param.NodeLimit, self.setting.solver.nodelimit)
        if self.setting.solver.method:
            self.model.setParam(GRB.Param.Method, self.setting.solver.method)
        if self.setting.solver.presolve:
            self.model.setParam(GRB.Param.Presolve, self.setting.solver.presolve)
        if self.setting.solver.focus:
            self.model.setParam(GRB.Param.MIPFocus, self.setting.solver.focus)
        if self.setting.solver.threads:
            self.model.setParam(GRB.Param.Threads, self.setting.solver.threads)

    def formulate(self):
        self.create_variables()
        self.create_objective()
        self.create_constraints()
        self.set_start_values()
        self.fix_solution()
        # self.model.write(self.lp_file)

    def create_variables(self):
        self.X_VAR = self.model.addVars(
            ((b, t) for b in self.batteries for t in self.slot_indices),
            name="X",
            vtype=GRB.BINARY,
            lb=0,
            ub=1,
        )

        self.Y_VAR = self.model.addVars(
            ((b, t) for b in self.batteries for t in self.slot_indices),
            name="Y",
            vtype=GRB.BINARY,
            lb=0,
            ub=1,
        )

        self.Z_VAR = self.model.addVars(
            ((a, t) for a in self.activities for t in self.activities[a].start_times),
            name="Z",
            vtype=GRB.BINARY,
        )

        self.V_VAR = self.model.addVars(
            (
                (a, t)
                for a in self.activities
                for t in self.activities[a].progress_times
            ),
            name="V",
            vtype=GRB.BINARY,
        )

        self.S_VAR = self.model.addVars(
            ((b, t) for b in self.batteries for t in self.slot_indices),
            name="S",
            vtype=GRB.CONTINUOUS,
        )

        self.L_VAR = self.model.addVars(
            ((t, s) for t in self.slot_indices for s in self.scenarios),
            name="L",
            lb=-GRB.INFINITY,
            ub=GRB.INFINITY,
            vtype=GRB.CONTINUOUS,
        )

        self.W_VAR = self.model.addVars(
            (a for a in self.activities), name="W", vtype=GRB.BINARY,
        )

        self.U_VAR = self.model.addVars(
            (a for a in self.activities_o), name="U", vtype=GRB.BINARY,
        )

        self.D_VAR = self.model.addVars(
            (a for a in self.activities), name="D", vtype=GRB.INTEGER,
        )

        self.LAMBDA_VAR = self.model.addVars(
            ((i, s) for i in self.load_indices for s in self.scenarios),
            name="LAMBDA",
            vtype=GRB.CONTINUOUS,
        )

        # self.ETA_VAR = self.model.addVar(name="_E", vtype=GRB.CONTINUOUS)

        self.ETA_VAR = self.model.addVars(
            (s for s in self.scenarios), name="_E", vtype=GRB.CONTINUOUS,
        )

    def create_objective(self):
        obj = (
            gp.quicksum(
                self.L_VAR[t, s]
                * self.instance.scenarios[s].price[t]
                / (self.slots_per_hour * 1000 * len(self.instance.scenarios))
                for t in self.slot_indices
                for s in self.scenarios
            )
            + gp.quicksum(
                self.LAMBDA_VAR[i, s] * 0.005 * (i ** 2) / len(self.instance.scenarios)
                for i in self.load_indices
                for s in self.scenarios
            )
            + gp.quicksum(
                self.U_VAR[a] * self.activities[a].penalty for a in self.activities_o
            )
            - gp.quicksum(
                self.W_VAR[a] * self.activities[a].revenue for a in self.activities_o
            )
        )

        self.model.setObjective(obj, GRB.MINIMIZE)

    def map_time(self, t):
        if t < self.instance.first_monday_slot:
            return t
        return self.instance.first_monday_slot + (
            (t - self.instance.first_monday_slot) % self.instance.time.slots_per_week
        )

    def create_constraints(self):

        self.model.addConstrs(
            (
                (
                    gp.quicksum(
                        self.Z_VAR[a, tp]
                        for tp in range(t - self.activities[a].duration + 1, t + 1)
                        if tp in self.activities[a].start_times
                    )
                    == self.V_VAR[a, t]
                )
                for a in self.activities
                for t in self.activities[a].progress_times
            ),
            name="C1",
        )

        self.model.addConstrs(
            (
                (self.V_VAR.sum(a, "*") == self.activities[a].duration * self.W_VAR[a])
                for a in self.activities
            ),
            name="C2",
        )

        self.model.addConstrs(
            (
                (self.Z_VAR.sum(a, self.activities[a].start_times) == self.W_VAR[a])
                for a in self.activities
            ),
            name="C3",
        )

        self.model.addConstrs(
            (
                (self.Z_VAR.sum(a, self.activities[a].penalty_times) == self.U_VAR[a])
                for a in self.activities_o
            ),
            name="C4",
        )

        self.model.addConstrs(
            (
                (
                    gp.quicksum(
                        self.Z_VAR[a, t]
                        * (
                            (t + self.instance.time.utc_offset)
                            // self.instance.time.slots_per_day
                        )
                        for t in self.activities[a].start_times
                    )
                    + math.ceil(
                        1
                        + (len(self.slot_indices) + self.instance.time.utc_offset)
                        / self.instance.time.slots_per_day
                    )
                    * (1 - self.W_VAR[a])
                    == self.D_VAR[a]
                )
                for a in self.activities
            ),
            name="C5",
        )

        self.model.addConstrs(
            (
                (self.D_VAR[a] + self.W_VAR[a] <= self.D_VAR[ap])
                for ap in self.activities
                for a in self.activities[ap].prerequisites
            ),
            name="C6",
        )

        self.model.addConstrs(
            (
                (self.W_VAR[ap] <= self.W_VAR[a])
                for ap in self.activities
                for a in self.activities[ap].prerequisites
            ),
            name="C7",
        )

        self.model.addConstrs(
            (
                (
                    self.S_VAR[b, 0]
                    == self.batteries[b].initial_state
                    + (self.batteries[b].max_power / self.slots_per_hour)
                    * (self.X_VAR[b, 0] - self.Y_VAR[b, 0])
                )
                for b in self.batteries
            ),
            name="C8",
        )

        self.model.addConstrs(
            (
                (
                    self.S_VAR[b, t]
                    == self.S_VAR[b, t - 1]
                    + (self.batteries[b].max_power / self.slots_per_hour)
                    * (self.X_VAR[b, t] - self.Y_VAR[b, t])
                )
                for b in self.batteries
                for t in self.slot_indices[1:]
            ),
            name="C9",
        )

        self.model.addConstrs(
            (
                (self.X_VAR[b, t] + self.Y_VAR[b, t] <= 1)
                for b in self.batteries
                for t in self.slot_indices
            ),
            name="C10",
        )

        self.model.addConstrs(
            (
                (
                    self.L_VAR[t, s]
                    == self.instance.scenarios[s].base_load[t]
                    - self.instance.scenarios[s].solar_load[t]
                    + gp.quicksum(
                        (
                            self.X_VAR[b, t]
                            - self.batteries[b].efficiency * self.Y_VAR[b, t]
                        )
                        * (
                            self.batteries[b].max_power
                            / math.sqrt(self.batteries[b].efficiency)
                        )
                        for b in self.batteries
                    )
                    + gp.quicksum(
                        self.V_VAR.get((a, t), 0)
                        * self.activities[a].load_per_room
                        * (
                            self.activities[a].small_rooms
                            + self.activities[a].large_rooms
                        )
                        for a in self.activities_o
                    )
                    + gp.quicksum(
                        self.V_VAR.get((a, self.map_time(t)), 0)
                        * self.activities[a].load_per_room
                        * (
                            self.activities[a].small_rooms
                            + self.activities[a].large_rooms
                        )
                        for a in self.activities_r
                    )
                )
                for t in self.slot_indices
                for s in self.scenarios
            ),
            name="C11",
        )

        self.model.addConstrs(
            (
                (
                    gp.quicksum(
                        self.V_VAR.get((a, t), 0) * self.activities[a].large_rooms
                        for a in self.activities_o
                    )
                    + gp.quicksum(
                        self.V_VAR.get((a, self.map_time(t)), 0)
                        * self.activities[a].large_rooms
                        for a in self.activities_r
                    )
                    <= self.instance.large_room_count
                )
                for t in self.slot_indices
            ),
            name="C12",
        )

        self.model.addConstrs(
            (
                (
                    gp.quicksum(
                        self.V_VAR.get((a, t), 0) * self.activities[a].small_rooms
                        for a in self.activities_o
                    )
                    + gp.quicksum(
                        self.V_VAR.get((a, self.map_time(t)), 0)
                        * self.activities[a].small_rooms
                        for a in self.activities_r
                    )
                    <= self.instance.small_room_count
                )
                for t in self.slot_indices
            ),
            name="C13",
        )

        self.model.addConstrs(
            (self.LAMBDA_VAR.sum("*", s) <= 1 for s in self.scenarios), name="C14",
        )

        self.model.addConstrs(
            (
                gp.quicksum(self.LAMBDA_VAR[i, s] * i for i in self.load_indices)
                >= self.ETA_VAR[s]
                for s in self.scenarios
            ),
            name="C15",
        )

        self.model.addConstrs(
            (
                (self.ETA_VAR[s] >= self.L_VAR[t, s])
                for t in self.slot_indices
                for s in self.scenarios
            ),
            name="C16",
        )

        self.model.addConstrs(
            (
                (self.ETA_VAR[s] >= -self.L_VAR[t, s])
                for t in self.slot_indices
                for s in self.scenarios
            ),
            name="C17",
        )

        self.model.addConstrs(
            ((self.W_VAR[a] == 1) for a in self.activities_r), name="C18",
        )

        self.model.addConstrs(
            (
                (self.S_VAR[b, t] <= self.batteries[b].capacity)
                for b in self.batteries
                for t in self.slot_indices
            ),
            name="C19",
        )

        # self.model.addConstrs(
        #     ((self.U_VAR[a] <= self.W_VAR[a]) for a in self.activities_o), name="C20",
        # )

    def solve(self) -> SolutionInfo:
        Util.writeln(self.log_file, Util.SEPARATOR)

        self.model.update()

        # self.model.optimize(lazyCallback)
        self.model.optimize()
        self.solve_count += 1
        info = SolutionInfo()
        info.STATUS = self.model.getAttr(GRB.Attr.Status)
        # https://www.gurobi.com/documentation/9.1/refman/optimization_status_codes.html
        if self.model.getAttr(GRB.Attr.SolCount) == 0:
            if info.STATUS == 3:
                self.model.computeIIS()
                self.model.write(self.instance.folder + "conflict.ilp")
            return info
        info.CPU = self.model.getAttr(GRB.Attr.Runtime)
        info.ITR = self.model.getAttr(GRB.Attr.IterCount)
        info.GAP = 100 * self.model.getAttr(GRB.Attr.MIPGap)
        info.UB = self.model.getAttr(GRB.Attr.ObjVal)
        info.LB = self.model.getAttr(GRB.Attr.ObjBound)
        info.NOD = self.model.getAttr(GRB.Attr.NodeCount)
        info.NNZ = self.model.getAttr(GRB.Attr.NumNZs)
        info.VARs = self.model.getAttr(GRB.Attr.NumVars)
        info.CONs = self.model.getAttr(GRB.Attr.NumConstrs)
        self.total_runtime += info.CPU
        info.write(self.info_file.replace("summary", f"summary_{self.solve_count}"))
        self.unset_start_values()
        return info

    def set_start_values(self):
        if not self.setting.solver.setstart:
            return
        if self.instance.sol_battery_bt_mode:
            for key in self.X_VAR:
                self.start_vars.append(self.X_VAR[key])
                self.start_vars.append(self.Y_VAR[key])
                mode = self.instance.sol_battery_bt_mode.get(key, 1)
                if mode == 0:
                    self.X_VAR[key].start = 1
                    self.Y_VAR[key].start = 0
                elif mode == 2:
                    self.X_VAR[key].start = 0
                    self.Y_VAR[key].start = 1
                else:
                    self.X_VAR[key].start = 0
                    self.Y_VAR[key].start = 0
        else:
            for key in self.X_VAR:
                self.X_VAR[key].start = 0
                self.Y_VAR[key].start = 0
        if self.instance.sol_activity_start:
            for a in self.activities_o:
                self.start_vars.append(self.W_VAR[a])
                self.W_VAR[a].start = 0
            for a, t in self.instance.sol_activity_start.items():
                self.Z_VAR[a, t].start = 1
                self.W_VAR[a].start = 1
                self.start_vars.append(self.Z_VAR[a, t])

    def fix_solution(self):
        if not self.setting.solver.fixsol:
            return
        if self.instance.sol_battery_bt_mode:
            for key in self.X_VAR:
                mode = self.instance.sol_battery_bt_mode.get(key, 1)
                if mode == 0:
                    self.X_VAR[key].lb = 1
                    self.Y_VAR[key].ub = 0
                elif mode == 2:
                    self.X_VAR[key].ub = 0
                    self.Y_VAR[key].lb = 1
                else:
                    self.X_VAR[key].ub = 0
                    self.Y_VAR[key].ub = 0
        else:
            for key in self.X_VAR:
                self.X_VAR[key].ub = 0
                self.Y_VAR[key].ub = 0
        if self.instance.sol_activity_start:
            for a in self.activities_o:
                self.W_VAR[a].ub = 0
            for a, t in self.instance.sol_activity_start.items():
                self.Z_VAR[a, t].lb = 1
                self.W_VAR[a].ub = 1
                self.W_VAR[a].lb = 1

    def unset_start_values(self):
        if not self.setting.solver.setstart:
            return
        for var in self.model.getVars():
            var.start = GRB.UNDEFINED
        self.start_vars.clear()

    def set_start_from_model(self, optimized_model):
        for var in optimized_model.getVars():
            if var.x > 0.01:
                self.model.getVarByName(var.VarName).start = var.x

    def exclude_penalized_activities(self):
        for _, var in self.U_VAR.items():
            var.ub = 0

    def include_penalized_activities(self):
        for _, var in self.U_VAR.items():
            var.ub = 1

    def exclude_batteries(self):
        for idx in self.X_VAR:
            self.X_VAR[idx].ub = 0
            self.Y_VAR[idx].ub = 0

    def include_batteries(self):
        for idx in self.X_VAR:
            self.X_VAR[idx].ub = 1
            self.Y_VAR[idx].ub = 1

    def restrict_charge_discharge_times(self):
        for b in self.batteries:
            for t in self.slot_indices:
                if self.instance.is_office_hour(t):
                    self.X_VAR[b, t].ub = 0
                else:
                    self.Y_VAR[b, t].ub = 0

    def use_restricted_activity_starts(self):
        for a, t in self.Z_VAR:
            if t % 2 == 1:
                self.Z_VAR[a, t].ub = 0

    def undo_restricted_activity_starts(self):
        for a, t in self.Z_VAR:
            if t % 2 == 1:
                self.Z_VAR[a, t].ub = 1

    def use_double_bubble_slots(self):
        self.use_restricted_activity_starts()
        max_t = len(self.slot_indices)
        for b in self.batteries:
            for t in self.slot_indices:
                if t % 2 == 0 and t + 1 < max_t:
                    x_const = self.model.addLConstr(
                        self.X_VAR[b, t] == self.X_VAR[b, t + 1]
                    )
                    y_const = self.model.addLConstr(
                        self.Y_VAR[b, t] == self.Y_VAR[b, t + 1]
                    )
                    self.temporary_constraints.append(x_const)
                    self.temporary_constraints.append(y_const)

    def undo_double_bubble_slots(self):
        self.undo_restricted_activity_starts()
        self.model.remove(self.temporary_constraints)
        self.temporary_constraints.clear()

    def fix_activities(self, flexible=False):
        related_vars = {}
        width = 1
        for (a, t), var in self.Z_VAR.items():
            if var.x > 0.1:
                related_vars[a, t] = var
            if self.W_VAR[a].x > 0.1:
                var.ub = 0
        for (a, t), var in related_vars.items():
            self.W_VAR[a].lb = 1
            if flexible:
                for tp in range(t - width, t + width + 1):
                    if (a, tp) in self.Z_VAR:
                        self.Z_VAR[a, tp].ub = 1
            else:
                var.lb = 1
                var.ub = 1

    def use_continuous_battery_variables(self):
        for idx in self.X_VAR:
            self.X_VAR[idx].VType = GRB.CONTINUOUS
            self.Y_VAR[idx].VType = GRB.CONTINUOUS

    def use_binary_battery_variables(self):
        for idx in self.X_VAR:
            self.X_VAR[idx].VType = GRB.BINARY
            self.Y_VAR[idx].VType = GRB.BINARY
