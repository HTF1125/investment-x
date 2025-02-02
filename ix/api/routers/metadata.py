from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Body, Query, status
from ix.db import Metadata, DataSource, User
from .auth import get_current_active_user

router = APIRouter(prefix="/metadata", tags=["metadata"])

@router.get(
    path="/",
    response_model=List[Metadata],
    status_code=status.HTTP_200_OK,
)
def get_metadata(
    skip: Optional[int] = Query(0, ge=0, description="Number of records to skip"),
    limit: Optional[int] = Query(
        100, gt=0, description="Maximum number of records to return"
    ),
    search: Optional[str] = Query(
        None, description="Search term to filter insights by issuer, name, or date"
    ),
):
    try:
        query = {}
        if search:
            # Use regex to search across multiple fields
            regex = {"$regex": search, "$options": "i"}  # Case-insensitive search
            query["$or"] = [
                {"code": regex},
                {"name": regex},
            ]

        metadatas = Metadata.find(query).skip(skip).limit(limit).run()

        if not metadatas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No metadatas found.",
            )
        return metadatas
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching metadatas: {str(e)}",
        )


@router.get(
    path="/{code}",
    response_model=Metadata,
    status_code=status.HTTP_200_OK,
)
def get_metadata_by_code(
    code: str, current_user: User = Depends(get_current_active_user)
):
    try:
        metadata = Metadata.find_one({"code": code}).run()
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metadata with code {code} not found.",
            )
        return metadata
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching metadata: {str(e)}",
        )


@router.delete(
    "/{code}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete a metadata entry by its code.",
)
def delete_metadata(code: str, current_user: User = Depends(get_current_active_user)):
    metadata = Metadata.find_one({"code": code}).run()
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metadata with code {code} not found.",
        )
    Metadata.find_one({"code": code}).delete().run()


@router.put(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=Metadata,
    description="Update a metadata entry.",
)
def update_metadata(
    metadata: Metadata = Body(...),
    current_user: User = Depends(get_current_active_user),
):
    try:
        _metadata = Metadata.find_one(Metadata.id == metadata.id).run()
        if not _metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Metadata not found"
            )
        return _metadata.set(metadata.model_dump())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the metadata: {str(e)}",
        )


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=Metadata,
    description="Add a new metadata entry.",
)
def create_metadata(
    metadata: Metadata = Body(...),
    current_user: User = Depends(get_current_active_user),
):
    try:
        return metadata.create()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the metadata: {str(e)}",
        )


# @router.get(
#     "/metadata",
#     status_code=status.HTTP_201_CREATED,
#     description="Get ticker code",
# )
# def get_metadata(
#     id: Optional[str] = Query(None, description="MetaData id (optional)"),
#     code: Optional[str] = Query(None, description="MetaData code (optional)"),
# ):
#     if code:
#         metadata = Metadata.find_one(Metadata.code == code).run()
#     elif id:
#         metadata = Metadata.find_one(Metadata.id == id).run()
#     if not metadata:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="No metadatas found.",
#         )
#     return metadata


# @router.delete(
#     "/metadata",
#     status_code=status.HTTP_200_OK,
#     description="Add a new ticker code to the database.",
# )
# def delete_metata(metadata: Metadata):
#     """
#     Endpoint to create a new insight source.

#     Parameters:
#     - url: URL data provided in the request body.

#     Returns:
#     - The created InsightSource document.
#     """
#     if not ObjectId.is_valid(metadata.id):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Invalid ID format",
#         )
#     Metadata.find_one(Metadata.id == metadata.id).delete().run()
#     return {"message": "InsightSource deleted successfully"}


# @router.put(
#     "/metadata",
#     status_code=status.HTTP_200_OK,
#     response_model=Metadata,
#     description="Add a new ticker code to the database.",
# )
# def update_metadata(metadata: Metadata):

#     if not ObjectId.is_valid(metadata.id):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Invalid ID format",
#         )

#     try:
#         _metadata = Metadata.find_one(Metadata.id == metadata.id).run()
#         if not _metadata:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found"
#             )
#         return _metadata.set(metadata.model_dump())
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"An error occurred while creating the insight source: {str(e)}",
#         )


# @router.post(
#     "/metadata",
#     status_code=status.HTTP_200_OK,
#     response_model=Metadata,
#     description="Add a new ticker code to the database.",
# )
# def create_metadata(metadata: Metadata):

#     try:
#         return metadata.create()
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"An error occurred while creating the insight source: {str(e)}",
#         )
