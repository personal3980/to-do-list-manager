"""Authenticated task operations. Every query is scoped to the session owner."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Task, User
from ..schemas import TaskImport, TaskInput, TaskOutput, TaskStatus
from .auth import current_user

router = APIRouter(prefix='/api/tasks', tags=['Tasks'])


def owned_task(task_id, user, db):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    if task is None:
        raise HTTPException(404, 'Task not found.')
    return task


@router.get('', response_model=list[TaskOutput])
def list_tasks(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Task).where(Task.user_id == user.id)
                      .order_by(Task.created_at.desc(), Task.id)).all()


@router.post('', response_model=TaskOutput, status_code=201)
def create_task(data: TaskInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = Task(user_id=user.id, **data.model_dump())
    db.add(task)
    db.commit()
    return task


@router.post('/import', response_model=TaskOutput)
def import_task(data: TaskImport, user: User = Depends(current_user), db: Session = Depends(get_db)):
    # Stable browser IDs make retries safe, including partially finished imports.
    query = select(Task).where(Task.user_id == user.id, Task.legacy_id == data.legacy_id)
    task = db.scalar(query)
    if task is None:
        task = Task(user_id=user.id, **data.model_dump())
        db.add(task)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            task = db.scalar(query)
            if task is None:
                raise
    return task


@router.delete('/completed', status_code=204)
def clear_completed(user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(delete(Task).where(Task.user_id == user.id, Task.completed.is_(True)))
    db.commit()
    return Response(status_code=204)


@router.put('/{task_id}', response_model=TaskOutput)
def update_task(task_id: str, data: TaskInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = owned_task(task_id, user, db)
    for name, value in data.model_dump().items():
        setattr(task, name, value)
    db.commit()
    return task


@router.patch('/{task_id}', response_model=TaskOutput)
def task_status(task_id: str, data: TaskStatus, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = owned_task(task_id, user, db)
    task.completed = data.completed
    db.commit()
    return task


@router.delete('/{task_id}', status_code=204)
def delete_task(task_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(owned_task(task_id, user, db))
    db.commit()
    return Response(status_code=204)
