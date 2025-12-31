# -*- coding: utf-8 -*-
from yaml import load
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

import os
from sqlalchemy import Table, select, text

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

    print("Importing Universe")

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

    print("Importing Regions")

    targetPath = os.path.join(sourcePath, 'mapRegions.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'mapRegions.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'mapRegions.yaml')

    print(f"  Opening {targetPath}")
    with open(targetPath, 'r', encoding='utf-8') as yamlstream:
        regions = load(yamlstream, Loader=SafeLoader)
        print(f"  Processing {len(regions)} regions")

        region_rows = []
        for regionID, region in regions.items():
            # Extract name based on language
            name_data = region.get('name', {})
            regionName = name_data.get(language, '') if isinstance(name_data, dict) else str(name_data)

            position = region.get('position', {})

            # Note: The new SDE doesn't provide min/max bounds, only position
            # We'll leave those as None or calculate them if needed
            region_rows.append({
                'regionID': regionID,
                'regionName': regionName,
                'x': position.get('x'),
                'y': position.get('y'),
                'z': position.get('z'),
                'xMin': None,  # Not provided in new SDE
                'xMax': None,
                'yMin': None,
                'yMax': None,
                'zMin': None,
                'zMax': None,
                'factionID': region.get('factionID'),
                'nebula': region.get('nebulaID'),
                'radius': None  # Not provided in new SDE
            })

        if region_rows:
            connection.execute(mapRegions.insert(), region_rows)
            print(f"  Inserted {len(region_rows)} regions")

    connection.commit()
    print("  Done")

    print("Importing Constellations")
    targetPath = os.path.join(sourcePath, 'mapConstellations.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'mapConstellations.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'mapConstellations.yaml')

    print(f"  Opening {targetPath}")
    with open(targetPath, 'r', encoding='utf-8') as yamlstream:
        constellations = load(yamlstream, Loader=SafeLoader)
        print(f"  Processing {len(constellations)} constellations")

        constellation_rows = []
        for constellationID, constellation in constellations.items():
            # Extract name based on language
            name_data = constellation.get('name', {})
            constellationName = name_data.get(language, '') if isinstance(name_data, dict) else str(name_data)

            position = constellation.get('position', {})

            constellation_rows.append({
                'constellationID': constellationID,
                'constellationName': constellationName,
                'regionID': constellation.get('regionID'),
                'x': position.get('x'),
                'y': position.get('y'),
                'z': position.get('z'),
                'xMin': None,
                'xMax': None,
                'yMin': None,
                'yMax': None,
                'zMin': None,
                'zMax': None,
                'factionID': constellation.get('factionID'),
                'radius': None
            })

        if constellation_rows:
            connection.execute(mapConstellations.insert(), constellation_rows)
            print(f"  Inserted {len(constellation_rows)} constellations")

    connection.commit()
    print("  Done")

    print("Importing Solar Systems")
    targetPath = os.path.join(sourcePath, 'mapSolarSystems.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'fsd', 'mapSolarSystems.yaml')
    if not os.path.exists(targetPath):
        targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'mapSolarSystems.yaml')

    print(f"  Opening {targetPath}")
    with open(targetPath, 'r', encoding='utf-8') as yamlstream:
        systems = load(yamlstream, Loader=SafeLoader)
        print(f"  Processing {len(systems)} solar systems")

        system_rows = []
        for solarSystemID, system in systems.items():
            # Extract name based on language
            name_data = system.get('name', {})
            solarSystemName = name_data.get(language, '') if isinstance(name_data, dict) else str(name_data)

            position = system.get('position', {})
            position2D = system.get('position2D', {})

            system_rows.append({
                'solarSystemID': solarSystemID,
                'solarSystemName': solarSystemName,
                'regionID': system.get('regionID'),
                'constellationID': system.get('constellationID'),
                'x': position.get('x'),
                'y': position.get('y'),
                'z': position.get('z'),
                'xMin': None,
                'xMax': None,
                'yMin': None,
                'yMax': None,
                'zMin': None,
                'zMax': None,
                'luminosity': system.get('luminosity'),
                'border': system.get('border', False),
                'fringe': system.get('fringe', False),
                'corridor': system.get('corridor', False),
                'hub': system.get('hub', False),
                'international': system.get('international', False),
                'regional': system.get('regional', False),
                'constellation': None,  # Not in new SDE
                'security': system.get('securityStatus'),
                'factionID': system.get('factionID'),
                'radius': system.get('radius'),
                'sunTypeID': None,
                'starID': system.get('starID'),
                'securityClass': system.get('securityClass'),
                'x2D': position2D.get('x'),
                'y2D': position2D.get('y')
            })

        if system_rows:
            connection.execute(mapSolarSystems.insert(), system_rows)
            print(f"  Inserted {len(system_rows)} solar systems")

    connection.commit()
    print("  Done")

    print("Importing Stargates")
    try:
        targetPath = os.path.join(sourcePath, 'mapStargates.yaml')
        if not os.path.exists(targetPath):
            targetPath = os.path.join(sourcePath, 'fsd', 'mapStargates.yaml')
        if not os.path.exists(targetPath):
            targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'mapStargates.yaml')

        print(f"  Opening {targetPath}")
        with open(targetPath, 'r', encoding='utf-8') as yamlstream:
            stargates = load(yamlstream, Loader=SafeLoader)
            print(f"  Processing {len(stargates)} stargates")

            jump_rows = []
            denormalize_rows = []
            for stargateID, stargate in stargates.items():
                # Add to mapJumps for navigation
                destination = stargate.get('destination')
                if destination:
                    # destination is a dict with 'stargateID' and 'solarSystemID'
                    destinationID = destination.get('stargateID') if isinstance(destination, dict) else destination
                    jump_rows.append({
                        'stargateID': stargateID,
                        'destinationID': destinationID
                    })

                # Add to mapDenormalize
                position = stargate.get('position', {})
                denormalize_rows.append({
                    'itemID': stargateID,
                    'typeID': stargate.get('typeID'),
                    'groupID': grouplookup(connection, metadata, stargate.get('typeID'), defaultid=gid_stargate),
                    'solarSystemID': stargate.get('solarSystemID'),
                    'constellationID': None,  # Will be filled by denormalization
                    'regionID': None,  # Will be filled by denormalization
                    'orbitID': None,
                    'x': position.get('x'),
                    'y': position.get('y'),
                    'z': position.get('z'),
                    'radius': None,
                    'itemName': None,  # Stargates don't have custom names in new SDE
                    'security': None,
                    'celestialIndex': None,
                    'orbitIndex': None
                })

            if jump_rows:
                connection.execute(mapJumps.insert(), jump_rows)
                print(f"  Inserted {len(jump_rows)} stargate jumps")
            if denormalize_rows:
                connection.execute(mapDenormalize.insert(), denormalize_rows)
                print(f"  Inserted {len(denormalize_rows)} stargates into mapDenormalize")

        connection.commit()
        print("  Done")
    except FileNotFoundError:
        print("  Warning: mapStargates.yaml not found, skipping")

    print("Importing Planets")
    try:
        targetPath = os.path.join(sourcePath, 'mapPlanets.yaml')
        if not os.path.exists(targetPath):
            targetPath = os.path.join(sourcePath, 'fsd', 'mapPlanets.yaml')
        if not os.path.exists(targetPath):
            targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'mapPlanets.yaml')

        print(f"  Opening {targetPath}")
        with open(targetPath, 'r', encoding='utf-8') as yamlstream:
            planets = load(yamlstream, Loader=SafeLoader)
            print(f"  Processing {len(planets)} planets")

            planet_rows = []
            for planetID, planet in planets.items():
                position = planet.get('position', {})
                planet_rows.append({
                    'itemID': planetID,
                    'typeID': planet.get('typeID'),
                    'groupID': grouplookup(connection, metadata, planet.get('typeID'), defaultid=gid_planet),
                    'solarSystemID': planet.get('solarSystemID'),
                    'constellationID': None,
                    'regionID': None,
                    'orbitID': None,
                    'x': position.get('x'),
                    'y': position.get('y'),
                    'z': position.get('z'),
                    'radius': planet.get('radius'),
                    'itemName': None,
                    'security': None,
                    'celestialIndex': planet.get('celestialIndex'),
                    'orbitIndex': None
                })

            if planet_rows:
                connection.execute(mapDenormalize.insert(), planet_rows)
                print(f"  Inserted {len(planet_rows)} planets into mapDenormalize")

        connection.commit()
        print("  Done")
    except FileNotFoundError:
        print("  Warning: mapPlanets.yaml not found, skipping")

    print("Importing Moons")
    try:
        targetPath = os.path.join(sourcePath, 'mapMoons.yaml')
        if not os.path.exists(targetPath):
            targetPath = os.path.join(sourcePath, 'fsd', 'mapMoons.yaml')
        if not os.path.exists(targetPath):
            targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'mapMoons.yaml')

        print(f"  Opening {targetPath}")
        with open(targetPath, 'r', encoding='utf-8') as yamlstream:
            moons = load(yamlstream, Loader=SafeLoader)
            print(f"  Processing {len(moons)} moons")

            moon_rows = []
            for moonID, moon in moons.items():
                position = moon.get('position', {})
                moon_rows.append({
                    'itemID': moonID,
                    'typeID': moon.get('typeID'),
                    'groupID': grouplookup(connection, metadata, moon.get('typeID'), defaultid=gid_moon),
                    'solarSystemID': moon.get('solarSystemID'),
                    'constellationID': None,
                    'regionID': None,
                    'orbitID': moon.get('planetID'),  # Moons orbit planets
                    'x': position.get('x'),
                    'y': position.get('y'),
                    'z': position.get('z'),
                    'radius': moon.get('radius'),
                    'itemName': None,
                    'security': None,
                    'celestialIndex': None,
                    'orbitIndex': None
                })

            if moon_rows:
                connection.execute(mapDenormalize.insert(), moon_rows)
                print(f"  Inserted {len(moon_rows)} moons into mapDenormalize")

        connection.commit()
        print("  Done")
    except FileNotFoundError:
        print("  Warning: mapMoons.yaml not found, skipping")

    print("Importing Asteroid Belts")
    try:
        targetPath = os.path.join(sourcePath, 'mapAsteroidBelts.yaml')
        if not os.path.exists(targetPath):
            targetPath = os.path.join(sourcePath, 'fsd', 'mapAsteroidBelts.yaml')
        if not os.path.exists(targetPath):
            targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'mapAsteroidBelts.yaml')

        print(f"  Opening {targetPath}")
        with open(targetPath, 'r', encoding='utf-8') as yamlstream:
            belts = load(yamlstream, Loader=SafeLoader)
            print(f"  Processing {len(belts)} asteroid belts")

            belt_rows = []
            for beltID, belt in belts.items():
                position = belt.get('position', {})
                belt_rows.append({
                    'itemID': beltID,
                    'typeID': belt.get('typeID'),
                    'groupID': grouplookup(connection, metadata, belt.get('typeID'), defaultid=gid_asteroid),
                    'solarSystemID': belt.get('solarSystemID'),
                    'constellationID': None,
                    'regionID': None,
                    'orbitID': None,
                    'x': position.get('x'),
                    'y': position.get('y'),
                    'z': position.get('z'),
                    'radius': None,
                    'itemName': None,
                    'security': None,
                    'celestialIndex': None,
                    'orbitIndex': None
                })

            if belt_rows:
                connection.execute(mapDenormalize.insert(), belt_rows)
                print(f"  Inserted {len(belt_rows)} asteroid belts into mapDenormalize")

        connection.commit()
        print("  Done")
    except FileNotFoundError:
        print("  Warning: mapAsteroidBelts.yaml not found, skipping")

    print("Importing Stars")
    try:
        targetPath = os.path.join(sourcePath, 'mapStars.yaml')
        if not os.path.exists(targetPath):
            targetPath = os.path.join(sourcePath, 'fsd', 'mapStars.yaml')
        if not os.path.exists(targetPath):
            targetPath = os.path.join(sourcePath, 'sde', 'fsd', 'mapStars.yaml')

        print(f"  Opening {targetPath}")
        with open(targetPath, 'r', encoding='utf-8') as yamlstream:
            stars = load(yamlstream, Loader=SafeLoader)
            print(f"  Processing {len(stars)} stars")

            star_rows = []
            for starID, star in stars.items():
                position = star.get('position', {})
                star_rows.append({
                    'itemID': starID,
                    'typeID': star.get('typeID'),
                    'groupID': grouplookup(connection, metadata, star.get('typeID'), defaultid=gid_sun),
                    'solarSystemID': star.get('solarSystemID'),
                    'constellationID': None,
                    'regionID': None,
                    'orbitID': None,
                    'x': position.get('x'),
                    'y': position.get('y'),
                    'z': position.get('z'),
                    'radius': star.get('radius'),
                    'itemName': None,
                    'security': None,
                    'celestialIndex': None,
                    'orbitIndex': None
                })

            if star_rows:
                connection.execute(mapDenormalize.insert(), star_rows)
                print(f"  Inserted {len(star_rows)} stars into mapDenormalize")

        connection.commit()
        print("  Done")
    except FileNotFoundError:
        print("  Warning: mapStars.yaml not found, skipping")


