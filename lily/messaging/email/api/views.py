import logging

from django.conf import settings
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
import phonenumbers
from oauth2client.client import HttpAccessTokenRefreshError
from rest_framework import viewsets, mixins, status, filters
from rest_framework.decorators import detail_route, list_route
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from lily.accounts.models import Account
from lily.contacts.models import Contact
from lily.messaging.email.connector import GmailConnector, NotFoundError, FailedServiceCallException
from lily.messaging.email.credentials import InvalidCredentialsError
from lily.messaging.email.utils import get_email_parameter_api_dict, reindex_email_message, get_shared_email_accounts
from lily.users.models import UserInfo
from lily.users.api.serializers import LilyUserSerializer
from lily.utils.functions import format_phone_number
from lily.utils.models.models import PhoneNumber

from .serializers import (EmailLabelSerializer, EmailAccountSerializer, EmailMessageListSerializer,
                          EmailTemplateFolderSerializer, EmailTemplateSerializer, SharedEmailConfigSerializer,
                          TemplateVariableSerializer, EmailMessageDetailSerializer,
                          EmailMessageActivityStreamSerializer, EmailMessageDashboardSerializer,
                          EmailAccountSerializerSimple)
from ..models.models import (EmailLabel, EmailAccount, EmailMessage, EmailTemplateFolder, EmailTemplate,
                             SharedEmailConfig, TemplateVariable, Recipient)
from ..tasks import (trash_email_message, toggle_read_email_message,
                     add_and_remove_labels_for_message, toggle_star_email_message, toggle_spam_email_message)
from ..utils import get_filtered_message


logger = logging.getLogger(__name__)


class EmailLabelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EmailLabel.objects.all()
    serializer_class = EmailLabelSerializer

    # Set all filter backends that this viewset uses.
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('account__id', 'label_id')

    def get_queryset(self):
        return EmailLabel.objects.filter(account__tenant_id=self.request.user.tenant_id)


class SharedEmailConfigViewSet(viewsets.ModelViewSet):
    queryset = SharedEmailConfig.objects.all()
    serializer_class = SharedEmailConfigSerializer

    # Set all filter backends that this viewset uses.
    filter_backends = (DjangoFilterBackend,)
    filter_fields = {
        'email_account',
        'is_hidden',
    }

    def perform_create(self, serializer):
        email_account_id = self.request.data['email_account']
        try:
            shared_email_setting = self.get_queryset().get(email_account_id=email_account_id)
        except SharedEmailConfig.DoesNotExist:
            serializer.save(tenant_id=self.request.user.tenant_id, user=self.request.user)
        else:
            if 'is_hidden' in self.request.data:
                shared_email_setting.is_hidden = self.request.data.get('is_hidden')
                shared_email_setting.save()

    def perform_update(self, serializer):
        if 'is_hidden' in self.request.data:
            is_hidden = self.request.data.get('is_hidden')

        serializer.save(tenant_id=self.request.user.tenant_id, user=self.request.user, is_hidden=is_hidden)

    def get_queryset(self):
        return SharedEmailConfig.objects.filter(tenant_id=self.request.user.tenant_id,
                                                user=self.request.user)


