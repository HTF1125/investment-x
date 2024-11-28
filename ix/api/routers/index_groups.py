from typing import List, Dict
from fastapi import APIRouter, HTTPException, status
from ix import db
from .base import get_model_codes

router = APIRouter(prefix="/data/index_groups", tags=["data"])


@router.get(
    "/codes",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
)
def get_index_group_codes():
    """
    Retrieves all index_grop codes.
    """
    try:
        return get_model_codes(model=db.IndexGroup)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching index group codes: {str(e)}",
        )


@router.get(
    "/all",
    response_model=Dict[str, List[db.Performance]],
    status_code=status.HTTP_200_OK,
)
def get_all_index_group_performances():

    codes = get_model_codes(model=db.IndexGroup)

    index_performances = {}

    for code in codes:
        try:
            # Attempt to retrieve the strategy
            index_group = db.IndexGroup.find_one(db.IndexGroup.code == code).run()

            if index_group is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found"
                )

            constituents = index_group.constituents

            performances = []

            for key, name in constituents.items():
                performance = db.Performance.find_one(
                    db.Performance.code == key,
                ).run()

                if performance is None:
                    continue
                performance.code = name
                performances.append(performance)

            index_performances[code] = performances

        except Exception as e:
            # Log the exception here
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while fetching the strategy: {str(e)}",
            )

    return index_performances


@router.get(
    "/{code}",
    response_model=db.IndexGroup,
    status_code=status.HTTP_200_OK,
)
def get_index_group_by_id(code: str):
    """
    Retrieves a strategy by its ID.
    """
    try:
        # Attempt to retrieve the strategy
        index_group = db.IndexGroup.find_one(db.IndexGroup.code == code).run()

        if index_group is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"IndexGroup {code} not found",
            )

        return index_group

    except Exception as e:
        # Log the exception here
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching the strategy: {str(e)}",
        )


@router.get(
    "/performances/{code}",
    response_model=List[db.Performance],
    status_code=status.HTTP_200_OK,
)
def get_index_group_performances_by_code(code: str):
    """
    Retrieves a strategy by its ID.
    """
    try:
        # Attempt to retrieve the strategy
        index_group = db.IndexGroup.find_one(db.IndexGroup.code == code).run()

        if index_group is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found"
            )

        constituents = index_group.constituents

        performances = []

        for key, name in constituents.items():
            performance = db.Performance.find_one(
                db.Performance.code == key,
            ).run()

            if performance is None:
                continue
            performance.code = name
            performances.append(performance)

        return performances

    except Exception as e:
        # Log the exception here
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching the strategy: {str(e)}",
        )
