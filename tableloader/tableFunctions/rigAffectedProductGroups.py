"""
rigAffectedProductGroups.py

Uses CCP/Hoboleaks industry modifier metadata to build:
  rigTypeID -> affected productGroupIDs

Data sources:
  https://sde.hoboleaks.space/tq/industrymodifiersources.json
  https://sde.hoboleaks.space/tq/industrytargetfilters.json

This avoids fragile heuristics (rig name parsing, market group trees) and works well
with "eve-stripped.db" where invTypes.marketGroupID may be missing for many items.

Outputs (created inside your eve.db / eve-stripped.db):
  - rigIndustryModifierSources
      (rigTypeID, activityKey, bonusType, dogmaAttributeID, filterID)
  - rigAffectedProductGroups
      (rigTypeID, activityKey, bonusType, productGroupID, filterID)

Notes:
- We compute affected productGroupIDs by intersecting target filters with
  *industry outputs*:
    - Manufacturing: industryActivityProducts activityID=1
    - Reaction:      industryActivityProducts activityID=11
  This keeps the mapping grounded to actual producible items in your DB.

- Some modifier entries omit filterID on material/cost/time, while another bonus entry
  for the same rig+activity includes it. In practice, the filter applies to the whole
  rig+activity. We implement:
      filters_for(rig,activity) = UNION of filterIDs across all bonus entries.
  If none exist, we treat it as "global" (all producible product groups for that activity).

"""

from __future__ import annotations

# import argparse
import json
import os
import sys
import urllib.request
from sqlalchemy import Table, select, text, func
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


HOBOSRC_DEFAULT = "https://sde.hoboleaks.space/tq/industrymodifiersources.json"
HOBOTGT_DEFAULT = "https://sde.hoboleaks.space/tq/industrytargetfilters.json"


# ----------------------------
# Activity IDs
# ----------------------------
# Try to resolve from industryActivities if present; otherwise fall back here.
FALLBACK_ACTIVITY_IDS = {
    "manufacturing": 1,
    "reaction": 11,
    "copying": 5,
    "invention": 8,
    "research_time": 3,
    "research_material": 4,
}


# ----------------------------
# Download / cache
# ----------------------------
def download_if_needed(url: str, dest_path: Path, force: bool = False) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists() and not force:
        return
    print(f"Downloading {url} -> {dest_path}")
    with urllib.request.urlopen(url) as resp:
        data = resp.read()
    dest_path.write_bytes(data)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ----------------------------
# DB helpers
# ----------------------------
def resolve_activity_id(connection, metadata, activity_key: str) -> Optional[int]:
    """
    Prefer industryActivities table if present, else fallback mapping.
    """
    ak = activity_key.lower()

    # Get table reference
    industryActivities = Table('industryActivities', metadata)

    # Query using SQLAlchemy
    try:
        result = connection.execute(
            select(industryActivities.c.activityID)
            .where(industryActivities.c.activityName.ilike(ak))
            .limit(1)
        ).fetchall()

        if result:
            return int(result[0][0])  # activityID
    except:
        pass  # Table might not exist

    return FALLBACK_ACTIVITY_IDS.get(ak)


# ----------------------------
# Core logic
# ----------------------------
@dataclass(frozen=True)
class FilterDef:
    name: str
    category_ids: Set[int]
    group_ids: Set[int]


def parse_filters(target_filters_json: dict) -> Dict[int, FilterDef]:
    out: Dict[int, FilterDef] = {}
    for k, v in target_filters_json.items():
        fid = int(k)
        out[fid] = FilterDef(
            name=str(v.get("name", "")),
            category_ids=set(int(x) for x in v.get("categoryIDs", []) or []),
            group_ids=set(int(x) for x in v.get("groupIDs", []) or []),
        )
    return out


def rig_typeids_in_db(connection, metadata) -> Set[int]:
    invTypes = Table('invTypes', metadata)
    rows = connection.execute(select(invTypes.c.typeID)).fetchall()
    return {int(r[0]) for r in rows}


def is_standup_rig_item(connection, metadata, type_id: int) -> bool:
    """
    Keep this intentionally loose: Hoboleaks source list is authoritative.
    But we exclude obvious blueprint pseudo-items by name.
    """
    invTypes = Table('invTypes', metadata)

    result = connection.execute(
        select(
            invTypes.c.typeName,
            invTypes.c.published
        )
        .where(invTypes.c.typeID == type_id)
        .limit(1)
    ).fetchall()

    if not result:
        return False

    name = str(result[0][0])  # typeName
    if int(result[0][1]) != 1:  # published
        return False
    if not name.startswith("Standup "):
        return False
    if name.endswith(" Blueprint") or " Blueprint" in name:
        return False
    return True


