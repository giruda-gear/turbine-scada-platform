from uuid import UUID

from fastapi import APIRouter, HTTPException

from scada_api.dependencies import SessionDep
from scada_api.turbines import service
from scada_api.turbines.schema import TurbineResponse

router = APIRouter(prefix="/turbines", tags=["turbines"])


@router.get(
    "/{turbine_id}",
    response_model=TurbineResponse,
)
def get_turbine(turbine_id: UUID, session: SessionDep):
    turbine = service.get_turbine(session, turbine_id=turbine_id)
    if turbine is None:
        raise HTTPException(
            status_code=404,
            detail="Turbine not found",
        )
    return turbine
