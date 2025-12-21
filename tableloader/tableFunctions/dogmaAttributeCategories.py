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
    print("Importing dogma attribute categories")
    dgmAttributeCategories = Table('dgmAttributeCategories',metadata)
    
    print("opening Yaml")
        
    trans = connection.begin()
    with open(os.path.join(sourcePath,'dogmaAttributeCategories.yaml'),'r', encoding='utf-8') as yamlstream:
        print("importing")
        dogmaAttributeCategories=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for dogmaAttributeCategoryID in dogmaAttributeCategories:
          attribute = dogmaAttributeCategories[dogmaAttributeCategoryID]
          connection.execute(dgmAttributeCategories.insert().values(
                             categoryID=dogmaAttributeCategoryID,
                             categoryName=attribute['name'],
                             categoryDescription=attribute.get('description','')
                ))
    trans.commit()
