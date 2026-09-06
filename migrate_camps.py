from sqlalchemy import inspect, text

from app.database import engine


inspector = inspect(engine)

columns = [
    column["name"]
    for column in inspector.get_columns("camps")
]

if "status" not in columns:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                ALTER TABLE camps
                ADD COLUMN status VARCHAR(20)
                NOT NULL
                DEFAULT 'scheduled'
                """
            )
        )

    print("Camp status column added successfully.")
else:
    print("Camp status column already exists.")