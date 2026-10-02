
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import CentreTest, DiagnosticCentre, DiagnosticTest, User
from app.schemas import CentreCreate, CentreResponse, TestAtCentreResponse

router = APIRouter(prefix="/centres", tags=["Diagnostic centres"])


def centre_to_response(centre: DiagnosticCentre):
    return CentreResponse(
        id=centre.id,
        name=centre.name,
        location=centre.location,
        tests=[
            TestAtCentreResponse(
                test_id=ct.test.id,
                test_name=ct.test.name,
                description=ct.test.description,
                price=ct.price,
            )
            for ct in centre.centre_tests
        ],
    )


def centre_query(db: Session):
    return db.query(DiagnosticCentre).options(
        joinedload(DiagnosticCentre.centre_tests).joinedload(CentreTest.test)
    )


@router.get("/", response_model=list[CentreResponse])
def list_centres(
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = centre_query(db).filter(DiagnosticCentre.is_active.is_(True))

    if search:
        query = query.filter(DiagnosticCentre.name.ilike(f"%{search}%"))

    centres = query.order_by(DiagnosticCentre.id).offset(offset).limit(limit).all()
    return [centre_to_response(centre) for centre in centres]


@router.get("/{centre_id}", response_model=CentreResponse)
def get_centre(centre_id: int, db: Session = Depends(get_db)):
    centre = (
        centre_query(db)
        .filter(
            DiagnosticCentre.id == centre_id,
            DiagnosticCentre.is_active.is_(True),
        )
        .first()
    )

    if centre is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic centre not found",
        )

    return centre_to_response(centre)


@router.post(
    "/",
    response_model=CentreResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_centre(
    payload: CentreCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Authentication is required.
    # For admin-only access, add a role check to the User model
    # and reject users whose role is not admin.

    centre = DiagnosticCentre(
        name=payload.name.strip(),
        location=payload.location.strip(),
    )
    db.add(centre)

    try:
        db.flush()

        for item in payload.tests:
            test_name = item.test_name.strip()

            test = (
                db.query(DiagnosticTest)
                .filter(DiagnosticTest.name == test_name)
                .first()
            )

            if test is None:
                test = DiagnosticTest(
                    name=test_name,
                    description=item.description,
                )
                db.add(test)
                db.flush()
            elif item.description and not test.description:
                test.description = item.description

            db.add(
                CentreTest(
                    centre_id=centre.id,
                    test_id=test.id,
                    price=item.price,
                )
            )

        db.commit()

    except Exception:
        db.rollback()
        raise

    centre = (
        centre_query(db)
        .filter(DiagnosticCentre.id == centre.id)
        .first()
    )

    return centre_to_response(centre)
