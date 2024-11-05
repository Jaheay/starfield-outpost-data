from copy import deepcopy
from config import (
    ALMANAC_SYSTEM_DATA_PATH,
    INARA_SYSTEM_DATA_PATH,
    INORGANIC_GROUPS_PATH,
    RAW_SYSTEMS_DATA_PATH
)
from common import load_system_data, save_system_data, load_resource_groups

# Constant to control the verbosity of fixed discrepancy messages
PRINT_FIXED = False


def get_almanac_flora_fauna_set(biomes):
    """
    Extract flora and fauna sets from almanac biomes.

    Parameters:
    - biomes (dict): Biomes data from almanac.

    Returns:
    - (set, set): Tuple containing sets of flora and fauna.
    """
    flora = set()
    fauna = set()
    for biome in biomes.values():
        flora.update(biome.get('flora', []))
        fauna.update(biome.get('fauna', []))
    return flora, fauna


def get_almanac_inorganic(biomes):
    """
    Extract inorganic resources from almanac biomes.

    Parameters:
    - biomes (dict): Biomes data from almanac.

    Returns:
    - set: Set of inorganic resources.
    """
    inorganic = set()
    for biome in biomes.values():
        inorganic.update(biome.get('resources', {}).get('inorganic', []))
    return inorganic

def get_inara_flora_fauna_set(flora, fauna):
    """
    Extract flora and fauna sets from INARA data.

    Parameters:
    - flora (dict): Flora data from INARA.
    - fauna (dict): Fauna data from INARA.

    Returns:
    - (set, set): Tuple containing sets of flora and fauna.
    """
    flora_set = set()
    fauna_set = set()

    for category in ['domesticable', 'gatherable']:
        flora_set.update(flora.get(category, {}).values())
        fauna_set.update(fauna.get(category, {}).values())

    return flora_set, fauna_set

def handle_flora_fauna_discrepancies(fixed_planet, almanac_flora, almanac_fauna, inara_flora, inara_fauna):
    """
    Handle discrepancies in flora and fauna between Almanac and INARA.

    Parameters:
    - fixed_planet (dict): The planet data from fixed_data.
    - almanac_flora (set): Flora from Almanac.
    - almanac_fauna (set): Fauna from Almanac.
    - inara_flora (set): Flora from INARA.
    - inara_fauna (set): Fauna from INARA.
    """
    # Correct fauna names directly within the fixed_planet structure
    for category in ['domesticable', 'gatherable']:
        if category in fixed_planet['fauna']:
            for key, fauna_name in fixed_planet['fauna'][category].items():
                matched_name = next(
                    (a_fauna for a_fauna in almanac_fauna if fauna_name.lower() in a_fauna.lower()),
                    fauna_name
                )
                if matched_name != fauna_name and PRINT_FIXED:
                    print(
                        f"\nFauna Fixed for {fixed_planet['name']}:\n"
                        f"Original: {fauna_name}\n"
                        f"Fixed: {matched_name}"
                    )
                fixed_planet['fauna'][category][key] = matched_name

    # Correct flora names directly within the fixed_planet structure
    for category in ['domesticable', 'gatherable']:
        if category in fixed_planet['flora']:
            for key, flora_name in fixed_planet['flora'][category].items():
                matched_name = next(
                    (a_flora for a_flora in almanac_flora if flora_name.lower() in a_flora.lower()),
                    flora_name
                )
                if matched_name != flora_name and PRINT_FIXED:
                    print(
                        f"\nFlora Fixed for {fixed_planet['name']}:\n"
                        f"Original: {flora_name}\n"
                        f"Fixed: {matched_name}"
                    )
                fixed_planet['flora'][category][key] = matched_name

    # Case 1: Missing Fauna or Flora in Almanac Only (Ignored)
    # No action needed, as per user instructions


