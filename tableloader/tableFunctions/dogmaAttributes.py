# -*- coding: utf-8 -*-
import os
from sqlalchemy import Table

from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader



def importyaml(connection,metadata,sourcePath,language='en'):
    print("Importing Dogma Attributes")
    dgmAttributes = Table('dgmAttributeTypes',metadata)
    
    targetPath = os.path.join(sourcePath, 'dogmaAttributes.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'dogmaAttributes.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'dogmaAttributes.yaml')

    print(f"  Opening {targetPath}")

    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        dogmaAttributes=load(yamlstream,Loader=SafeLoader)
        print(f"  Processing {len(dogmaAttributes)} attributes")
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
    print("  Done")
