# -*- coding: utf-8 -*-
import sys
from yaml import load, dump
try:
	from yaml import CSafeLoader as SafeLoader
	print("Using CSafeLoader")
except ImportError:
	from yaml import SafeLoader
	print("Using Python SafeLoader")

import os
from sqlalchemy import Table,select,text
import glob

typeidcache={}
group_name_cache={}

def get_group_id_by_name(connection, metadata, group_name):
    if group_name in group_name_cache:
        return group_name_cache[group_name]

    invGroups = Table('invGroups', metadata)
    try:
        # Use select generic sqlalchemy
        row = connection.execute(
            select(invGroups.c.groupID).where(invGroups.c.groupName == group_name)
        ).fetchone()
        if row:
            id = row[0]
            group_name_cache[group_name] = id
            return id
    except Exception as e:
        print(f"Warning: Could not resolve group ID for '{group_name}': {e}")
    
    return None

def grouplookup(connection,metadata,typeid,defaultid=None):

    if typeidcache.get(typeid):
        return typeidcache.get(typeid)

    invTypes =  Table('invTypes', metadata)
    try:
        groupid=connection.execute(
                invTypes.select().where( invTypes.c.typeID == typeid )
            ).fetchall()[0]['groupID']
    except:
        if defaultid is not None:
             # Silence error if we have a valid default (expected behavior for some system types)
             groupid=defaultid
        else:
             print("Group lookup failed on typeid {}".format(typeid))
             groupid=-1
    typeidcache[typeid]=groupid
    return groupid

def get_distance_squared(c1, c2):
    pos = c1['position']
    mx, my, mz = pos[0], pos[1], pos[2]
    pos = c2['position']
    px, py, pz = pos[0], pos[1], pos[2]
    dx, dy, dz = mx - px, my - py, mz - pz

    return dx * dx + dy * dy + dz * dz

def get_sorted_objects(planet, key):
    with_radius = [(get_distance_squared(obj, planet), obj_id)
                   for (obj_id, obj)
                   in planet.get(key, {}).items()]
    with_radius.sort()
    return [obj_id for (radius, obj_id) in with_radius]

