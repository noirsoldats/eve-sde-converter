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
    print("Importing Type Materials")
    invTypeMaterials = Table('invTypeMaterials',metadata)
    
    print("opening Yaml")
        
    trans = connection.begin()
    with open(os.path.join(sourcePath,'typeMaterials.yaml'),'r', encoding='utf-8') as yamlstream:
        print("importing")
        materials=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for typeid in materials:
            # Check if this type has materials defined
            if 'materials' in materials[typeid]:
                for material in materials[typeid]['materials']:
                    connection.execute(invTypeMaterials.insert().values(
                                typeID=typeid,
                                materialTypeID=material['materialTypeID'],
                                quantity=material['quantity']
                    ))
    trans.commit()
