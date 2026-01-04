from django.test import TestCase
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import Mock, patch
from .models import Account
from .serializers import AccountSerializer
from .utils.clerkauth import verify_auth_token
from .middleware.clerkauth import ClerkAuthMiddleware


class AccountModelTest(TestCase):
    """Test cases for Account model"""

    def test_account_creation(self):
        """Test creating an account with minimal fields"""
        account = Account.objects.create(
            clerk_id='clerk_123',
            username='testuser'
        )
        self.assertIsNotNone(account.account_id)
        self.assertEqual(account.clerk_id, 'clerk_123')
        self.assertEqual(account.username, 'testuser')
        self.assertIsNotNone(account.created)

    def test_account_with_all_fields(self):
        """Test creating an account with all fields"""
        account = Account.objects.create(
            clerk_id='clerk_456',
            username='fulluser',
            display_pic='https://example.com/pic.jpg'
        )
        self.assertEqual(account.clerk_id, 'clerk_456')
        self.assertEqual(account.username, 'fulluser')
        self.assertEqual(account.display_pic, 'https://example.com/pic.jpg')

    def test_account_clerk_id_unique(self):
        """Test that clerk_id must be unique"""
        Account.objects.create(clerk_id='clerk_unique', username='user1')
        with self.assertRaises(Exception):
            Account.objects.create(clerk_id='clerk_unique', username='user2')

    def test_account_username_unique(self):
        """Test that username must be unique"""
        Account.objects.create(clerk_id='clerk_1', username='uniqueuser')
        with self.assertRaises(Exception):
            Account.objects.create(clerk_id='clerk_2', username='uniqueuser')

    def test_account_str_method(self):
        """Test Account __str__ method"""
        account = Account.objects.create(
            clerk_id='clerk_789',
            username='struser'
        )
        self.assertEqual(str(account), 'struser')

    def test_account_ordering(self):
        """Test that accounts are ordered by created date"""
        account1 = Account.objects.create(clerk_id='clerk_1', username='user1')
        account2 = Account.objects.create(clerk_id='clerk_2', username='user2')
        account3 = Account.objects.create(clerk_id='clerk_3', username='user3')
        
        accounts = list(Account.objects.all())
        self.assertEqual(accounts[0], account1)
        self.assertEqual(accounts[1], account2)
        self.assertEqual(accounts[2], account3)


class AccountSerializerTest(TestCase):
    """Test cases for AccountSerializer"""

    def test_serializer_fields(self):
        """Test that serializer includes correct fields"""
        account = Account.objects.create(
            clerk_id='clerk_serializer',
            username='serializeruser',
            display_pic='https://example.com/pic.jpg'
        )
        serializer = AccountSerializer(account)
        self.assertIn('account_id', serializer.data)
        self.assertIn('username', serializer.data)
        self.assertIn('display_pic', serializer.data)
        self.assertIn('created', serializer.data)
        self.assertNotIn('clerk_id', serializer.data)

    def test_serializer_serialization(self):
        """Test serializing an account"""
        account = Account.objects.create(
            clerk_id='clerk_ser',
            username='testserializer',
            display_pic='https://example.com/pic.jpg'
        )
        serializer = AccountSerializer(account)
        self.assertEqual(serializer.data['username'], 'testserializer')
        self.assertEqual(serializer.data['display_pic'], 'https://example.com/pic.jpg')
        self.assertEqual(str(serializer.data['account_id']), str(account.account_id))

    def test_serializer_deserialization(self):
        """Test deserializing account data"""
        data = {
            'username': 'newuser',
            'display_pic': 'https://example.com/newpic.jpg'
        }
        serializer = AccountSerializer(data=data)
        self.assertTrue(serializer.is_valid())


