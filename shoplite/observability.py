"""Structured JSON logs with request IDs, and Prometheus-format metrics."""

import json
import logging
import re
import sys
import threading
import time
import uuid
from collections import defaultdict

from flask import Flask, current_app, g, has_request_context, request

REQUEST_ID_HEADER = "X-Request-ID"
VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)

METRIC_HELP = {
    "shoplite_http_requests_total": ("counter", "HTTP requests by method, route and status."),
    "shoplite_http_errors_total": ("counter", "HTTP 5xx responses by route."),
    "shoplite_http_request_duration_seconds": ("histogram", "Request latency by route."),
    "shoplite_checkouts_total": ("counter", "Checkout attempts by outcome."),
    "shoplite_payments_total": ("counter", "Payment attempts by status."),
    "shoplite_warehouse_sync_failures_total": ("counter", "Failed pushes to the warehouse."),
    "shoplite_stock_reserved_units": ("gauge", "Units currently held for unpaid orders."),
}


class JsonFormatter(logging.Formatter):
    """Format each log record as one JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        """Turn a record into a JSON string with the request ID."""
        entry = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": g.get("request_id") if has_request_context() else None,
        }
        entry.update(getattr(record, "fields", {}))
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


class Metrics:
    """In-process counters and histograms, rendered in Prometheus text format."""

    def __init__(self):
        """Start with empty metrics."""
        self.lock = threading.Lock()
        self.counters: dict[tuple, float] = defaultdict(float)
        self.histograms: dict[tuple, list] = {}

    def inc(self, name: str, labels: dict, amount: float = 1) -> None:
        """Add to a counter."""
        with self.lock:
            self.counters[(name, tuple(sorted(labels.items())))] += amount

    def observe(self, name: str, labels: dict, value: float) -> None:
        """Record one value in a histogram."""
        key = (name, tuple(sorted(labels.items())))
        with self.lock:
            buckets = self.histograms.setdefault(key, [0] * len(LATENCY_BUCKETS) + [0, 0.0])
            for i, bound in enumerate(LATENCY_BUCKETS):
                if value <= bound:
                    buckets[i] += 1
            buckets[-2] += 1  # count
            buckets[-1] += value  # sum

    def render(self, gauges: dict[str, float]) -> str:
        """Return all metrics as Prometheus exposition text."""
        lines = []
        with self.lock:
            counters = dict(self.counters)
            histograms = {key: list(value) for key, value in self.histograms.items()}
        for name, (kind, help_text) in METRIC_HELP.items():
            lines += [f"# HELP {name} {help_text}", f"# TYPE {name} {kind}"]
            if kind == "gauge":
                lines.append(f"{name} {gauges.get(name, 0)}")
            for (metric, labels), value in sorted(counters.items()):
                if metric == name:
                    lines.append(f"{name}{format_labels(labels)} {value:g}")
            for (metric, labels), buckets in sorted(histograms.items()):
                if metric != name:
                    continue
                for bound, count in zip(LATENCY_BUCKETS, buckets, strict=False):
                    lines.append(f"{name}_bucket{format_labels(labels + (('le', str(bound)),))} "
                                 f"{count}")
                lines.append(f"{name}_bucket{format_labels(labels + (('le', '+Inf'),))} "
                             f"{buckets[-2]}")
                lines.append(f"{name}_count{format_labels(labels)} {buckets[-2]}")
                lines.append(f"{name}_sum{format_labels(labels)} {buckets[-1]:.6f}")
        return "\n".join(lines) + "\n"


def format_labels(labels: tuple) -> str:
    """Render label pairs as {a="1",b="2"}."""
    if not labels:
        return ""
    return "{" + ",".join(f'{key}="{value}"' for key, value in labels) + "}"


def count(name: str, **labels) -> None:
    """Add 1 to a counter on the current app's metrics."""
    current_app.extensions["shoplite_metrics"].inc(name, labels)


def setup_logging(app: Flask) -> None:
    """Send the app's logs to stdout as JSON lines."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.shoplite_handler = True
    logger = logging.getLogger("shoplite")
    logger.handlers = [h for h in logger.handlers if not getattr(h, "shoplite_handler", False)]
    logger.addHandler(handler)
    logger.setLevel(app.config["SHOPLITE_LOG_LEVEL"])
    logger.propagate = False


def start_request() -> None:
    """Give the request an ID and start its timer."""
    incoming = request.headers.get(REQUEST_ID_HEADER, "")
    g.request_id = incoming if VALID_REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
    g.request_started = time.perf_counter()


def finish_request(response):
    """Log the request, record its metrics and return the request ID header."""
    duration = time.perf_counter() - g.get("request_started", time.perf_counter())
    route = request.url_rule.rule if request.url_rule else "unmatched"
    metrics = current_app.extensions["shoplite_metrics"]
    metrics.inc("shoplite_http_requests_total",
                {"method": request.method, "route": route, "status": str(response.status_code)})
    metrics.observe("shoplite_http_request_duration_seconds", {"route": route}, duration)
    if response.status_code >= 500:
        metrics.inc("shoplite_http_errors_total", {"route": route})
    logging.getLogger("shoplite.access").info("request finished", extra={"fields": {
        "method": request.method, "path": request.path, "route": route,
        "status": response.status_code, "duration_ms": round(duration * 1000, 2)}})
    response.headers[REQUEST_ID_HEADER] = g.request_id
    return response


def init_app(app: Flask) -> None:
    """Attach logging, metrics and the request hooks to an app."""
    setup_logging(app)
    app.extensions["shoplite_metrics"] = Metrics()
    app.before_request(start_request)
    app.after_request(finish_request)
