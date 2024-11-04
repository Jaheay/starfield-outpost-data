import itertools

# Local Imports
from config import *
from common import (
    get_grouped_inorganics,
    get_grouped_organics,
    score_inorganic,
    score_organics,
    load_resource_groups,
    load_resources,
    load_system_data,
    save_system_data,
)


def find_fullchain_planets(system_data, inorganic_groups):

    for system in system_data:
        for planet in system["planets"]:
            grouped_resources = get_grouped_inorganics(
                planet["resources"]["inorganic"], inorganic_groups, full_chain=True
            )

            # Determine if full resource chain exists
            full_chain = any(is_complete for is_complete in grouped_resources.values())
            if full_chain:
                planet.setdefault("outpost_candidacy", {})
                planet["outpost_candidacy"]["full_resource_chain"] = list(grouped_resources.keys())


def find_unique_resources(system_data, unique_resources):
    for system in system_data:
        for planet in system["planets"]:
            unique_resources_found = []

            # Check each resource type in unique_resources
            for resource_type, unique_list in unique_resources.items():
                if resource_type == "organic":
                    # Collect all 'organic' resources in a single pass
                    resources = (
                        list(planet["resources"].get(resource_type, []))
                        + list(planet["flora"]["gatherable"].keys())
                        + list(planet["fauna"]["gatherable"].keys())
                    )
                    unique_resources_found.extend(resource for resource in resources if resource in unique_list)
                else:
                    # Process non-organic resources as usual
                    unique_resources_found.extend(
                        resource for resource in planet["resources"].get(resource_type, []) if resource in unique_list
                    )

            # Check if 'Caelumite' is found separately
            if "Caelumite" in unique_resources_found:
                planet.setdefault("outpost_candidacy", {})
                planet["outpost_candidacy"]["caelumite"] = True
                unique_resources_found.remove("Caelumite")  # Remove Caelumite from unique_resources_found

            # If any unique resources are found, update outpost_candidacy
            if unique_resources_found:
                planet.setdefault("outpost_candidacy", {})
                planet["outpost_candidacy"]["unique"] = unique_resources_found


def score_by_desired(
    candidate_planets,
    resources_by_rarity,
    groups,
    desired_inorganics=[],
    desired_organics=[],
):
    """
    A scoring function that only scores based on desired resources.
    It loses some of the complexity of the proper scores, but not meaningfully so for its purpose.
    """
    planet_scores = {}

    for planet in candidate_planets:
        resource_score_organic = 0
        resource_score_inorganic = 0

        # Gather only desired organics for scoring
        if len(desired_organics) > 0:
            organic_group_counts = get_grouped_organics(
                resources=planet["resources"]["organic"],
                flora=planet["flora"]["domesticable"],
                fauna=planet["fauna"]["domesticable"],
                resource_groups=groups["organic"],
            )
            planet_flora = [resource for resource in planet["flora"]["domesticable"] if resource in desired_organics]
            planet_fauna = [resource for resource in planet["flora"]["domesticable"] if resource in desired_organics]
            resource_score_organic = score_organics(
                planet_flora,
                planet_fauna,
                organic_group_counts,
                resources_by_rarity["organic"],
            )
        if len(desired_inorganics) > 0:
            planet_inorganics = [
                resource for resource in planet["resources"]["inorganic"] if resource in desired_inorganics
            ]
            resource_score_inorganic = score_inorganic(planet_inorganics, rarity["inorganic"], full_chain=True)

        planet_scores[planet["name"]] = resource_score_inorganic + resource_score_organic

    return planet_scores


def score_systems_by_full_chains(system_data, uncaptured_inorganic_groups, processed_systems):
    """
    Scores systems based on the number of uncaptured full resource chains they contain.
    Returns a dictionary of system names and their scores.
    """
    system_scores = {}
    for system in system_data:
        if system["name"] in processed_systems:
            continue

        unique_uncaptured_groups = set()
        for planet in system["planets"]:
            candidacy = planet.get("outpost_candidacy", {})
            if candidacy.get("full_resource_chain"):
                unique_uncaptured_groups.update(
                    group for group in candidacy["full_resource_chain"] if group in uncaptured_inorganic_groups
                )

        if unique_uncaptured_groups:
            system_scores[system["name"]] = len(unique_uncaptured_groups)

    return system_scores


