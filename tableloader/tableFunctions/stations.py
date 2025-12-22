# -*- coding: utf-8 -*-
import os
from sqlalchemy import Table

from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


def int_to_roman(num):
    """Convert an integer to a Roman numeral."""
    val = [
        1000, 900, 500, 400,
        100, 90, 50, 40,
        10, 9, 5, 4,
        1
    ]
    syms = [
        "M", "CM", "D", "CD",
        "C", "XC", "L", "XL",
        "X", "IX", "V", "IV",
        "I"
    ]
    roman_num = ''
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syms[i]
            num -= val[i]
        i += 1
    return roman_num


def importyaml(connection, metadata, sourcePath, language='en'):
    print("Importing Stations")

    staStations = Table('staStations', metadata)
    staOperations = Table('staOperations', metadata)
    staServices = Table('staServices', metadata)
    staOperationServices = Table('staOperationServices', metadata)

    print("Importing Station Operations")
    targetPath = os.path.join(sourcePath, 'stationOperations.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'stationOperations.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'stationOperations.yaml')

    print(f"  Opening {targetPath}")
    with open(targetPath, 'r', encoding='utf-8') as yamlstream:
        operations = load(yamlstream, Loader=SafeLoader)
        print(f"  Processing {len(operations)} station operations")

        for operationID, operation in operations.items():
            # Extract operation name based on language
            name_data = operation.get('operationName', {})
            operationName = name_data.get(language, '') if isinstance(name_data, dict) else str(name_data)

            # Extract description based on language
            desc_data = operation.get('description', {})
            description = desc_data.get(language, '') if isinstance(desc_data, dict) else str(desc_data)

            # Get station types - this is a dict like {1: typeID1, 2: typeID2, 4: typeID3, 8: typeID4, 16: typeID5}
            # These map to factions: 1=Caldari, 2=Minmatar, 4=Amarr, 8=Gallente, 16=Jove
            station_types = operation.get('stationTypes', {})

            connection.execute(staOperations.insert().values(
                activityID=operation.get('activityID'),
                operationID=operationID,
                operationName=operationName,
                description=description,
                fringe=operation.get('fringe'),
                corridor=operation.get('corridor'),
                hub=operation.get('hub'),
                border=operation.get('border'),
                ratio=operation.get('ratio'),
                caldariStationTypeID=station_types.get(1),
                minmatarStationTypeID=station_types.get(2),
                amarrStationTypeID=station_types.get(4),
                gallenteStationTypeID=station_types.get(8),
                joveStationTypeID=station_types.get(16)
            ))

            # Import operation services (many-to-many relationship)
            services = operation.get('services', [])
            for serviceID in services:
                connection.execute(staOperationServices.insert().values(
                    operationID=operationID,
                    serviceID=serviceID
                ))

    connection.commit()
    print("  Done")

    print("Importing NPC Stations")
    targetPath = os.path.join(sourcePath, 'npcStations.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'npcStations.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'npcStations.yaml')

    print(f"  Opening {targetPath}")
    with open(targetPath, 'r', encoding='utf-8') as yamlstream:
        stations = load(yamlstream, Loader=SafeLoader)
        print(f"  Processing {len(stations)} NPC stations")

        for stationID, station in stations.items():
            position = station.get('position', {})

            # Get ownerID (corporationID)
            corporationID = station.get('ownerID')

            # Get solarSystemID to lookup constellation and region
            solarSystemID = station.get('solarSystemID')

            # Lookup constellation and region from mapSolarSystems
            constellationID = None
            regionID = None
            security = None

            if solarSystemID:
                mapSolarSystems = Table('mapSolarSystems', metadata)
                try:
                    result = connection.execute(
                        mapSolarSystems.select().where(mapSolarSystems.c.solarSystemID == solarSystemID)
                    ).fetchone()
                    if result:
                        constellationID = result.constellationID
                        regionID = result.regionID
                        security = result.security
                except:
                    pass

            # Build station name
            stationName = None
            if station.get('useOperationName', False):
                # Format: [System Name] [Planet Roman] - Moon [Moon#] - [Corp Name] [Operation]
                # Example: Muvolailen X - Moon 3 - CBD Corporation Storage

                # Get solar system name
                systemName = None
                if solarSystemID:
                    mapSolarSystems = Table('mapSolarSystems', metadata)
                    try:
                        result = connection.execute(
                            mapSolarSystems.select().where(mapSolarSystems.c.solarSystemID == solarSystemID)
                        ).fetchone()
                        if result:
                            systemName = result.solarSystemName
                    except:
                        pass

                # Get planet celestial index from the moon's orbitID
                planetRoman = None
                orbitID = station.get('orbitID')
                planetRoman = int_to_roman(station.get('celestialIndex', 0))
                # Get moon number (orbitIndex)
                moonString = None
                moonNumber = station.get('orbitIndex', None)
                if moonNumber:
                    moonString = f" Moon {moonNumber} -"
                else:
                    moonString = ""

                # Get corporation name
                corpName = None
                ownerID = station.get('ownerID')
                if ownerID:
                    crpNPCCorporations = Table('crpNPCCorporations', metadata)
                    try:
                        corp_result = connection.execute(
                            crpNPCCorporations.select().where(crpNPCCorporations.c.corporationID == ownerID)
                        ).fetchone()
                        if corp_result:
                            corpName = corp_result.corporationName
                    except:
                        pass

                # Get operation name
                operationName = None
                operationID = station.get('operationID')
                if operationID:
                    staOperationsTable = Table('staOperations', metadata)
                    try:
                        op_result = connection.execute(
                            staOperationsTable.select().where(staOperationsTable.c.operationID == operationID)
                        ).fetchone()
                        if op_result:
                            operationName = op_result.operationName
                    except:
                        pass

                # Build the full name
                if systemName and corpName and operationName:
                    stationName = f"{systemName} {planetRoman} -{moonString} {corpName} {operationName}"
                else:
                    # Fallback if we're missing components
                    stationName = f"FB {systemName} {planetRoman} -{moonString} {corpName} {operationName}"
                    # stationName = f"Fallback Station {stationID}"
            else:
                # If not using operation name, just use a generic name
                stationName = f"Op False Station {stationID}"

            connection.execute(staStations.insert().values(
                stationID=stationID,
                security=security,
                dockingCostPerVolume=None,  # Not in new SDE
                maxShipVolumeDockable=None,  # Not in new SDE
                officeRentalCost=None,  # Not in new SDE
                operationID=station.get('operationID'),
                stationTypeID=station.get('typeID'),
                corporationID=corporationID,
                solarSystemID=solarSystemID,
                constellationID=constellationID,
                regionID=regionID,
                stationName=stationName,
                x=position.get('x'),
                y=position.get('y'),
                z=position.get('z'),
                reprocessingEfficiency=station.get('reprocessingEfficiency'),
                reprocessingStationsTake=station.get('reprocessingStationsTake'),
                reprocessingHangarFlag=station.get('reprocessingHangarFlag')
            ))

    connection.commit()
    print("  Done")

    print("Importing Station Services")
    targetPath = os.path.join(sourcePath, 'stationServices.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'stationServices.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'stationServices.yaml')

    print(f"  Opening {targetPath}")
    with open(targetPath, 'r', encoding='utf-8') as yamlstream:
        services = load(yamlstream, Loader=SafeLoader)
        print(f"  Processing {len(services)} station services")

        for serviceID, service in services.items():
            # Extract service name based on language
            name_data = service.get('serviceName', {})
            serviceName = name_data.get(language, '') if isinstance(name_data, dict) else str(name_data)

            # Extract description if present
            desc_data = service.get('description', {})
            description = desc_data.get(language, '') if isinstance(desc_data, dict) else ''

            connection.execute(staServices.insert().values(
                serviceID=serviceID,
                serviceName=serviceName,
                description=description
            ))

    connection.commit()
    print("  Done")
