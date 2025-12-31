from clerk_backend_api import Clerk, ResponseValidationError
from django.core.exceptions import PermissionDenied
from django.conf import settings


def verify_auth_token(oauthtoken: str):
    if not oauthtoken:
        raise PermissionDenied

    try:
        sdk = Clerk(bearer_auth=settings.CLERK_SECRET_KEY)
        request_state = sdk.sessions.get(session_id=oauthtoken)

        if request_state is None or not hasattr(request_state, 'user_id'):
            raise PermissionDenied
    except ResponseValidationError as e:
        raise PermissionDenied

    return request_state.user_id