def build_producible_group_sets(connection, metadata, activity_id: int) -> Tuple[Set[int], Dict[int, Set[int]]]:
    """
    Returns:
      - all_product_group_ids produced by this activity (restricted to published outputs)
      - categoryID -> set(groupID) for produced outputs
    """
    industryActivityProducts = Table('industryActivityProducts', metadata)
    invTypes = Table('invTypes', metadata)
    invGroups = Table('invGroups', metadata)

    # Build query with joins
    query = select(
        invTypes.c.groupID,
        invGroups.c.categoryID
    ).select_from(
        industryActivityProducts
        .join(invTypes, invTypes.c.typeID == industryActivityProducts.c.productTypeID)
        .join(invGroups, invGroups.c.groupID == invTypes.c.groupID)
    ).where(
        industryActivityProducts.c.activityID == activity_id,
        invTypes.c.published == True,  # Use True instead of 1 for PostgreSQL boolean compatibility
        invTypes.c.groupID.isnot(None)
    ).distinct()

    rows = connection.execute(query).fetchall()

    all_groups: Set[int] = set()
    cat_to_groups: Dict[int, Set[int]] = defaultdict(set)
    for r in rows:
        gid = int(r[0])  # groupID
        cid = int(r[1])  # categoryID
        all_groups.add(gid)
        cat_to_groups[cid].add(gid)
    return all_groups, cat_to_groups


def compute_affected_groups_for_filter(
    filter_def: FilterDef,
    producible_groups_all: Set[int],
    producible_cat_to_groups: Dict[int, Set[int]],
) -> Set[int]:
    """
    Apply filter categoryIDs + groupIDs, but restrict to groups that actually occur
    among producible outputs for this activity.
    """
    out: Set[int] = set()

    # Direct groupIDs
    out |= (filter_def.group_ids & producible_groups_all)

    # Categories expand to groups in those categories
    for cid in filter_def.category_ids:
        out |= producible_cat_to_groups.get(cid, set())

    return out


def extract_modifier_rows(mod_sources_json: dict) -> List[Tuple[int, str, str, int, Optional[int]]]:
    """
    Returns rows for rigIndustryModifierSources:
      (rigTypeID, activityKey, bonusType, dogmaAttributeID, filterID)
    """
    rows: List[Tuple[int, str, str, int, Optional[int]]] = []
    for rig_type_id_str, by_activity in mod_sources_json.items():
        rig_type_id = int(rig_type_id_str)
        for activity_key, by_bonus in by_activity.items():
            for bonus_type, entries in by_bonus.items():
                for entry in entries or []:
                    dogma_attr = int(entry["dogmaAttributeID"])
                    filter_id = entry.get("filterID")
                    filter_id = int(filter_id) if filter_id is not None else None
                    rows.append((rig_type_id, activity_key, bonus_type, dogma_attr, filter_id))
    return rows


def filters_for_rig_activity(mod_rows: Iterable[Tuple[int, str, str, int, Optional[int]]]) -> Dict[Tuple[int, str], Set[Optional[int]]]:
    """
    For each (rigTypeID, activityKey), collect UNION of filterIDs across all bonus entries.
    If none present, store {None} to mean 'global'.
    """
    tmp: Dict[Tuple[int, str], Set[Optional[int]]] = defaultdict(set)
    for rig_type_id, activity_key, _bonus_type, _dogma_attr, filter_id in mod_rows:
        if filter_id is not None:
            tmp[(rig_type_id, activity_key)].add(filter_id)

    # ensure global if empty
    out: Dict[Tuple[int, str], Set[Optional[int]]] = {}
    keys = {(r, a) for (r, a, *_rest) in mod_rows}
    for key in keys:
        s = tmp.get(key, set())
        out[key] = s if s else {None}
    return out