def buildJumps(connection, metadata):
    """
    Build jump connection tables using database-agnostic SQLAlchemy Core queries.

    Creates:
    - mapSolarSystemJumps: Solar system to solar system connections
    - mapRegionJumps: Region to region connections (distinct)
    - mapConstellationJumps: Constellation to constellation connections (distinct)
    """
    print("Building jump tables...")

    # Get table references from metadata (tables already defined and created)
    mapJumps = Table('mapJumps', metadata)
    mapDenormalize = Table('mapDenormalize', metadata)
    mapSolarSystemJumps = Table('mapSolarSystemJumps', metadata)
    mapRegionJumps = Table('mapRegionJumps', metadata)
    mapConstellationJumps = Table('mapConstellationJumps', metadata)

    # Create aliases for self-joins (f = from, t = to)
    f = mapDenormalize.alias('f')
    t = mapDenormalize.alias('t')

    # Query 1: Solar System Jumps
    # Maps stargate connections to solar system connections
    print("  Building solar system jumps...")
    solar_system_query = select(
        f.c.regionID.label('fromRegionID'),
        f.c.constellationID.label('fromConstellationID'),
        f.c.solarSystemID.label('fromSolarSystemID'),
        t.c.regionID.label('toRegionID'),
        t.c.constellationID.label('toConstellationID'),
        t.c.solarSystemID.label('toSolarSystemID')
    ).select_from(
        mapJumps.join(f, mapJumps.c.stargateID == f.c.itemID)
                .join(t, mapJumps.c.destinationID == t.c.itemID)
    )

    connection.execute(
        mapSolarSystemJumps.insert().from_select(
            ['fromRegionID', 'fromConstellationID', 'fromSolarSystemID',
             'toRegionID', 'toConstellationID', 'toSolarSystemID'],
            solar_system_query
        )
    )

    # Query 2: Region Jumps (DISTINCT)
    # Maps unique region-to-region connections
    print("  Building region jumps...")
    region_query = select(
        f.c.regionID,
        t.c.regionID
    ).distinct().select_from(
        mapJumps.join(f, mapJumps.c.stargateID == f.c.itemID)
                .join(t, mapJumps.c.destinationID == t.c.itemID)
    ).where(
        f.c.regionID != t.c.regionID
    )

    connection.execute(
        mapRegionJumps.insert().from_select(
            ['fromRegionID', 'toRegionID'],
            region_query
        )
    )

    # Query 3: Constellation Jumps (DISTINCT)
    # Maps unique constellation-to-constellation connections
    print("  Building constellation jumps...")
    constellation_query = select(
        f.c.regionID,
        f.c.constellationID,
        t.c.constellationID,
        t.c.regionID
    ).distinct().select_from(
        mapJumps.join(f, mapJumps.c.stargateID == f.c.itemID)
                .join(t, mapJumps.c.destinationID == t.c.itemID)
    ).where(
        f.c.constellationID != t.c.constellationID
    )

    connection.execute(
        mapConstellationJumps.insert().from_select(
            ['fromRegionID', 'fromConstellationID', 'toConstellationID', 'toRegionID'],
            constellation_query
        )
    )

    connection.commit()
    print("  Done building jump tables")


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
