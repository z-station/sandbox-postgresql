from typing import Optional, List
from dataclasses import dataclass
from app.service.enums import SQLCommandType
from app.service.enums import DebugFormat


@dataclass
class DebugData:
    result: str = None
    error: Optional[str] = None
    name: Optional[str] = None
    code: Optional[str] = None
    format: DebugFormat = None


@dataclass
class TestData:
    __test__ = False

    data_in: Optional[str] = None
    error: Optional[str] = None
    ok: Optional[bool] = None


@dataclass
class TestingData:
    __test__ = False

    num: int = 0
    num_ok: int = 0
    tests: List[TestData] = None
    code: Optional[str] = None
    name: Optional[str] = None
    check_code: Optional[str] = None
    request_type: Optional[SQLCommandType] = None


@dataclass
class CreateData:
    name: Optional[str] = None
    filename: Optional[str] = None


@dataclass
class StatusData:
    name: Optional[str] = None
    status: Optional[str] = None