def collect_candidate_planets(system_data, candidate_systems, uncaptured_inorganic_groups):
    """
    Collects candidate planets with full resource chains from the top-scoring systems.
    Returns a list of candidate planets.
    """
    candidate_planets = []
    for system in system_data:
        if system["name"] in candidate_systems:
            for planet in system["planets"]:
                candidacy = planet.get("outpost_candidacy", {}).get("full_resource_chain")
                if candidacy and any(item in uncaptured_inorganic_groups for item in candidacy):
                    candidate_planets.append(planet)
    return candidate_planets


def recalculate_captured_resources(final_planets, old_captured_resources):
    """
    Recalculates captured inorganic and organic resources based on the final list of planets.
    Returns inorganics and organics sets.
    """
    captured_inorganics = set()
    captured_organics = set()

    for planet in final_planets:
        # Capture inorganic resources
        captured_inorganics.update(planet["resources"].get("inorganic", []))
        # Capture organic resources
        captured_organics.update(planet["resources"].get("organic", []))

    captured_resources = {
        "inorganic": captured_inorganics,
        "organic": captured_organics,
    }
    return captured_resources


def calculate_uncaptured_resources(captured_resources, resources_by_rarity, gatherable_only):
    """
    Calculates uncaptured inorganic and organic resources.
    Returns uncaptured_inorganics and uncaptured_organics.
    """
    all_inorganic_resources = set(resources_by_rarity["inorganic"].keys())
    all_organic_resources = set(resources_by_rarity["organic"].keys())

    uncaptured_inorganics = (
        all_inorganic_resources - captured_resources["inorganic"] - set(gatherable_only["inorganic"])
    )
    uncaptured_organics = all_organic_resources - captured_resources["organic"] - set(gatherable_only["organic"])

    uncaptured_resources = {
        "inorganic": uncaptured_inorganics,
        "organic": uncaptured_organics,
    }

    return uncaptured_resources


def capture_unique_resource_systems(system_data, unique_resources, groups):
    """
    Captures systems with unique resources and any full chains within those systems.
    Returns the list of planets, processed systems, and the captured resources.
    """
    captured_inorganics = set()
    captured_organics = set()
    processed_systems = set()
    final_planets = []

    for system in system_data:
        unique_system = False
        for planet in system["planets"]:
            candidacy = planet.get("outpost_candidacy", {})

            # Check if this planet has unique resources
            if candidacy.get("unique", False):
                unique_resource = candidacy.get("unique")
                unique_resource = [
                    res
                    for res in unique_resource
                    if res not in groups["gatherable_only"]["organic"]
                    and res not in groups["gatherable_only"]["inorganic"]
                ]
                if not unique_resource:
                    continue  # Skip if only gatherable-only resources
                unique_system = True
                final_planets.append(planet)  # Add planet for outpost setup

                # Capture unique inorganic resources
                for resource in planet["resources"].get("inorganic", []):
                    if resource in unique_resources["inorganic"]:
                        captured_inorganics.add(resource)

                # Collect potential inorganics and their groups
                planet_inorganics = set(planet["resources"].get("inorganic", []))
                potential_groups = {}
                for group_name, group_resources in groups["inorganic"].items():
                    capturable_inorganics = planet_inorganics & set(group_resources)
                    if capturable_inorganics:
                        potential_groups[group_name] = list(capturable_inorganics)  # Store as list of resources

                # Store potential groups in outpost_candidacy
                planet.setdefault("outpost_candidacy", {})
                planet["outpost_candidacy"]["potential_groups"] = potential_groups

                # Capture organic resources available on the unique planet
                captured_organics.update(planet["resources"].get("organic", []))

        # If the system contains unique resources, process full chains
        if unique_system:
            processed_systems.add(system['name'])
            for planet in system['planets']:
                candidacy = planet.get('outpost_candidacy', {})
                if candidacy.get('full_resource_chain') and planet not in final_planets:
                    final_planets.append(planet)
                    for group in candidacy['full_resource_chain']:
                        captured_inorganics.update(groups['inorganic'][group])
                        captured_organics.update(planet['resources'].get('organic', []))

                        
    captured_resources = {
        "inorganic": captured_inorganics,
        "organic": captured_organics,
    }

    return final_planets, processed_systems, captured_resources


