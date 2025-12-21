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
    certCerts = Table('certCerts',metadata)
    certSkills = Table('certSkills',metadata,)
    skillmap={"basic":0,"standard":1,"improved":2,"advanced":3,"elite":4}

    print("Importing Certificates")
    print("opening Yaml")
    with open(os.path.join(sourcePath,'certificates.yaml'),'r', encoding='utf-8') as yamlstream:
        trans = connection.begin()
        certificates=load(yamlstream,Loader=SafeLoader)
        print("Yaml Processed into memory")
        for certificate in certificates:
            # Extract language-specific strings from dictionaries
            name_data = certificates[certificate].get('name', {})
            name = name_data.get(language, '') if isinstance(name_data, dict) else str(name_data)

            description_data = certificates[certificate].get('description', {})
            description = description_data.get(language, '') if isinstance(description_data, dict) else str(description_data)

            connection.execute(certCerts.insert().values(
                            certID=certificate,
                            name=name,
                            description=description,
                            groupID=certificates[certificate].get('groupID')))
            for skill in certificates[certificate]['skillTypes']:
                for skillLevel in certificates[certificate]['skillTypes'][skill]:
                    connection.execute(certSkills.insert().values(
                                        certID=certificate,
                                        skillID=skill,
                                        certLevelInt=skillmap[skillLevel],
                                        certLevelText=skillLevel,
                                        skillLevel=certificates[certificate]['skillTypes'][skill][skillLevel]
                                        ))
    trans.commit()