class EmailAccountViewSet(mixins.DestroyModelMixin,
                          mixins.UpdateModelMixin,
                          viewsets.ReadOnlyModelViewSet):

    queryset = EmailAccount.objects.all()
    serializer_class = EmailAccountSerializer

    # Set all filter backends that this viewset uses.
    filter_backends = (DjangoFilterBackend,)
    filter_fields = (
        'owner',
        'sharedemailconfig__user__id',
        'privacy',
    )

    def get_queryset(self):
        return EmailAccount.objects.filter(is_deleted=False).distinct('id')

    def perform_destroy(self, instance):
        if instance.owner_id == self.request.user.id:
            instance.delete()
            instance.is_authorized = False
            instance.sharedemailconfig_set.all().delete()
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    @list_route()
    def mine(self, request):
        email_account_list = get_shared_email_accounts(request.user)

        serializer = self.get_serializer(email_account_list, many=True)

        return Response(serializer.data)

    @list_route()
    def color(self, request):
        email_account_list = get_shared_email_accounts(request.user)

        serializer = EmailAccountSerializerSimple(email_account_list, many=True)

        return Response(serializer.data)

    @detail_route(methods=['delete'])
    def cancel(self, request, pk):
        """
        Cancel creation of an email account and deletes it.

        Returns:

        """
        user = request.user
        account = EmailAccount.objects.get(id=pk, owner=user)

        if not account.is_authorized:
            # Account is being added, so delete it.
            account.delete()

        if not user.info.email_account_status:
            # First time setup, so set status to skipped.
            user.info.email_account_status = UserInfo.SKIPPED
            user.info.save()

            serializer = LilyUserSerializer(user, partial=True)
            return Response(serializer.data)

        return Response(status=status.HTTP_204_NO_CONTENT)