def capture_full_chain_systems(
    system_data,
    processed_systems,
    final_planets,
    captured_resources,
    resources_by_rarity,
    groups,
):
    """
    Iteratively selects additional systems to minimize the number of outposts needed to capture all resources.
    Returns the updated list of final planets and captured resources.
    """
    inorganic_groups = groups["inorganic"]
    all_inorganic_resources = set(resources_by_rarity["inorganic"].keys())
    all_organic_resources = set(resources_by_rarity["organic"].keys())

    captured_inorganics = captured_resources["inorganic"]
    captured_organics = captured_resources["organic"]
    captured_inorganic_groups = set()

    while True:
        # Determine remaining uncaptured resources
        uncaptured_inorganic_groups = [group for group in inorganic_groups if group not in captured_inorganic_groups]
        uncaptured_inorganics = [
            res
            for res in all_inorganic_resources
            if res not in captured_inorganics and res not in groups["gatherable_only"]["inorganic"]
        ]
        uncaptured_organics = [
            res
            for res in all_organic_resources
            if res not in captured_organics and res not in groups["gatherable_only"]["organic"]
        ]

        if not uncaptured_inorganic_groups:
            break  # Exit if all resource groups are captured

        # Score systems based on the count of uncaptured full chains
        system_scores = score_systems_by_full_chains(system_data, uncaptured_inorganic_groups, processed_systems)

        if not system_scores:
            captured_resources = recalculate_captured_resources(final_planets, captured_resources)
            captured_inorganics = captured_resources["inorganic"]
            captured_organics = captured_resources["organic"]
            continue

        # Identify the maximum count of uncaptured groups and select those systems
        max_score = max(system_scores.values(), default=0)
        candidate_systems = [system for system, score in system_scores.items() if score == max_score]

        # Collect candidate planets with full chains in the top-scoring systems
        candidate_planets = collect_candidate_planets(system_data, candidate_systems, uncaptured_inorganic_groups)

        # Use `score_by_desired` to rank candidates based on desired organics and desired inorganics
        scored_planets = score_by_desired(
            candidate_planets,
            resources_by_rarity,
            groups,
            desired_inorganics=[],
            desired_organics=uncaptured_organics,
        )

        # Select the best planet(s)
        best_planet_name = max(scored_planets, key=lambda planet: scored_planets.get(planet, -float("inf")))

        # Find the system name for the best planet
        best_system_name = next(
            system["name"]
            for system in system_data
            if any(planet["name"] == best_planet_name for planet in system["planets"])
        )
        processed_systems.add(best_system_name)

        # Capture resources from the selected system
        for system in system_data:
            if system["name"] == best_system_name:
                for planet in system["planets"]:
                    if planet.get("outpost_candidacy", {}).get("full_resource_chain"):
                        if planet not in final_planets:
                            final_planets.append(planet)
                        for group in planet["outpost_candidacy"]["full_resource_chain"]:
                            captured_inorganic_groups.add(group)
                            captured_inorganics.update(groups["inorganic"][group])
                            captured_organics.update(planet["resources"]["organic"])
                break

    # Update captured resources
    captured_resources.update(
        {
            "inorganic": captured_inorganics,
            "organic": captured_organics,
        }
    )

    return final_planets, processed_systems, captured_resources


