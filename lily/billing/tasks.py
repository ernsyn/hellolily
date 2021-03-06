from datetime import datetime
import logging
from errno import ETIMEDOUT

import chargebee
from celery.task import task
from django.conf import settings

from lily.billing.models import Plan
from lily.messaging.email.utils import limit_email_accounts
from lily.tenant.models import Tenant

logger = logging.getLogger(__name__)


@task(name='check_subscriptions')
def check_subscriptions():
    if settings.BILLING_ENABLED:
        tenants = Tenant.objects.all()

        for tenant in tenants:
            subscription = tenant.billing.get_subscription()
            billing = tenant.billing

            if not billing.free_forever and subscription:
                convert_to_free = False

                if subscription.plan_id == settings.CHARGEBEE_PRO_TRIAL_PLAN_NAME:
                    # Once the free pro trial is done we will convert to the free plan.
                    trial_end = datetime.fromtimestamp(subscription.trial_end)

                    if datetime.now() > trial_end:
                        convert_to_free = True

                if subscription.status == 'cancelled':
                    convert_to_free = True

                if convert_to_free:
                    # Subscription was set to cancelled for whatever reason (expired trial, card declined, etc)
                    max_attempts = 3
                    for attempt in range(max_attempts):
                        try:
                            chargebee.Subscription.update(subscription.id, {
                                'plan_id': settings.CHARGEBEE_FREE_PLAN_NAME,
                            })
                        except ETIMEDOUT:
                            # If this is the last attempt, reraise the exception (attempt is zero indexed).
                            if attempt == max_attempts - 1:
                                raise
                        else:
                            break

                    billing.plan = Plan.objects.get(name=settings.CHARGEBEE_FREE_PLAN_NAME)
                    billing.save()

                    limit_email_accounts(tenant)

                    logger.info('Set subscription for %s to free plan' % tenant.name)
                elif subscription.plan_id != billing.plan.name:
                    # The plan changed in Chargebee (e.g. manual change), but not in the database.
                    billing.plan = Plan.objects.get(name=subscription.plan_id)
                    billing.save()

                    logger.info('Updated subscription for %s' % tenant.name)
