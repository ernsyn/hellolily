# coding=utf-8
import StringIO
import csv

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.core.paginator import Paginator

from lily.accounts.models import Account, Website
from lily.hubspot.prefetch_objects import website_prefetch, phone_prefetch, addresses_prefetch
from lily.hubspot.utils import _s, _strip_website, get_phone_numbers_old
from lily.tenant.middleware import set_current_user
from lily.tenant.models import Tenant
from lily.users.models import LilyUser

field_names = (
    # 'account_id',

    # 'name',
    # 'description',
    'domain',
    # 'owner',
    # 'type',

    # 'phone',
    'extra_phone_1',
    'extra_phone_2',

    # 'street',
    # 'city',
    # 'state',
    # 'zip',
    # 'country',

    # 'twitterhandle',
    # 'linkedin_company_page',
    # 'facebook_company_page',

    # 'freedom_url',
    # 'entity',

    # 'pinned_notes',

    # 'lily_created',
    # 'lily_modified',
)


class Command(BaseCommand):
    help = 'Export accounts for specified tenant id.'

    def add_arguments(self, parser):
        parser.add_argument('tenant_id', type=int)

    def handle(self, tenant_id, *args, **options):
        self.stdout.write(self.style.SUCCESS('>>') + '  Starting with accounts export')
        set_current_user(LilyUser.objects.filter(tenant_id=tenant_id, is_active=True).first())
        tenant = Tenant.objects.get(id=tenant_id)
        # m = get_mappings(tenant_id)

        csvfile = StringIO.StringIO()
        writer = csv.DictWriter(csvfile, fieldnames=field_names)
        writer.writeheader()

        account_qs = Account.objects.filter(
            is_deleted=False
        ).exclude(
            id=20005  # Do not export account id: 20005 (automatically created).
        ).prefetch_related(
            website_prefetch,
            phone_prefetch,
            addresses_prefetch,
            # social_media_prefetch,
            # pinned_notes_prefetch,
            # tags_prefetch
        ).order_by('pk')
        paginator = Paginator(account_qs, 1000)

        # users = {user.id: user.full_name for user in LilyUser.objects.all()}

        self.stdout.write('    Page: 0 / {}    ({} items)'.format(paginator.num_pages, paginator.count))
        for page_number in paginator.page_range:
            account_list = paginator.page(page_number).object_list

            self.stdout.write('    Page: {} / {}'.format(page_number, paginator.num_pages))
            for account in account_list:
                website = account.prefetched_websites[0] if account.prefetched_websites else Website()
                # address = account.prefetched_addresses[0] if account.prefetched_addresses else Address()
                # phone_numbers = get_phone_numbers(account, tenant)
                phone_numbers = get_phone_numbers_old(account, tenant)
                # social_media = {social.name: social for social in account.prefetched_social_media}
                # tags = [tag.name for tag in account.prefetched_tags]

                extra_numbers = phone_numbers.get('extra_numbers')
                if phone_numbers.get('phone'):
                    # There is a phone, so mobile was not yet used.
                    if phone_numbers.get('mobile'):
                        # There is a mobile, so use that as first extra.
                        extra_phone_1 = phone_numbers.get('mobile')
                    else:
                        # There is no mobile, so just use the extra phone numbers.
                        extra_phone_1 = extra_numbers.pop() if extra_numbers else None

                    extra_phone_2 = extra_numbers.pop() if extra_numbers else None
                else:
                    # There is no phone, so probably mobile was used as phone.
                    extra_phone_1 = extra_numbers.pop() if extra_numbers else None
                    extra_phone_2 = extra_numbers.pop() if extra_numbers else None

                # pinned_notes = ''
                # for note in account.prefetched_pinned_notes:
                #     content = _s(
                #         users.get(note.author_id) + ' created a note on ' + note.created.strftime(
                #             "%d %b %Y - %H:%M"
                #         ) + ':\n\n' + note.content + '\n\n'
                #     )
                #
                #     pinned_notes += content

                # f_url = 'https://freedom.voys.nl/client/{}'.format(
                #     account.customer_id
                # ) if account.customer_id else ''
                if extra_phone_1:
                    print 'test'
                    data = {
                        # 'account_id': _s(account.pk),

                        # 'name': _s(account.name),
                        # 'description': _s(account.description),
                        'domain': _s(_strip_website(website.website)),
                        # 'owner': _s(m.lilyuser_to_owner_mapping.get(account.assigned_to_id, '')),
                        # 'type': _s(m.account_status_to_company_type_mapping[account.status_id]),

                        # 'phone': _s(phone_numbers),
                        # 'phone': _s(phone_numbers.get('phone') or phone_numbers.get('mobile')),
                        'extra_phone_1': _s(extra_phone_1 or ''),
                        'extra_phone_2': _s(extra_phone_2 or ''),

                        # 'street': _s(address.address),
                        # 'city': _s(address.city),
                        # 'state': _s(address.state_province),
                        # 'zip': _s(address.postal_code),
                        # 'country': _s(address.country),

                        # 'twitterhandle': _s(social_media.get('twitter', SocialMedia()).username or ''),
                        # 'linkedin_company_page': _s(social_media.get('linkedin', SocialMedia()).profile_url or ''),
                        # 'facebook_company_page': _s(social_media.get('facebook', SocialMedia()).profile_url or ''),

                        # 'freedom_url': _s(f_url),
                        # 'entity': _s('c_entity_VoysBE' if u'belgië' in tags else 'c_entity_VoysNL'),

                        # 'pinned_notes': pinned_notes,

                        # 'lily_created': _s(account.created.strftime("%d %b %Y - %H:%M:%S")),
                        # 'lily_modified': _s(account.modified.strftime("%d %b %Y - %H:%M:%S")),
                    }
                    writer.writerow(data)

        filename = 'exports/tenant_{}/companies.csv'.format(tenant_id)
        default_storage.save(name=filename, content=csvfile)

        self.stdout.write(self.style.SUCCESS('>>') + '  Successfully exported accounts. \n\n')
