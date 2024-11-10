import csv
import json
import os
from config import (
    INORGANIC_DATA_PATH,
    ORGANIC_DATA_PATH,
    GATHERABLE_ONLY_PATH,
    ORGANIC_GROUPS_PATH,
    SCORED_SYSTEM_DATA_PATH,
    INORGANIC_GROUPS_PATH,
    RARITY_SCORES
)

def load_resources(filename, shortname=False):
    resources = {}
    with open(filename, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            resource_name = row['Resource'].strip()
            if shortname: 
                # Use resource name if short name is empty
                short_name = row['Short name'].strip() if row['Short name'].strip() else resource_name 
                resources[short_name] = {
                    'Resource': resource_name,
                    'Rarity': row['Rarity'].strip()
                }
            else: 
                resources[resource_name] = row['Rarity'].strip()
    
    return resources

def load_system_data(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as file:
            system_data = json.load(file)
    else:
        system_data = {}
    return system_data

def save_system_data(path, data):
    with open(path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    
def load_resource_groups(filename, unique_resource=[]):
    with open(filename, 'r', encoding='utf-8') as file:
        data = json.load(file)

    result = {}

    for key, values in data.items():
        if isinstance(values, list):
            # Filter and add lists directly to the result
            filtered_values = [item for item in values if item not in unique_resource]
            if filtered_values:
                result[key] = filtered_values
        elif isinstance(values, dict):
            # Flatten nested structures with 'Main' list
            main_values = values.get('Main', [])
            for sub_key, sub_values in values.items():
                if sub_key != 'Main':  # Ignore the 'Main' key itself
                    combined_values = main_values + sub_values
                    filtered_combined = [item for item in combined_values if item not in unique_resource]
                    if filtered_combined:
                        result[f"{sub_key}"] = filtered_combined
    return result

   
def get_gatherable_domesticable(planet, flora_only=False, fauna_only=False):
    """Collect gatherable and domesticable resources from a planet."""
    
    # Gatherable resources
    gatherable_resources = set()
    domesticable_resources = set()

    # Accessing fauna and flora data
    fauna_data = planet.get('fauna', {})
    flora_data = planet.get('flora', {})

    # Collecting gatherable flora
    if not fauna_only:
        for flora, name in flora_data.get('gatherable', {}).items():
            gatherable_resources.add(flora)

    # Collecting gatherable fauna
    if not flora_only:
        for fauna, name in fauna_data.get('gatherable', {}).items():
            gatherable_resources.add(fauna)

    # Collecting domesticable flora
    if not fauna_only:
        for flora, name in flora_data.get('domesticable', {}).items():
            domesticable_resources.add(flora)

    # Collecting domesticable fauna
    if not flora_only:
        for fauna, name in fauna_data.get('domesticable', {}).items():
            domesticable_resources.add(fauna)

    return domesticable_resources, gatherable_resources

def score_resources_by_rarity(resource_list, resource_rarity):
    
    score = 0
    for resource in resource_list:
        rarity = resource_rarity.get(resource, 'Common')
        score += RARITY_SCORES.get(rarity, 1)  # Default to common score if unknown
    return score

def get_grouped_inorganics(resources, resource_groups, full_chain=False):
    group_counts = {}
    flat_resources = {}

    # Flatten and map resources
    for group, group_resources in resource_groups.items():
        for item in group_resources:
            flat_resources[item] = group
        group_counts[group] = False if full_chain else 0  # Initialize based on `full_chain`

    if full_chain:
        # Set to True if a complete group is found
        for group_name, required_resources in resource_groups.items():
            if all(item in resources for item in required_resources):
                group_counts[group_name] = True
    else:
        # Count individual resource occurrences
        for resource in resources:
            if resource in flat_resources:
                group = flat_resources[resource]
                group_counts[group] += 1

    return {group: count for group, count in group_counts.items() if count}


def get_grouped_organics(resources, flora, fauna, resource_groups):
    group_counts = {'flora': 0.0, 'fauna': 0.0}

    for resource in resources:
        # Check flora grouping
        if resource in flora:
            group_counts['flora'] += 1.0 if resource in resource_groups['flora'] else 0.25

        # Check fauna grouping
        elif resource in fauna:
            group_counts['fauna'] += 1.0 if resource in resource_groups['fauna'] else 0.25

    return {group: count for group, count in group_counts.items()}

def score_inorganic(resources, rarity, inorganic_groups={}, biomes=[], full_chain=False):
    biome_group_ratio = 1
    # Don't do the biome bonus when calcualting for full chains, 
    # as full chains will always be in one biome
    if not full_chain: 
        num_biomes = len(biomes)
        inorganic_group_count = len(inorganic_groups)
        biome_group_ratio = inorganic_group_count / num_biomes if num_biomes else 1

    # Inorganic resource score calculation
    inorganic_score = score_resources_by_rarity(resources, rarity) * biome_group_ratio

    return inorganic_score

def score_organics(flora, fauna, organic_groups, rarity):
    # Organic resource score calculation, only score farmable resources
    resource_score_flora = score_resources_by_rarity(flora, rarity)
    resource_score_fauna = score_resources_by_rarity(fauna,  rarity)
    # Calculate weights based on counts of relevant resources
    total_relevant_resources = organic_groups['flora'] + organic_groups['fauna']
    flora_score_weight = organic_groups['flora'] / total_relevant_resources if total_relevant_resources else 0
    fauna_score_weight = organic_groups['fauna'] / total_relevant_resources if total_relevant_resources else 0

    # Calculate resource scores based only on relevant resources
    organic_score = (resource_score_flora * flora_score_weight) + (resource_score_fauna * fauna_score_weight)

    # Half the organic score if we don't have any water. 
    # if 'Water' not in planet['resources']['inorganic']:
    #    resource_score_organic /= 2

    return organic_score


def load_all_data(systems_data_path=SCORED_SYSTEM_DATA_PATH):
    inorganic_rarity = load_resources(INORGANIC_DATA_PATH, shortname=False)
    organic_rarity = load_resources(ORGANIC_DATA_PATH, shortname=False)
    gatherable_only = load_resource_groups(GATHERABLE_ONLY_PATH)

    rarity = {"inorganic": inorganic_rarity, "organic": organic_rarity}

    unique = {
        category: {key: value for key, value in items.items() if value == "Unique" and key}
        for category, items in rarity.items()
    }

    inorganic_groups = load_resource_groups(INORGANIC_GROUPS_PATH, unique["inorganic"])
    organic_groups = load_resource_groups(ORGANIC_GROUPS_PATH, unique["inorganic"])
    groups = {
        "inorganic": inorganic_groups,
        "organic": organic_groups,
        "gatherable_only": gatherable_only,
    }

    all_systems = load_system_data(systems_data_path)

    return all_systems, rarity, unique, groups