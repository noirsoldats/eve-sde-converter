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
    print("Importing Dogma Attribute Categories")
    dgmAttributeCategories = Table('dgmAttributeCategories',metadata)
    
    targetPath = os.path.join(sourcePath, 'dogmaAttributeCategories.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'dogmaAttributeCategories.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'dogmaAttributeCategories.yaml')

    print(f"Opening {targetPath}")
        
    trans = connection.begin()
    with open(targetPath,'r', encoding='utf-8') as yamlstream:
        dogmaAttributeCategories=load(yamlstream,Loader=SafeLoader)
        print(f"Populating Dogma Attribute Categories Table with {len(dogmaAttributeCategories)} entries")
        for dogmaAttributeCategoryID in dogmaAttributeCategories:
          attribute = dogmaAttributeCategories[dogmaAttributeCategoryID]
          connection.execute(dgmAttributeCategories.insert().values(
                             categoryID=dogmaAttributeCategoryID,
                             categoryName=attribute['name'],
                             categoryDescription=attribute.get('description','')
                ))
    trans.commit()
