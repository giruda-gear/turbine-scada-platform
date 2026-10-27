from typing import Annotated

from fastapi import Depends

from scada_api.core.database import Session, get_session

SessionDep = Annotated[Session, Depends(get_session)]
