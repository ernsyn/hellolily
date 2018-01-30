from rest_framework import mixins
from rest_framework.filters import OrderingFilter, DjangoFilterBackend
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from email_wrapper_lib.models import EmailAccount, EmailMessage
from lily.email.api.filters import EmailAccountFilter, EmailMessageFilter
from lily.email.api.serializers import EmailAccountSerializer, EmailMessageSerializer
from lily.email.utils import get_email_accounts


class EmailAccountViewSet(ModelViewSet):
    # Set the queryset.
    queryset = EmailAccount.objects
    # Set the serializer class for this viewset.
    serializer_class = EmailAccountSerializer
    # Set all filter backends that this viewset uses.
    filter_backends = (OrderingFilter, DjangoFilterBackend,)

    # OrderingFilter: set all possible fields to order by.
    ordering_fields = ('id',)
    # OrderingFilter: set the default ordering fields.
    ordering = ('id',)
    # DjangoFilter: set the filter class.
    filter_class = EmailAccountFilter


class EmailMessageViewSet(mixins.RetrieveModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin,
                          mixins.ListModelMixin,
                          GenericViewSet):
    # Set the queryset.
    queryset = EmailMessage.objects
    # Set the serializer class for this viewset.
    serializer_class = EmailMessageSerializer
    # Set all filter backends that this viewset uses.
    filter_backends = (OrderingFilter, DjangoFilterBackend,)

    # OrderingFilter: set all possible fields to order by.
    ordering_fields = ('id',)
    # OrderingFilter: set the default ordering fields.
    ordering = ('id',)
    # DjangoFilter: set the filter class.
    filter_class = EmailMessageFilter

    # list/detail
    # move to folder (INBOX/TRASH/LABEL)
    # search
    # mark as read/important/spam
