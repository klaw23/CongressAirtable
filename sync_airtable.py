# -*- coding: utf-8 -*-
""" Import from data sources into airtable.
"""

import argparse
import requests

AIRTABLE_URL = 'https://api.airtable.com/v0/app0RqdyYr4uyVWxm'

SUNLIGHT_URL = 'https://congress.api.sunlightfoundation.com'

def getAirtableRepresentativeIds(airtable_api_key):
    """ Generate a mapping from district to 
        to airtable representative id.
    """
    # Fetch paginated representatives.
    representatives = []
    offset = ''
    while True:
        response = requests.get('%s/House%%20Districts' % AIRTABLE_URL,
                                params={'offset': offset},
                                headers={'Authorization': 'Bearer %s' % airtable_api_key})
        representatives.extend(response.json()['records'])
        if not response.json().get('offset'):
            break
        offset = response.json()['offset']

    # Convert to mapping.
    return dict([(r['fields']['CD'], r['fields']['Incumbent'][0]) for r in representatives
                 if r['fields'].get('Incumbent')])

def syncCommittees(representative_ids, airtable_api_key):
    """ Sync committee members.

        Args:
            representative_ids - Rep name to airtable id mapping.

        TODO: Update existing committee rather than writing new ones.
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

        # Join sunlight reps with airtable reps by district.
        member_ids = []
        for member in members:
            district = '%(state)s-%(district)02d' % member['legislator']
            rep_id = representative_ids.get(district)
            if rep_id:
                member_ids.append(rep_id)

        # Write committee to airtable.
        response = requests.post('%s/House%%20Committees' % AIRTABLE_URL,
                                 headers={'Authorization': 'Bearer %s' % airtable_api_key},
                                 json={'fields': {
                                     "Name": committee['name'],
                                     "Members": member_ids
                                 }})
        response.raise_for_status()

def main():
    # Parse command line args.
    parser = argparse.ArgumentParser(description='Sync data sources to airtable.')
    parser.add_argument('-a', '--airtable_api_key',
                    	help='Airtable api key',
                    	required=True)
    args = parser.parse_args()

    # Get airtable representative ids. District -> airtable rep id.
    representative_ids = getAirtableRepresentativeIds(args.airtable_api_key)

    # Sync committees.
    syncCommittees(representative_ids, args.airtable_api_key)

if __name__ == "__main__":
    main()