def handle_biome_discrepancies(fixed_planet, almanac_planet):
    """
    Handle discrepancies in biomes between Almanac and INARA.

    Parameters:
    - fixed_planet (dict): The planet data from fixed_data.
    - almanac_planet (dict): The corresponding planet data from Almanac.

    Returns:
    - (set, set): Tuple containing sets of missing biomes in INARA and Almanac respectively.
    """
    inara_biomes = set(fixed_planet.get('biomes', []))
    almanac_biomes = set(almanac_planet['biomes'].keys())
    missing_in_inara_biomes = almanac_biomes - inara_biomes  # Biomes present in Almanac but missing in INARA
    missing_in_almanac_biomes = inara_biomes - almanac_biomes  # Biomes present in INARA but missing in Almanac

    # Case 2: Missing Biome in Almanac Only (Add as empty biome)
    if missing_in_almanac_biomes:
        for biome in missing_in_almanac_biomes:
            fixed_planet['biomes'].append(biome)
            fixed_planet['biome_resources'][biome] = {}
        if PRINT_FIXED:
            print(
                f"\nBiome discrepancy for {fixed_planet['name']}:\n"
                f"Missing in Almanac Biomes: {sorted(missing_in_almanac_biomes)}\n"
                f"Solution: Added missing biomes with no resources."
            )

    return missing_in_inara_biomes, missing_in_almanac_biomes


def handle_inorganic_discrepancies(fixed_planet, almanac_planet, resource_groups, missing_in_inara_biomes, missing_in_almanac_biomes):
    """
    Handle discrepancies in inorganic resources between Almanac and INARA.

    Parameters:
    - fixed_planet (dict): The planet data from fixed_data.
    - almanac_planet (dict): The corresponding planet data from Almanac.
    - resource_groups (dict): Mapping of resource groups to their respective resources.
    - missing_in_inara_biomes (set): Biomes missing in INARA.
    - missing_in_almanac_biomes (set): Biomes missing in Almanac.
    """
    almanac_inorganic = get_almanac_inorganic(almanac_planet["biomes"])
    fixed_inorganic = set(fixed_planet.get("resources", {}).get("inorganic", []))
    missing_in_inara_inorganic = almanac_inorganic - fixed_inorganic  # Inorganics present in Almanac but missing in INARA
    missing_in_almanac_inorganic = fixed_inorganic - almanac_inorganic  # Inorganics present in INARA but missing in Almanac

    # Case 3: Missing Inorganic in Almanac Only
    if missing_in_almanac_inorganic:
        for resource in missing_in_almanac_inorganic:
            # Find the resource group for this resource
            group_found = False
            for group, resources in resource_groups.items():
                if resource in resources:
                    group_found = True
                    # Assign to a biome that contains another resource from the same group
                    assigned = False
                    for biome_name, biome_data in almanac_planet['biomes'].items():
                        biome_inorganics = set(biome_data.get('resources', {}).get('inorganic', []))
                        if any(r in resources for r in biome_inorganics):
                            # Ensure 'inorganic' key is initialized
                            fixed_planet["biome_resources"].setdefault(biome_name, {}).setdefault("inorganic", []).append(resource)
                            if PRINT_FIXED:
                                print(
                                    f"\nInorganic discrepancy for {fixed_planet['name']}:\n"
                                    f"Missing in Almanac Inorganic: {resource}\n"
                                    f"Solution: Assigned {resource} to biome '{biome_name}'."
                                )
                            assigned = True
                            break
                    if not assigned:
                        if PRINT_FIXED:
                            print(
                                f"\nInorganic discrepancy for {fixed_planet['name']}:\n"
                                f"Missing in Almanac Inorganic: {resource}\n"
                                f"Solution: No suitable biome found in resource group '{group}'. Ignored."
                            )
                    break
            if not group_found:
                if PRINT_FIXED:
                    print(
                        f"\nInorganic discrepancy for {fixed_planet['name']}:\n"
                        f"Missing in Almanac Inorganic: {resource}\n"
                        f"Solution: No resource group found. Ignored."
                    )
                # Ignore as per Case 3 instructions

    # Case 4: Missing Inorganic in INARA Only
    if missing_in_inara_inorganic:
        if "inorganic" not in fixed_planet["resources"]:
            fixed_planet["resources"]["inorganic"] = []
        fixed_planet["resources"]["inorganic"].extend(sorted(missing_in_inara_inorganic))
        if PRINT_FIXED:
            print(
                f"\nInorganic discrepancy for {fixed_planet['name']}:\n"
                f"Missing in INARA Inorganic: {sorted(missing_in_inara_inorganic)}\n"
                f"Solution: Added missing inorganics to INARA's list."
            )

    # Case 6: Missing Inorganic in Both INARA and Almanac
    if missing_in_inara_inorganic and missing_in_almanac_inorganic:
        # Specific case: Helium-3 vs Water
        if missing_in_inara_inorganic == {'Helium-3'} and missing_in_almanac_inorganic == {'Water'}:
            # Replace 'Helium-3' with 'Water'
            fixed_planet["resources"]["inorganic"] = sorted(
                (almanac_inorganic | fixed_inorganic) - {'Helium-3'} | {'Water'}
            )
            if PRINT_FIXED:
                print(
                    f"\nInorganic discrepancy for {fixed_planet['name']}:\n"
                    f"Missing in INARA Inorganic: {sorted(missing_in_inara_inorganic)}\n"
                    f"Missing in Almanac Inorganic: {sorted(missing_in_almanac_inorganic)}\n"
                    f"Solution: Replaced 'Helium-3' with 'Water'."
                )
        else:
            # Flag for manual review
            manual_review(
                fixed_planet,
                fixed_planet['name'],
                sorted(missing_in_inara_inorganic),
                sorted(missing_in_almanac_inorganic)
            )

        # Case 8: Missing Biome and Inorganic in Almanac (Assign to Missing Biome)
        if missing_in_almanac_biomes and missing_in_almanac_inorganic:
            for resource in missing_in_almanac_inorganic:
                assigned = False
                for biome_name in missing_in_almanac_biomes:
                    # Ensure 'biome_name' exists and 'inorganic' list is initialized
                    fixed_planet["biome_resources"].setdefault(biome_name, {}).setdefault("inorganic", []).append(resource)
                    if PRINT_FIXED:
                        print(
                            f"\nInorganic discrepancy for {fixed_planet['name']}:\n"
                            f"Missing In Almanac Inorganic: {resource}\n"
                            f"Missing Biome: {sorted(missing_in_almanac_biomes)}\n"
                            f"Solution: Assigned {resource} to missing biome '{biome_name}'."
                        )
                    assigned = True
                    break  # Assign to the first suitable missing biome
                if not assigned:
                    if PRINT_FIXED:
                        print(
                            f"\nInorganic discrepancy for {fixed_planet['name']}:\n"
                            f"Missing In Almanac Inorganic: {resource}\n"
                            f"Missing Biome: {sorted(missing_in_almanac_biomes)}\n"
                            f"Solution: No suitable biome found to assign {resource}. Ignored."
                        )


