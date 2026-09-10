from __future__ import annotations

from pathlib import Path

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, func, select

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        Path("data").mkdir(parents=True, exist_ok=True)

    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, future=True, connect_args=connect_args)
    metadata = MetaData()
    student = Table(
        "STUDENT",
        metadata,
        Column("NAME", String(25), nullable=False),
        Column("CLASS", String(25), nullable=False),
        Column("SECTION", String(25), nullable=False),
        Column("MARKS", Integer, nullable=False),
    )
    metadata.create_all(engine)

    rows = [
        {"NAME": "Akshay", "CLASS": "Data Science", "SECTION": "A", "MARKS": 90},
        {"NAME": "Aryan", "CLASS": "Data Science", "SECTION": "B", "MARKS": 100},
        {"NAME": "Priya", "CLASS": "Data Science", "SECTION": "A", "MARKS": 86},
        {"NAME": "Anam", "CLASS": "DEVOPS", "SECTION": "A", "MARKS": 50},
        {"NAME": "Shreyas", "CLASS": "DEVOPS", "SECTION": "A", "MARKS": 35},
    ]

    with engine.begin() as connection:
        count = connection.execute(select(func.count()).select_from(student)).scalar_one()
        if count == 0:
            connection.execute(student.insert(), rows)

    print(f"Database ready: {settings.database_url}")


if __name__ == "__main__":
    main()

