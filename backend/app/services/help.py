import re
from uuid import UUID
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.models.help import HelpCategory, HelpArticle, HelpFAQ, HelpFeedback, HelpBookmark

def check_article_visibility(article: HelpArticle, active_modules: list[str], user_role: str, is_platform_admin: bool) -> bool:
    """Helper to check if a user is permitted to view an article based on tenant modules and roles."""
    if is_platform_admin:
        return True
    
    # 1. Check Module Gating
    if article.applicable_module != "core" and article.applicable_module not in active_modules:
        return False
        
    # 2. Check Role Gating
    if article.role_visibility:
        if user_role not in article.role_visibility and user_role != "admin":
            return False
            
    return True

async def get_help_menu(db: AsyncSession, active_modules: list[str], user_role: str, is_platform_admin: bool):
    """
    Builds a hierarchical categories and articles tree, filtered by active modules and user roles.
    Unsubscribed module documentation items are either locked or excluded depending on SaaS settings.
    """
    # Load categories
    cat_stmt = select(HelpCategory).where(HelpCategory.is_active == True).order_code = HelpCategory.display_order
    # Wait, SQLAlchemy order_by takes the column attribute:
    cat_stmt = select(HelpCategory).where(HelpCategory.is_active == True).order_by(HelpCategory.display_order)
    cat_res = await db.execute(cat_stmt)
    categories = cat_res.scalars().all()

    # Load all active published articles
    art_stmt = select(HelpArticle).where(
        HelpArticle.is_active == True,
        HelpArticle.status == "published"
    ).order_by(HelpArticle.title)
    art_res = await db.execute(art_stmt)
    all_articles = art_res.scalars().all()

    # Build category hierarchy map
    categories_by_id = {cat.id: cat for cat in categories}
    articles_by_cat = {}
    for art in all_articles:
        if check_article_visibility(art, active_modules, user_role, is_platform_admin):
            articles_by_cat.setdefault(art.category_id, []).append({
                "id": str(art.id),
                "title": art.title,
                "slug": art.slug,
                "applicable_module": art.applicable_module,
                "required_permission": art.required_permission
            })

    # Construct hierarchical tree
    roots = []
    children_map = {}
    for cat in categories:
        cat_data = {
            "id": str(cat.id),
            "name": cat.name,
            "slug": cat.slug,
            "description": cat.description,
            "icon": cat.icon,
            "articles": articles_by_cat.get(cat.id, []),
            "subcategories": []
        }
        if cat.parent_id is None:
            roots.append(cat_data)
        else:
            children_map.setdefault(cat.parent_id, []).append(cat_data)

    # Nest subcategories recursively
    def nest_subcategories(parent_node):
        parent_id = UUID(parent_node["id"])
        if parent_id in children_map:
            for child in children_map[parent_id]:
                nest_subcategories(child)
                parent_node["subcategories"].append(child)
            # Order subcategories by display_order matching parent DB entities
            parent_node["subcategories"].sort(
                key=lambda x: categories_by_id[UUID(x["id"])].display_order
            )

    for root in roots:
        nest_subcategories(root)

    # Filter out categories that have neither articles nor subcategories with articles
    def clean_empty_nodes(node):
        node["subcategories"] = [sub for sub in node["subcategories"] if clean_empty_nodes(sub)]
        has_content = len(node["articles"]) > 0 or len(node["subcategories"]) > 0
        return has_content

    filtered_roots = [root for root in roots if clean_empty_nodes(root)]
    return filtered_roots


async def get_help_article(
    db: AsyncSession,
    slug: str,
    active_modules: list[str],
    user_role: str,
    is_platform_admin: bool
) -> HelpArticle:
    """Retrieves article details, enforcing module-awareness and role visibility restrictions."""
    stmt = select(HelpArticle).where(
        HelpArticle.slug == slug,
        HelpArticle.is_active == True,
        HelpArticle.status == "published"
    ).options(
        selectinload(HelpArticle.faqs),
        selectinload(HelpArticle.attachments)
    )
    res = await db.execute(stmt)
    article = res.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Help article not found."
        )

    # Enforce active module gating
    if article.applicable_module != "core" and article.applicable_module not in active_modules and not is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"This topic requires the '{article.applicable_module.upper()}' module subscription."
        )

    # Enforce role visibility gating
    if article.role_visibility and not is_platform_admin:
        if user_role not in article.role_visibility and user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this article."
            )

    return article