def map_biome_resources(fixed_planet, almanac_planet):
    """
    Map biome resources from Almanac to fixed_planet.

    Parameters:
    - fixed_planet (dict): The planet data from fixed_data.
    - almanac_planet (dict): The corresponding planet data from Almanac.
    """
    for biome_name, biome_data in almanac_planet["biomes"].items():
        if biome_name not in fixed_planet["biome_resources"]:
            fixed_planet["biome_resources"][biome_name] = {}
        fixed_planet["biome_resources"][biome_name]["inorganic"] = biome_data.get("resources", {}).get("inorganic", [])


def manual_review(fixed_planet, planet_name, missing_in_inara, missing_in_almanac):
    """
    Handle discrepancies that require manual review by applying predefined fixes.
    
    Parameters:
    - fixed_planet (dict): The planet data from fixed_data.
    - planet_name (str): Name of the planet.
    - missing_in_inara (list): List of inorganics missing in INARA.
    - missing_in_almanac (list): List of inorganics missing in Almanac.
    """
    # Define manual fixes based on planet names
    manual_fixes = {
        "Ourea": {
            "add": ["Copper"],
            "remove": ["Cobalt"],
            "solution": "Almanac is wrong. Fixed_planet should contain Copper, no Cobalt."
        },
        "Cruth": {
            "add": ["Fluorine"],
            "remove": ["Iron"],
            "solution": "INARA is wrong. Fixed_planet should contain Fluorine, no Iron."
        },
        "Linnaeus IV-c": {
            "add": ["Palladium"],
            "remove": ["Lead"],
            "solution": "INARA is wrong. Fixed_planet should contain Palladium, no Lead."
        },
        "Nirvana II": {
            "add": [],
            "remove": ["Iridium"],
            "solution": "Almanac is wrong. No Iridium, but Vanadium is there."
        },
        "Tirna III": {
            "add": [],
            "remove": ["Mercury"],
            "solution": "Almanac is wrong. It's Silver here, no Mercury."
        },
        "Heinlein III-a": {
            "add": [],
            "remove": ["Europium"],
            "solution": "Almanac is wrong. It's got Europium."
        },
        "Muphrid I-a": {
            "add": ["Aluminum", "Helium-3"],
            "remove": ["Iridium", "Uranium"],
            "solution": "INARA is wrong. It's got ['Aluminum', 'Helium-3']."
        }
    }
    
    if planet_name in manual_fixes:
        fix = manual_fixes[planet_name]
        
        # Add missing inorganics from INARA
        for resource in fix.get("add", []):
            fixed_planet["resources"]["inorganic"].append(resource)
        
        # Remove inorganics missing in Almanac
        for resource in fix.get("remove", []):
            if resource in fixed_planet["resources"]["inorganic"]:
                fixed_planet["resources"]["inorganic"].remove(resource)
        
        if PRINT_FIXED:
            print(
                f"\nManual Review Applied for {planet_name}:\n"
                f"Missing in INARA Inorganic: {missing_in_inara}\n"
                f"Missing in Almanac Inorganic: {missing_in_almanac}\n"
                f"Solution: {fix['solution']}"
            )
    else:
            print(
                f"\nManual Review Needed for {planet_name}:\n"
                f"Missing in INARA Inorganic: {missing_in_inara}\n"
                f"Missing in Almanac Inorganic: {missing_in_almanac}\n"
                f"Solution: Manual intervention required."
            )



