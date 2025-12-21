# -*- coding: utf-8 -*-
import sys
import os
from sqlalchemy import Table

from yaml import load,dump
try:
    from yaml import CSafeLoader as SafeLoader
    print("Using CSafeLoader")
except ImportError:
    from yaml import SafeLoader
    print("Using Python SafeLoader")



def importyaml(connection,metadata,sourcePath,language='en'):
    print("Importing dogma attributes")
    dgmAttributes = Table('dgmAttributeTypes',metadata)
    
    print("opening Yaml")
        
    trans = connection.begin()
    with open(os.path.join(sourcePath,'dogmaAttributes.yaml'),'r', encoding='utf-8') as yamlstream:
        print("importing")
        dogmaAttributes=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for dogmaAttributeID in dogmaAttributes:
            attribute = dogmaAttributes[dogmaAttributeID]
            connection.execute(dgmAttributes.insert().values(
                               attributeID=dogmaAttributeID,
                               categoryID=attribute.get('attributeCategoryID'),
                               defaultValue=attribute.get('defaultValue'),
                               description=attribute.get('description'),
                               iconID=attribute.get('iconID'),
                               attributeName=attribute.get('displayName',{}).get(language, 'None'),
                               published=attribute.get('published'),
                               unitID=attribute.get('unitID'),
                               stackable=attribute.get('stackable'),
                               highIsGood=attribute.get('highIsGood'),
                               displayName=attribute.get('displayName',{}).get(language, 'None'),
                ))
    trans.commit()
