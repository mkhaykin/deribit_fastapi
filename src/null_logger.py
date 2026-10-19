import logging
from types import TracebackType
from typing import Mapping, Optional, Tuple, Type, Union

from typing_extensions import TypeAlias

# блок кода взят непосредственно из Logger
SysExcInfoType: TypeAlias = Union[
    Tuple[Type[BaseException], BaseException, Optional[TracebackType]],
    Tuple[None, None, None],
]
ExcInfoType: TypeAlias = Optional[Union[bool, SysExcInfoType, BaseException]]
ArgsType: TypeAlias = Union[Tuple[object, ...], Mapping[str, object]]


class NullLogger(logging.Logger):
    def _log(
        self,
        level: int,  # noqa: U100
        msg: object,  # noqa: U100
        args: ArgsType,  # noqa: U100
        exc_info: Optional[ExcInfoType] = None,  # noqa: U100
        extra: Optional[Mapping[str, object]] = None,  # noqa: U100
        stack_info: bool = False,  # noqa: U100
        stacklevel: int = 1,  # noqa: U100
    ) -> None:
        pass
