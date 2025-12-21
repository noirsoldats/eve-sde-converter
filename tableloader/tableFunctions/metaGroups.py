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
    print("Importing metaGroups")
    invMetaGroups = Table('invMetaGroups',metadata)
    trnTranslations = Table('trnTranslations',metadata)
    
    print("opening Yaml")
        
    trans = connection.begin()
    with open(os.path.join(sourcePath,'metaGroups.yaml'),'r', encoding='utf-8') as yamlstream:
        print("importing")
        metagroups=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for metagroupid in metagroups:
            connection.execute(invMetaGroups.insert().values(
                            metaGroupID=metagroupid,
                            metaGroupName=metagroups[metagroupid].get('name',{}).get(language,''),
                            iconID=metagroups[metagroupid].get('iconID'),
                            description=metagroups[metagroupid].get('description',{}).get(language,'')
            ))

            if ('name' in metagroups[metagroupid]):
                for lang in metagroups[metagroupid]['name']:
                    try:
                        connection.execute(trnTranslations.insert().values(tcID=34,keyID=metagroupid,languageID=lang,text=metagroups[metagroupid]['name'][lang]));
                    except:
                        print('{} {} has a category problem'.format(metagroupid,lang))
            if ('description' in metagroups[metagroupid]):
                for lang in metagroups[metagroupid]['description']:
                    try:
                        connection.execute(trnTranslations.insert().values(tcID=35,keyID=metagroupid,languageID=lang,text=metagroups[metagroupid]['description'][lang]));
                    except:                        
                        print('{} {} has a category problem'.format(metagroupid,lang))
    trans.commit()
