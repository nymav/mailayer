from googleapiclient.discovery import build
from app.gmail.auth import load_credentials


def get_gmail_service(interactive: bool = False):
    creds = load_credentials(interactive=interactive)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def get_profile(service):
    return service.users().getProfile(userId="me").execute()