class ClerkAuthUtilityTest(TestCase):
    """Test cases for verify_auth_token utility"""

    @patch('user.utils.clerkauth.Clerk')
    def test_verify_auth_token_success(self, mock_clerk_class):
        """Test successful token verification"""
        mock_session = Mock()
        mock_session.user_id = 'clerk_user_123'
        
        mock_clerk_instance = Mock()
        mock_clerk_instance.sessions.get.return_value = mock_session
        mock_clerk_class.return_value = mock_clerk_instance
        
        result = verify_auth_token('valid_token')
        self.assertEqual(result, 'clerk_user_123')
        mock_clerk_instance.sessions.get.assert_called_once_with(session_id='valid_token')

    @patch('user.utils.clerkauth.Clerk')
    def test_verify_auth_token_empty_token(self, mock_clerk_class):
        """Test that empty token raises PermissionDenied"""
        with self.assertRaises(PermissionDenied):
            verify_auth_token('')

    def test_verify_auth_token_none_token(self):
        """Test that None token raises PermissionDenied"""
        with self.assertRaises(PermissionDenied):
            verify_auth_token(None)

    @patch('user.utils.clerkauth.Clerk')
    def test_verify_auth_token_invalid_token(self, mock_clerk_class):
        """Test that invalid token raises PermissionDenied"""
        from clerk_backend_api import ResponseValidationError
        
        mock_clerk_instance = Mock()
        mock_clerk_instance.sessions.get.side_effect = ResponseValidationError(
            message='Invalid token', 
            raw_response=Mock(status_code=401), 
            cause=Exception('Invalid token')
        )
        mock_clerk_class.return_value = mock_clerk_instance
        
        with self.assertRaises(PermissionDenied):
            verify_auth_token('invalid_token')

    @patch('user.utils.clerkauth.Clerk')
    def test_verify_auth_token_no_user_id(self, mock_clerk_class):
        """Test that session without user_id raises PermissionDenied"""
        mock_session = Mock()
        del mock_session.user_id  # Remove user_id attribute
        
        mock_clerk_instance = Mock()
        mock_clerk_instance.sessions.get.return_value = mock_session
        mock_clerk_class.return_value = mock_clerk_instance
        
        with self.assertRaises(PermissionDenied):
            verify_auth_token('token_without_user')

    @patch('user.utils.clerkauth.Clerk')
    def test_verify_auth_token_none_session(self, mock_clerk_class):
        """Test that None session raises PermissionDenied"""
        mock_clerk_instance = Mock()
        mock_clerk_instance.sessions.get.return_value = None
        mock_clerk_class.return_value = mock_clerk_instance
        
        with self.assertRaises(PermissionDenied):
            verify_auth_token('token_none_session')


class ClerkAuthMiddlewareTest(TestCase):
    """Test cases for ClerkAuthMiddleware"""

    def setUp(self):
        """Set up test client and middleware"""
        self.get_response = Mock(return_value=Mock(status_code=200))
        self.middleware = ClerkAuthMiddleware(self.get_response)

    @patch('user.middleware.clerkauth.verify_auth_token')
    def test_middleware_exempts_admin_path(self, mock_verify):
        """Test that /admin paths are exempt from authentication"""
        request = Mock()
        request.path = '/admin/'
        request.headers = {}
        
        response = self.middleware(request)
        
        self.get_response.assert_called_once_with(request)
        mock_verify.assert_not_called()

    @patch('user.middleware.clerkauth.verify_auth_token')
    def test_middleware_exempts_admin_subpath(self, mock_verify):
        """Test that /admin subpaths are exempt from authentication"""
        request = Mock()
        request.path = '/admin/users/'
        request.headers = {}
        
        response = self.middleware(request)
        
        self.get_response.assert_called_once_with(request)
        mock_verify.assert_not_called()

    @patch('user.middleware.clerkauth.verify_auth_token')
    def test_middleware_valid_token(self, mock_verify):
        """Test middleware with valid token"""
        mock_verify.return_value = 'clerk_user_123'
        request = Mock()
        request.path = '/api/auth/'
        request.headers = Mock()
        request.headers.get = Mock(return_value='valid_token')
        
        response = self.middleware(request)
        
        mock_verify.assert_called_once_with('valid_token')
        self.get_response.assert_called_once_with(request)
        request.headers.get.assert_called_once_with('HTTP_AUTHORIZATION')

    @patch('user.middleware.clerkauth.verify_auth_token')
    def test_middleware_missing_token(self, mock_verify):
        """Test middleware raises PermissionDenied when token is missing"""
        request = Mock()
        request.path = '/api/auth/'
        request.headers = Mock()
        request.headers.get = Mock(return_value=None)
        
        with self.assertRaises(PermissionDenied):
            self.middleware(request)
        
        mock_verify.assert_not_called()
        request.headers.get.assert_called_once_with('HTTP_AUTHORIZATION')

    @patch('user.middleware.clerkauth.verify_auth_token')
    def test_middleware_invalid_token(self, mock_verify):
        """Test middleware raises PermissionDenied when token is invalid"""
        mock_verify.side_effect = PermissionDenied()
        request = Mock()
        request.path = '/api/auth/'
        request.headers = Mock()
        request.headers.get = Mock(return_value='invalid_token')
        
        with self.assertRaises(PermissionDenied):
            self.middleware(request)
        
        mock_verify.assert_called_once_with('invalid_token')
        request.headers.get.assert_called_once_with('HTTP_AUTHORIZATION')


