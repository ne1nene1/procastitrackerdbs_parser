import zlib
from ctypes import c_int, c_ushort, c_char, sizeof
from math import floor

import logging

C_CHAR_S = sizeof(c_char)  # 1
C_INT_S = sizeof(c_int)  # 4
C_USHORT_S = sizeof(c_ushort)  # 2

log = logging.getLogger(__name__)
logging.basicConfig(filename='log.log', level=logging.INFO)


class Database(object):
    pts = 0

    def __init__(self, data_buf):
        self.data_buf = data_buf  # == 13, as of June 9 2019
        self.version = self._read_data_get_int(data_buf)
        self.magic = self.__get_magic()  # == 'PTFF' on x85
        self.numtags = self._read_data_get_int(data_buf)
        self.tags = self.__create_tags()
        self.minifilter = self._read_data_get_int(data_buf)
        self.foldlevel = self._read_data_get_int(data_buf)
        self.prefs = self.__create_prefs()
        self.root = Node(self)

        self.root._create_day()
        self.root._create_child()  # this will recursively read child node

        if self.version < 13:
            log.error("database file is in version < 13")
            exit(1)
        if self.magic != "PTFF":
            log.error("not a procastitracker database file")
            exit(1)

    def __get_magic(self):
        magic = self._read_data(self.data_buf, C_INT_S)
        magic = bytes(reversed(magic))  # big -> little endian
        return magic.decode("utf-8")

    def __create_tags(self):
        tags = [[0 for i in range(2)] for j in range(self.numtags)]
        for tag in range(self.numtags):
            tags[tag][0] = self._read_data(
                self.data_buf, 32).decode("utf-8")  # name
            tags[tag][1] = hex(int.from_bytes(
                self._read_data(self.data_buf, C_INT_S)))
        return tags

    def __create_prefs(self):
        prefs = [0]*10
        for pref in range(10):
            prefs[pref] = self._read_data_get_int(self.data_buf)
        return prefs

    def _read_data(self, data_buf, size):
        old_pts = self.pts
        self.pts += size
        try:
            return data_buf[old_pts:self.pts]
        except IndexError:
            log.error("Index Error")
            exit(1)

    def flatten_node_tree(self) -> list:
        """
        flatten data structure
        return a list of lists that is a representation of node's day
        """
        r = []

        def proc_recursively_get_child_until_depth(lnode):
            # if node doesn't have days, return just name of the node
            if not lnode.days:
                name = lnode.name.split('\00')[0]
                r.append(["", "", name, "", "", "", "", "", "", ""])

            # get all days of the node
            for day in lnode.days:
                name = lnode.name.split('\00')[0]
                date = day.day
                times = day.firstminuteused
                tag = self.tags[lnode.tagindex][0].replace("\00", "")
                r.append([date, times, name, tag, day.activeseconds,
                          day.semiidleseconds,
                          day.key, day.lmb, day.rmb, day.scrollwheel])

            for child in lnode.children:
                proc_recursively_get_child_until_depth(child)

        proc_recursively_get_child_until_depth(self.root)
        log.debug("crawled node: %s", r)
        return r

    def _read_data_get_int(self, data_buf) -> int:
        return int.from_bytes(self._read_data(data_buf, C_INT_S), "little")

    # i know there must be a better way to do this
    def _read_data_nulltermstr(self, data_buf) -> bytes:
        old_pts = self.pts
        while data_buf[self.pts] != 0:
            self.pts += 1
        self.pts += 1  # count null too
        # print("Node name", data_buf[old_pts:pts])
        return data_buf[old_pts:self.pts]

    def _read_get_date(self, data_buf):
        old_pts = self.pts
        self.pts += C_USHORT_S
        d = int.from_bytes(data_buf[old_pts:self.pts], "little")
        return d >> 9 & 0x7ff, d >> 5 & 0xf, d & 0x1f


class Node(object):
    def __init__(self, db: Database):
        self.db = db
        self.name = db._read_data_nulltermstr(db.data_buf).decode("utf-8")
        self.tagindex = db._read_data_get_int(db.data_buf)
        self.ishidden = int.from_bytes(db._read_data(db.data_buf, C_CHAR_S))
        self.days = []
        self.children = []

    def _create_day(self):
        self.numberofdays = self.db._read_data_get_int(self.db.data_buf)
        if self.numberofdays != 0:
            for d in range(self.numberofdays):
                self.days.append(Day(self.db))

    def _create_child(self):
        self.numchildren = self.db._read_data_get_int(self.db.data_buf)
        if self.numchildren != 0:
            for c in range(self.numchildren):
                self.children.append(Node(self.db))
                self.children[c]._create_day()
                self.children[c]._create_child()


class Day(object):
    def __init__(self, db: Database):
        self.day = self.__convert_day(
            db._read_get_date(db.data_buf))  # (year, month, date)
        self.firstminuteused = self.__convert_firstminuteused(int.from_bytes(
            db._read_data(db.data_buf, C_USHORT_S), "little"))
        self.activeseconds = self.__convert_second(
            db._read_data_get_int(db.data_buf))
        self.semiidleseconds = self.__convert_second(
            db._read_data_get_int(db.data_buf))
        self.key = db._read_data_get_int(db.data_buf)
        self.lmb = db._read_data_get_int(db.data_buf)
        self.rmb = db._read_data_get_int(db.data_buf)
        self.scrollwheel = db._read_data_get_int(db.data_buf)

    def __convert_day(self, ymd_tuples):
        """
        from tuples of (year, month, day) to isodate of yyyy-mm-dd
        ex. (2025, 1, 1) -> 2025-01-01
        """
        return str(int(ymd_tuples[0])+2000) + "-" + \
            str(f'{ymd_tuples[1]:02}') + "-" + \
            str(f'{ymd_tuples[2]:02}')

    def __convert_firstminuteused(self, m):
        """
        counted from midnight, converted to isotime (HH:mm)
        ex. 1245 -> 20:45:00
        """
        hour = floor(m / 60)
        minute = m % 60
        return str(f'{hour:02}') + ":" + \
            str(f'{minute:02}' + ":00")

    def __convert_second(self, s):
        """
        converted to isotime (HH:mm:ss)
        ex. 6610 -> 01:50:10
        """
        minute = s / 60
        second = s % 60
        hour = floor(minute / 60)
        minute = floor(minute % 60)
        return str(f'{hour:02}') + ":" + \
            str(f'{minute:02}') + ":" + \
            str(f'{second:02}')


def load_db(db_file):
    """
    loading procastitracker database file (db.PT) return a Database object.
    usually in this path
        "%%APPDATA%%/Roaming/procastitrackerdbs/db.PT"
    please refer to procastitracker database's data structure for more detail
    """

    log.debug("database file: %s", db_file)

    with open(db_file, 'rb') as file:
        gzdata = file.read()
        data_buf = zlib.decompress(gzdata, zlib.MAX_WBITS | 16)

    udb = Database(data_buf)
    log.debug("total data length: %s", len(udb.data_buf))
    return udb
