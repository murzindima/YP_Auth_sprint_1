from uuid import UUID

from pydantic import EmailStr
from sqlalchemy import and_, select, update

from src.core.config import app_settings
from src.models.login_history import LoginHistory
from src.models.role import Role as RoleModel
from src.models.user import User as UserModel
from src.services.data_repository.postgres_crud import PostgresCrudService


class PostgresService(PostgresCrudService):
    """A data storage service implementation for working with Postgres."""

    async def get_user_by_email(self, email: EmailStr) -> UserModel | None:
        """Retrieve a model by email."""
        async with self.session.begin():
            stmt = select(self.model_class).where(self.model_class.email == email)
            result = await self.session.execute(stmt)
            model = result.scalar()
            return model

    async def get_role(self, role_id: UUID) -> RoleModel | None:
        """Retrieve a role."""
        async with self.session.begin():
            model = await self.session.get(RoleModel, role_id)
            return model

    async def get_login_history(
        self, user_id: UUID, page: int = 1, size: int = app_settings.pagination_size, refresh_token: str | None = None
    ) -> list[LoginHistory]:
        """Retrieve user's login history with pagination."""
        async with self.session.begin():
            query = select(LoginHistory).filter_by(user_id=user_id)

            if refresh_token:
                query = query.filter_by(refresh_token=refresh_token)

            offset = (page - 1) * size
            query = query.offset(offset).limit(size)

            models = await self.session.execute(query)
            return models.scalars().all()

    async def deactivate_from_user_history(self, user_id: UUID, current_user_ip_address: str) -> None:
        """Deactivate login history record for a user."""
        async with self.session.begin():
            await self.session.execute(
                update(LoginHistory)
                .where(
                    and_(
                        LoginHistory.user_id == user_id,
                        LoginHistory.is_active,
                        LoginHistory.ip_address == current_user_ip_address,
                    )
                )
                .values(is_active=False)
            )

    async def create_login_history(self, user_id: UUID, ip_address, refresh_token: str) -> None:
        """Create a login history record for a user."""
        model_instance = LoginHistory(user_id=user_id, ip_address=ip_address, refresh_token=refresh_token)
        self.session.add(model_instance)
        await self.session.commit()

    async def update_user_history(self, user_id: UUID, refresh_token: str) -> None:
        """Updates active refresh token of the user."""
        async with self.session.begin():
            await self.session.execute(
                update(LoginHistory)
                .where(
                    and_(
                        LoginHistory.user_id == user_id,
                        LoginHistory.is_active,
                    )
                )
                .values(refresh_token=refresh_token)
            )
