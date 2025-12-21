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
    print("Importing marketGroups")
    invMarketGroups = Table('invMarketGroups',metadata)
    trnTranslations = Table('trnTranslations',metadata)
    
    print("opening Yaml")
        
    trans = connection.begin()
    with open(os.path.join(sourcePath,'marketGroups.yaml'),'r', encoding='utf-8') as yamlstream:
        print("importing")
        marketgroups=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for marketgroupid in marketgroups:
            connection.execute(invMarketGroups.insert().values(
                            marketGroupID=marketgroupid,
                            parentGroupID=marketgroups[marketgroupid].get('parentGroupID',None),
                            marketGroupName=marketgroups[marketgroupid].get('name',{}).get(language,''),
                            description=marketgroups[marketgroupid].get('description',{}).get(language,''),
                            iconID=marketgroups[marketgroupid].get('iconID'),
                            hasTypes=marketgroups[marketgroupid].get('hasTypes',False)
            ))

            if ('name' in marketgroups[marketgroupid]):
                for lang in marketgroups[marketgroupid]['name']:
                    try:
                        connection.execute(trnTranslations.insert().values(tcID=36,keyID=marketgroupid,languageID=lang,text=marketgroups[marketgroupid]['name'][lang]));
                    except:
                        print('{} {} has a category problem'.format(marketgroupid,lang))
            if ('description' in marketgroups[marketgroupid]):
                for lang in marketgroups[marketgroupid]['description']:
                    try:
                        connection.execute(trnTranslations.insert().values(tcID=37,keyID=marketgroupid,languageID=lang,text=marketgroups[marketgroupid]['description'][lang]));
                    except:                        
                        print('{} {} has a category problem'.format(marketgroupid,lang))
    trans.commit()
