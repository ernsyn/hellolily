import StringIO
import csv

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.core.paginator import Paginator

from lily.contacts.models import Contact
from lily.hubspot.mappings import contact_status_to_contact_status_mapping
from lily.hubspot.prefetch_objects import (
    addresses_prefetch, phone_prefetch, accounts_prefetch, twitter_prefetch, email_addresses_prefetch
)
from lily.socialmedia.models import SocialMedia
from lily.tenant.middleware import set_current_user
from lily.users.models import LilyUser
from lily.utils.models.models import Address, EmailAddress, PhoneNumber


def _s(value):
    return unicode(value).encode('utf-8')


field_names = (
    'contact_id',
    'first_name',
    'last_name',
    'gender',
    'status',

    'phone',
    'mobile_phone',
    'email',

    'street',
    'city',
    'state',
    'zip',
    'country',

    'twitterhandle',

    'lily_created',
    'lily_modified',

    'account_id',
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('tenant_id', type=int)

    def handle(self, tenant_id, *args, **options):
        self.stdout.write(self.style.SUCCESS('>>') + '  Starting with contacts export')
        set_current_user(LilyUser.objects.filter(tenant_id=tenant_id, is_active=True).first())

        csvfile = StringIO.StringIO()
        writer = csv.DictWriter(csvfile, fieldnames=field_names)
        writer.writeheader()

        contact_qs = Contact.objects.filter(
            is_deleted=False
        ).prefetch_related(
            accounts_prefetch,
            addresses_prefetch,
            twitter_prefetch,
            phone_prefetch,
            email_addresses_prefetch
        ).order_by('pk')
        paginator = Paginator(contact_qs, 100)

        self.stdout.write('    Page: 0 / {}    ({} items)'.format(paginator.num_pages, paginator.count))
        for page_number in paginator.page_range:
            contact_list = paginator.page(page_number).object_list

            self.stdout.write('    Page: {} / {}'.format(page_number, paginator.num_pages))
            for contact in contact_list:
                account_id = contact.prefetched_accounts[0].pk if contact.prefetched_accounts else ''
                address = contact.prefetched_addresses[0] if contact.prefetched_addresses else Address()
                twitter = contact.prefetched_twitters[0] if contact.prefetched_twitters else SocialMedia()
                phone_numbers = {pn.type: pn for pn in contact.prefetched_phone_numbers}
                emails = contact.prefetched_email_addresses

                if emails:
                    primary_email = emails[0]

                    if len(emails) > 1:
                        for email in emails[1:]:
                            data = {
                                'first_name': _s(contact.first_name),
                                'last_name': _s(contact.last_name),
                                'email': _s(email.email_address),
                                'account_id': _s(account_id),
                            }
                            writer.writerow(data)
                else:
                    primary_email = EmailAddress()

                data = {
                    'contact_id': _s(contact.pk),
                    'first_name': _s(contact.first_name),
                    'last_name': _s(contact.last_name),
                    'gender': _s(contact.get_gender_display()),
                    'status': _s(contact_status_to_contact_status_mapping[contact.status]),
                    'phone': _s(phone_numbers.get('work', PhoneNumber()).number),
                    'mobile_phone': _s(phone_numbers.get('mobile', PhoneNumber()).number),
                    'email': _s(primary_email.email_address),
                    'street': _s(address.address),
                    'city': _s(address.city),
                    'state': _s(address.state_province),
                    'zip': _s(address.postal_code),
                    'country': _s(address.country),
                    'twitterhandle': _s(twitter.username or ''),

                    'lily_created': _s(contact.created.strftime("%d %b %Y - %H:%M:%S")),
                    'lily_modified': _s(contact.modified.strftime("%d %b %Y - %H:%M:%S")),

                    'account_id': _s(account_id),
                }
                writer.writerow(data)

        filename = 'exports/tenant_{}/contacts.csv'.format(tenant_id)
        default_storage.save(name=filename, content=csvfile)

        self.stdout.write(self.style.SUCCESS('>>') + '  Successfully exported contacts. \n\n')
