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


distribution={'twosome':1,'bubble':2}
effectcategory={}


def importyaml(connection,metadata,sourcePath,language='en'):
    print("Importing dogma effects")
    dgmEffects = Table('dgmTypeEffects',metadata)
    dgmAttributes = Table('dgmTypeAttributes',metadata)
    
    print("opening Yaml")
        
    trans = connection.begin()
    with open(os.path.join(sourcePath,'typeDogma.yaml'),'r', encoding='utf-8') as yamlstream:
        print("importing")
        dogmaEffects=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for typeid in dogmaEffects:
            # Check if this type has dogmaEffects defined
            if 'dogmaEffects' in dogmaEffects[typeid]:
                for effect in dogmaEffects[typeid]['dogmaEffects']:
                    connection.execute(dgmEffects.insert().values(
                                    typeID=typeid,
                                    effectID=effect['effectID'],
                                    isDefault=effect.get('isDefault')
                    ))
            # Check if this type has dogmaAttributes defined
            if 'dogmaAttributes' in dogmaEffects[typeid]:
                for attribute in dogmaEffects[typeid]['dogmaAttributes']:
                    connection.execute(dgmAttributes.insert().values(
                                    typeID=typeid,
                                    attributeID=attribute.get('attributeID'),
                                    valueFloat=attribute.get('value')
                    ))
    trans.commit()
