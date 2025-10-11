from fastapi import Response, status, HTTPException, Depends, APIRouter
from sqlalchemy import select
from .. import models, schemas, utils, oauth2
from ..database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
router = APIRouter(
    prefix="/users",
    tags=['Users']
)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):

    #hash the password - user.password
    hashed_password = utils.hash(user.password)
    user.password = hashed_password
    
    new_user = models.User(**user.model_dump())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.delete("/delete_account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    result = await db.execute(select(models.User).where(models.User.id == current_user.id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You do not exist. This should not have happened, so there is a bug somewhere"
        )
    
    await db.delete(user)
    await db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/{id}', response_model=schemas.UserOut)
async def get_user(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.id == id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id: {id} does not exist"
        )
    
    return user