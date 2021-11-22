from collections import OrderedDict
from Instance import Instance
import Util
from Setting import Setting


class Data:
    def __init__(self, setting: Setting):
        self.setting = setting
        self.datasets = OrderedDict()
        self.scenarios = OrderedDict()
        for key in setting.dataset_keys:
            instance_dir = Util.joinpath(setting.input_dir, key + "_instances")
            scenario_dir = Util.joinpath(setting.input_dir, key + "_scenarios")
            self.datasets[key] = Util.getFileList(instance_dir)
            self.scenarios[key] = Util.getFileList(scenario_dir)

    def get_instances(self, key):
        return (
            self.get_instance(file_path, self.scenarios[key])
            for file_path in self.datasets[key]
        )

    def get_instance_by_index(self, key, index):
        return self.get_instance(self.datasets[key][index], self.scenarios[key])

    def get_instance(self, file_path: str, scenario_dir: str):
        name = Util.getNameFromPath(file_path)
        instance = Instance(name, self.setting)
        instance.load_ppoi(file_path)
        instance.load_scenario(scenario_dir)
        instance.set_activity_times()
        sol_name = instance.name.replace("instance", "instance_solution")
        sol_path = Util.joinpath(self.setting.startsol_dir, sol_name + ".txt")
        instance.load_start_solution(sol_path)
        return instance

