from typing import AnyStr, Pattern, Optional

from attr import dataclass


@dataclass(frozen=True)
class MappingInfo:
    pattern: Pattern[AnyStr]
    payee: str
    account: str
    tags: [str]
    transfer_to: Optional[str]
