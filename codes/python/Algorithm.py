import timeit
from gurobipy import GRB
from Optimizer import Optimizer
from Solution import Solution
from Instance import Instance
import Util


class Algorithm:
    def __init__(self, instance: Instance) -> None:
        self.instance = instance
        self.setting = instance.setting
        self.start_time = timeit.default_timer()
        self.time_limit = self.setting.solver.runtime

    def _elapsed(self):
        return timeit.default_timer() - self.start_time

    def run(self):
        if self.setting.algorithm == 0:
            optimizer = Optimizer(self.instance)
            optimizer.formulate()
            summary = optimizer.solve()
            solution = Solution(optimizer)
            solution.export()
            return summary, solution
        if self.setting.algorithm == 1:
            optimizer = Optimizer(self.instance)
            optimizer.formulate()
            optimizer.exclude_penalized_activities()
            optimizer.use_double_bubble_slots()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.5 * self.time_limit)
            summary = optimizer.solve()
            Solution(optimizer).export()
            optimizer.undo_double_bubble_slots()
            optimizer.include_penalized_activities()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.5 * self.time_limit)
            summary = optimizer.solve()
            solution = Solution(optimizer)
            solution.export()
            return summary, solution
        if self.setting.algorithm == 2:
            optimizer = Optimizer(self.instance)
            optimizer.formulate()
            optimizer.exclude_penalized_activities()
            optimizer.exclude_batteries()
            optimizer.use_double_bubble_slots()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.5 * self.time_limit)
            summary = optimizer.solve()
            Solution(optimizer).export()
            optimizer.undo_double_bubble_slots()
            optimizer.include_penalized_activities()
            optimizer.include_batteries()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.5 * self.time_limit)
            summary = optimizer.solve()
            solution = Solution(optimizer)
            solution.export()
            return summary, solution
        if self.setting.algorithm == 3:
            optimizer = Optimizer(self.instance)
            optimizer.formulate()
            optimizer.exclude_penalized_activities()
            optimizer.restrict_charge_discharge_times()
            optimizer.use_double_bubble_slots()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.5 * self.time_limit)
            summary = optimizer.solve()
            Solution(optimizer).export()
            optimizer.undo_double_bubble_slots()
            optimizer.include_penalized_activities()
            optimizer.include_batteries()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.5 * self.time_limit)
            summary = optimizer.solve()
            solution = Solution(optimizer)
            solution.export()
            return summary, solution
        if self.setting.algorithm == 4:
            optimizer = Optimizer(self.instance)
            optimizer.formulate()
            optimizer.exclude_batteries()
            optimizer.use_double_bubble_slots()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.5 * self.time_limit)
            summary = optimizer.solve()
            Solution(optimizer).export()
            optimizer.undo_double_bubble_slots()
            optimizer.include_batteries()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.5 * self.time_limit)
            summary = optimizer.solve()
            solution = Solution(optimizer)
            solution.export()
            return summary, solution
        if self.setting.algorithm == 5:
            optimizer = Optimizer(self.instance)
            optimizer.formulate()
            optimizer.restrict_charge_discharge_times()
            optimizer.use_double_bubble_slots()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.5 * self.time_limit)
            summary = optimizer.solve()
            Solution(optimizer).export()
            optimizer.undo_double_bubble_slots()
            optimizer.include_batteries()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.5 * self.time_limit)
            summary = optimizer.solve()
            solution = Solution(optimizer)
            solution.export()
            return summary, solution

        if self.setting.algorithm == 6:
            optimizer = Optimizer(self.instance)
            optimizer.formulate()
            optimizer.exclude_batteries()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.5 * self.time_limit)
            summary = optimizer.solve()
            Solution(optimizer).export()
            optimizer.fix_activities()
            optimizer.include_batteries()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.5 * self.time_limit)
            summary = optimizer.solve()
            solution = Solution(optimizer)
            solution.export()
            return summary, solution

        if self.setting.algorithm == 7:
            optimizer = Optimizer(self.instance)
            optimizer.formulate()
            optimizer.use_continuous_battery_variables()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.9 * self.time_limit)
            summary = optimizer.solve()
            Solution(optimizer).export()
            optimizer.use_binary_battery_variables()
            optimizer.fix_activities()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.1 * self.time_limit)
            summary = optimizer.solve()
            solution = Solution(optimizer)
            solution.export()
            return summary, solution

        if self.setting.algorithm == 8:
            optimizer = Optimizer(self.instance)
            optimizer.formulate()
            optimizer.use_continuous_battery_variables()
            optimizer.use_restricted_activity_starts()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.9 * self.time_limit)
            summary = optimizer.solve()
            Solution(optimizer).export()
            optimizer.use_binary_battery_variables()
            optimizer.fix_activities()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.1 * self.time_limit)
            summary = optimizer.solve()
            solution = Solution(optimizer)
            solution.export()
            return summary, solution

        if self.setting.algorithm == 9:
            optimizer = Optimizer(self.instance)
            optimizer.formulate()
            optimizer.exclude_penalized_activities()
            optimizer.use_continuous_battery_variables()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.9 * self.time_limit)
            summary = optimizer.solve()
            Solution(optimizer).export()
            optimizer.include_penalized_activities()
            optimizer.use_binary_battery_variables()
            optimizer.fix_activities()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.1 * self.time_limit)
            summary = optimizer.solve()
            solution = Solution(optimizer)
            solution.export()
            return summary, solution

        if self.setting.algorithm == 10:
            optimizer = Optimizer(self.instance)
            optimizer.formulate()
            optimizer.exclude_penalized_activities()
            optimizer.exclude_batteries()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.9 * self.time_limit)
            summary = optimizer.solve()
            Solution(optimizer).export()
            optimizer.include_penalized_activities()
            optimizer.include_batteries()
            optimizer.fix_activities()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.1 * self.time_limit)
            summary = optimizer.solve()
            solution = Solution(optimizer)
            solution.export()
            return summary, solution

        if self.setting.algorithm == 11:
            optimizer = Optimizer(self.instance)
            optimizer.formulate()
            optimizer.exclude_penalized_activities()
            optimizer.use_continuous_battery_variables()
            optimizer.use_restricted_activity_starts()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.7 * self.time_limit)
            summary = optimizer.solve()
            Solution(optimizer).export()
            optimizer.undo_restricted_activity_starts()
            optimizer.include_penalized_activities()
            optimizer.use_binary_battery_variables()
            optimizer.fix_activities(flexible=True)
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.3 * self.time_limit)
            summary = optimizer.solve()
            solution = Solution(optimizer)
            solution.export()
            return summary, solution

        if self.setting.algorithm == 12:
            optimizer = Optimizer(self.instance)
            optimizer.formulate()
            optimizer.exclude_penalized_activities()
            optimizer.exclude_batteries()
            optimizer.use_restricted_activity_starts()
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.7 * self.time_limit)
            summary = optimizer.solve()
            Solution(optimizer).export()
            optimizer.undo_restricted_activity_starts()
            optimizer.include_penalized_activities()
            optimizer.include_batteries()
            optimizer.fix_activities(flexible=True)
            optimizer.model.setParam(GRB.Param.TimeLimit, 0.3 * self.time_limit)
            summary = optimizer.solve()
            solution = Solution(optimizer)
            solution.export()
            return summary, solution

