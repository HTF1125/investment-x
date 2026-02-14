from ix.db.conn import conn, Base
from ix.db.models import *  # Import all models to ensure they are registered
from ix.db.models.user import User
from ix.misc.auth import get_password_hash
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db():
    logger.info("Initializing database...")
    if not conn.connect():
        logger.error("Failed to connect to database")
        return

    # Create tables
    logger.info("Creating tables...")
    Base.metadata.create_all(bind=conn.engine)
    logger.info("Tables created.")

    # Create default admin user
    session = conn.SessionLocal()
    try:
        admin_email = "admin@investmentx.com"
        existing_admin = session.query(User).filter(User.email == admin_email).first()
        if not existing_admin:
            logger.info("Creating default admin user...")
            admin_user = User(
                email=admin_email,
                hashed_password=get_password_hash("admin"),
                is_admin=True,
                first_name="Admin",
                last_name="User",
            )
            session.add(admin_user)
            session.commit()
            logger.info(f"Default admin created: {admin_email} / admin")
        else:
            logger.info("Default admin already exists.")
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    init_db()
