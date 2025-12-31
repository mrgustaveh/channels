from django.core.exceptions import PermissionDenied
from ..utils.clerkauth import verify_auth_token


class ClerkAuthMiddleware:
    EXEMPT_PATHS = ['/admin']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(path) for path in self.EXEMPT_PATHS):
            return self.get_response(request)

        clerk_session_id = request.headers.get('HTTP_AUTHORIZATION')

        if not clerk_session_id:
            raise PermissionDenied

        try:
            verify_auth_token(clerk_session_id)
            return self.get_response(request)
        except Exception as e:
            raise PermissionDenied