class EmailMessageViewSet(mixins.RetrieveModelMixin,
                          mixins.ListModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin,
                          GenericViewSet):

    queryset = EmailMessage.objects.all()
    serializer_class = EmailMessageDetailSerializer

    def get_object(self):
        pk = int(self.kwargs['pk'])
        try:
            email_message = EmailMessage.objects.get(pk=pk)
        except EmailMessage.DoesNotExist:
            raise NotFound()

        user = self.request.user

        try:
            email_account = EmailAccount.objects.get(pk=email_message.account.id)
        except EmailAccount.DoesNotExist:
            email_message = None
        else:
            email_message = get_filtered_message(email_message, email_account, user)

        if not email_message:
            raise NotFound()

        if not isinstance(email_message, EmailMessage) and self.action != 'retrieve':
            raise NotFound()

        return email_message

    def get_queryset(self):
        user = self.request.user
        email_messages = EmailMessage.objects.filter(account__tenant=user.tenant)

        # Get all email accounts.
        email_accounts = EmailAccount.objects.filter(tenant=user.tenant, is_deleted=False).distinct('id')

        filtered_queryset = []

        for email_message in email_messages:
            email_account = email_accounts.get(pk=email_message.account.id)

            filtered_message = get_filtered_message(email_message, email_account, user)

            if filtered_message:
                filtered_queryset.append(filtered_message)

        return filtered_queryset

    def perform_update(self, serializer):
        """
        For now, only the read status will be updated. Opposite to others email modification (archive, spam, star, etc)
        read status is a model field. This enables calculations of the unread count per label. So in this case
        update database directly. Save will trigger an update of the search index.
        """
        email = self.get_object()
        email.read = self.request.data['read']
        email.save()
        toggle_read_email_message.apply_async(args=(email.id, self.request.data['read']))

    def perform_destroy(self, instance):
        """
        Delete an email message asynchronous through the manager and not directly on the database.
        """
        trash_email_message.apply_async(args=(instance.id,))

    @detail_route(methods=['put'])
    def archive(self, request, pk=None):
        """
        Archive an email message asynchronous through the manager and not directly on the database. Just update the
        search index by an instance variable so changes are immediately visible.
        An email message is archived by removing the inbox label and the provided label of the current inbox.
        """
        email = self.get_object()

        current_inbox = request.data['data'].get('current_inbox', '')

        # Filter out labels an user should not manipulate.
        remove_labels = []
        if current_inbox and current_inbox not in settings.GMAIL_LABELS_DONT_MANIPULATE:
            remove_labels.append(current_inbox)

        # Archiving email should always remove the inbox label.
        if settings.GMAIL_LABEL_INBOX not in remove_labels:
            remove_labels.append(settings.GMAIL_LABEL_INBOX)

        email._is_archived = True
        reindex_email_message(email)
        serializer = self.get_serializer(email, partial=True)
        add_and_remove_labels_for_message.delay(email.id, remove_labels=remove_labels)
        return Response(serializer.data)

    @detail_route(methods=['put'])
    def trash(self, request, pk=None):
        """
        Trash an email message asynchronous through the manager and not directly on the database. Just update the
        search index by an instance variable so changes are immediately visible.
        """
        email = self.get_object()
        if email.is_trashed:
            email._is_deleted = True
        email._is_trashed = True
        reindex_email_message(email)
        serializer = self.get_serializer(email, partial=True)
        trash_email_message.apply_async(args=(email.id,))
        return Response(serializer.data)

    @detail_route(methods=['put'])
    def move(self, request, pk=None):
        """
        Move an email message asynchronous through the manager and not directly on the database. Just update the
        search index by an instance variable so changes are immediately visible.
        """
        email = self.get_object()
        serializer = self.get_serializer(email, partial=True)
        add_and_remove_labels_for_message.delay(
            email.id,
            add_labels=request.data['data'].get('add_labels', []),
            remove_labels=request.data['data'].get('remove_labels', []),
        )
        return Response(serializer.data)

    @detail_route(methods=['put'])
    def star(self, request, pk=None):
        """
        Star an email message asynchronous through the manager and not directly on the database. Just update the
        search index by an instance variable so changes are immediately visible.
        """
        email = self.get_object()
        email._is_starred = request.data['starred']
        reindex_email_message(email)
        serializer = self.get_serializer(email, partial=True)
        toggle_star_email_message.delay(email.id, star=request.data['starred'])
        return Response(serializer.data)

    @detail_route(methods=['put'])
    def spam(self, request, pk=None):
        """
        Mark / unmark an email message as spam asynchronous through the manager and not directly on the database. Just
        update the search index by an instance variable so changes are immediately visible.
        """
        email = self.get_object()
        email._is_spam = request.data['markAsSpam']
        reindex_email_message(email)
        serializer = self.get_serializer(email, partial=True)
        toggle_spam_email_message.delay(email.id, spam=request.data['markAsSpam'])
        return Response(serializer.data)

    @detail_route(methods=['post'])
    def extract(self, request, pk=None):
        """
        Attempt to extract phone numbers from the given email message.
        If an account is given it will attempt to use that account's country.
        Otherwise it will use the user's tenant's country.
        """
        email = self.get_object()
        account = request.data['account']
        country = None

        if account:
            account = Account.objects.get(pk=account)

            if account.addresses:
                address = account.addresses.first()

                if address:
                    country = address.country

        if not country:
            country = self.request.user.tenant.country or None

        phone_numbers = []

        # We can't extract phone numbers without a country.
        if country:
            for match in phonenumbers.PhoneNumberMatcher(email.body_text, country):
                number_format = phonenumbers.PhoneNumberFormat.NATIONAL
                number = match.number

                number = phonenumbers.format_number(number, number_format).replace(' ', '')
                number = format_phone_number(number, country, True)

                number_exists = PhoneNumber.objects.filter(number=number, status=PhoneNumber.ACTIVE_STATUS).exists()

                if number not in phone_numbers and not number_exists:
                    phone_numbers.append(number)

        return Response({'phone_numbers': phone_numbers})


class EmailTemplateFolderViewSet(viewsets.ModelViewSet):
    """
    EmailTemplateFolder API.
    """
    # Set the queryset, this takes care of setting the `base_name`.
    queryset = EmailTemplateFolder.objects
    # Set the serializer class for this viewset.
    serializer_class = EmailTemplateFolderSerializer
    # Set all filter backends that this viewset uses.
    filter_backends = (filters.OrderingFilter, )

    # OrderingFilter: set the default ordering fields.
    ordering = ('name', )

    def get_queryset(self):
        """
        Set the queryset here so it filters on tenant.
        """
        folders = super(EmailTemplateFolderViewSet, self).get_queryset().all()

        for folder in folders:
            folder.email_templates = folder.email_templates.order_by('name')

        return folders

    def destroy(self, request, *args, **kwargs):
        """
        Unlink all email templates from the folder and then delete the folder.
        """
        folder = self.get_object()

        templates = folder.email_templates.all()

        for template in templates:
            template.folder = None
            template.save()

        # Don't call super, since that only fires another query using self.get_object().
        self.perform_destroy(folder)
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmailTemplateFilter(FilterSet):
    class Meta:
        model = EmailTemplate
        fields = {
            'folder': ['isnull', ],
        }


