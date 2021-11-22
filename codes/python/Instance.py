from collections import OrderedDict
from datetime import timedelta, datetime as dt
from enum import Enum
from Time import Time
from Setting import Setting
import Util


class Type(Enum):
    O = "once-off"
    R = "recurring"


class Activity:
    def __init__(self, key):
        self.key = key
        self.type = Type.R
        self.start_times = []
        self.progress_times = []
        self.penalty_times = []
        self.prerequisites = []
        self.revenue = 0
        self.penalty = 0
        self.duration = 0
        self.small_rooms = 0
        self.large_rooms = 0
        self.load_per_room = 0


class Battery:
    def __init__(self, key):
        self.key = key
        self.building = 0
        self.capacity = 0
        self.initial_state = 0
        self.max_power = 0
        self.efficiency = 0


class Building:
    def __init__(self, key):
        self.key = key
        self.small_rooms = 0
        self.large_rooms = 0
        self.solar_id = 0


class Scenario:
    def __init__(self, planning_horizon, name):
        self.name = name
        self.price = [None for t in planning_horizon]
        self.base_load = [0 for t in planning_horizon]
        self.solar_load = [0 for t in planning_horizon]


class Instance:
    def __init__(self, name: str, setting: Setting):
        self.name = name
        self.folder = Util.joinpath(setting.output_dir, name)
        Util.mkdir(self.folder)
        self.setting = setting
        self.time = Time(setting)
        self.planning_horizon = self.time.planning_horizon
        self.large_room_count = 0
        self.small_room_count = 0
        self.scenarios = []
        self.activities: list[Activity] = []
        self.activities_r: list[Activity] = []
        self.activities_o: list[Activity] = []
        self.batteries = []
        self.buildings = []
        self._max_load_ub = None
        self.first_monday_slot = None
        self.sol_battery_bt_mode = OrderedDict()
        self.sol_activity_start = OrderedDict()

    def get_activity_duration_stat(self):
        return Util.Stat([a.duration for a in self.activities])

    @property
    def max_load_ub(self):
        if self._max_load_ub:
            return self._max_load_ub
        max_small_room_load = 0
        max_large_room_load = 0
        for a in self.activities:
            if a.large_rooms > 0:
                max_large_room_load = max(max_large_room_load, a.load_per_room)
            else:
                max_small_room_load = max(max_small_room_load, a.load_per_room)
        max_load = (
            self.small_room_count * max_small_room_load
            + self.large_room_count * max_large_room_load
        )
        for s in self.scenarios:
            max_load += max(
                s.base_load[t] - s.solar_load[t] for t in self.planning_horizon
            ) / len(self.scenarios)
        return int(max_load / 2)

    def is_office_hour(self, t):
        slot = self.time.slots[t]
        AEDT = slot.interval.a
        if self.setting.use_utc_time:
            AEDT += timedelta(hours=11)
        return AEDT.hour < 17 and AEDT.hour >= 9 and AEDT.weekday() < 5

    def set_activity_times(self):
        def _first_monday(year, month):
            d = dt(year, month, 7)
            offset = -d.weekday()  # weekday=0 => monday
            return d + timedelta(offset)

        # we currently do not exclude public holidays
        first_timeslot = self.time.slots[0].interval.a
        first_monday = _first_monday(first_timeslot.year, first_timeslot.month)
        first_friday = first_monday + timedelta(days=4)
        self.first_monday_slot = self.time.index_of(first_monday) - self.time.utc_offset
        monday_9am = (
            self.time.index_of(first_monday.replace(hour=9)) - self.time.utc_offset
        )
        friday_5pm = (
            self.time.index_of(first_friday.replace(hour=17)) - self.time.utc_offset
        )

        progress_times_r = [
            t for t in range(monday_9am, friday_5pm) if self.is_office_hour(t)
        ]

        for a in self.activities_r:
            a.progress_times = progress_times_r
            a.start_times = [
                t for t in progress_times_r if self.is_office_hour(t + a.duration - 1)
            ]

        progress_times_o = [t for t in self.planning_horizon]
        progress_times_o_office = [
            t for t in self.planning_horizon if self.is_office_hour(t)
        ]
        for a in self.activities_o:
            a.progress_times = (
                progress_times_o_office if a.revenue <= a.penalty else progress_times_o
            )
            a.start_times = (
                [
                    t
                    for t in a.progress_times
                    if t + a.duration <= len(self.planning_horizon)
                    and self.is_office_hour(t + a.duration - 1)
                ]
                if a.revenue <= a.penalty
                else [
                    t
                    for t in a.progress_times
                    if t + a.duration <= len(self.planning_horizon)
                ]
            )
            a.penalty_times = (
                []
                if a.revenue <= a.penalty
                else [
                    t
                    for t in a.start_times
                    if (not self.is_office_hour(t))
                    or (not self.is_office_hour(t + a.duration - 1))
                    or (a.duration > 8 * self.time.slots_per_hour)
                ]
            )

    def load_real_data(self, scenario_dir):
        exclude_outliers = True
        real_load_file = [f for f in scenario_dir if "All_data.csv" in f][0]
        price_files = [f for f in scenario_dir if "PRICE_AND_DEMAND" in f]
        valid_buildings = [b.key for b in self.buildings]
        valid_solars = [b.solar_id for b in self.buildings]
        with open(real_load_file, "r") as file:
            load_lines = file.readlines()
        t = 0
        for l in load_lines:
            line = l.split(",")
            key = int(Util.rx.findall(line[1])[0])
            load = Util.rx.findall(line[3])
            load = float(load[0]) if load else 0
            if exclude_outliers:
                load = load if load < 1700 else 144
            if "Building" in l and key in valid_buildings:
                self.scenarios[0].base_load[t % len(self.time.slots)] += load
            if "Solar" in l and key in valid_solars:
                self.scenarios[0].solar_load[t % len(self.time.slots)] += load
            t += 1
        with open(price_files[0], "r") as file:
            price_lines = file.readlines()
        # assuming 15 minute time slots:
        index = 0
        for l in price_lines[1:]:
            line = l.split(",")
            pr = float(line[3])
            self.scenarios[0].price[index] = pr
            self.scenarios[0].price[index + 1] = pr
            index += 2

    def load_scenario(self, scenario_dir):
        if self.setting.use_real_data:
            self.scenarios = [Scenario(self.planning_horizon, "real_data")]
            self.load_real_data(scenario_dir)
            return
        price_files = [f for f in scenario_dir if "PRICE_AND_DEMAND" in f]
        load_files = [f for f in scenario_dir if "submission" in f]
        if not self.setting.use_multiple_scenarios:
            load_files = [load_files[0]]
        self.scenarios = [
            Scenario(self.planning_horizon, Util.getNameFromPath(l)) for l in load_files
        ]
        valid_buildings = [b.key for b in self.buildings]
        valid_solars = [b.solar_id for b in self.buildings]
        with open(price_files[0], "r") as file:
            price_lines = file.readlines()
        for i, load_file in enumerate(load_files):
            with open(load_file, "r") as file:
                load_lines = file.readlines()
            for l in load_lines:
                line = l.split(",")
                key = int(Util.rx.findall(line[0])[0])
                if "Building" in l and key in valid_buildings:
                    for t, s in enumerate(line[1:]):
                        self.scenarios[i].base_load[t] += float(s)
                if "Solar" in l and key in valid_solars:
                    for t, s in enumerate(line[1:]):
                        self.scenarios[i].solar_load[t] += float(s)
            # assuming 15 minute time slots:
            index = 0
            for l in price_lines[1:]:
                line = l.split(",")
                pr = float(line[3])
                self.scenarios[i].price[index] = pr
                self.scenarios[i].price[index + 1] = pr
                index += 2

    def load_ppoi(self, file_path: str):
        with open(file_path, "r") as file:
            lines = file.readlines()
        header = Util.rx.findall(lines[0])
        building_count = int(header[0])
        # solar_count = int(header[1])
        battery_count = int(header[2])
        recurring_count = int(header[3])
        onceoff_count = int(header[4])
        for l in lines[1:]:
            line = [float(i) for i in Util.rx.findall(l)]
            entity = l[0]
            if entity == "s":
                continue
            elif entity == "b":
                building = Building(int(line[0]))
                building.small_rooms = int(line[1])
                building.large_rooms = int(line[2])
                building.solar_id = building.key
                self.buildings.append(building)
                self.small_room_count += building.small_rooms
                self.large_room_count += building.large_rooms
            elif entity == "c":
                battery = Battery(int(line[0]))
                battery.building = int(line[1])
                battery.capacity = line[2]
                battery.initial_state = battery.capacity
                battery.max_power = line[3]
                battery.efficiency = line[4]
                self.batteries.append(battery)
            elif entity == "r":
                activity = Activity(int(line[0]))
                activity.type = Type.R
                if "S" in l:
                    activity.small_rooms = int(line[1])
                else:
                    activity.large_rooms = int(line[1])
                activity.load_per_room = line[2]
                activity.duration = int(line[3])
                for p in range(5, 5 + int(line[4])):
                    activity.prerequisites.append(int(line[p]))
                self.activities.append(activity)
                self.activities_r.append(activity)
            elif entity == "a":
                activity = Activity(int(line[0]))
                activity.type = Type.O
                if "S" in l:
                    activity.small_rooms = int(line[1])
                else:
                    activity.large_rooms = int(line[1])
                activity.load_per_room = line[2]
                activity.duration = int(line[3])
                activity.revenue = line[4]
                activity.penalty = line[5]
                for p in range(7, 7 + int(line[6])):
                    activity.prerequisites.append(int(line[p]) + recurring_count)
                self.activities.append(activity)
                self.activities_o.append(activity)
        if len(self.buildings) != building_count:
            raise "BuildingCountError!"
        if len(self.batteries) != battery_count:
            raise "BatteryCountError!"
        if len(self.activities) != recurring_count + onceoff_count:
            raise "ActivityCountError!"
        for i, a in enumerate(self.activities_r):
            if a.key != i:
                raise "ActivityKeyError!"
        for i, a in enumerate(self.activities_o):
            if a.key != i:
                raise "ActivityKeyError!"
        # for i, b in enumerate(self.buildings):
        #     if b.key != i:
        #         raise "BuildingKeyError!"
        for i, b in enumerate(self.batteries):
            if b.key != i:
                raise "BuildingKeyError!"

    def load_start_solution(self, file_path: str):
        if not Util.exists(file_path):
            if self.setting.solver.fixsol or self.setting.solver.setstart:
                raise "NoStartsolFolder"
            else:
                return
        with open(file_path, "r") as file:
            lines = file.readlines()
        header = Util.rx.findall(lines[0])
        recurring_count = int(header[3])
        for l in lines[1:]:
            line = Util.rx.findall(l)
            entity = l[0]
            if entity in "sb":
                continue
            elif entity == "r":
                self.sol_activity_start[int(line[0])] = int(line[1])
            elif entity == "a":
                self.sol_activity_start[int(line[0]) + recurring_count] = int(line[1])
            elif entity == "c":
                self.sol_battery_bt_mode[(int(line[0]), int(line[1]))] = int(line[2])

