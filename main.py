#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function
import httplib2
import os
import io
import re

from apiclient import discovery
from apiclient.http import MediaIoBaseDownload
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    parser = argparse.ArgumentParser(description='Automatically upload Spectator articles.',
                                     parents=[tools.argparser])
    parser.add_argument('--read-article', help='reads article in file')
    args = parser.parse_args()
except ImportError:
    flags = None

from colorama import init, Fore, Back, Style
init()

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/drive'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Spec-Uploader CLI'


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
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def readArticle(text):
    metadata = text.split('\n')
    title = metadata[0].strip() # gets first line of text
    if 'Title: ' in title:
        title = title[title.find('Title: ') + len('Title: '):]
    if 'worldbeat' in title.lower():
        print(Fore.RED + Style.BRIGHT + 'title: (Worldbeat); skipped')
        return False
    title = raw_input((Fore.GREEN + Style.BRIGHT + 'title: ' + Style.RESET_ALL + '({0}) ').format(title.strip())) or title # defaults to title

    byline = None
    contributors = []
    try:
        byline = next((line for line in metadata if line.find('By') >= 0))
        if 'By:' in byline:
            byline = byline[len('By:'):].strip()
        else:
            byline = byline[len('By'):].strip()

        # splits string into words and punctuation
        byline = re.findall(r"[\w']+|[.,!-?;]", byline)
        cutoff = 0
        for i in range(0, len(byline)):
            if byline[i] in ',&' or byline[i] == 'and':
                name = cleanName(' '.join(byline[cutoff:i]))
                contributors.append(name)
                cutoff = i + 1
        contributors.append(cleanName(' '.join(byline[cutoff:])))  # clean up last one
        contributors = filter(None, contributors)  # removes empty strings
    except StopIteration: # no byline found
        print(Back.RED + Fore.WHITE + 'No byline found. Header text: ' + Back.RESET + Fore.RED)
        for line in metadata:
            print(line.strip())
            if 'words' in line.lower(): # print heading up to word count
                contributors = raw_input((Fore.GREEN + Style.BRIGHT + 'enter contributors separated by ", ": ' + Style.RESET_ALL)).split(', ')
                break
    byline = raw_input((Fore.GREEN + Style.BRIGHT + 'contributors: ' + Style.RESET_ALL + '({0}) ').format(', '.join(contributors))) or byline

    try:
        summary = next((line for line in metadata if 'focus sentence:' in line.lower()))
        summary = summary.replace('Focus Sentence:', '').replace('Focus sentence:', '').strip()
        summary = raw_input(
            (Fore.GREEN + Style.BRIGHT + 'summary/focus: ' + Style.RESET_ALL + '({0}) ').format(summary)) or summary
    except StopIteration: # no focus sentence found
        print(Back.RED + Fore.WHITE + 'No focus sentence found. Header text (input "m" for more header text, ENTER to progress): ' + Back.RESET + Fore.RED)
        lineNum = 0
        while True:
            print(*metadata[lineNum:lineNum + 5], sep='\n')
            lineNum += 5
            if lineNum >= len(metadata):
                break
            showMore = raw_input()
            if showMore != 'm':
                break
        summary = raw_input(Fore.GREEN + Style.BRIGHT + 'summary/focus (may leave blank): ' + Style.RESET_ALL) or None
    summary = summary.strip()
    return True

def cleanName(name):
    name = name.replace(' - ', '-')
    # remove nickname formatting e.g. "By Ying Zi (Jessy) Mei"
    nicknameRegex = re.compile(r"\([\w\s-]*\)\s")
    name = nicknameRegex.sub('', name) # removes nicknames
    return name

def main():
    print("This utility will walk you through the uploading of all articles in the current Issue.")
    print("Press ^C at any time to quit.\n")
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    drive_service = discovery.build('drive', 'v3', http=http)

    # Gets all folder names under SBC
    page_token = None
    response = drive_service.files().list(q="(mimeType='application/vnd.google-apps.folder' or mimeType='application/vnd.google-apps.document') and not trashed",
                                          spaces='drive',
                                          fields='nextPageToken, files(id, name, parents, mimeType)',
                                          pageToken=page_token).execute()
    files = response.get('files', []) # if no key 'files', defaults to []
    SBC = next((file for file in files if file['name'] == 'SBC'), None)
    folders = getFoldersInFile(files, SBC['id'])
    for file in files:
        if file['mimeType'] == 'application/vnd.google-apps.document' and file.get('parents', [None])[0] in folders:

            # find sectionName by getting folder with parentId
            sectionName = folders[file.get('parents', [None])[0]].upper()

            # create new download request
            request = drive_service.files().export_media(fileId=file['id'],
                                                         mimeType='text/plain')
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(Fore.CYAN + Style.BRIGHT + sectionName, end='')
                print(Fore.BLUE + ' ' + file['name'] + Style.RESET_ALL, end=' ')
                print('%d%%' % int(status.progress() * 100))

            #if not readArticle(fh.getvalue()): # process was interrupted
            readArticle(fh.getvalue())
            print('\n')
    page_token = response.get('nextPageToken', None)
    if page_token is None:
        return

def getFoldersInFile(files, parentFolderId):
    folders = {}
    for file in files:
        # check if parent folder is SBC and file type is folder
        if file.get('parents', [None])[0] == parentFolderId and file.get('mimeType') == 'application/vnd.google-apps.folder':
            folders[file['id']] = file['name']
    return folders

if __name__ == '__main__':
    if args.read_article:
        with open(args.read_article) as file:
            readArticle(file.read())
    else:
        main()