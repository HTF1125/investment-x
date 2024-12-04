from typing import List
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status
from ix import db
from .base import get_model_codes
from fastapi.responses import StreamingResponse
import io

router = APIRouter(prefix="/data/research_file", tags=["data"])


@router.get(
    "/codes",
    response_model=List[str],
    status_code=status.HTTP_200_OK,
)
def get_reserach_file_codes():
    """
    Retrieves all signal codes.
    """
    try:
        return get_model_codes(model=db.ResearchFile)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching signal codes: {str(e)}",
        )


@router.get(
    "/{code}",
    response_model=db.ResearchFile,
    status_code=status.HTTP_200_OK,
)
def get_research_file_by_code(code: str):
    """
    Retrieves a research file by its code and streams it as a response.
    """
    try:
        file = db.ResearchFile.find_one(db.ResearchFile.code == code).run()
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        # Serve the content as a streaming response
        return StreamingResponse(
            io.BytesIO(file.content), media_type="application/pdf"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )
