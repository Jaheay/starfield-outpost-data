from tqdm import tqdm
from collections import defaultdict
from rich.live import Live
from rich.table import Table
from rich import box
import itertools

# Local Imports
from config import *
from common import (
    load_resource_groups,
    save_system_data,
    load_system_data,
    load_resources,
)
from find_outposts import (
    apply_highlander_rules,
    calculate_uncaptured_resources,
    capture_remaining_organics,
    eliminate_redundant_planets,
    recalculate_captured_resources,
    capture_helium_and_water,
    capture_unique_resource_systems,
    find_fullchain_planets,
    find_unique_resources,
    print_final_results,
    score_by_desired,

)


def collect_full_chain_planets(system_data, groups, processed_systems, final_planets):
    """
    Collects all planets that have a full chain for each resource group.
    Returns a dictionary mapping group names to lists of planets.
    """
    fullchain_by_group = {}
    remaining_inorganic_groups = set(groups["inorganic"].keys())

    for group_name in remaining_inorganic_groups:
        candidate_planets = []
        for system in system_data:
            if system["name"] in processed_systems:
                continue
            for planet in system["planets"]:
                if planet in final_planets:
                    continue
                if group_name in planet.get("outpost_candidacy", {}).get(
                    "full_resource_chain", []
                ):
                    planet["system_name"] = system[
                        "name"
                    ]  # Store system name for later use
                    candidate_planets.append(planet)
        if candidate_planets:
            fullchain_by_group[group_name] = candidate_planets
        else:
            print(f"No candidate planets found for group {group_name}.")
            # Depending on requirements, you might handle this differently

    return fullchain_by_group


def generate_full_chain_combinations(fullchain_by_group):
    """
    Generates all possible combinations where each group is represented by one planet.
    Returns a list of combinations, where each combination is a list of planets.
    """
    group_names = list(fullchain_by_group.keys())
    candidate_lists = [fullchain_by_group[group_name] for group_name in group_names]
    all_combinations = list(itertools.product(*candidate_lists))
    return all_combinations


def process_combination(
    combination,
    initial_final_planets,
    initial_processed_systems,
    initial_captured_resources,
    system_data,
    resources_by_rarity,
    groups,
):
    """
    Processes a single combination of planets.
    Returns the final planets, the total number of planets, and uncaptured resources.
    """
    import copy

    # Deep copy the initial data structures to avoid modifying the originals
    final_planets = copy.deepcopy(initial_final_planets)
    processed_systems = copy.deepcopy(initial_processed_systems)
    captured_resources = copy.deepcopy(initial_captured_resources)

    # Add planets from the combination to final_planets
    for planet in combination:
        if planet not in final_planets:
            final_planets.append(planet)
            captured_resources["inorganic"].update(
                planet["resources"].get("inorganic", [])
            )
            captured_resources["organic"].update(planet["resources"].get("organic", []))
            # Mark the system as processed
            planet_system_name = planet.get("system_name")
            processed_systems.add(planet_system_name)

    # Proceed with the rest of the steps
    # Step 3: Apply Highlander Rules
    final_planets = apply_highlander_rules(
        final_planets, captured_resources, resources_by_rarity, groups
    )

    # Calculate uncaptured resources for next step
    uncaptured_resources = calculate_uncaptured_resources(
        captured_resources, resources_by_rarity, groups["gatherable_only"]
    )

    iter_count = 1
    while len(uncaptured_resources["organic"]) > 0:
        # Step 4: Capture remaining organics
        final_planets, captured_resources = capture_remaining_organics(
            system_data,
            final_planets,
            captured_resources,
            groups,
            uncaptured_resources["organic"],
        )

        # Step 5: Elimination
        final_planets = eliminate_redundant_planets(final_planets, groups)

        captured_resources = recalculate_captured_resources(
            final_planets, captured_resources
        )
        uncaptured_resources = calculate_uncaptured_resources(
            captured_resources, resources_by_rarity, groups["gatherable_only"]
        )
        iter_count += 1

    # Step 6: Capture Helium-3 and Water
    captured_resources = capture_helium_and_water(final_planets, captured_resources)

    # Recalculate captured resources
    captured_resources = recalculate_captured_resources(
        final_planets, captured_resources
    )
    uncaptured_resources = calculate_uncaptured_resources(
        captured_resources, resources_by_rarity, groups["gatherable_only"]
    )

    # Return the final planets, their count, and uncaptured_resources
    return final_planets, len(final_planets), uncaptured_resources


