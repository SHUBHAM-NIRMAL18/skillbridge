import logging
from functools import wraps
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django_ratelimit.core import is_ratelimited

logger = logging.getLogger(__name__)


def _is_ajax_or_json(request):
    """
    Determines whether a request expects a JSON or AJAX response.
    """
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return True
    accept = request.headers.get("accept", "").lower()
    if "application/json" in accept or "*/*" not in accept and "json" in accept:
        return True
    if getattr(request, "content_type", "") == "application/json":
        return True
    if request.GET.get("format") == "json":
        return True
    return False


def ratelimit_endpoint(
    rate=None,
    rate_key=None,
    default_rate="10/m",
    key="ip",
    methods=None,
    group=None,
    error_msg=None,
):
    """
    View decorator that enforces rate limiting using django-ratelimit.

    Parameters:
    - rate: Explicit rate limit string, e.g. "5/m", "20/h".
    - rate_key: Key in settings.RATELIMIT_RATES to look up configured rate limit dynamically.
    - default_rate: Fallback rate limit if rate_key is not found in settings (default "10/m").
    - key: 'ip', 'user', 'user_or_ip', or custom callable function (request).
    - methods: HTTP method or list of methods to apply limit to (default ['POST', 'GET']).
    - group: Group identifier for bucket tracking. Defaults to function module.name.
    - error_msg: Custom message to return upon hitting the rate limit.
    """
    if methods is None:
        methods = ["POST", "GET"]
    elif isinstance(methods, str):
        methods = [methods.upper()]
    else:
        methods = [m.upper() for m in methods]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(*args, **kwargs):
            # Check if global rate limiting is enabled
            if not getattr(settings, "RATELIMIT_ENABLE", True):
                return view_func(*args, **kwargs)

            # Resolve request object (supports both function views and class-based methods)
            request = None
            if args:
                if hasattr(args[0], "META"):
                    request = args[0]
                elif len(args) > 1 and hasattr(args[1], "META"):
                    request = args[1]

            if request and (request.method in methods or "ALL" in methods):
                # Resolve rate string
                resolved_rate = rate
                if not resolved_rate and rate_key:
                    rates_config = getattr(settings, "RATELIMIT_RATES", {})
                    resolved_rate = rates_config.get(rate_key, default_rate)
                if not resolved_rate:
                    resolved_rate = default_rate

                grp = group or f"{view_func.__module__}.{view_func.__name__}"

                limited = is_ratelimited(
                    request=request,
                    group=grp,
                    key=key,
                    rate=resolved_rate,
                    method=methods,
                    increment=True,
                )

                if limited:
                    msg = error_msg or "Too many requests. Please slow down and try again shortly."
                    logger.warning(
                        "Rate limit exceeded for %s on %s (group=%s, rate=%s)",
                        getattr(request.user, "username", "anonymous"),
                        request.path,
                        grp,
                        resolved_rate,
                    )

                    if _is_ajax_or_json(request):
                        return JsonResponse(
                            {
                                "ok": False,
                                "status": "rate_limited",
                                "error": msg,
                            },
                            status=429,
                        )

                    # Standard HTML / Form submission response
                    messages.error(request, msg)
                    referer = request.META.get("HTTP_REFERER")
                    if referer:
                        return redirect(referer)
                    return HttpResponse(msg, status=429)

            return view_func(*args, **kwargs)

        return _wrapped_view

    return decorator
