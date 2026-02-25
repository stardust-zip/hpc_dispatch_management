from datetime import datetime, timezone

from hpc_dispatch_management.database import SessionLocal
from hpc_dispatch_management.models import Dispatch, DispatchStatus, User


def run_seeder():
    db = SessionLocal()

    try:
        print("Starting Database Seeder...")

        author_id = 1
        author = db.get(User, author_id)
        if not author:
            author = User(
                id=author_id,
                username="admin",
                email="admin@system.com",
                full_name="Admin System",
                user_type="lecturer",
                is_admin=True,
                department_id=1,
            )
            db.add(author)
            db.commit()
            print("Created dummy author.")

        dispatches = [
            Dispatch(
                title="Quyết định nghỉ lễ 30/4",
                serial_number="QD-001/2026",
                description="Thông báo lịch nghỉ lễ 30/4 và 1/5 cho toàn trường.",
                status=DispatchStatus.APPROVED,
                author_id=author.id,
                created_at=datetime.now(timezone.utc),
            ),
            Dispatch(
                title="Kế hoạch thi học kỳ 1",
                serial_number="KH-002/2026",
                description="Kế hoạch tổ chức thi kết thúc học phần.",
                status=DispatchStatus.IN_PROGRESS,
                author_id=author.id,
                created_at=datetime.now(timezone.utc),
            ),
        ]

        for d in dispatches:
            exists = db.query(Dispatch).filter_by(serial_number=d.serial_number).first()
            if not exists:
                db.add(d)

        db.commit()
        print("Successfully seeded dispatches!")

    except Exception as e:
        db.rollback()
        print(f"Failed to seed database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    run_seeder()
