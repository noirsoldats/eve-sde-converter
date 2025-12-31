# -*- coding: utf-8 -*-
import sys
import os
from sqlalchemy import Table

from yaml import load
try:
	from yaml import CSafeLoader as SafeLoader
	print("Using CSafeLoader")
except ImportError:
	from yaml import SafeLoader
	print("Using Python SafeLoader")


def importyaml(connection,metadata,sourcePath,language='en'):
    print("Importing Meta Groups")
    invMetaGroups = Table('invMetaGroups',metadata)
    trnTranslations = Table('trnTranslations',metadata)
    
    targetPath = os.path.join(sourcePath, 'metaGroups.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'metaGroups.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'metaGroups.yaml')

    print(f"  Opening {targetPath}")
        
    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        metagroups=load(yamlstream,Loader=SafeLoader)
        print(f"  Populating Meta Groups Table with {len(metagroups)} entries")

        # Build bulk insert lists
        metagroup_rows = []
        translation_rows = []

        for metagroupid in metagroups:
            metagroup_rows.append({
                'metaGroupID': metagroupid,
                'metaGroupName': metagroups[metagroupid].get('name',{}).get(language,''),
                'iconID': metagroups[metagroupid].get('iconID'),
                'description': metagroups[metagroupid].get('description',{}).get(language,'')
            })

            if ('name' in metagroups[metagroupid]):
                for lang in metagroups[metagroupid]['name']:
                    try:
                        translation_rows.append({
                            'tcID': 34,
                            'keyID': metagroupid,
                            'languageID': lang,
                            'text': metagroups[metagroupid]['name'][lang]
                        })
                    except:
                        print('{} {} has a category problem'.format(metagroupid,lang))

            if ('description' in metagroups[metagroupid]):
                for lang in metagroups[metagroupid]['description']:
                    try:
                        translation_rows.append({
                            'tcID': 35,
                            'keyID': metagroupid,
                            'languageID': lang,
                            'text': metagroups[metagroupid]['description'][lang]
                        })
                    except:
                        print('{} {} has a category problem'.format(metagroupid,lang))

        # BULK INSERTS
        if metagroup_rows:
            connection.execute(invMetaGroups.insert(), metagroup_rows)
            print(f"  Inserted {len(metagroup_rows)} meta groups")

        if translation_rows:
            connection.execute(trnTranslations.insert(), translation_rows)
            print(f"  Inserted {len(translation_rows)} meta group translations")

    trans.commit()
    print("  Done")