def apply_highlander_rules(final_planets, captured_resources, resources_by_rarity, groups):
    """
    Applies the Highlander rules to eliminate duplicate resource chains,
    favoring unique resource planets.
    Returns the updated list of planets.
    """
    unique_resource_planets = []
    locked_full_chains = set()
    unique_resource_counts = {}

    # Count the number of planets each unique resource appears on
    for planet in final_planets:
        if planet.get("outpost_candidacy", {}).get("unique"):
            for unique_res in planet["outpost_candidacy"]["unique"]:
                unique_resource_counts.setdefault(unique_res, []).append(planet)

    # Process unique resource planets
    for unique_res, planets in unique_resource_counts.items():
        if len(planets) == 1:
            # Only one planet has this unique resource
            planet = planets[0]
            unique_resource_planets.append(planet)
            full_resource_chain = tuple(planet.get("outpost_candidacy", {}).get("full_resource_chain", []))
            if full_resource_chain:
                locked_full_chains.add(full_resource_chain)
        else:
            # Multiple planets have this unique resource
            # Prefer the one with a full chain
            planets_with_full_chain = [p for p in planets if "full_resource_chain" in p.get("outpost_candidacy", {})]
            if planets_with_full_chain:
                # Pick the best one among them
                scored_planets = score_by_desired(
                    planets_with_full_chain,
                    resources_by_rarity,
                    groups,
                    desired_inorganics=[],
                    desired_organics=[],
                )
            else:
                # Score all planets
                scored_planets = score_by_desired(
                    planets,
                    resources_by_rarity,
                    groups,
                    desired_inorganics=[],
                    desired_organics=[],
                )
            best_planet_name = max(
                scored_planets,
                key=lambda planet: scored_planets.get(planet, -float("inf")),
            )
            best_planet = next(p for p in planets if p["name"] == best_planet_name)
            unique_resource_planets.append(best_planet)
            full_resource_chain = tuple(best_planet.get("outpost_candidacy", {}).get("full_resource_chain", []))
            if full_resource_chain:
                locked_full_chains.add(full_resource_chain)

    # Process non-unique planets
    unique_full_chain_planets = {}
    for planet in final_planets:
        if planet in unique_resource_planets:
            continue
        full_resource_chain = tuple(planet.get("outpost_candidacy", {}).get("full_resource_chain", []))
        if not full_resource_chain or full_resource_chain in locked_full_chains:
            continue
        unique_full_chain_planets.setdefault(full_resource_chain, []).append(planet)

    # Determine the best planet for each full resource chain
    best_planets = []
    for chain, candidates in unique_full_chain_planets.items():
        # Score candidate planets for this chain
        all_organics = [res for res in resources_by_rarity["organic"]]
        scored_planets = score_by_desired(
            candidates,
            resources_by_rarity,
            groups,
            desired_inorganics=[],
            desired_organics=all_organics,
        )
        # Find the planet with the highest score
        best_planet_name = max(scored_planets, key=lambda planet: scored_planets.get(planet, -float("inf")))
        best_planet = next(planet for planet in candidates if planet["name"] == best_planet_name)
        best_planets.append(best_planet)

    # Retain the final list of planets
    final_planets = unique_resource_planets + best_planets

    # Recalculate captured resources and uncaptured resources after removing planets
    captured_resources = recalculate_captured_resources(final_planets, captured_resources)

    return final_planets


def capture_organic_resources(planet, groups, filter=set()):
    """If were going to sift through all systems lets get it perfect"""

    capturable_resources = set()

    flora_resources = set(planet.get("flora", {}).get("domesticable", []))
    capturable_flora = flora_resources & filter

    # Get capturable organics from fauna only if in groups['organic']['fauna']

    fauna_resources = set(planet.get("fauna", {}).get("domesticable", []))
    capturable_fauna = fauna_resources & set(groups["organic"]["fauna"]) & filter

    # Total capturable organics from this planet
    capturable_resources = set()
    capturable_resources = capturable_flora | capturable_fauna

    return capturable_resources