class EmailTemplateViewSet(viewsets.ModelViewSet):
    """
    EmailTemplate API.
    """
    # Set the queryset, this takes care of setting the `base_name`.
    queryset = EmailTemplate.objects
    # Set the serializer class for this viewset.
    serializer_class = EmailTemplateSerializer
    # Set all filter backends that this viewset uses.
    filter_backends = (filters.OrderingFilter, filters.DjangoFilterBackend)

    filter_class = EmailTemplateFilter

    # OrderingFilter: set the default ordering fields.
    ordering = ('name', )

    def get_queryset(self):
        """
        Set the queryset here so it filters on tenant.
        """
        return super(EmailTemplateViewSet, self).get_queryset().all()

    @list_route(methods=['PATCH'])
    def move(self, request):
        templates = request.data.get('templates')
        folder = request.data.get('folder')

        if folder:
            folder = EmailTemplateFolder.objects.get(pk=folder)

        templates = EmailTemplate.objects.filter(id__in=templates)

        for template in templates:
            template.folder = folder
            template.save()

        return Response(status=status.HTTP_200_OK)


class TemplateVariableViewSet(mixins.DestroyModelMixin,
                              mixins.RetrieveModelMixin,
                              GenericViewSet):
    """
    TemplateVariable API.
    """
    queryset = TemplateVariable.objects
    serializer_class = TemplateVariableSerializer
    filter_backends = (filters.OrderingFilter,)
    ordering = ('name', )

    def list(self, request):
        queryset = TemplateVariable.objects.all().filter(Q(is_public=True) | Q(owner=request.user))
        serializer = TemplateVariableSerializer(queryset, many=True)

        default_variables = get_email_parameter_api_dict()

        template_variables = {
            'default': default_variables,
            'custom': serializer.data
        }

        return Response(template_variables)


