from datetime import timedelta, datetime as dt
from Setting import Setting

#########################################################################
#########################################################################
#########################################################################


def get_datetime(date: str):
    date_time = dt.strptime(date.replace(" ", "").replace("-", "_"), "%y_%m_%d")
    return date_time.replace(hour=0, minute=0, second=0, microsecond=0)


def _get_all_slots(start_date: str, end_date: str, slot_minutes: int):
    start_dt = get_datetime(start_date)
    end_dt = get_datetime(end_date)
    one_day = timedelta(days=1)
    slots = []
    d = 0
    date = start_dt
    while date <= end_dt:
        t = 0
        while t + slot_minutes <= 1440:
            hour_a = t // 60
            minute_a = t % 60
            hour_b = (t + slot_minutes - 1) // 60
            minute_b = (t + slot_minutes - 1) % 60
            a = date.replace(hour=hour_a, minute=minute_a)
            b = date.replace(
                hour=hour_b, minute=minute_b, second=59, microsecond=999999
            )
            slot = Slot(d, t // slot_minutes, Interval(a, b))
            slots.append(slot)
            t += slot_minutes
        date += one_day
        d += 1
    return slots


#########################################################################
class Interval:
    def __init__(self, a, b) -> None:
        self.a = a
        self.b = b

    def overlaps(self, other):
        return (not (self.a > other.b)) and (not (other.a > self.b))


#########################################################################
class Slot:
    def __init__(self, day, index, interval) -> None:
        self.day = day
        self.index = index
        self.interval = interval


#########################################################################
class Time:
    def __init__(self, setting: Setting) -> None:
        self.slot_minutes = setting.slot_minutes
        self.slots = _get_all_slots(
            setting.start_date, setting.end_date, setting.slot_minutes
        )
        self.planning_horizon = range(len(self.slots))
        self.slots_per_hour = 60 // self.slot_minutes
        self.slots_per_day = 24 * self.slots_per_hour
        self.slots_per_week = 7 * self.slots_per_day
        self.utc_offset = 11 * self.slots_per_hour if setting.use_utc_time else 0

    def slot_of(self, dt_time):
        return self.slots[self.index_of(dt_time)]

    def index_of(self, dt_time):
        interval = Interval(dt_time, dt_time)
        for t in self.planning_horizon:
            if interval.overlaps(self.slots[t].interval):
                return t
        return -1


#########################################################################
#########################################################################
#########################################################################
