"""Shared pagination.

Every list endpoint is paged. An unbounded ``SELECT * FROM project`` is a denial
of service waiting for a user with a hundred projects, and it makes the UI's
infinite scroll impossible to build correctly.
"""

from __future__ import annotations

from typing import Annotated, Generic, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel, Field

T = TypeVar("T")

MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


class PageParams(BaseModel):
    """Normalised, clamped paging parameters."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class Page(BaseModel, Generic[T]):
    """A page of results plus the metadata a UI needs to render a pager."""

    total: int = Field(..., ge=0, description="Total rows matching the filter.")
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)
    items: list[T] = Field(default_factory=list)

    @property
    def total_pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        return self.page > 1


def page_params(
    page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
    page_size: Annotated[
        int,
        Query(
            ge=MIN_PAGE_SIZE,
            le=MAX_PAGE_SIZE,
            description=f"Rows per page (1-{MAX_PAGE_SIZE}).",
        ),
    ] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    """FastAPI dependency producing clamped paging parameters.

    ``page_size`` is bounded by the ``Query`` constraint rather than clamped after
    the fact, so a request for ``page_size=100000`` gets a 422 with a field error
    the client can bind, instead of silently receiving a different number than it
    asked for.
    """
    return PageParams(page=page, page_size=page_size)


PageParamsDep = Annotated[PageParams, Depends(page_params)]


def build_page(items: list[T], total: int, params: PageParams) -> Page[T]:
    """Assemble a :class:`Page` from a result slice."""
    return Page[T](total=total, page=params.page, page_size=params.page_size, items=items)