def importyaml(connection,metadata,sourcePath,language='en'):
    """Import universe data from new consolidated YAML files"""

    print("Importing universe data")

    # Get table references
    mapRegions = Table('mapRegions', metadata)
    mapConstellations = Table('mapConstellations', metadata)
    mapSolarSystems = Table('mapSolarSystems', metadata)
    mapDenormalize = Table('mapDenormalize', metadata)
    mapJumps = Table('mapJumps', metadata)
    
    # Pre-resolve standard group IDs by name to handle missing TypeIDs in modern SDE
    gid_stargate = get_group_id_by_name(connection, metadata, 'Stargate')
    gid_planet = get_group_id_by_name(connection, metadata, 'Planet')
    gid_moon = get_group_id_by_name(connection, metadata, 'Moon')
    gid_asteroid = get_group_id_by_name(connection, metadata, 'Asteroid Belt')
    gid_sun = get_group_id_by_name(connection, metadata, 'Sun')

    # Import regions
    print("Importing regions from mapRegions.yaml")
    with open(os.path.join(sourcePath, 'mapRegions.yaml'), 'r', encoding='utf-8') as yamlstream:
        regions = load(yamlstream, Loader=SafeLoader)
        print(f"Processing {len(regions)} regions")

        for regionID, region in regions.items():
            # Extract name based on language
            name_data = region.get('name', {})
            regionName = name_data.get(language, '') if isinstance(name_data, dict) else str(name_data)

            position = region.get('position', {})

            # Note: The new SDE doesn't provide min/max bounds, only position
            # We'll leave those as None or calculate them if needed
            connection.execute(mapRegions.insert().values(
                regionID=regionID,
                regionName=regionName,
                x=position.get('x'),
                y=position.get('y'),
                z=position.get('z'),
                xMin=None,  # Not provided in new SDE
                xMax=None,
                yMin=None,
                yMax=None,
                zMin=None,
                zMax=None,
                factionID=region.get('factionID'),
                nebula=region.get('nebulaID'),
                radius=None  # Not provided in new SDE
            ))

    connection.commit()
    print(f"Imported {len(regions)} regions")

    # Import constellations
    print("Importing constellations from mapConstellations.yaml")
    with open(os.path.join(sourcePath, 'mapConstellations.yaml'), 'r', encoding='utf-8') as yamlstream:
        constellations = load(yamlstream, Loader=SafeLoader)
        print(f"Processing {len(constellations)} constellations")

        for constellationID, constellation in constellations.items():
            # Extract name based on language
            name_data = constellation.get('name', {})
            constellationName = name_data.get(language, '') if isinstance(name_data, dict) else str(name_data)

            position = constellation.get('position', {})

            connection.execute(mapConstellations.insert().values(
                constellationID=constellationID,
                constellationName=constellationName,
                regionID=constellation.get('regionID'),
                x=position.get('x'),
                y=position.get('y'),
                z=position.get('z'),
                xMin=None,
                xMax=None,
                yMin=None,
                yMax=None,
                zMin=None,
                zMax=None,
                factionID=constellation.get('factionID'),
                radius=None
            ))

    connection.commit()
    print(f"Imported {len(constellations)} constellations")

    # Import solar systems
    print("Importing solar systems from mapSolarSystems.yaml")
    with open(os.path.join(sourcePath, 'mapSolarSystems.yaml'), 'r', encoding='utf-8') as yamlstream:
        systems = load(yamlstream, Loader=SafeLoader)
        print(f"Processing {len(systems)} solar systems")

        for solarSystemID, system in systems.items():
            # Extract name based on language
            name_data = system.get('name', {})
            solarSystemName = name_data.get(language, '') if isinstance(name_data, dict) else str(name_data)

            position = system.get('position', {})
            position2D = system.get('position2D', {})

            connection.execute(mapSolarSystems.insert().values(
                solarSystemID=solarSystemID,
                solarSystemName=solarSystemName,
                regionID=system.get('regionID'),
                constellationID=system.get('constellationID'),
                x=position.get('x'),
                y=position.get('y'),
                z=position.get('z'),
                xMin=None,
                xMax=None,
                yMin=None,
                yMax=None,
                zMin=None,
                zMax=None,
                luminosity=system.get('luminosity'),
                border=system.get('border', False),
                fringe=system.get('fringe', False),
                corridor=system.get('corridor', False),
                hub=system.get('hub', False),
                international=system.get('international', False),
                regional=system.get('regional', False),
                constellation=None,  # Not in new SDE
                security=system.get('securityStatus'),
                factionID=system.get('factionID'),
                radius=system.get('radius'),
                sunTypeID=None,
                starID=system.get('starID'),
                securityClass=system.get('securityClass'),
                x2D=position2D.get('x'),
                y2D=position2D.get('y')
            ))

    connection.commit()
    print(f"Imported {len(systems)} solar systems")

    # Import stargates and populate mapJumps
    print("Importing stargates from mapStargates.yaml")
    try:
        with open(os.path.join(sourcePath, 'mapStargates.yaml'), 'r', encoding='utf-8') as yamlstream:
            stargates = load(yamlstream, Loader=SafeLoader)
            print(f"Processing {len(stargates)} stargates")

            for stargateID, stargate in stargates.items():
                # Add to mapJumps for navigation
                destination = stargate.get('destination')
                if destination:
                    # destination is a dict with 'stargateID' and 'solarSystemID'
                    destinationID = destination.get('stargateID') if isinstance(destination, dict) else destination
                    connection.execute(mapJumps.insert().values(
                        stargateID=stargateID,
                        destinationID=destinationID
                    ))

                # Add to mapDenormalize
                position = stargate.get('position', {})
                connection.execute(mapDenormalize.insert().values(
                    itemID=stargateID,
                    typeID=stargate.get('typeID'),
                    groupID=grouplookup(connection, metadata, stargate.get('typeID'), defaultid=gid_stargate),
                    solarSystemID=stargate.get('solarSystemID'),
                    constellationID=None,  # Will be filled by denormalization
                    regionID=None,  # Will be filled by denormalization
                    orbitID=None,
                    x=position.get('x'),
                    y=position.get('y'),
                    z=position.get('z'),
                    radius=None,
                    itemName=None,  # Stargates don't have custom names in new SDE
                    security=None,
                    celestialIndex=None,
                    orbitIndex=None
                ))

        connection.commit()
        print(f"Imported {len(stargates)} stargates and jump connections")
    except FileNotFoundError:
        print("Warning: mapStargates.yaml not found, skipping stargate import")

    # Import planets
    print("Importing planets from mapPlanets.yaml")
    try:
        with open(os.path.join(sourcePath, 'mapPlanets.yaml'), 'r', encoding='utf-8') as yamlstream:
            planets = load(yamlstream, Loader=SafeLoader)
            print(f"Processing {len(planets)} planets")

            for planetID, planet in planets.items():
                position = planet.get('position', {})
                connection.execute(mapDenormalize.insert().values(
                    itemID=planetID,
                    typeID=planet.get('typeID'),
                    groupID=grouplookup(connection, metadata, planet.get('typeID'), defaultid=gid_planet),
                    solarSystemID=planet.get('solarSystemID'),
                    constellationID=None,
                    regionID=None,
                    orbitID=None,
                    x=position.get('x'),
                    y=position.get('y'),
                    z=position.get('z'),
                    radius=planet.get('radius'),
                    itemName=None,
                    security=None,
                    celestialIndex=planet.get('celestialIndex'),
                    orbitIndex=None
                ))

        connection.commit()
        print(f"Imported {len(planets)} planets")
    except FileNotFoundError:
        print("Warning: mapPlanets.yaml not found, skipping planet import")

    # Import moons
    print("Importing moons from mapMoons.yaml")
    try:
        with open(os.path.join(sourcePath, 'mapMoons.yaml'), 'r', encoding='utf-8') as yamlstream:
            moons = load(yamlstream, Loader=SafeLoader)
            print(f"Processing {len(moons)} moons")

            for moonID, moon in moons.items():
                position = moon.get('position', {})
                connection.execute(mapDenormalize.insert().values(
                    itemID=moonID,
                    typeID=moon.get('typeID'),
                    groupID=grouplookup(connection, metadata, moon.get('typeID'), defaultid=gid_moon),
                    solarSystemID=moon.get('solarSystemID'),
                    constellationID=None,
                    regionID=None,
                    orbitID=moon.get('planetID'),  # Moons orbit planets
                    x=position.get('x'),
                    y=position.get('y'),
                    z=position.get('z'),
                    radius=moon.get('radius'),
                    itemName=None,
                    security=None,
                    celestialIndex=None,
                    orbitIndex=None
                ))

        connection.commit()
        print(f"Imported {len(moons)} moons")
    except FileNotFoundError:
        print("Warning: mapMoons.yaml not found, skipping moon import")

    # Import asteroid belts
    print("Importing asteroid belts from mapAsteroidBelts.yaml")
    try:
        with open(os.path.join(sourcePath, 'mapAsteroidBelts.yaml'), 'r', encoding='utf-8') as yamlstream:
            belts = load(yamlstream, Loader=SafeLoader)
            print(f"Processing {len(belts)} asteroid belts")

            for beltID, belt in belts.items():
                position = belt.get('position', {})
                connection.execute(mapDenormalize.insert().values(
                    itemID=beltID,
                    typeID=belt.get('typeID'),
                    groupID=grouplookup(connection, metadata, belt.get('typeID'), defaultid=gid_asteroid),
                    solarSystemID=belt.get('solarSystemID'),
                    constellationID=None,
                    regionID=None,
                    orbitID=None,
                    x=position.get('x'),
                    y=position.get('y'),
                    z=position.get('z'),
                    radius=None,
                    itemName=None,
                    security=None,
                    celestialIndex=None,
                    orbitIndex=None
                ))

        connection.commit()
        print(f"Imported {len(belts)} asteroid belts")
    except FileNotFoundError:
        print("Warning: mapAsteroidBelts.yaml not found, skipping asteroid belt import")

    # Import stars
    print("Importing stars from mapStars.yaml")
    try:
        with open(os.path.join(sourcePath, 'mapStars.yaml'), 'r', encoding='utf-8') as yamlstream:
            stars = load(yamlstream, Loader=SafeLoader)
            print(f"Processing {len(stars)} stars")

            for starID, star in stars.items():
                position = star.get('position', {})
                connection.execute(mapDenormalize.insert().values(
                    itemID=starID,
                    typeID=star.get('typeID'),
                    groupID=grouplookup(connection, metadata, star.get('typeID'), defaultid=gid_sun),
                    solarSystemID=star.get('solarSystemID'),
                    constellationID=None,
                    regionID=None,
                    orbitID=None,
                    x=position.get('x'),
                    y=position.get('y'),
                    z=position.get('z'),
                    radius=star.get('radius'),
                    itemName=None,
                    security=None,
                    celestialIndex=None,
                    orbitIndex=None
                ))

        connection.commit()
        print(f"Imported {len(stars)} stars")
    except FileNotFoundError:
        print("Warning: mapStars.yaml not found, skipping star import")

    print("Universe data import complete")


