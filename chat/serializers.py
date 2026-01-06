from rest_framework.serializers import ModelSerializer, SerializerMethodField
from user.serializers import AccountSerializer
from .models import UserChat, GroupChat, Message


class UserChatSerializer(ModelSerializer):
    user1 = AccountSerializer(read_only=True)
    user2 = AccountSerializer(read_only=True)
    
    class Meta:
        model = UserChat
        fields = ['chat_id', 'user1', 'user2', 'created', 'updated']
        read_only_fields = ['chat_id', 'created', 'updated']


class UserChatListSerializer(ModelSerializer):
    user1 = AccountSerializer(read_only=True)
    user2 = AccountSerializer(read_only=True)
    
    class Meta:
        model = UserChat
        fields = ['chat_id', 'user1', 'user2', 'updated']


class GroupChatSerializer(ModelSerializer):
    creator = AccountSerializer(read_only=True)
    members = AccountSerializer(many=True, read_only=True)
    members_count = SerializerMethodField()
    
    class Meta:
        model = GroupChat
        fields = ['chat_id', 'name', 'description', 'creator', 'members', 'members_count', 'profile_pic', 'created', 'updated']
        read_only_fields = ['chat_id', 'creator', 'created', 'updated']
    
    def get_members_count(self, obj):
        return obj.members.count()


class GroupChatListSerializer(ModelSerializer):
    creator = AccountSerializer(read_only=True)
    members_count = SerializerMethodField()
    
    class Meta:
        model = GroupChat
        fields = ['chat_id', 'name', 'creator', 'members_count', 'profile_pic', 'updated']
    
    def get_members_count(self, obj):
        return obj.members.count()


class MessageSerializer(ModelSerializer):
    sender = AccountSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = ['message_id', 'sender', 'text_content', 'file_content_url', 'chat_type', 'user_chat', 'group_chat', 'created']
        read_only_fields = ['message_id', 'sender', 'created']


class MessageCreateSerializer(ModelSerializer):
    class Meta:
        model = Message
        fields = ['text_content', 'file_content_url', 'chat_type', 'user_chat', 'group_chat']
    
    def validate(self, data):
        chat_type = data.get('chat_type')
        user_chat = data.get('user_chat')
        group_chat = data.get('group_chat')
        
        if chat_type == 'user' and not user_chat:
            raise ValueError('user_chat is required when chat_type is "user"')
        if chat_type == 'group' and not group_chat:
            raise ValueError('group_chat is required when chat_type is "group"')
        
        return data


class MessageListSerializer(ModelSerializer):
    sender = AccountSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = ['message_id', 'sender', 'text_content', 'file_content_url', 'created']
