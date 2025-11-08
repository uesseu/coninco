from datetime import datetime


class LineParser:
    def __init__(self, data):
        self.data = data
        self.cursor = 0

    def __next__(self):
        try:
            next_cursor = self.data.index('\n', self.cursor + 1)
            result = self.data[self.cursor: next_cursor]
            self.cursor = next_cursor
            return result.strip()
        except ValueError:
            raise StopIteration

    def __iter__(self):
        return self


def match_first(text, key):
    return text[:len(key)] == key


class Calender:
    def __init__(self, data):
        self.summary = ''
        self.description = ''
        self.data = data
        d: str
        for d in data:
            if match_first(d, 'DTSTART'):
                self.start_raw = d.split(':')[1]
                self.start = self.parse_date(self.start_raw)
            if match_first(d, 'DTEND'):
                self.end_raw = d.split(':')[1]
                self.end = self.parse_date(self.end_raw)
            if match_first(d, 'SUMMARY'):
                self.summary = d.split(':')[1]
            if match_first(d, 'DESCRIPTION'):
                self.description = d.split(':')[1]

    def parse_date(self, time):
        year, month, day = time[:4], time[4:6], time[6:8]
        hour = time[9:11] if time[9:11] else 0
        minites = time[11:13] if time[11:13] else 0
        return datetime(*(int(d) for d in (year, month, day, hour, minites)))

    def from_now(self):
        return (self.start - datetime.today()).days


class CalenderParser:
    def __init__(self, data: LineParser):
        self.data = data
        while True:
            try:
                if next(self.data) == 'BEGIN:VEVENT':
                    return None
            except StopIteration as er:
                return None

    def __next__(self):
        result = []
        while True:
            tmp = next(self.data)
            if tmp != 'END:VEVENT':
                result.append(tmp)
            else:
                return result

    def __iter__(self):
        return self


def parse_calender(data):
    return CalenderParser(LineParser(data))

