"""Retry and error mapping shared by every tool that calls Tavily."""

import logging
import time
from collections.abc import Callable

from tavily.errors import (
    BadRequestError,
    InvalidAPIKeyError,
    UsageLimitExceededError,
)
from tavily.errors import (
    TimeoutError as TavilyTimeoutError,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class TavilyCallError(Exception):
    """A Tavily call failed for good. The message is safe to show to an agent."""


def call_with_retries(call: Callable[[], dict], *, what: str) -> dict:
    """Run `call`, retrying rate limits and timeouts with exponential backoff.

    Auth and bad-request errors are not retried. Raises `TavilyCallError` on failure.
    """
    for attempt in range(MAX_RETRIES):
        is_last_attempt = attempt == MAX_RETRIES - 1
        try:
            logger.info(f"Tavily {what} (attempt {attempt + 1}/{MAX_RETRIES})")
            return call()
        except InvalidAPIKeyError as e:
            raise TavilyCallError(f"Authentication error: {e!s}") from e
        except BadRequestError as e:
            raise TavilyCallError(f"Fatal parameter error: {e!s}") from e
        except (UsageLimitExceededError, TavilyTimeoutError) as e:
            if is_last_attempt:
                raise TavilyCallError(
                    f"{what.capitalize()} failed after {MAX_RETRIES} attempts: {type(e).__name__}"
                ) from e
            wait_time = 2**attempt
            logger.warning(f"{type(e).__name__}. Retrying in {wait_time}s")
            time.sleep(wait_time)
        except Exception as e:
            logger.exception(f"Unexpected error during {what}")
            raise TavilyCallError(f"Unexpected error: {type(e).__name__}: {e!s}") from e
    raise TavilyCallError(f"{what.capitalize()} failed after all retries")  # pragma: no cover
