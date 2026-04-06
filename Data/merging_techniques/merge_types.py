from enum import Enum

class MergeType(Enum):
    SQUAREBUCKETMERGE = "square"
    DBSCANMERGE = "dbscan"
    DEFAULT = None
    @classmethod
    def _missing_(cls, value):
        return cls.DEFAULT