def capture_remaining_organics(system_data, final_planets, captured_resources, groups, remaining_organics):
    """
    Selects planets to capture the remaining uncaptured organics using a greedy set cover algorithm.
    Returns the updated list of final planets and captured resources.
    """
    candidate_planets = []
    for system in system_data:
        for planet in system["planets"]:
            if planet not in final_planets:
                candidate_planets.append(planet)

    # Initialize sets
    captured_organics = captured_resources["organic"]
    remaining_organics = set(remaining_organics) - captured_organics

    while remaining_organics:
        best_planet = None
        best_candidate_organic_resources = set()
        best_potential_groups = {}
        max_capturable_inorganics = -1

        for planet in candidate_planets:
            # Get capturable organics
            capturable_organic_resources = capture_organic_resources(planet, groups, remaining_organics)

            if not capturable_organic_resources:
                # Skip planets that do not have any of the remaining organics
                continue

            # Collect potential inorganics and their groups
            planet_inorganics = set(planet["resources"].get("inorganic", []))
            potential_groups = {}
            for group_name, group_resources in groups["inorganic"].items():
                capturable_inorganics = planet_inorganics & set(group_resources)
                if capturable_inorganics:
                    potential_groups[group_name] = list(capturable_inorganics)

            num_capturable_inorganics = len(potential_groups)

            if num_capturable_inorganics > max_capturable_inorganics:
                best_planet = planet
                best_candidate_organic_resources = capturable_organic_resources
                best_potential_groups = potential_groups
                max_capturable_inorganics = num_capturable_inorganics

        if not best_planet:
            print("Cannot find a planet to cover the remaining organics.")
            break

        # Add the best planet to final_planets
        final_planets.append(best_planet)
        # Set outpost candidacy for the best planet
        best_planet.setdefault("outpost_candidacy", {})
        best_planet["outpost_candidacy"]["other"] = list(best_candidate_organic_resources)
        best_planet["outpost_candidacy"]["potential_groups"] = best_potential_groups

        # Update captured resources
        captured_organics.update(best_candidate_organic_resources)

        # Update remaining organics
        remaining_organics -= best_candidate_organic_resources

        # Remove the selected planet from candidates
        candidate_planets.remove(best_planet)

    # Update captured resources dictionary
    captured_resources["organic"] = captured_organics

    return final_planets, captured_resources


def compute_main_group_shared_resources(groups):
    main_group_shared_resources = {}
    for group_name, resources in groups["inorganic"].items():
        main_group_name = group_name.split("-")[0]
        resources_set = set(resources)
        if main_group_name not in main_group_shared_resources:
            main_group_shared_resources[main_group_name] = resources_set.copy()
        else:
            main_group_shared_resources[main_group_name] &= resources_set
    return main_group_shared_resources


