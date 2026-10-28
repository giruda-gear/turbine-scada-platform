from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from scada_api.dependencies import SessionDep
from scada_api.turbines import service
from scada_api.turbines.schema import TurbineCreate, TurbineResponse

router = APIRouter(prefix="/turbines", tags=["turbines"])


@router.post(
    "",
    response_model=TurbineResponse,
    status_code=status.HTTP_201_CREATED,
)
def craete_turbine(data: TurbineCreate, session: SessionDep):
    turbine = service.create_turbine(session, data)

    if turbine is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return turbine


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
