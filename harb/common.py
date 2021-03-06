from __future__ import print_function, division

import re
import logging
import datetime


TO_BE_PLACED = 'TO BE PLACED'

SELECTION_BLACK_LIST = [
    'yes',
    'no',
    'lengths inclusive',
    'any other individual jockey',
    'winners'
]


get_first = lambda x: x.iget(0)


def extract_horse_name(s):
    pos = re.search('[A-Za-z]', s)
    if pos is None:
        return None
    else:
        name = s[pos.start():].strip().lower()
        if any(map(lambda x: x == name, SELECTION_BLACK_LIST)):
            return None
        return name


class MongoLoggingHandler(logging.Handler):
    def __init__(self, coll):
        super(MongoLoggingHandler, self).__init__()
        self.coll = coll
        self.logger_id = coll.find_and_modify({'last_logger_id': {'$exists': True}},
                                              update={'$inc': {'last_logger_id': 1}})
        if self.logger_id is None:
            coll.insert({'last_logger_id': 0})
            self.logger_id = 0
        else:
            self.logger_id = self.logger_id['last_logger_id']

    def emit(self, record):
        self.coll.insert({'logger_id': self.logger_id,
                          'msg': record.msg,
                          'levelname': record.levelname,
                          'levelno': record.levelno,
                          'name': record.name,
                          'process': record.process,
                          'processname': record.processName,
                          'created': record.created}, w=0)


def configure_root_logger(to_stdout=True, file_out=None, coll_out=None, level=logging.DEBUG, formatter=None):
    logger = logging.getLogger()
    logger.handlers = []
    logger.setLevel(level)
    # create console handler and set level to debug
    if formatter is None:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    if file_out is not None:
        file_log = logging.FileHandler(file_out, mode='a')
        file_log.setLevel(level)
        file_log.setFormatter(formatter)
        logger.addHandler(file_log)
    if coll_out is not None:
        coll_log = MongoLoggingHandler(coll_out)
        coll_log.setLevel(level)
        coll_log.setFormatter(formatter)
        logger.addHandler(coll_log)
    if to_stdout:
        stdout_log = logging.StreamHandler()
        stdout_log.setLevel(level)
        stdout_log.setFormatter(formatter)
        logger.addHandler(stdout_log)
    return logger


def update_root_logger_formatters(formatter):
    for h in logging.getLogger().handlers:
        h.setFormatter(formatter)


def convert_types(dicts, mappers=None):
    if mappers is None:
        mappers = {}

    def map_it(d):
        for (m, f) in mappers.items():
            if m in d:
                d[m] = f(d[m])
        return d

    return (map_it(d) for d in dicts)


def pandas_to_dicts(df, mappers=None):
    if mappers is None:
        mappers = {}
    dicts = (df.ix[i].to_dict() for i in df.index)
    if len(mappers) == 0:
        return dicts
    else:
        return convert_types(dicts, mappers)


def to_json(x):
    if isinstance(x, datetime.date) or isinstance(x, datetime.datetime):
        return x.isoformat()
    else:
        repr_json = getattr(x, "__repr_json__", None)
        if repr_json:
            return repr_json()
        else:
            return dict((k, v) for k, v in x.__dict__.iteritems() if not k.startswith("_"))