def eliminate_redundant_planets(final_planets, groups):
    """
    Attempts to eliminate redundant planets by combining potential inorganics from other planets
    to cover resource groups, ensuring each planet is used in at most one partial resource group.
    """
    from itertools import combinations

    # Planets to remove (store planet names)
    planets_to_remove = set()
    assigned_planets = set()  # Track planets already assigned to partial groups

    # For each planet with a full resource chain, check if we can eliminate it
    for planet in final_planets:
        full_resource_chain = planet.get("outpost_candidacy", {}).get("full_resource_chain", [])
        if not full_resource_chain:
            continue  # Skip planets without a full resource chain

        for group_name in full_resource_chain:
            group_resources = set(groups["inorganic"][group_name])

            # Collect other planets' potential inorganics for this group, excluding assigned planets
            other_planets = [
                p for p in final_planets if p["name"] != planet["name"] and p["name"] not in assigned_planets
            ]
            potential_planets = []
            for p in other_planets:
                potential_groups = p.get("outpost_candidacy", {}).get("potential_groups", {})
                if group_name in potential_groups:
                    potential_planets.append({"planet": p, "resources": set(potential_groups[group_name])})

            # Try to find combinations of planets that cover the group
            found_combination = False
            max_combination_size = min(4, len(potential_planets))  # Cap combinations at size 4
            for r in range(1, max_combination_size + 1):
                for combo in combinations(potential_planets, r):
                    combo_planets = [info["planet"] for info in combo]
                    # Skip combinations if any planet is already assigned
                    if any(p["name"] in assigned_planets for p in combo_planets):
                        continue
                    combined_resources = set().union(*(info["resources"] for info in combo))
                    if combined_resources >= group_resources:
                        # Found a valid combination
                        planets_to_remove.add(planet["name"])
                        # Add resource group info to combo planets
                        for combo in combo_planets:
                            combo.setdefault("outpost_candidacy", {})
                            # Use a set temporarily to avoid duplicate checks slowing down
                            resource_group_partial = set(combo["outpost_candidacy"].setdefault("resource_group_partial", []))
                            
                            if f"{group_name} (partial)" not in resource_group_partial:
                                resource_group_partial.add(f"{group_name} (partial)")
                            # Convert back to list
                            combo["outpost_candidacy"]["resource_group_partial"] = list(resource_group_partial)

                            partner_planets = {p["name"] for p in combo_planets if p["name"] != combo["name"]}
                            current_partners = set(combo["outpost_candidacy"].setdefault("partner_planets", []))
                            # Convert back to list
                            combo["outpost_candidacy"]["partner_planets"] = list(current_partners | partner_planets)
                            assigned_planets.add(combo["name"])  # Mark planet as assigned
                        # print(f"Eliminated planet {planet['name']} covering group {group_name} with combination of planets {[p['name'] for p in combo_planets]}")
                        found_combination = True
                        break
                if found_combination:
                    break  # No need to check larger combinations

    # Remove redundant planets
    final_planets = [p for p in final_planets if p["name"] not in planets_to_remove]

    return final_planets


def capture_helium_and_water(final_planets, captured_resources):
    """
    Goes through final_planets, and for any planet with 'Helium-3' or 'Water',
    adds a key to outpost_candidacy and updates captured_resources.
    """
    helium_resource = "Helium-3"
    water_resource = "Water"

    for planet in final_planets:
        planet_resources = set(planet["resources"].get("inorganic", []))
        if helium_resource in planet_resources:
            planet.setdefault("outpost_candidacy", {})
            planet["outpost_candidacy"]["has_helium"] = True
            captured_resources["inorganic"].add(helium_resource)
        if water_resource in planet_resources:
            planet.setdefault("outpost_candidacy", {})
            planet["outpost_candidacy"]["has_water"] = True
            captured_resources["inorganic"].add(water_resource)

    return captured_resources


def clean_up_after_processing(all_systems, final_planets):

    # Iterate over each system's planets in all_systems and each planet in final_planets
    for planet in [planet for system in all_systems for planet in system["planets"]] + final_planets:
        if "outpost_candidacy" in planet:
            planet["outpost_candidacy"].pop("potential_groups", None)  # Remove potential_groups if it exists
            if not planet["outpost_candidacy"]:  # Remove outpost_candidacy if empty
                del planet["outpost_candidacy"]

    return all_systems, final_planets


