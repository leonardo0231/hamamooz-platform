from django.db import transaction
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken


@transaction.atomic
def revoke_user_refresh_tokens(user):
    tokens = OutstandingToken.objects.select_for_update().filter(user=user)
    for token in tokens.iterator():
        BlacklistedToken.objects.get_or_create(token=token)
