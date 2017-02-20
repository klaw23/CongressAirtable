# -*- coding: utf-8 -*-
""" Import from data sources into airtable.
"""

import argparse
import re
import requests

AIRTABLE_URL = 'https://api.airtable.com/v0/app0RqdyYr4uyVWxm'

SUNLIGHT_URL = 'https://congress.api.sunlightfoundation.com'

# Airtable doesn't have 
ALTERNATE_NAMES = {
    u'Cárdenas, Tony': 'Cardenas, Tony',
    u'Barragán, Nanette': 'Barragan, Nanette',
    u'Luján, Ben': 'Lujan, Ben',
    u'Gutiérrez, Luis': 'Gutierrez, Luis',
    u'Sánchez, Linda': 'Sanchez, Linda',
    'Shuster, Bill': 'Schuster, Bill'
}

def getAirtableRepresentativeIds(airtable_api_key):
    """ Generate a mapping from "last_name, first_name" to 
        to airtable representative id.
    """
    # Fetch paginated representatives.
    representatives = []
    offset = ''
    while True:
        response = requests.get('%s/Representatives' % AIRTABLE_URL,
                                params={'offset': offset},
                                headers={'Authorization': 'Bearer %s' % airtable_api_key})
        representatives.extend(response.json()['records'])
        if not response.json().get('offset'):
            break
        offset = response.json()['offset']

    # Convert to mapping.
    return dict([(r['fields']['Name'], r['id']) for r in representatives])

def syncCommittees(representative_ids):
    """ Sync committee members.

        Args:
            representative_ids - Rep name to airtable id mapping.
    """
    # Get house committee list.
    committees = requests.get('%s/committees' % SUNLIGHT_URL,
                              {
                                'chamber': 'house',
                                'per_page': 'all',
                              }).json()['results']

    # Get committee members.
    for committee in committees:
        print committee['name']
        members = requests.get('%s/committees' % SUNLIGHT_URL,
                               {
                                  'committee_id': committee['committee_id'],
                                  'fields': 'members',
                               }).json()['results'][0]['members']

        # Skip empty committees
        if not members:
            continue

        for member in members:
            first_name = member['legislator']['first_name']
            full_name = '%s, %s' % (member['legislator']['last_name'], first_name)

            # Try alternate name if missing.
            if full_name not in representative_ids:
                if full_name in ALTERNATE_NAMES:
                    full_name = ALTERNATE_NAMES[full_name]
                else:
                    # Try to find a common last name.
                    for rep in representative_ids:
                        if (re.sub('[\W]', '', rep.split(',')[0]) == 
                            re.sub('[\W]', '', full_name.split(',')[0])):
                            full_name = rep

            print '%s - %s' % (full_name, representative_ids.get(full_name, 'None'))
        print '\n'

        # Join and submit to airable.


def main():
    # Parse command line args.
    parser = argparse.ArgumentParser(description='Sync data sources to airtable.')
    parser.add_argument('-a', '--airtable_api_key',
                    	help='Airtable api key',
                    	required=True)
    args = parser.parse_args()

    # Get airtable representative ids.
    representative_ids = getAirtableRepresentativeIds(args.airtable_api_key)

    # Sync committees.
    syncCommittees(representative_ids)

if __name__ == "__main__":
    main()
