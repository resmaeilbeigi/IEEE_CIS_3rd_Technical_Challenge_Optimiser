from collections import OrderedDict, defaultdict
import gurobipy as gp
from gurobipy import GRB
from Optimizer import Optimizer
import Util


class Solution:
    def __init__(self, optimizer: Optimizer):
        self.optimizer = optimizer
        self.x = [
            (b, t)
            for b in optimizer.batteries
            for t in optimizer.slot_indices
            if optimizer.X_VAR[b, t].x >= 0.5
        ]
        self.y = [
            (b, t)
            for b in optimizer.batteries
            for t in optimizer.slot_indices
            if optimizer.Y_VAR[b, t].x >= 0.5
        ]
        self.z = [
            (a, t)
            for a in optimizer.activities
            for t in optimizer.activities[a].start_times
            if optimizer.Z_VAR[a, t].x >= 0.5
        ]
        self.vvar = [
            (a, t)
            for a in optimizer.activities
            for t in optimizer.activities[a].progress_times
            if optimizer.V_VAR[a, t].x >= 0.5
        ]
        self.w = [a for a in optimizer.activities if optimizer.W_VAR[a].x >= 0.5]
        self.u = [a for a in optimizer.activities_o if optimizer.U_VAR[a].x >= 0.5]
        self.o = list(set(self.w).intersection(optimizer.activities_o))
        self.l = [
            [optimizer.L_VAR[t, s].x for s in optimizer.scenarios]
            for t in optimizer.slot_indices
        ]
        self.eta_var = [optimizer.ETA_VAR[s].x for s in optimizer.scenarios]
        self.instance = optimizer.instance
        self.min_load = [
            min(self.l[t][s] for t in optimizer.slot_indices)
            for s in optimizer.scenarios
        ]
        self.max_load = [
            max(self.l[t][s] for t in optimizer.slot_indices)
            for s in optimizer.scenarios
        ]
        self.max_abs_load = [
            max(abs(self.min_load[s]), abs(self.max_load[s]))
            for s in optimizer.scenarios
        ]
        self.enforced_load_ub = self.instance.max_load_ub
        self.linearized_obj = optimizer.model.objVal
        self.actual_obj = 0
        self.sched_count_r = len(self.w) - len(self.o)
        self.sched_count_o = len(self.o)

        for a in self.u:
            self.actual_obj += self.instance.activities[a].penalty
        for a in self.o:
            self.actual_obj -= self.instance.activities[a].revenue

        self.scenario_objectives = [self.actual_obj for s in optimizer.scenarios]

        for s in optimizer.scenarios:
            for t in self.instance.planning_horizon:
                price_cost = (
                    self.l[t][s]
                    * self.instance.scenarios[s].price[t]
                    / (self.instance.time.slots_per_hour * 1000)
                )
                self.actual_obj += price_cost / len(self.instance.scenarios)
                self.scenario_objectives[s] += price_cost

        for s in optimizer.scenarios:
            max_load_cost = 0.005 * self.max_abs_load[s] * self.max_abs_load[s]
            self.actual_obj += max_load_cost / len(self.instance.scenarios)
            self.scenario_objectives[s] += max_load_cost

        if optimizer.instance.setting.solver.fixsol:
            return

        self.m, a_b_m = self.get_building_allocation()

        self.variables = []
        self.variables.append(
            f'Scenarios: {" ".join(s.name for s in self.instance.scenarios)}'
        )
        self.variables.append(f"actual_obj {self.actual_obj}")
        self.variables.append(f"linearized_obj {self.linearized_obj}")
        self.variables.append(f"min_load {' '.join(str(val) for val in self.min_load)}")
        self.variables.append(f"max_load {' '.join(str(val) for val in self.max_load)}")
        self.variables.append(f"eta_var {' '.join(str(val) for val in self.eta_var)}")
        self.variables.append(f"enforced_load_ub {self.enforced_load_ub}")
        self.variables.append(f"sched_count_r {self.sched_count_r}")
        self.variables.append(f"sched_count_o {self.sched_count_o}")
        self.variables.extend(f"abm {key[0]} {key[1]} {a_b_m[key]}" for key in a_b_m)
        self.variables.extend(f"w {i}" for i, v in enumerate(self.w) if v >= 0.5)
        self.variables.extend(f"u {i}" for i, v in enumerate(self.u) if v >= 0.5)
        self.variables.extend(f"z {v[0]} {v[1]}" for v in self.z)
        self.variables.extend(f"v {v[0]} {v[1]}" for v in self.vvar)
        self.variables.extend(f"x {v[0]} {v[1]}" for v in self.x)
        self.variables.extend(f"y {v[0]} {v[1]}" for v in self.y)

    def csv_header(self, filepath):
        writer = Util.Writer(filepath, sep=",")
        fields = ["KEY"]
        fields.extend(
            s.name.replace("_submission", "") for s in self.instance.scenarios
        )
        writer.pretty_out(fields, len(fields))

    def add2csv(self, filepath):
        writer = Util.Writer(filepath, sep=",", empty=False)
        values = [self.instance.name]
        values.extend(self.scenario_objectives)
        writer.pretty_out(values, len(values))

    def export_variables(self):
        if self.optimizer.instance.setting.solver.fixsol:
            return
        file_path = Util.joinpath(
            self.instance.folder, f"variables_{self.optimizer.solve_count}.txt"
        )
        writer = Util.Writer(file_path, sep=", ")
        writer.pretty_out(self.variables, max_words=1)

    def get_start_time(self, a):
        for key in self.z:
            if key[0] == a:
                return key[1]
        return -1

    def export_ppoi(self, folder=None, tag=True):
        if self.optimizer.instance.setting.solver.fixsol:
            return
        tag = f"_{self.optimizer.solve_count}" if tag else ""
        file_name = self.instance.name.replace("instance", "instance_solution")
        if not folder:
            folder = self.instance.folder
        else:
            Util.mkdir(folder)
        file_path = Util.joinpath(folder, file_name + f"{tag}.txt")
        ppoi = f"ppoi {len(self.instance.buildings)} {len(self.instance.buildings)} {len(self.instance.batteries)} {len(self.instance.activities_r)} {len(self.instance.activities_o)}"
        sched = f"sched {self.sched_count_r} {self.sched_count_o}"
        writer = Util.Writer(file_path)
        writer.outln(ppoi)
        writer.outln(sched)
        for a in self.optimizer.activities_r:
            line = f"r {self.instance.activities[a].key} {self.get_start_time(a)} {self.instance.activities[a].small_rooms + self.instance.activities[a].large_rooms}"
            for b in self.m[a]:
                line += f" {b}"
            writer.outln(line)
        for a in self.o:
            line = f"a {self.instance.activities[a].key} {self.get_start_time(a)} {self.instance.activities[a].small_rooms + self.instance.activities[a].large_rooms}"
            for b in self.m[a]:
                line += f" {b}"
            writer.outln(line)
        for b in self.optimizer.batteries:
            for t in self.optimizer.slot_indices:
                if self.optimizer.X_VAR[b, t].x >= 0.5:
                    writer.outln(f"c {self.instance.batteries[b].key} {t} {0}")
                elif self.optimizer.Y_VAR[b, t].x >= 0.5:
                    writer.outln(f"c {self.instance.batteries[b].key} {t} {2}")

    def export(self):
        self.export_variables()
        self.export_ppoi()
        self.export_ppoi(
            Util.joinpath(
                self.optimizer.setting.startsol_dir, f"{self.optimizer.solve_count}",
            ),
            tag=False,
        )

    def get_building_allocation(self):
        model = gp.Model()
        M_VAR = model.addVars(
            ((a, b) for a in self.w for b in self.instance.buildings),
            name="M",
            vtype=GRB.INTEGER,
        )

        model.addConstrs(
            (
                (
                    gp.quicksum(
                        M_VAR[a, b] * self.optimizer.V_VAR[a, t].x
                        for a in self.o
                        if self.instance.activities[a].small_rooms >= 1
                        and t in self.instance.activities[a].progress_times
                    )
                    + gp.quicksum(
                        M_VAR[a, b]
                        * self.optimizer.V_VAR[a, self.optimizer.map_time(t)].x
                        for a in self.optimizer.activities_r
                        if self.instance.activities[a].small_rooms >= 1
                        and self.optimizer.map_time(t)
                        in self.instance.activities[a].progress_times
                    )
                    <= b.small_rooms
                )
                for b in self.instance.buildings
                for t in self.optimizer.slot_indices
            ),
            name="C1",
        )

        model.addConstrs(
            (
                (
                    gp.quicksum(
                        M_VAR[a, b] * self.optimizer.V_VAR[a, t].x
                        for a in self.o
                        if self.instance.activities[a].large_rooms >= 1
                        and t in self.instance.activities[a].progress_times
                    )
                    + gp.quicksum(
                        M_VAR[a, b]
                        * self.optimizer.V_VAR[a, self.optimizer.map_time(t)].x
                        for a in self.optimizer.activities_r
                        if self.instance.activities[a].large_rooms >= 1
                        and self.optimizer.map_time(t)
                        in self.instance.activities[a].progress_times
                    )
                    <= b.large_rooms
                )
                for b in self.instance.buildings
                for t in self.optimizer.slot_indices
            ),
            name="C2",
        )

        model.addConstrs(
            (
                (
                    M_VAR.sum(a, "*")
                    == self.instance.activities[a].small_rooms
                    + self.instance.activities[a].large_rooms
                )
                for a in self.w
            ),
            name="C3",
        )

        model.update()
        # lp_file = Util.joinpath(self.instance.folder, "build_allo_model.lp")
        # Util.empty_file(lp_file)
        # model.write(lp_file)
        model.optimize()
        STATUS = model.getAttr(GRB.Attr.Status)
        # https://www.gurobi.com/documentation/9.1/refman/optimization_status_codes.html
        if model.getAttr(GRB.Attr.SolCount) == 0:
            if STATUS == 3:
                model.computeIIS()
                model.write(self.instance.folder + "conflict.ilp")

        a_b_m = OrderedDict()  # note: this is building key
        m = defaultdict(list)
        for a, b in M_VAR:
            if (count := int(M_VAR[a, b].x)) >= 0.5:
                a_b_m[(a, b.key)] = count
                m[a].extend(b.key for i in range(count))
        return m, a_b_m