def find_best_systems(system_data, unique_resources, resources_by_rarity, groups):
    """
    Identifies the best systems for outpost setup based on unique resources and full resource chains.
    Returns the final list of planets for outpost placement.
    """
    # Step 1: Capture unique resource systems
    final_planets, processed_systems, captured_resources = capture_unique_resource_systems(
        system_data, unique_resources, groups
    )

    # Step 2: Capture systems with full chains that contibute the most to uncaptured organics.
    final_planets, processed_systems, captured_resources = capture_full_chain_systems(
        system_data,
        processed_systems,
        final_planets,
        captured_resources,
        resources_by_rarity,
        groups,
    )

    # final_planets, processed_systems, captured_resources = capture_full_chain_systems_greedy(
    #    system_data, processed_systems, final_planets, captured_resources, resources_by_rarity, groups
    # )

    # Step 3: Apply Highlander Rules
    final_planets = apply_highlander_rules(final_planets, captured_resources, resources_by_rarity, groups)

    # Calculate uncaptured resources for next step
    uncaptured_resources = calculate_uncaptured_resources(
        captured_resources, resources_by_rarity, groups["gatherable_only"]
    )

    iter_count = 1
    while len(uncaptured_resources["organic"]) > 0:
        print(f" {iter_count}: Reducing planet count... ")
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

        captured_resources = recalculate_captured_resources(final_planets, captured_resources)
        uncaptured_resources = calculate_uncaptured_resources(
            captured_resources, resources_by_rarity, groups["gatherable_only"]
        )
        iter_count += 1

    # Step 6: Capture Helium-3 and Water and clean up potential groups.
    captured_resources = capture_helium_and_water(final_planets, captured_resources)
    system_data, final_planets = clean_up_after_processing(system_data, final_planets)

    # Print final results
    captured_resources = recalculate_captured_resources(final_planets, captured_resources)
    uncaptured_resources = calculate_uncaptured_resources(
        captured_resources, resources_by_rarity, groups["gatherable_only"]
    )

    save_system_data(FINAL_SYSTEM_DATA_PATH, system_data)

    print_final_results(final_planets, uncaptured_resources)

    return final_planets


def print_final_results(final_planets, uncaptured_resources):
    """
    Prints the final planets, the count of final planets, and uncaptured resources.
    """
    success = True
    if len(final_planets) > 24:
        print("FAILURE")
        success = False

    print(f"\nFinal Planets:")
    for planet in final_planets:
        outpost_candidacy = planet.get("outpost_candidacy", {})
        system_name = planet.get("system_name", "Unknown System")
        print(f"{planet['name']} ({system_name})")
        # Collect reasons
        if success:
            reasons = []
            if outpost_candidacy.get("unique"):
                unique_resources = ", ".join(outpost_candidacy["unique"])
                reasons.append(f"- Unique Resource: {unique_resources}")
            if outpost_candidacy.get("full_resource_chain"):
                full_chain = ", ".join(outpost_candidacy["full_resource_chain"])
                reasons.append(f"- Full Chain: [{full_chain}]")
            if outpost_candidacy.get("other"):
                other_resources = ", ".join(outpost_candidacy["other"])
                reasons.append(f"- Other: {other_resources}")
            if outpost_candidacy.get("resource_group_partial"):
                partial_groups = ", ".join(outpost_candidacy["resource_group_partial"])
                reasons.append(f"- Partial Resource Group: {partial_groups}")
                partners = ", ".join(outpost_candidacy.get("partner_planets", []))
                reasons.append(f"- Partner Planets: {partners}")
            if outpost_candidacy.get("has_helium"):
                reasons.append("- Has Helium-3")
            if outpost_candidacy.get("has_water"):
                reasons.append("- Has Water")
            for reason in reasons:
                print(f"\t{reason}")

    print(f"\nNumber of Planets: {len(final_planets)}")

    if len(uncaptured_resources["inorganic"]) > 0:
        print(f"Uncaptured Inorganics:\n{'\n'.join(sorted(uncaptured_resources['inorganic']))}")
    if len(uncaptured_resources["organic"]) > 0:
        print(f"Uncaptured Organics:\n{'\n'.join(sorted(uncaptured_resources['organic']))}")


if __name__ == "__main__":
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

    all_systems = load_system_data(SCORED_SYSTEM_DATA_PATH)

    fullchain_inorganic_planets = find_fullchain_planets(all_systems, groups["inorganic"])
    unique_resource_planets = find_unique_resources(all_systems, unique)
    selected_systems = find_best_systems(all_systems, unique, rarity, groups)
