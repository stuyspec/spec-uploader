from colorama import Fore, Back, Style

import requests
import constants, utils

sections = []

def init():
    """Initiates globals with API data"""
    global sections
    sections = requests.get(constants.API_SECTIONS_ENDPOINT).json()


def choose_subsection(section_id):
    subsections = [
        section for section in sections if section['parent_id'] == section_id
    ]
    print(Fore.GREEN + Style.BRIGHT +
          'Optional subsection ->'
          + Style.RESET_ALL)
    for i in range(len(subsections)):
        print('  [{}] {}'.format(i, subsections[i]['name']))

    index_choice = 'default'
    while not utils.represents_int(index_choice) or index_choice == '':
        index_choice = raw_input(Fore.GREEN + Style.BRIGHT
                                 + 'subsection (leave blank if none): '
                                 + Style.RESET_ALL)
    return 
    if index_choice != '':
        return [
            subsections[int(i)]['id'] for i in index_choices.split('/')
        ]

def get_section_name_by_id(section_name):
    return next(
        (s for s in sections
         if (s['name'].lower() == section_name.lower() or
             section_name == 'A&E'
             and s['name'] == "Arts & Entertainment")
         ),
        {}
    ).get('id', -1)