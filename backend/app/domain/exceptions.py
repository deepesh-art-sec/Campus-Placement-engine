"""
Domain exceptions for Placement Engine.
Pure domain logic: No database or framework dependencies.
"""


class DomainException(Exception):
    """Base domain exception."""
    pass


class ProtectedAttributeViolationError(DomainException):
    """Raised when an eligibility rule attempts to query or filter on protected demographic attributes."""
    pass


class ConcurrencyConflictError(DomainException):
    """Raised when an optimistic concurrency check fails on an aggregate."""
    pass


class StaleVersionError(ConcurrencyConflictError):
    """Raised when an optimistic lock check fails due to an outdated base version."""
    pass


class ValidationError(DomainException):
    """Raised when domain constraints or invariants are violated."""
    pass
