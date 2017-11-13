from apiclient import discovery
from apiclient.http import MediaIoBaseDownload
from pyfiglet import figlet_format
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
import httplib2

import os
import re
import io

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/drive'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Spec-Uploader CLI'


files = []
drive_service = None

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def init():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    global drive_service
    drive_service = discovery.build('drive', 'v3', http=http)

    print('\n')
    print(figlet_format('SPEC CLI', font='slant'))

    page_token = None
    response = drive_service.files().list(
        q="(mimeType='application/vnd.google-apps.folder'"
          + " or mimeType='application/vnd.google-apps.document'"
          + " or mimeType contains 'image')"
          + " and not trashed",
        spaces='drive',
        fields='nextPageToken, files(id, name, parents, mimeType)',
        pageToken=page_token).execute()

    global files
    files = response.get('files', [])

    page_token = response.get('nextPageToken', None)
    if page_token is None:
        return
    # todo: in the future, files should be sorted into hashtable or dictionary by issue num


def get_file(name_pattern, file_type, parent_id=None):
    mime_type = 'application/vnd.google-apps.' + file_type
    if parent_id:
        return next((
            f for f in files if (f['mimeType'] == mime_type and
                                 re.match(name_pattern, f['name']) and
                                 f.get('parents', [None])[0] == parent_id)
        ))
    return next((
        f for f in files if (f['mimeType'] == mime_type and
                             re.match(name_pattern, f['name']))
    ))


def get_children(parent_id, file_type=None):
    if file_type:
        mime_type = 'application/vnd.google-apps.' + file_type
        return [
            f for f in files if (f['mimeType'] == mime_type and
                                 f.get('parents', [None])[0] == parent_id)
        ]
    return [
        f for f in files if f.get('parents', [None])[0] == parent_id
    ]


def download_document(file):
    if file['mimeType'] != 'application/vnd.google-apps.document':
        raise ValueError('File of MIME type {} should not be downloaded here.'
                         .format(file['mimeType']))
    request = drive_service.files().export_media(
        fileId=file['id'], mimeType='text/plain')
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print('%d%%' % int(status.progress() * 100))

    return fh.getvalue()