def assign_resource_to_biome(fixed_planet, resource, group_resources):
    """
    Assign a resource to a suitable biome based on resource group.

    Parameters:
    - fixed_planet (dict): The planet data from fixed_data.
    - resource (str): The resource to assign.
    - group_resources (list): List of resources in the same group.
    """
    for biome_name, biome_data in fixed_planet['biome_resources'].items():
        if any(r in group_resources for r in biome_data.get('inorganic', [])):
            fixed_planet["biome_resources"][biome_name]["inorganic"].append(resource)
            return biome_name
    return None


def stitch_planet_data(systems_almanac, systems_inara, resource_groups):
    """
    Stitch planet data from systems_inara and systems_almanac, applying corrections based on discrepancies.

    Parameters:
    - systems_almanac (list): List of systems from the Almanac.
    - systems_inara (list): List of systems from INARA.
    - resource_groups (dict): Mapping of resource groups to their respective resources.

    Returns:
    - fixed_data (list): Modified copy of systems_inara with corrections applied.
    """
    fixed_data = deepcopy(systems_inara)  # Deep copy to preserve original data

    for fixed_system in fixed_data:
        for fixed_planet in fixed_system["planets"]:
            # Initialize biome_resources if not present
            if "biome_resources" not in fixed_planet:
                fixed_planet["biome_resources"] = {}

            # Search for corresponding planet in Almanac
            for almanac_system in systems_almanac:
                for almanac_planet in almanac_system["planets"]:
                    if fixed_planet["name"].lower() == almanac_planet["name"].lower():
                        # Flora and Fauna discrepancy check and fix
                        almanac_flora, almanac_fauna = get_almanac_flora_fauna_set(almanac_planet['biomes'])
                        inara_flora, inara_fauna = get_inara_flora_fauna_set(
                            fixed_planet.get('flora', {}), fixed_planet.get('fauna', {})
                        )

                        # Correct flora and fauna names
                        handle_flora_fauna_discrepancies(
                            fixed_planet, almanac_flora, almanac_fauna, inara_flora, inara_fauna
                        )

                        # Handle biome discrepancies
                        missing_in_inara_biomes, missing_in_almanac_biomes = handle_biome_discrepancies(
                            fixed_planet, almanac_planet
                        )

                        # Handle inorganic discrepancies
                        handle_inorganic_discrepancies(
                            fixed_planet,
                            almanac_planet,
                            resource_groups,
                            missing_in_inara_biomes,
                            missing_in_almanac_biomes
                        )

                        # Apply biome resource mapping to fixed_planet directly
                        map_biome_resources(fixed_planet, almanac_planet)

                        break  # Exit after processing the matching planet
                else:
                    continue  # Continue if inner loop wasn't broken
                break  # Break outer loop if inner loop was broken

    return fixed_data  # Return the modified copy with all corrections applied

def combine_scraped_data():
    systems_almanac = load_system_data(ALMANAC_SYSTEM_DATA_PATH)
    systems_inara = load_system_data(INARA_SYSTEM_DATA_PATH)

    resource_groups = load_resource_groups(INORGANIC_GROUPS_PATH)

    combined_data = stitch_planet_data(systems_almanac, systems_inara, resource_groups)

    save_system_data(RAW_SYSTEMS_DATA_PATH, combined_data)

if __name__ == "__main__":
    combine_scraped_data()
    

