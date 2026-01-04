from django.urls import path
from .views import AccountViewset, AccountsListView, AccountRetrieveView

urlpatterns = [
    path('', AccountViewset.as_view({'get': 'list', 'post': 'create'}), name='accounts-list'),
    path('<str:pk>/', AccountViewset.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='accounts-detail'),
    path('list/', AccountsListView.as_view(), name='accounts-list'),
    path('retrieve/<str:pk>/', AccountRetrieveView.as_view(), name='accounts-retrieve'),
]