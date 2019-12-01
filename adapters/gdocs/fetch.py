# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Recursively extracts the text from a Google Doc.
"""
from __future__ import print_function

from apiclient import discovery
from httplib2 import Http
from oauth2client import client
from oauth2client import file
from oauth2client import tools

import json

SCOPES = 'https://www.googleapis.com/auth/documents.readonly'
DISCOVERY_DOC = 'https://docs.googleapis.com/$discovery/rest?version=v1'
DOCUMENT_ID = '1HvcEoOh98xi_mhjXAfBsq2p79n5Vc_TAN0HX8owarnI'

CONTENT_FILE = 'iok_cache_body.json'  # for debugging really
MOCK_MD_FILE = 'iok_cache.md'

START_DELIM = '__START__'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth 2.0 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    store = file.Storage('token.json')
    credentials = store.get()

    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        credentials = tools.run_flow(flow, store)
    return credentials

def write_md_link(text, link):
    return f'[{text}]({link})'

def read_paragraph_element(element):
    """Returns the text in the given ParagraphElement.

        Args:
            element: a ParagraphElement from a Google Doc.
    """
    text_run = element.get('textRun')
    if not text_run:
        return ''
    content = text_run.get('content')
    text_style = text_run.get('textStyle')
    if not text_style:
        return content
    url = text_style.get('link').get('url')
    return write_md_link(content, url)

def read_strucutural_elements(elements):
    """Recurses through a list of Structural Elements to read a document's text where text may be
        in nested elements.

        Args:
            elements: a list of Structural Elements.
    """
    text = ''
    for value in elements:
        if 'paragraph' in value:
            if value.get('paragraph').get('bullet'):
                text += "* "
            if value.get('paragraph').get('paragraphStyle'):
                namedStyleType = value.get('paragraph').get('paragraphStyle').get('namedStyleType')
                if namedStyleType == 'HEADING_1':
                    text += "\n# "
                elif namedStyleType == 'HEADING_2':
                    text += "\n## "
                elif namedStyleType == 'HEADING_3':
                    text += "\n### "
                
            elements = value.get('paragraph').get('elements')
            for elem in elements:
                text += read_paragraph_element(elem) + '\n'
                if START_DELIM in text:  # restart if found delim
                    text = ""
        elif 'table' in value:
            # The text in table cells are in nested Structural Elements and tables may be
            # nested.
            table = value.get('table')
            for row in table.get('tableRows'):
                cells = row.get('tableCells')
                for cell in cells:
                    text += read_strucutural_elements(cell.get('content'))
        elif 'tableOfContents' in value:
            # The text in the TOC is also in a Structural Element.
            toc = value.get('tableOfContents')
            text += read_strucutural_elements(toc.get('content'))
    return text


def main():
    """Uses the Docs API to print out the text of a document."""
    credentials = get_credentials()
    http = credentials.authorize(Http())
    docs_service = discovery.build(
        'docs', 'v1', http=http, discoveryServiceUrl=DISCOVERY_DOC)
    doc = docs_service.documents().get(documentId=DOCUMENT_ID).execute()
    doc_content = doc.get('body').get('content')
    with open(CONTENT_FILE, "w") as f:
        f.write(json.dumps(doc_content))

    with open(MOCK_MD_FILE, 'w') as fd:
        fd.write(read_strucutural_elements(doc_content))
    # print(read_strucutural_elements(doc_content))

if __name__ == '__main__':
    main()