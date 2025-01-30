from typing import List
from fastapi import APIRouter, HTTPException, Depends, Body, status
from ix.db import Metadata, User
from .auth import get_current_active_user

router = APIRouter(prefix="/metadatanew", tags=["metadatanew"])


@router.get(
    path="/",
    response_model=List[Metadata],
    status_code=status.HTTP_200_OK,
)
def get_metadata():
    try:
        metadatas = Metadata.find_all().run()
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