def importRigMappings(connection,metadata):
    print("Importing Rig Mappings")
    show_debug = True
    cache_dir = Path('.cache_hoboleaks')
    mods_path = cache_dir / "industrymodifiersources.json"
    filters_path = cache_dir / "industrytargetfilters.json"

    # Download/cache JSON
    download_if_needed(HOBOSRC_DEFAULT, mods_path, force=True)
    download_if_needed(HOBOTGT_DEFAULT, filters_path, force=True)

    mod_sources_json = load_json(mods_path)
    target_filters_json = load_json(filters_path)

    filters = parse_filters(target_filters_json)
    mod_rows = extract_modifier_rows(mod_sources_json)

    conn = connection

    # Get table references
    rigIndustryModifierSources = Table('rigIndustryModifierSources', metadata)
    rigAffectedProductGroups = Table('rigAffectedProductGroups', metadata)

    # Begin transaction for first batch of inserts (defensive check)
    trans = conn.begin() if not conn.in_transaction() else None

    # Insert modifier source rows (authoritative)
    if not show_debug:
        print(f"Inserting {len(mod_rows)} rigIndustryModifierSources rows...")

    for row in mod_rows:
        conn.execute(rigIndustryModifierSources.insert().values(
            rigTypeID=row[0],
            activityKey=row[1],
            bonusType=row[2],
            dogmaAttributeID=row[3],
            filterID=row[4]
        ))

    # Commit first batch of inserts
    if trans is not None:
        trans.commit()
    else:
        conn.commit()

    # Precompute which rig typeIDs exist + are real standup rig items
    db_type_ids = rig_typeids_in_db(conn, metadata)
    valid_rigs: Set[int] = set()
    for rig_type_id_str in mod_sources_json.keys():
        tid = int(rig_type_id_str)
        if tid not in db_type_ids:
            continue
        if is_standup_rig_item(conn, metadata, tid):
            valid_rigs.add(tid)

    if not show_debug:
        print(f"Modifier sources in JSON: {len(mod_sources_json)}; present+valid standup items in DB: {len(valid_rigs)}")

    # Build filter union per rig+activity
    rig_activity_filters = filters_for_rig_activity(mod_rows)

    total_insert = 0

    for activity_key in ["manufacturing", "reaction"]:
        activity_id = resolve_activity_id(conn, metadata, activity_key)
        if activity_id is None:
            print(f"[WARN] Unknown activityKey={activity_key!r} (no industryActivities table match and no fallback mapping). Skipping.")
            continue

        # Only mapping from industryActivityProducts is reliable for manufacturing/reaction.
        producible_all, producible_cat_to_groups = build_producible_group_sets(conn, metadata, activity_id)

        if not show_debug:
            print(f"[{activity_key}] activityID={activity_id} producible productGroupIDs={len(producible_all)}")

        # For each rig affecting this activity, compute targets and insert
        # We keep bonusType dimension; targets are computed from unioned filters per rig+activity.
        # If filters are {None}, treat as global (all producible groups).
        affected_cache: Dict[Tuple[int, Optional[int]], Set[int]] = {}

        # Get all relevant rig+bonus rows for this activity from DB (keeps in sync with what we inserted)
        query = select(
            rigIndustryModifierSources.c.rigTypeID,
            rigIndustryModifierSources.c.bonusType
        ).where(
            rigIndustryModifierSources.c.activityKey.ilike(activity_key)
        ).distinct()

        rows = conn.execute(query).fetchall()

        # Begin transaction for this activity's inserts (defensive check)
        trans = conn.begin() if not conn.in_transaction() else None

        for r in rows:
            rig_type_id = int(r[0])  # rigTypeID
            bonus_type = str(r[1]).lower()  # bonusType

            if rig_type_id not in valid_rigs:
                continue

            fset = rig_activity_filters.get((rig_type_id, activity_key), {None})

            for fid in fset:
                if fid is None:
                    groups = producible_all
                else:
                    fdef = filters.get(fid)
                    if fdef is None:
                        # Unknown filterID: skip (better than mis-mapping)
                        continue
                    key = (activity_id, fid)
                    cache_key = (activity_id, fid)
                    # cache per (activity_id, filterID)
                    if cache_key not in affected_cache:
                        affected_cache[cache_key] = compute_affected_groups_for_filter(
                            fdef,
                            producible_all,
                            producible_cat_to_groups,
                        )
                    groups = affected_cache[cache_key]

                # Insert rigAffectedProductGroups
                for gid in groups:
                    conn.execute(rigAffectedProductGroups.insert().values(
                        rigTypeID=rig_type_id,
                        activityKey=activity_key,
                        bonusType=bonus_type,
                        productGroupID=int(gid),
                        filterID=fid
                    ))
                total_insert += len(groups)

        # Commit this activity's inserts
        if trans is not None:
            trans.commit()
        else:
            conn.commit()

    if not show_debug:
        count_result = conn.execute(
            select(func.count()).select_from(rigAffectedProductGroups)
        ).fetchall()
        c2 = count_result[0][0]
        print(f"rigAffectedProductGroups rows: {c2} (attempted inserts pre-dedupe: {total_insert})")

    if not show_debug:
        print("Imported Rig Mappings.")