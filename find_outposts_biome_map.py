import sys
import math
from itertools import combinations
from collections import defaultdict
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

# Local Imports
from config import (
    INORGANIC_DATA_PATH,
    ORGANIC_DATA_PATH,
    GATHERABLE_ONLY_PATH,
    ORGANIC_GROUPS_PATH,
    SCORED_SYSTEM_DATA_PATH
)
from common import (
    load_resources,
    load_system_data,
    load_resource_groups
)

def find_outposts_with_biome_resource_map(): 
    """
    Main function to find and rank biome combinations covering all required inorganic and organic resources.
    """
    # Load resources
    inorganic_rarity = load_resources(INORGANIC_DATA_PATH, shortname=False)
    organic_rarity = load_resources(ORGANIC_DATA_PATH, shortname=False)

    rarity = {"inorganic": inorganic_rarity, "organic": organic_rarity}

    unique_resources = {
        category: {key: value for key, value in items.items() if value == "Unique" and key}
        for category, items in rarity.items()
    }

    # Load systems
    all_systems = load_system_data(SCORED_SYSTEM_DATA_PATH)

    # Load gatherable_only lists
    gatherable_only = load_resource_groups(GATHERABLE_ONLY_PATH)

    # Load organic groups
    organic_groups = load_resource_groups(ORGANIC_GROUPS_PATH)

    # Determine required resources
    required_inorganic = set(inorganic_rarity.keys()) - set(gatherable_only.get('inorganic', set())) - set(unique_resources['inorganic'])
    required_organic = set(organic_rarity.keys()) - set(gatherable_only.get('organic', set())) - set(unique_resources['organic'])

    # Create mappings
    planet_to_organics = {}
    biome_to_inorganics = {}

    for system in all_systems:
        for planet in system['planets']:
            planet_name = planet['name']
            planet_to_organics[planet_name] = set(planet['resources'].get('organic', []))
            for biome in planet['biomes']:
                unique_biome = f"{planet_name} - {biome}"
                biome_inorganics = planet['biome_resources'].get(biome, {}).get('inorganic', [])
                biome_to_inorganics[unique_biome] = set(biome_inorganics)

    # Greedy set cover function
    def greedy_set_cover(required, available_dict):
        uncovered = set(required)
        selected = set()
        while uncovered:
            # Find the key with the maximum intersection
            best_key = max(available_dict, key=lambda k: len(available_dict[k] & uncovered), default=None)
            if not best_key or not (available_dict[best_key] & uncovered):
                break
            selected.add(best_key)
            uncovered -= available_dict[best_key]
        return selected, uncovered

    # Select planets to cover organics
    selected_planets, missing_organics = greedy_set_cover(required_organic, planet_to_organics)

    # If organics are missing, try to cover them
    if missing_organics:
        for organ in list(missing_organics):
            for planet, organics in planet_to_organics.items():
                if organ in organics and planet not in selected_planets:
                    selected_planets.add(planet)
                    missing_organics.remove(organ)
                    break

    # Greedy set cover for inorganics using selected planets' biomes
    biome_available = {biome: inorganics for biome, inorganics in biome_to_inorganics.items()
                    if biome.split(' - ')[0] in selected_planets}

    selected_biomes, missing_inorganics = greedy_set_cover(required_inorganic, biome_available)

    # If inorganics are missing, select additional biomes from any planet
    if missing_inorganics:
        additional_biomes, missing_inorganics = greedy_set_cover(missing_inorganics, biome_to_inorganics)
        selected_biomes.update(additional_biomes)
        # Add planets of the additional biomes
        for biome in additional_biomes:
            planet = biome.split(' - ')[0]
            selected_planets.add(planet)

    # Final organics coverage check
    organics_covered = set()
    for planet in selected_planets:
        organics_covered.update(planet_to_organics.get(planet, set()))

    organics_missing_final = required_organic - organics_covered

    # Final inorganics coverage check
    inorganics_covered = set()
    for biome in selected_biomes:
        inorganics_covered.update(biome_to_inorganics.get(biome, set()))

    inorganics_missing_final = required_inorganic - inorganics_covered

    # Adjust selection if necessary
    while organics_missing_final or inorganics_missing_final:
        # If organics are missing, add planets covering them
        if organics_missing_final:
            for organ in list(organics_missing_final):
                for planet, organics in planet_to_organics.items():
                    if organ in organics and planet not in selected_planets:
                        selected_planets.add(planet)
                        organics_covered.update({organ})
                        organics_missing_final.remove(organ)
                        # Add all biomes of the new planet to cover inorganics
                        for biome in biome_to_inorganics:
                            if biome.startswith(f"{planet} - "):
                                selected_biomes.add(biome)
                                inorganics_covered.update(biome_to_inorganics[biome])
                        break
        # If inorganics are missing, add biomes covering them
        if inorganics_missing_final:
            for inorganic in list(inorganics_missing_final):
                for biome, inorganics in biome_to_inorganics.items():
                    if inorganic in inorganics and biome not in selected_biomes:
                        selected_biomes.add(biome)
                        inorganics_covered.update({inorganic})
                        inorganics_missing_final.remove(inorganic)
                        # Ensure the planet is selected
                        planet = biome.split(' - ')[0]
                        selected_planets.add(planet)
                        break

        # Recalculate missing organics and inorganics
        organics_covered = set()
        for planet in selected_planets:
            organics_covered.update(planet_to_organics.get(planet, set()))
        organics_missing_final = required_organic - organics_covered

        inorganics_covered = set()
        for biome in selected_biomes:
            inorganics_covered.update(biome_to_inorganics.get(biome, set()))
        inorganics_missing_final = required_inorganic - inorganics_covered

        if not organics_missing_final and not inorganics_missing_final:
            break

    # Print the results
    print("Selected Planets:")
    for planet in selected_planets:
        print(f"  {planet}")

    print("\nSelected Biomes:")
    for biome in selected_biomes:
        print(f"  {biome}")

    print("\nOrganics Covered:")
    for organic in organics_covered:
        print(f"  {organic}")

    if organics_missing_final:
        print("\nOrganics Missing:")
        for organic in organics_missing_final:
            print(f"  {organic}")
    else:
        print("\nAll required organics are covered.")

    print("\nInorganics Covered:")
    for inorganic in inorganics_covered:
        print(f"  {inorganic}")

    if inorganics_missing_final:
        print("\nInorganics Missing:")
        for inorganic in inorganics_missing_final:
            print(f"  {inorganic}")
    else:
        print("\nAll required inorganics are covered.")

if __name__ == '__main__':
    find_outposts_with_biome_resource_map()