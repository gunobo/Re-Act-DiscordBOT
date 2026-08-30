from sqlmodel import Session, select

from app.categories.models import CategoryTemplate


def list_categories(session: Session) -> list[CategoryTemplate]:
    return list(session.exec(select(CategoryTemplate).order_by(CategoryTemplate.id)))


def get_category(session: Session, category_id: int) -> CategoryTemplate | None:
    return session.get(CategoryTemplate, category_id)


def create_category(session: Session, name: str, template_text: str) -> CategoryTemplate:
    row = CategoryTemplate(name=name.strip(), template_text=template_text)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_category(session: Session, category_id: int, name: str, template_text: str) -> None:
    row = session.get(CategoryTemplate, category_id)
    if row:
        row.name = name.strip()
        row.template_text = template_text
        session.add(row)
        session.commit()


def delete_category(session: Session, category_id: int) -> None:
    row = session.get(CategoryTemplate, category_id)
    if row:
        session.delete(row)
        session.commit()