def buildJumps(connection,connectiontype):

    sql={}
    sql['postgres']=[]
    sql['postgresschema']=[]
    sql['other']=[]

    sql['postgres'].append("""insert into "mapSolarSystemJumps" ("fromRegionID","fromConstellationID","fromSolarSystemID","toRegionID","toConstellationID","toSolarSystemID")
    select f."regionID" "fromRegionID",f."constellationID" "fromConstellationID",f."solarSystemID" "fromSolarSystemID",t."regionID" "toRegionID",t."constellationID" "toConstellationID",t."solarSystemID" "toSolarSystemID"
    from "mapJumps" join "mapDenormalize" f on "mapJumps"."stargateID"=f."itemID" join "mapDenormalize" t on "mapJumps"."destinationID"=t."itemID" """)
    sql['postgres'].append("""insert into "mapRegionJumps"
    select distinct f."regionID",t."regionID"
    from "mapJumps" join "mapDenormalize" f on "mapJumps"."stargateID"=f."itemID" join "mapDenormalize" t on "mapJumps"."destinationID"=t."itemID" where f."regionID"!=t."regionID" """)
    sql['postgres'].append("""insert into "mapConstellationJumps"
    select distinct f."regionID",f."constellationID",t."constellationID",t."regionID"
    from "mapJumps" join "mapDenormalize" f on "mapJumps"."stargateID"=f."itemID" join "mapDenormalize" t on "mapJumps"."destinationID"=t."itemID" where f."constellationID"!=t."constellationID" """)
    sql['postgresschema'].append("""insert into evesde."mapSolarSystemJumps" ("fromRegionID","fromConstellationID","fromSolarSystemID","toRegionID","toConstellationID","toSolarSystemID")
    select f."regionID" "fromRegionID",f."constellationID" "fromConstellationID",f."solarSystemID" "fromSolarSystemID",t."regionID" "toRegionID",t."constellationID" "toConstellationID",t."solarSystemID" "toSolarSystemID"
    from  evesde."mapJumps" join  evesde."mapDenormalize" f on "mapJumps"."stargateID"=f."itemID" join  evesde."mapDenormalize" t on "mapJumps"."destinationID"=t."itemID" """)
    sql['postgresschema'].append("""insert into  evesde."mapRegionJumps"
    select distinct f."regionID",t."regionID"
    from  evesde."mapJumps" join  evesde."mapDenormalize" f on "mapJumps"."stargateID"=f."itemID" join  evesde."mapDenormalize" t on "mapJumps"."destinationID"=t."itemID" where f."regionID"!=t."regionID" """)
    sql['postgresschema'].append("""insert into  evesde."mapConstellationJumps"
    select distinct f."regionID",f."constellationID",t."constellationID",t."regionID"
    from  evesde."mapJumps" join  evesde."mapDenormalize" f on "mapJumps"."stargateID"=f."itemID" join  evesde."mapDenormalize" t on "mapJumps"."destinationID"=t."itemID" where f."constellationID"!=t."constellationID" """)

    sql['other'].append("""insert into mapSolarSystemJumps (fromRegionID,fromConstellationID,fromSolarSystemID,toRegionID,toConstellationID,toSolarSystemID)
    select f.regionID fromRegionID,f.constellationID fromConstellationID,f.solarSystemID fromSolarSystemID,t.regionID toRegionID,t.constellationID toConstellationID,t.solarSystemID toSolarSystemID
    from mapJumps join mapDenormalize f on mapJumps.stargateID=f.itemID join mapDenormalize t on mapJumps.destinationID=t.itemID""")
    sql['other'].append("""insert into mapRegionJumps
    select distinct f.regionID,t.regionID
    from mapJumps join mapDenormalize f on mapJumps.stargateID=f.itemID join mapDenormalize t on mapJumps.destinationID=t.itemID where f.regionID!=t.regionID""")
    sql['other'].append("""insert into mapConstellationJumps
    select distinct f.regionID,f.constellationID,t.constellationID,t.regionID
    from mapJumps join mapDenormalize f on mapJumps.stargateID=f.itemID join mapDenormalize t on mapJumps.destinationID=t.itemID where f.constellationID!=t.constellationID""")

    if connectiontype == "sqlite" or connectiontype == "mysql" or connectiontype=="mssql":
        connectiontype="other"
    connection.execute(text(sql[connectiontype][0]))
    connection.execute(text(sql[connectiontype][1]))
    connection.execute(text(sql[connectiontype][2]))
    connection.commit()


def fixStationNames(connection,metadata):
    """
    Update station names from npcStations data
    Note: In the new SDE, station names are embedded in the npcStations.yaml file
    This function may no longer be necessary if stations.py handles names directly
    """
    print("Checking if station name fixup is needed...")

    # Check if staStations table exists and has data
    try:
        staStations = Table('staStations', metadata)
        result = connection.execute(text("SELECT COUNT(*) FROM staStations")).fetchone()
        if result and result[0] > 0:
            print(f"Found {result[0]} stations, station names should already be populated from npcStations.yaml")
        else:
            print("No stations found in staStations table")
    except Exception as e:
        print(f"Could not check staStations: {e}")

    # Commit transaction (query above triggered autobegin)
    connection.commit()