def find_best_combinations(
    all_combinations,
    initial_final_planets,
    initial_processed_systems,
    initial_captured_resources,
    system_data,
    resources_by_rarity,
    groups,
):
    """
    Processes all combinations and finds the ones with the minimal total number of planets.
    Returns a list of best combinations, the minimal planet count, and a count of each planet count occurrence.
    """
    combination_results = []
    min_planet_count = float("inf")
    planet_count_occurrences = defaultdict(int)

    total_combinations = len(all_combinations)

    # Function to generate a table with planet count distribution
    def generate_distribution_table():
        table = Table(title="Planet Count Distribution", box=box.MINIMAL_HEAVY_HEAD)
        table.add_column("Planet Count", justify="right")
        table.add_column("Occurrences", justify="right")
        for count, occurrences in sorted(planet_count_occurrences.items()):
            table.add_row(str(count), str(occurrences))
        return table

    # Initialize progress bar and live table update
    with tqdm(total=total_combinations, desc="Processing combinations") as pbar:
        with Live(generate_distribution_table(), refresh_per_second=2) as live:
            for idx, combination in enumerate(all_combinations):
                # Process the combination
                final_planets, planet_count, uncaptured_resources = process_combination(
                    combination,
                    initial_final_planets,
                    initial_processed_systems,
                    initial_captured_resources,
                    system_data,
                    resources_by_rarity,
                    groups,
                )

                combination_results.append(
                    {
                        "combination": combination,
                        "final_planets": final_planets,
                        "planet_count": planet_count,
                        "uncaptured_resources": uncaptured_resources,
                    }
                )

                # Update the count for this planet count
                planet_count_occurrences[planet_count] += 1

                # Update the minimal planet count if necessary
                if planet_count < min_planet_count:
                    min_planet_count = planet_count

                # Update the progress bar description
                pbar.set_postfix({"Min planets": min_planet_count})

                # Refresh the live table display
                live.update(generate_distribution_table())

                # Update the progress bar
                pbar.update(1)
            print()

    # Find all combinations with the minimal planet count
    best_combinations = [
        result
        for result in combination_results
        if result["planet_count"] == min_planet_count
    ]

    return best_combinations, min_planet_count, dict(planet_count_occurrences)


def find_best_systems(system_data, unique_resources, resources_by_rarity, groups):
    """
    Identifies the best systems for outpost setup based on unique resources and full resource chains.
    Returns the final list of planets for outpost placement.
    """
    # Step 1: Capture unique resource systems
    initial_final_planets, initial_processed_systems, initial_captured_resources = (
        capture_unique_resource_systems(system_data, unique_resources, groups)
    )

    # Collect planets for each resource group
    fullchain_by_group = collect_full_chain_planets(
        system_data,
        groups,
        initial_processed_systems,
        initial_final_planets,
    )

    # Generate all possible combinations
    all_combinations = generate_full_chain_combinations(fullchain_by_group)
    print(f"Total combinations to process: {len(all_combinations)}")

    # For each combination, process and find the best ones
    best_combinations, min_planet_count = find_best_combinations(
        all_combinations,
        initial_final_planets,
        initial_processed_systems,
        initial_captured_resources,
        system_data,
        resources_by_rarity,
        groups,
    )

    print(f"\nMinimal total planets: {min_planet_count}")
    print(f"Number of combinations with minimal planets: {len(best_combinations)}")

    if min_planet_count < 23:
        # For each best combination, print the planet names and detailed results
        for idx, result in enumerate(best_combinations, 1):
            print(f"\nBest Combination {idx}:")
            final_planets = result["final_planets"]
            planet_names = [planet["name"] for planet in final_planets]
            print(f"Planets ({len(planet_names)}): {', '.join(planet_names)}")

            # Get uncaptured_resources from result
            uncaptured_resources = result["uncaptured_resources"]

            # Print detailed results for each combination
            print_final_results(final_planets, uncaptured_resources)

    if min_planet_count < 24:
        for idx, result in enumerate(best_combinations, 1):
            filename = "best_combinations/" + str(idx) + ".json"
            save_system_data(filename, final_planets)

    return best_combinations

if __name__ == "__main__":
    inorganic_rarity = load_resources(INORGANIC_DATA_PATH, shortname=False)
    organic_rarity = load_resources(ORGANIC_DATA_PATH, shortname=False)
    gatherable_only = load_resource_groups(GATHERABLE_ONLY_PATH)

    rarity = {"inorganic": inorganic_rarity, "organic": organic_rarity}

    unique = {
        category: {
            key: value for key, value in items.items() if value == "Unique" and key
        }
        for category, items in rarity.items()
    }

    inorganic_groups = load_resource_groups(INORGANIC_GROUPS_PATH, unique["inorganic"])
    organic_groups = load_resource_groups(ORGANIC_GROUPS_PATH, unique["inorganic"])
    groups = {
        "inorganic": inorganic_groups,
        "organic": organic_groups,
        "gatherable_only": gatherable_only,
    }

    all_systems = load_system_data(SCORED_SYSTEM_DATA_PATH)

    fullchain_inorganic_planets = find_fullchain_planets(
        all_systems, groups["inorganic"]
    )
    unique_resource_planets = find_unique_resources(all_systems, unique)
    selected_systems = find_best_systems(all_systems, unique, rarity, groups)
