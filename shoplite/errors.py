"""API error types; every error is returned as {"error": {"code", "message", "details"}}."""

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


class ShopLiteError(Exception):
    """Base error with an HTTP status and a stable error code (see docs/api.md)."""

    status = 400
    code = "SL-GEN-400"

    def __init__(self, message: str, *, code: str | None = None, details: dict | None = None):
        """Store the message, an optional code override and extra details."""
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details or {}


class ValidationError(ShopLiteError):
    """The request body or query string is invalid."""

    status = 422
    code = "SL-VAL-422"


class Unauthorized(ShopLiteError):
    """No valid bearer token was sent."""

    status = 401
    code = "SL-AUTH-401"


class Forbidden(ShopLiteError):
    """The user is logged in but not allowed to do this."""

    status = 403
    code = "SL-AUTH-403"


class NotFound(ShopLiteError):
    """The requested record does not exist (or is not yours)."""

    status = 404
    code = "SL-GEN-404"


class Conflict(ShopLiteError):
    """The request clashes with the current state."""

    status = 409
    code = "SL-GEN-409"


class OutOfStock(Conflict):
    """Not enough stock to fill the order."""

    code = "SL-INV-409"


class PaymentDeclined(ShopLiteError):
    """The payment gateway declined the charge."""

    status = 402
    code = "SL-PAY-402"


class PaymentGatewayError(ShopLiteError):
    """The payment gateway failed or was unreachable."""

    status = 502
    code = "SL-PAY-502"


def error_body(code: str, message: str, details: dict | None = None) -> dict:
    """Build the JSON error body."""
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_error_handlers(app: Flask) -> None:
    """Return every error as JSON in the same shape."""

    @app.errorhandler(ShopLiteError)
    def handle_shoplite_error(err: ShopLiteError):
        """Return a ShopLite error with its own status and code."""
        return jsonify(error_body(err.code, err.message, err.details)), err.status

    @app.errorhandler(HTTPException)
    def handle_http_error(err: HTTPException):
        """Return Flask's HTTP errors (404, 405...) as JSON."""
        return jsonify(error_body(f"SL-HTTP-{err.code}", err.description or err.name)), err.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(err: Exception):
        """Log the crash and return a generic 500."""
        app.logger.exception("unhandled error")
        return jsonify(error_body("SL-GEN-500", "internal server error")), 500
