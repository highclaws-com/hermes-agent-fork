"""Deliver cron completion events under the job store's active profile scope."""

import asyncio
import logging

from gateway.hooks import ProfileHookRegistries

_hooks = ProfileHookRegistries()
logger = logging.getLogger(__name__)


def emit_job_end(job, success, response, error, delivery_error, loop=None):
    context = {
        "job_id": job["id"],
        "job_name": job.get("name"),
        "success": success,
        "response": response,
        "error": error,
        "delivery_error": delivery_error,
        "silent": "[SILENT]" in response.upper(),
        "no_agent": bool(job.get("no_agent")),
    }
    try:
        coro = _hooks.emit("job:end", context)
        if loop is not None:
            asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=5)
        else:
            asyncio.run(coro)
    except Exception:
        logger.exception("job:end hook failed for job %s", job["id"])
