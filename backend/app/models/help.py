import uuid
from sqlalchemy import String, Boolean, ForeignKey, Integer, Text, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class HelpCategory(Base, TimestampMixin):
    """Hierarchical categories for organization of help center articles."""
    __tablename__ = "help_categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("help_categories.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    icon: Mapped[str] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    parent: Mapped["HelpCategory"] = relationship("HelpCategory", remote_side=[id], backref="children")
    articles: Mapped[list["HelpArticle"]] = relationship("HelpArticle", back_populates="category", cascade="all, delete-orphan")


class HelpArticle(Base, TimestampMixin):
    """Help center documentation articles containing markdown content and access visibility rules."""
    __tablename__ = "help_articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("help_categories.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    prerequisites: Mapped[str] = mapped_column(Text, nullable=True)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Access controls & categorization
    applicable_module: Mapped[str] = mapped_column(String(50), default="core", nullable=False, index=True) # e.g. sales, rental, amc, core
    required_permission: Mapped[str] = mapped_column(String(100), nullable=True) # e.g. quotations:create
    role_visibility: Mapped[list[str]] = mapped_column(JSON, nullable=True) # e.g. ["admin", "accounts"]
    
    status: Mapped[str] = mapped_column(String(50), default="published", nullable=False) # draft, published, archived
    version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    category: Mapped[HelpCategory] = relationship("HelpCategory", back_populates="articles")
    faqs: Mapped[list["HelpFAQ"]] = relationship("HelpFAQ", back_populates="article", cascade="all, delete-orphan")
    attachments: Mapped[list["HelpAttachment"]] = relationship("HelpAttachment", back_populates="article", cascade="all, delete-orphan")
    feedbacks: Mapped[list["HelpFeedback"]] = relationship("HelpFeedback", back_populates="article", cascade="all, delete-orphan")


class HelpFAQ(Base, TimestampMixin):
    """Frequently Asked Questions embedded directly inside a help article."""
    __tablename__ = "help_faqs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("help_articles.id", ondelete="CASCADE"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationship
    article: Mapped[HelpArticle] = relationship("HelpArticle", back_populates="faqs")


class HelpAttachment(Base, TimestampMixin):
    """Media assets like screenshots, GIFs, PDFs, or instruction videos linked to an article."""
    __tablename__ = "help_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("help_articles.id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. image, video, pdf, gif
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)

    # Relationship
    article: Mapped[HelpArticle] = relationship("HelpArticle", back_populates="attachments")


class HelpFeedback(Base, TimestampMixin):
    """User reviews, ratings, and outdated flag reports for documentation content quality."""
    __tablename__ = "help_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    article_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("help_articles.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False) # 1 to 5 rating
    comments: Mapped[str] = mapped_column(Text, nullable=True)
    is_outdated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationship
    article: Mapped[HelpArticle] = relationship("HelpArticle", back_populates="feedbacks")


class HelpBookmark(Base, TimestampMixin):
    """Personal bookmarked articles list for individual users."""
    __tablename__ = "help_bookmarks"
    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_user_help_bookmark"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    article_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("help_articles.id", ondelete="CASCADE"), nullable=False)
