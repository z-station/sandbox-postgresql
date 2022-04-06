from typing import Optional, List
from dataclasses import dataclass


@dataclass
class DebugData:

    result: List[List[str]]
    code: Optional[str] = None
    name: Optional[str] = None
    error: Optional[str] = None


@dataclass
class TestData:

    __test__ = False

    data_in: Optional[str] = None
    error: Optional[str] = None
    ok: Optional[bool] = None


@dataclass
class TestsData:

    __test__ = False

    tests: List[TestData]
    num: int = 0
    num_ok: int = 0
    ok: Optional[bool] = None
    code: Optional[str] = None
    name: Optional[str] = None



@dataclass
class TestsData:

    tests: List[TestData]
    num: int = 0
    num_ok: int = 0
    ok: Optional[bool] = None
    code: Optional[str] = None
    name: Optional[str] = None