class AccountViewsetTest(APITestCase):
    """Test cases for AccountViewset"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.clerk_id_1 = 'clerk_user_1'
        self.clerk_id_2 = 'clerk_user_2'
        
        # Create test accounts
        self.account1 = Account.objects.create(
            clerk_id=self.clerk_id_1,
            username='user1',
            display_pic='https://example.com/user1.jpg'
        )
        self.account2 = Account.objects.create(
            clerk_id=self.clerk_id_2,
            username='user2',
            display_pic='https://example.com/user2.jpg'
        )

    @patch('user.views.verify_auth_token')
    def test_list_accounts_filtered_by_clerk_id(self, mock_verify):
        """Test that list returns only accounts for authenticated user"""
        mock_verify.return_value = self.clerk_id_1
        
        url = reverse('accounts-list')
        response = self.client.get(url, HTTP_AUTHORIZATION='eyJhbGciOiJSUzI1NiIsImNhdCI6ImNsX0I3ZDRQRDExMUFBQSIsImtpZCI6Imluc18zMnBSOFNwdUVxMWQ1T3ZtaldhTzFmVmJ6OW4iLCJ0eXAiOiJKV1QifQ.eyJhenAiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguYWNjb3VudHMuZGV2IiwiZXhwIjoxNzY3NTI2MDQ4LCJmdmEiOlswLC0xXSwiaWF0IjoxNzY3NTI1OTg4LCJpc3MiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguY2xlcmsuYWNjb3VudHMuZGV2IiwibmJmIjoxNzY3NTI1OTc4LCJzaWQiOiJzZXNzXzM3bjVLeVIwY1Q2Y2lCSGQwUUVXbnhpZ3BUcCIsInN0cyI6ImFjdGl2ZSIsInN1YiI6InVzZXJfMzJ0SVJaN25PV1dsNE5uYVBrSmoxTDdqczZMIiwidiI6Mn0.leJdcJ3FMam0QGFEEEWIN34WnUYdnZgGeeyO6H59gEf2VEaLuVkN64riSdtwYx_3DzIqgAl5BdhRyfwbM1oAjGXEXUDmHabm2sHZjR-9qbXu2mu-vGnF2FjJ3XR4lcxVywqVlDqb5CpBuukz9KQKBG8Kw38SyKKhu_1APpvq2NZLCHHKrsMk1X4-GkEuArwqi7XE1aaBCKVH244myxpQYy7JIbbMAXg2l2LHsgEkz-EJvu1IAemjwKl5W9CJnXorFVoe87aUwOgs2XGjNXr_6RkdtLjiAdn-X-pHDZuWbuRsQKQF6kEoLLgAVPm2bOm5OVBOggbkhKWsE6du65lxsw')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'user1')
        mock_verify.assert_called_once()

    @patch('user.views.verify_auth_token')
    def test_list_accounts_no_matching_clerk_id(self, mock_verify):
        """Test that list returns empty when no accounts match clerk_id"""
        mock_verify.return_value = 'clerk_user_3'
        
        url = reverse('accounts-list')
        response = self.client.get(url, HTTP_AUTHORIZATION='eyJhbGciOiJSUzI1NiIsImNhdCI6ImNsX0I3ZDRQRDExMUFBQSIsImtpZCI6Imluc18zMnBSOFNwdUVxMWQ1T3ZtaldhTzFmVmJ6OW4iLCJ0eXAiOiJKV1QifQ.eyJhenAiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguYWNjb3VudHMuZGV2IiwiZXhwIjoxNzY3NTI2MDQ4LCJmdmEiOlswLC0xXSwiaWF0IjoxNzY3NTI1OTg4LCJpc3MiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguY2xlcmsuYWNjb3VudHMuZGV2IiwibmJmIjoxNzY3NTI1OTc4LCJzaWQiOiJzZXNzXzM3bjVLeVIwY1Q2Y2lCSGQwUUVXbnhpZ3BUcCIsInN0cyI6ImFjdGl2ZSIsInN1YiI6InVzZXJfMzJ0SVJaN25PV1dsNE5uYVBrSmoxTDdqczZMIiwidiI6Mn0.leJdcJ3FMam0QGFEEEWIN34WnUYdnZgGeeyO6H59gEf2VEaLuVkN64riSdtwYx_3DzIqgAl5BdhRyfwbM1oAjGXEXUDmHabm2sHZjR-9qbXu2mu-vGnF2FjJ3XR4lcxVywqVlDqb5CpBuukz9KQKBG8Kw38SyKKhu_1APpvq2NZLCHHKrsMk1X4-GkEuArwqi7XE1aaBCKVH244myxpQYy7JIbbMAXg2l2LHsgEkz-EJvu1IAemjwKl5W9CJnXorFVoe87aUwOgs2XGjNXr_6RkdtLjiAdn-X-pHDZuWbuRsQKQF6kEoLLgAVPm2bOm5OVBOggbkhKWsE6du65lxsw')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    @patch('user.views.verify_auth_token')
    def test_list_accounts_invalid_token(self, mock_verify):
        """Test that list raises PermissionDenied with invalid token"""
        mock_verify.side_effect = PermissionDenied()
        
        url = reverse('accounts-list')
        response = self.client.get(url, HTTP_AUTHORIZATION='invalid_token')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('user.views.verify_auth_token')
    def test_create_account(self, mock_verify):
        """Test creating a new account"""
        mock_verify.return_value = 'clerk_new_user'
        
        url = reverse('accounts-list')
        data = {
            'username': 'newuser',
            'display_pic': 'https://example.com/newuser.jpg'
        }
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION='eyJhbGciOiJSUzI1NiIsImNhdCI6ImNsX0I3ZDRQRDExMUFBQSIsImtpZCI6Imluc18zMnBSOFNwdUVxMWQ1T3ZtaldhTzFmVmJ6OW4iLCJ0eXAiOiJKV1QifQ.eyJhenAiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguYWNjb3VudHMuZGV2IiwiZXhwIjoxNzY3NTI2MDQ4LCJmdmEiOlswLC0xXSwiaWF0IjoxNzY3NTI1OTg4LCJpc3MiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguY2xlcmsuYWNjb3VudHMuZGV2IiwibmJmIjoxNzY3NTI1OTc4LCJzaWQiOiJzZXNzXzM3bjVLeVIwY1Q2Y2lCSGQwUUVXbnhpZ3BUcCIsInN0cyI6ImFjdGl2ZSIsInN1YiI6InVzZXJfMzJ0SVJaN25PV1dsNE5uYVBrSmoxTDdqczZMIiwidiI6Mn0.leJdcJ3FMam0QGFEEEWIN34WnUYdnZgGeeyO6H59gEf2VEaLuVkN64riSdtwYx_3DzIqgAl5BdhRyfwbM1oAjGXEXUDmHabm2sHZjR-9qbXu2mu-vGnF2FjJ3XR4lcxVywqVlDqb5CpBuukz9KQKBG8Kw38SyKKhu_1APpvq2NZLCHHKrsMk1X4-GkEuArwqi7XE1aaBCKVH244myxpQYy7JIbbMAXg2l2LHsgEkz-EJvu1IAemjwKl5W9CJnXorFVoe87aUwOgs2XGjNXr_6RkdtLjiAdn-X-pHDZuWbuRsQKQF6kEoLLgAVPm2bOm5OVBOggbkhKWsE6du65lxsw')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'newuser')
        self.assertEqual(Account.objects.filter(clerk_id='clerk_new_user').count(), 1)

    @patch('user.views.verify_auth_token')
    def test_create_account_invalid_token(self, mock_verify):
        """Test that create raises PermissionDenied with invalid token"""
        mock_verify.side_effect = PermissionDenied()
        
        url = reverse('accounts-list')
        data = {'username': 'newuser'}
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION='invalid_token')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('user.views.verify_auth_token')
    def test_retrieve_account(self, mock_verify):
        """Test retrieving an account"""
        mock_verify.return_value = self.clerk_id_1
        
        url = reverse('accounts-detail', kwargs={'pk': str(self.account1.account_id)})
        response = self.client.get(url, HTTP_AUTHORIZATION='eyJhbGciOiJSUzI1NiIsImNhdCI6ImNsX0I3ZDRQRDExMUFBQSIsImtpZCI6Imluc18zMnBSOFNwdUVxMWQ1T3ZtaldhTzFmVmJ6OW4iLCJ0eXAiOiJKV1QifQ.eyJhenAiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguYWNjb3VudHMuZGV2IiwiZXhwIjoxNzY3NTI2MDQ4LCJmdmEiOlswLC0xXSwiaWF0IjoxNzY3NTI1OTg4LCJpc3MiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguY2xlcmsuYWNjb3VudHMuZGV2IiwibmJmIjoxNzY3NTI1OTc4LCJzaWQiOiJzZXNzXzM3bjVLeVIwY1Q2Y2lCSGQwUUVXbnhpZ3BUcCIsInN0cyI6ImFjdGl2ZSIsInN1YiI6InVzZXJfMzJ0SVJaN25PV1dsNE5uYVBrSmoxTDdqczZMIiwidiI6Mn0.leJdcJ3FMam0QGFEEEWIN34WnUYdnZgGeeyO6H59gEf2VEaLuVkN64riSdtwYx_3DzIqgAl5BdhRyfwbM1oAjGXEXUDmHabm2sHZjR-9qbXu2mu-vGnF2FjJ3XR4lcxVywqVlDqb5CpBuukz9KQKBG8Kw38SyKKhu_1APpvq2NZLCHHKrsMk1X4-GkEuArwqi7XE1aaBCKVH244myxpQYy7JIbbMAXg2l2LHsgEkz-EJvu1IAemjwKl5W9CJnXorFVoe87aUwOgs2XGjNXr_6RkdtLjiAdn-X-pHDZuWbuRsQKQF6kEoLLgAVPm2bOm5OVBOggbkhKWsE6du65lxsw')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'user1')

    @patch('user.views.verify_auth_token')
    def test_retrieve_account_invalid_token(self, mock_verify):
        """Test that retrieve raises PermissionDenied with invalid token"""
        mock_verify.side_effect = PermissionDenied()
        
        url = reverse('accounts-detail', kwargs={'pk': str(self.account1.account_id)})
        response = self.client.get(url, HTTP_AUTHORIZATION='invalid_token')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('user.views.verify_auth_token')
    def test_partial_update_own_account(self, mock_verify):
        """Test updating own account"""
        mock_verify.return_value = self.clerk_id_1
        
        url = reverse('accounts-detail', kwargs={'pk': str(self.account1.account_id)})
        data = {'username': 'updated_user1'}
        response = self.client.patch(url, data, format='json', HTTP_AUTHORIZATION='eyJhbGciOiJSUzI1NiIsImNhdCI6ImNsX0I3ZDRQRDExMUFBQSIsImtpZCI6Imluc18zMnBSOFNwdUVxMWQ1T3ZtaldhTzFmVmJ6OW4iLCJ0eXAiOiJKV1QifQ.eyJhenAiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguYWNjb3VudHMuZGV2IiwiZXhwIjoxNzY3NTI2MDQ4LCJmdmEiOlswLC0xXSwiaWF0IjoxNzY3NTI1OTg4LCJpc3MiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguY2xlcmsuYWNjb3VudHMuZGV2IiwibmJmIjoxNzY3NTI1OTc4LCJzaWQiOiJzZXNzXzM3bjVLeVIwY1Q2Y2lCSGQwUUVXbnhpZ3BUcCIsInN0cyI6ImFjdGl2ZSIsInN1YiI6InVzZXJfMzJ0SVJaN25PV1dsNE5uYVBrSmoxTDdqczZMIiwidiI6Mn0.leJdcJ3FMam0QGFEEEWIN34WnUYdnZgGeeyO6H59gEf2VEaLuVkN64riSdtwYx_3DzIqgAl5BdhRyfwbM1oAjGXEXUDmHabm2sHZjR-9qbXu2mu-vGnF2FjJ3XR4lcxVywqVlDqb5CpBuukz9KQKBG8Kw38SyKKhu_1APpvq2NZLCHHKrsMk1X4-GkEuArwqi7XE1aaBCKVH244myxpQYy7JIbbMAXg2l2LHsgEkz-EJvu1IAemjwKl5W9CJnXorFVoe87aUwOgs2XGjNXr_6RkdtLjiAdn-X-pHDZuWbuRsQKQF6kEoLLgAVPm2bOm5OVBOggbkhKWsE6du65lxsw')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.username, 'updated_user1')

    @patch('user.views.verify_auth_token')
    def test_partial_update_other_account(self, mock_verify):
        """Test that updating another user's account raises PermissionDenied"""
        mock_verify.return_value = self.clerk_id_1
        
        url = reverse('accounts-detail', kwargs={'pk': str(self.account2.account_id)})
        data = {'username': 'hacked_user2'}
        response = self.client.patch(url, data, format='json', HTTP_AUTHORIZATION='eyJhbGciOiJSUzI1NiIsImNhdCI6ImNsX0I3ZDRQRDExMUFBQSIsImtpZCI6Imluc18zMnBSOFNwdUVxMWQ1T3ZtaldhTzFmVmJ6OW4iLCJ0eXAiOiJKV1QifQ.eyJhenAiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguYWNjb3VudHMuZGV2IiwiZXhwIjoxNzY3NTI2MDQ4LCJmdmEiOlswLC0xXSwiaWF0IjoxNzY3NTI1OTg4LCJpc3MiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguY2xlcmsuYWNjb3VudHMuZGV2IiwibmJmIjoxNzY3NTI1OTc4LCJzaWQiOiJzZXNzXzM3bjVLeVIwY1Q2Y2lCSGQwUUVXbnhpZ3BUcCIsInN0cyI6ImFjdGl2ZSIsInN1YiI6InVzZXJfMzJ0SVJaN25PV1dsNE5uYVBrSmoxTDdqczZMIiwidiI6Mn0.leJdcJ3FMam0QGFEEEWIN34WnUYdnZgGeeyO6H59gEf2VEaLuVkN64riSdtwYx_3DzIqgAl5BdhRyfwbM1oAjGXEXUDmHabm2sHZjR-9qbXu2mu-vGnF2FjJ3XR4lcxVywqVlDqb5CpBuukz9KQKBG8Kw38SyKKhu_1APpvq2NZLCHHKrsMk1X4-GkEuArwqi7XE1aaBCKVH244myxpQYy7JIbbMAXg2l2LHsgEkz-EJvu1IAemjwKl5W9CJnXorFVoe87aUwOgs2XGjNXr_6RkdtLjiAdn-X-pHDZuWbuRsQKQF6kEoLLgAVPm2bOm5OVBOggbkhKWsE6du65lxsw')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('user.views.verify_auth_token')
    def test_partial_update_invalid_token(self, mock_verify):
        """Test that partial update raises PermissionDenied with invalid token"""
        mock_verify.side_effect = PermissionDenied()
        
        url = reverse('accounts-detail', kwargs={'pk': str(self.account1.account_id)})
        data = {'username': 'updated_user1'}
        response = self.client.patch(url, data, format='json', HTTP_AUTHORIZATION='invalid_token')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AccountsListViewTest(APITestCase):
    """Test cases for AccountsListView"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.account1 = Account.objects.create(
            clerk_id='clerk_list_1',
            username='listuser1'
        )
        self.account2 = Account.objects.create(
            clerk_id='clerk_list_2',
            username='listuser2'
        )

    @patch('user.views.verify_auth_token')
    def test_list_all_accounts(self, mock_verify):
        """Test listing all accounts with valid token"""
        mock_verify.return_value = 'clerk_list_1'
        
        url = reverse('accounts-list')
        response = self.client.get(url, HTTP_AUTHORIZATION='eyJhbGciOiJSUzI1NiIsImNhdCI6ImNsX0I3ZDRQRDExMUFBQSIsImtpZCI6Imluc18zMnBSOFNwdUVxMWQ1T3ZtaldhTzFmVmJ6OW4iLCJ0eXAiOiJKV1QifQ.eyJhenAiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguYWNjb3VudHMuZGV2IiwiZXhwIjoxNzY3NTI2MDQ4LCJmdmEiOlswLC0xXSwiaWF0IjoxNzY3NTI1OTg4LCJpc3MiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguY2xlcmsuYWNjb3VudHMuZGV2IiwibmJmIjoxNzY3NTI1OTc4LCJzaWQiOiJzZXNzXzM3bjVLeVIwY1Q2Y2lCSGQwUUVXbnhpZ3BUcCIsInN0cyI6ImFjdGl2ZSIsInN1YiI6InVzZXJfMzJ0SVJaN25PV1dsNE5uYVBrSmoxTDdqczZMIiwidiI6Mn0.leJdcJ3FMam0QGFEEEWIN34WnUYdnZgGeeyO6H59gEf2VEaLuVkN64riSdtwYx_3DzIqgAl5BdhRyfwbM1oAjGXEXUDmHabm2sHZjR-9qbXu2mu-vGnF2FjJ3XR4lcxVywqVlDqb5CpBuukz9KQKBG8Kw38SyKKhu_1APpvq2NZLCHHKrsMk1X4-GkEuArwqi7XE1aaBCKVH244myxpQYy7JIbbMAXg2l2LHsgEkz-EJvu1IAemjwKl5W9CJnXorFVoe87aUwOgs2XGjNXr_6RkdtLjiAdn-X-pHDZuWbuRsQKQF6kEoLLgAVPm2bOm5OVBOggbkhKWsE6du65lxsw')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch('user.views.verify_auth_token')
    def test_list_invalid_token(self, mock_verify):
        """Test that list raises PermissionDenied with invalid token"""
        mock_verify.side_effect = PermissionDenied()
        
        url = reverse('accounts-list')
        response = self.client.get(url, HTTP_AUTHORIZATION='invalid_token')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AccountRetrieveViewTest(APITestCase):
    """Test cases for AccountRetrieveView"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.account = Account.objects.create(
            clerk_id='clerk_retrieve',
            username='retrieveuser',
            display_pic='https://example.com/retrieve.jpg'
        )

    @patch('user.views.verify_auth_token')
    def test_retrieve_account(self, mock_verify):
        """Test retrieving an account with valid token"""
        mock_verify.return_value = 'clerk_retrieve'
        
        url = reverse('accounts-detail', kwargs={'pk': str(self.account.account_id)})
        response = self.client.get(url, HTTP_AUTHORIZATION='eyJhbGciOiJSUzI1NiIsImNhdCI6ImNsX0I3ZDRQRDExMUFBQSIsImtpZCI6Imluc18zMnBSOFNwdUVxMWQ1T3ZtaldhTzFmVmJ6OW4iLCJ0eXAiOiJKV1QifQ.eyJhenAiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguYWNjb3VudHMuZGV2IiwiZXhwIjoxNzY3NTI2MDQ4LCJmdmEiOlswLC0xXSwiaWF0IjoxNzY3NTI1OTg4LCJpc3MiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguY2xlcmsuYWNjb3VudHMuZGV2IiwibmJmIjoxNzY3NTI1OTc4LCJzaWQiOiJzZXNzXzM3bjVLeVIwY1Q2Y2lCSGQwUUVXbnhpZ3BUcCIsInN0cyI6ImFjdGl2ZSIsInN1YiI6InVzZXJfMzJ0SVJaN25PV1dsNE5uYVBrSmoxTDdqczZMIiwidiI6Mn0.leJdcJ3FMam0QGFEEEWIN34WnUYdnZgGeeyO6H59gEf2VEaLuVkN64riSdtwYx_3DzIqgAl5BdhRyfwbM1oAjGXEXUDmHabm2sHZjR-9qbXu2mu-vGnF2FjJ3XR4lcxVywqVlDqb5CpBuukz9KQKBG8Kw38SyKKhu_1APpvq2NZLCHHKrsMk1X4-GkEuArwqi7XE1aaBCKVH244myxpQYy7JIbbMAXg2l2LHsgEkz-EJvu1IAemjwKl5W9CJnXorFVoe87aUwOgs2XGjNXr_6RkdtLjiAdn-X-pHDZuWbuRsQKQF6kEoLLgAVPm2bOm5OVBOggbkhKWsE6du65lxsw')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'retrieveuser')
        self.assertEqual(response.data['display_pic'], 'https://example.com/retrieve.jpg')

    @patch('user.views.verify_auth_token')
    def test_retrieve_nonexistent_account(self, mock_verify):
        """Test retrieving a nonexistent account"""
        mock_verify.return_value = 'clerk_retrieve'
        
        url = reverse('accounts-detail', kwargs={'pk': '00000000-0000-0000-0000-000000000000'})
        response = self.client.get(url, HTTP_AUTHORIZATION='eyJhbGciOiJSUzI1NiIsImNhdCI6ImNsX0I3ZDRQRDExMUFBQSIsImtpZCI6Imluc18zMnBSOFNwdUVxMWQ1T3ZtaldhTzFmVmJ6OW4iLCJ0eXAiOiJKV1QifQ.eyJhenAiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguYWNjb3VudHMuZGV2IiwiZXhwIjoxNzY3NTI2MDQ4LCJmdmEiOlswLC0xXSwiaWF0IjoxNzY3NTI1OTg4LCJpc3MiOiJodHRwczovL2N1dGUtY2hpcG11bmstNjguY2xlcmsuYWNjb3VudHMuZGV2IiwibmJmIjoxNzY3NTI1OTc4LCJzaWQiOiJzZXNzXzM3bjVLeVIwY1Q2Y2lCSGQwUUVXbnhpZ3BUcCIsInN0cyI6ImFjdGl2ZSIsInN1YiI6InVzZXJfMzJ0SVJaN25PV1dsNE5uYVBrSmoxTDdqczZMIiwidiI6Mn0.leJdcJ3FMam0QGFEEEWIN34WnUYdnZgGeeyO6H59gEf2VEaLuVkN64riSdtwYx_3DzIqgAl5BdhRyfwbM1oAjGXEXUDmHabm2sHZjR-9qbXu2mu-vGnF2FjJ3XR4lcxVywqVlDqb5CpBuukz9KQKBG8Kw38SyKKhu_1APpvq2NZLCHHKrsMk1X4-GkEuArwqi7XE1aaBCKVH244myxpQYy7JIbbMAXg2l2LHsgEkz-EJvu1IAemjwKl5W9CJnXorFVoe87aUwOgs2XGjNXr_6RkdtLjiAdn-X-pHDZuWbuRsQKQF6kEoLLgAVPm2bOm5OVBOggbkhKWsE6du65lxsw')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('user.views.verify_auth_token')
    def test_retrieve_invalid_token(self, mock_verify):
        """Test that retrieve raises PermissionDenied with invalid token"""
        mock_verify.side_effect = PermissionDenied()
        
        url = reverse('accounts-detail', kwargs={'pk': str(self.account.account_id)})
        response = self.client.get(url, HTTP_AUTHORIZATION='invalid_token')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

