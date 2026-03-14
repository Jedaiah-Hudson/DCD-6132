def refresh_contracting_opportunities_for_user(user):
    # TODO: wire this to real opportunity ingestion when email/provider integrations exist.
    return True


def refresh_user_opportunities(user):
    return refresh_contracting_opportunities_for_user(user)