class SearchView(APIView):

    def get(self, request, format=None):
        user = request.user

        # Search query.
        q = request.query_params.get('q', '').strip()

        # Paging parameters.
        page = request.query_params.get('page', '0')
        page = int(page) + 1
        size = int(request.query_params.get('size', '20'))
        sort = request.query_params.get('sort', '-sent_date')

        # Mail labeling parameters.
        label_id = request.query_params.get('label', None)
        read = request.query_params.get('read', None)

        # Search email for own accounts or related account/contact.
        account_ids = request.query_params.get('account', None)  # None means search in all owned email accounts.
        related_account_id = request.query_params.get('account_related', None)
        related_contact_id = request.query_params.get('contact_related', None)

        # Additional filtering.
        date_start = request.query_params.get('date_start', None)
        date_end = request.query_params.get('date_end', None)
        thread_id = request.query_params.get('thread', None)

        # Parameters indiciating search use case.
        activity_stream = request.query_params.get('activity_stream', None)
        dashboard = request.query_params.get('dashboard', None)
        activity_stream = request.query_params.get('activity_stream', None)

        if related_account_id and related_contact_id:
            # Raise error because related_x fields are mutually exclusive.
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if not account_ids:
            # Get a list of all email accounts added by the user or shared with the user.
            email_accounts = get_shared_email_accounts(user, not (related_account_id or related_contact_id))
        else:
            # Only search within the email accounts indicated by the account_ids parameter.
            account_ids = account_ids.split(',')
            email_accounts = EmailAccount.objects.filter(pk__in=account_ids)

        email_accounts = email_accounts.exclude(is_active=False, is_deleted=True)

        message_list = EmailMessage.objects

        # Apply initial filtering.
        if read is not None:
            message_list = message_list.filter(
                read=read
            )

        if date_start:
            message_list = message_list.filter(
                sent_date__gte=date_start
            )

        if date_end:
            message_list = message_list.filter(
                sent_date__lte=date_end
            )

        if thread_id:
            # Filtering on thread_id is used for the arrow signs indicating it's a reply(-all) or forward message.
            message_list = message_list.filter(
                thread_id=thread_id
            )

        if q:
            # Handle the search via Google.

            # Only exclude unauthorized accounts when the search is handled by Google.
            email_accounts = email_accounts.exclude(is_authorized=False)

            if label_id and label_id not in [settings.GMAIL_LABEL_INBOX, settings.GMAIL_LABEL_SPAM,
                                             settings.GMAIL_LABEL_TRASH, settings.GMAIL_LABEL_SENT,
                                             settings.GMAIL_LABEL_DRAFT, settings.GMAIL_LABEL_STAR]:
                # Also retrieve related labels because later the label name will be queried.
                email_accounts = email_accounts.prefetch_related('labels')

            # Prevent too much calls on the search api, so restrict number of search results per email account.
            max_results = 3 * size

            messages_ids = []
            total_number_of_results = 0
            for email_account in email_accounts:
                if label_id:
                    label_name = label_id
                    if label_id not in [settings.GMAIL_LABEL_INBOX, settings.GMAIL_LABEL_SPAM,
                                        settings.GMAIL_LABEL_TRASH, settings.GMAIL_LABEL_SENT,
                                        settings.GMAIL_LABEL_DRAFT, settings.GMAIL_LABEL_STAR]:
                        # Retrieve the label name if label_id will differ from the user set label name.
                        try:
                            label_name = email_account.labels.get(label_id=label_id).name
                        except EmailLabel.DoesNotExist:
                            logger.error(
                                "Incorrect label id {0} with search request for account {1}.".format(label_id,
                                                                                                     email_account)
                            )

                    q = u"{0} {1}:{2}".format(q, 'label', label_name)

                # With label_id missing Gmail defaults to searching through all mail.

                try:
                    connector = GmailConnector(email_account)
                    messages, number_of_results = connector.search(query=q, max_results=max_results)
                    messages_ids.extend([message['id'] for message in messages])
                    total_number_of_results += min(number_of_results, max_results)
                except (InvalidCredentialsError, NotFoundError, HttpAccessTokenRefreshError,
                        FailedServiceCallException) as e:
                    logger.error(
                        "Failed to search within account {0} with error: {1}.".format(email_account, e)
                    )
                    # Failing search within one account should not halt the complete search.
                    continue

            # Retrieve messages from the database.
            message_list = message_list.filter(
                message_id__in=messages_ids,
                account__in=email_accounts
            )

        else:
            # User isn't searching by a keyword, just show the emails for current box. Where current email box is:
            # 1. A combination of included and excluded labels.
            # email_accounts = list(email_accounts.prefetch_related('labels'))
            email_accounts = list(email_accounts)  # TODO: list needed?
            message_list = message_list.filter(
                account__in=email_accounts,
            )

            message_list = self._determine_label_filtering(message_list, label_id, email_accounts)

            # 2. or a combination of mail sent or received by a related account (used in the activity stream).
            if related_account_id:
                related_email_addresses = self._get_related_account_email_addresses(related_account_id)
                if related_email_addresses:
                    message_list = self._message_filter_on_related(message_list, related_email_addresses)
                else:
                    # When there are no known email addresses for the related account, provided an empty queryset so
                    # the follow-up filtering and pagination can continue.
                    message_list = message_list.none()

            # 3. or a combination of mail sent or received by a related contact (used in the activity stream).
            if related_contact_id:
                related_email_addresses = self._get_related_contact_email_addresses(related_contact_id)
                if related_email_addresses:
                    message_list = self._message_filter_on_related(message_list, related_email_addresses)
                else:
                    # When there are no known email addresses for the related contact, provided an empty queryset so
                    # the follow-up filtering and pagination can continue.
                    message_list = message_list.none()

        message_list = message_list.order_by(sort)

        # The serializer will query for account, sender and star label, so instead of the extra separate queries,
        # retrieve them now.
        message_list = message_list.select_related('account', 'sender')
        message_list = message_list.prefetch_related('labels')

        if activity_stream:
            message_list = message_list[:size]

            # No paginator needed for the activity stream.
            serializer = EmailMessageActivityStreamSerializer(message_list, many=True, context={'request': request})

            result = {
                'total': len(serializer.data),
                'hits': serializer.data,
            }
        elif dashboard:
            message_list = message_list[:size]

            # No paginator needed for the dashboard.
            serializer = EmailMessageDashboardSerializer(message_list, many=True, context={'request': request})

            result = {
                'total': len(serializer.data),
                'hits': serializer.data,
            }
        else:
            # Construct paginator.
            limit = size * page
            offset = limit - size
            message_list = message_list[offset:limit]

            serializer = EmailMessageListSerializer(message_list, many=True, context={'request': request})

            result = {
                'hits': serializer.data,
            }

            if q:
                result['total'] = total_number_of_results

        return Response(result)

    def _determine_label_filtering(self, queryset, folder_id, email_accounts):
        """
        Return a queryset for filtering messages by labels or boolean fields for common labels.

        :param queryset: queryset with messages.
        :param folder_id: id indicating a system / user defined label or none for 'all mail'.
        :param email_accounts: restrict the user label to the email accounts.
        :return: queryset of email messages.
        """
        if folder_id:
            # System of user defined label.
            if folder_id == settings.GMAIL_LABEL_INBOX:
                queryset = queryset.filter(is_inbox=True)
            elif folder_id == settings.GMAIL_LABEL_SENT:
                queryset = queryset.filter(is_sent=True)
            elif folder_id == settings.GMAIL_LABEL_DRAFT:
                queryset = queryset.filter(is_draft=True)
            elif folder_id == settings.GMAIL_LABEL_TRASH:
                queryset = queryset.filter(is_trashed=True)
            elif folder_id == settings.GMAIL_LABEL_SPAM:
                queryset = queryset.filter(is_spam=True)
            else:
                # User defined folder.
                include_labels = EmailLabel.objects.filter(
                    label_id=folder_id,
                    account__in=email_accounts
                )
                queryset = queryset.filter(
                    labels__in=include_labels
                )
        else:
            # All mail.
            queryset = queryset.filter(is_trashed=False, is_spam=False, is_draft=False)

        return queryset

    def _get_related_account_email_addresses(self, account_id):
        """
        Get a list of email addresses of the account and of the contacts of the account.
        """
        email_addresses = []
        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return email_addresses

        email_addresses = [email.email_address for email in account.email_addresses.all() if email.email_address]

        contacts = account.get_contacts()
        for contact in contacts:
            contact_email_addresses = [
                email.email_address for email in contact.email_addresses.all() if email.email_address
            ]
            email_addresses.extend(contact_email_addresses)

        return email_addresses

    def _get_related_contact_email_addresses(self, contact_id):
        """
        Get a list of email addresses of the contact.
        """
        email_addresses = []
        try:
            contact = Contact.objects.get(id=contact_id)
        except Contact.DoesNotExist:
            return email_addresses

        email_addresses = [email.email_address for email in contact.email_addresses.all() if email.email_address]
        return email_addresses

    def _message_filter_on_related(self, queryset, email_addresses):
        """
        Return a queryset for all the email messages sent or received by one of the email addressses which aren't
        private.

        :param queryset: EmailMessage queryset that needs to be filtered on related accounts.
        :param email_addresses:  list of email addressses.
        :return: QuerySet of email messages.
        """
        recipients = list(Recipient.objects.filter(email_address__in=email_addresses).values_list('id', flat=True))

        # Get email messages send or received by one of the email addresses.
        queryset = queryset.filter(
            Q(sender__in=recipients) |
            Q(received_by__in=recipients) |
            Q(received_by_cc__in=recipients)
        )

        return queryset
