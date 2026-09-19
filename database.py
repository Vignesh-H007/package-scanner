import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./inspections.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class InspectionRecord(Base):
    __tablename__ = "inspections"

    id = Column(String, primary_key=True, index=True)
    product_name = Column(String, default="Scanned Commodity")
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, nullable=False)
    total_checks = Column(Integer, default=0)
    passed_checks = Column(Integer, default=0)
    failed_checks = Column(Integer, default=0)
    checks_json = Column(Text, nullable=False)  # Serialized list of checks

    def to_dict(self):
        return {
            "id": self.id,
            "productName": self.product_name,
            "date": self.created_at.strftime("%d %b %Y, %I:%M %p"),
            "status": self.status,
            "totalChecks": self.total_checks,
            "passedChecks": self.passed_checks,
            "failedChecks": self.failed_checks,
            "checks": json.loads(self.checks_json)
        }

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()