async def search_help_articles(
    db: AsyncSession,
    query: str,
    active_modules: list[str],
    user_role: str,
    is_platform_admin: bool
) -> list[dict]:
    """
    Search articles and FAQs, filtering by visibility constraints and wrapping matched text in <mark> tags.
    """
    if not query or len(query.strip()) < 2:
        return []

    clean_query = query.strip()
    
    # Select articles
    stmt = select(HelpArticle).where(
        HelpArticle.is_active == True,
        HelpArticle.status == "published"
    ).options(
        selectinload(HelpArticle.faqs)
    )
    res = await db.execute(stmt)
    articles = res.scalars().all()

    results = []
    pattern = re.compile(re.escape(clean_query), re.IGNORECASE)

    for art in articles:
        # Check permissions
        if not check_article_visibility(art, active_modules, user_role, is_platform_admin):
            continue

        matched = False
        highlighted_title = art.title
        highlighted_snippet = ""

        # Check title match
        if pattern.search(art.title):
            matched = True
            highlighted_title = pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", art.title)

        # Check content match and extract snippet
        content_match = pattern.search(art.content_markdown)
        if content_match:
            matched = True
            start = max(0, content_match.start() - 60)
            end = min(len(art.content_markdown), content_match.end() + 60)
            snippet = art.content_markdown[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(art.content_markdown):
                snippet = snippet + "..."
            highlighted_snippet = pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", snippet)

        # Check FAQs match
        faq_matches = []
        for faq in art.faqs:
            faq_match = False
            hl_q = faq.question
            hl_a = faq.answer
            
            if pattern.search(faq.question):
                faq_match = True
                hl_q = pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", faq.question)
            if pattern.search(faq.answer):
                faq_match = True
                hl_a = pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", faq.answer)

            if faq_match:
                matched = True
                faq_matches.append({"question": hl_q, "answer": hl_a})

        if matched:
            results.append({
                "id": str(art.id),
                "title": highlighted_title,
                "slug": art.slug,
                "applicable_module": art.applicable_module,
                "snippet": highlighted_snippet or (art.purpose[:120] + "..."),
                "faq_matches": faq_matches
            })

    return results


async def create_feedback(
    db: AsyncSession,
    article_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
    rating: int,
    comments: str,
    is_outdated: bool
) -> HelpFeedback:
    """Saves user rating/comments and handles outdated reports."""
    feedback = HelpFeedback(
        article_id=article_id,
        tenant_id=tenant_id,
        user_id=user_id,
        rating=rating,
        comments=comments,
        is_outdated=is_outdated
    )
    db.add(feedback)
    await db.flush()
    return feedback


async def toggle_bookmark(db: AsyncSession, tenant_id: UUID, user_id: UUID, article_id: UUID) -> bool:
    """Toggles article bookmark. Returns True if bookmarked, False if removed."""
    stmt = select(HelpBookmark).where(
        HelpBookmark.user_id == user_id,
        HelpBookmark.article_id == article_id
    )
    res = await db.execute(stmt)
    bookmark = res.scalar_one_or_none()

    if bookmark:
        await db.delete(bookmark)
        return False
    else:
        new_bookmark = HelpBookmark(
            tenant_id=tenant_id,
            user_id=user_id,
            article_id=article_id
        )
        db.add(new_bookmark)
        return True


async def get_bookmarked_articles(db: AsyncSession, user_id: UUID) -> list[dict]:
    """Lists all user bookmarked articles."""
    stmt = select(HelpArticle).join(
        HelpBookmark, HelpBookmark.article_id == HelpArticle.id
    ).where(
        HelpBookmark.user_id == user_id,
        HelpArticle.is_active == True,
        HelpArticle.status == "published"
    )
    res = await db.execute(stmt)
    articles = res.scalars().all()
    return [{
        "id": str(art.id),
        "title": art.title,
        "slug": art.slug,
        "applicable_module": art.applicable_module
    } for art in articles]
