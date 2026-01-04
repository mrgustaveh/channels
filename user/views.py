from django.core.exceptions import PermissionDenied
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListAPIView, RetrieveAPIView
from .models import Account
from .serializers import AccountSerializer
from .utils.clerkauth import verify_auth_token


class AccountViewset(ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

    def get_queryset(self): # type: ignore
        try:
            oauthToken = self.request.META.get('HTTP_AUTHORIZATION')
            clerkid = verify_auth_token(oauthToken)

            return self.queryset.filter(clerk_id=clerkid)
        except:
            raise PermissionDenied
    
    def perform_create(self, serializer):
        try:
            oauthToken = self.request.META.get('HTTP_AUTHORIZATION')
            clerkid = verify_auth_token(oauthToken)

            return serializer.save(clerk_id=clerkid)
        except:
            raise PermissionDenied
    
    def partial_update(self, request, *args, **kwargs):
        try:
            oauthToken = self.request.META.get('HTTP_AUTHORIZATION')
            clerkid = verify_auth_token(oauthToken)
            
            account = self.get_object()

            if account and account.clerk_id != clerkid:
                raise PermissionDenied

            return super().partial_update(request, *args, **kwargs)
        except:
            raise PermissionDenied


class AccountsListView(ListAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

    def list(self, request, *args, **kwargs):
        try:
            oauthToken = self.request.META.get('HTTP_AUTHORIZATION')
            verify_auth_token(oauthToken)

            return super().list(request, *args, **kwargs)
        except:
            raise PermissionDenied
    

class AccountRetrieveView(RetrieveAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

    def get_object(self):
        try:
            oauthToken = self.request.META.get('HTTP_AUTHORIZATION')
            verify_auth_token(oauthToken)

            return super().get_object()
        except:
            raise PermissionDenied

    
