from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from .. import schemas, database, models, oauth2


router = APIRouter(
    prefix="/favourites",
    tags=['Favourite']
)

@router.post("/", status_code=status.HTTP_201_CREATED)
def add_to_favourites(favourite: schemas.Favourite, db: Session = Depends(database.get_db), current_user: models.User = Depends(oauth2.get_current_user)):

    quiz = db.query(models.Quiz).filter(models.Quiz.id == favourite.quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quiz with id: {favourite.quiz_id} does not exist")

    favourite_query = db.query(models.Favourite).filter(models.Favourite.quiz_id == favourite.quiz_id, models.Favourite.user_id == current_user.id)
    found_favourite = favourite_query.first()

    if(favourite.dir == 1):
        if found_favourite:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"User {current_user.id} has already added this quiz to favourites {favourite.quiz_id}")
        new_favourite = models.Favourite(quiz_id = favourite.quiz_id, user_id = current_user.id)
        db.add(new_favourite)
        db.commit()
        return {"message": "successfully added to favourites"}
    else:
        if not found_favourite:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favourite does not exist")
        
        favourite_query.delete(synchronize_session=False)
        db.commit()

        return {"messsage": "successfully deleted from favourites"}