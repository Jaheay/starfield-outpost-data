import json
import csv
from itertools import product
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency
from pprint import pprint

# Local Imports
from config import *
from common import (
    load_resources,
    load_resource_groups,
    load_system_data,
    get_grouped_inorganics,
)

### VALUES ###


def get_attribute_value(planet, attribute):
    """Extracts a comparable value for a specific attribute from the planet data."""
    if attribute == "planet_type":
        return planet["attributes"].get(attribute, [None, None])[
            1
        ]  # Return subtype only
    elif attribute == "atmosphere":
        atmosphere = planet["attributes"].get("atmosphere")
        return (
            f"{atmosphere.get('density', 'Unknown')} {atmosphere.get('type', 'Unknown')}"
            if atmosphere
            else None
        )
    elif attribute == "biomes":
        return planet.get(attribute, [])
    else:
        return planet["attributes"].get(attribute)


def get_unique_values(planets, attribute):
    """Fetch unique values for a given attribute from the dataset."""
    unique_values = set()
    for planet in planets:
        value = get_attribute_value(planet, attribute)
        if isinstance(value, list):
            unique_values.update(value)  # For lists like 'biomes'
        else:
            unique_values.add(value)
    print(f"Unique values for {attribute}: {unique_values}")  # Debug print
    return unique_values


### TWO_VALUE_HISTOGRAM ###


def get_attribute_combos(planets, attribute1, attribute2):
    """Find combinations of unique attribute values, count planets, and save data."""
    unique_values1 = get_unique_values(planets, attribute1)
    unique_values2 = get_unique_values(planets, attribute2)

    combinations = list(product(unique_values1, unique_values2))
    combo_data = []

    for val1, val2 in combinations:
        matching_planets = [
            planet["name"]
            for planet in planets
            if (
                get_attribute_value(planet, attribute1) == val1
                or (
                    attribute1 == "biomes"
                    and val1 in get_attribute_value(planet, attribute1)
                )
            )
            and (
                get_attribute_value(planet, attribute2) == val2
                or (
                    attribute2 == "biomes"
                    and val2 in get_attribute_value(planet, attribute2)
                )
            )
        ]
        count = len(matching_planets)
        combo_data.append([val1, val2, count, matching_planets])
        print(
            f"Combination {val1}, {val2}: count={count}, planets={matching_planets}"
        )  # Debug print

    output_csv = f"graph_{attribute1}_{attribute2}.csv"
    with open(output_csv, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([attribute1, attribute2, "count", "planet_list"])
        for row in combo_data:
            writer.writerow(row)
    print(f"Data written to {output_csv}")  # Debug print

    plot_bar_graph(combo_data, attribute1, attribute2)


def plot_bar_graph(combo_data, attribute1, attribute2):
    """Plot a bar graph for the attribute combinations and their counts with callouts for values."""
    labels = [f"{val1}, {val2}" for val1, val2, _, _ in combo_data]
    counts = [count for _, _, count, _ in combo_data]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(labels, counts)
    plt.xticks(rotation=90)
    plt.xlabel(f"{attribute1} and {attribute2} combinations")
    plt.ylabel("Count")
    plt.title(f"Planet Count by {attribute1} and {attribute2}")

    # Adding callouts above each bar with the count value
    for bar in bars:
        yval = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            yval,
            str(int(yval)),
            ha="center",
            va="bottom",
            fontsize=9,
        )

    plt.tight_layout()
    plt.show()


### FUN_FACTS ###


def get_min_max(planets, parameter):
    """Return the planet name with the min and max values for a numerical parameter like gravity or day_length."""
    min_value, max_value = float("inf"), float("-inf")
    min_planet, max_planet = None, None

    for planet in planets:
        if parameter in planet:
            value = planet["attributes"][parameter]
            try:
                # Convert value to a float (e.g., '0.89g' to 0.89)
                if "g" in value:
                    value = float(value.replace("g", ""))
                elif "hours" in value:
                    value = float(value.split()[0])
                else:
                    value = float(value)

                # Update min and max values and track the planet names
                if value < min_value:
                    min_value, min_planet = value, planet["name"]
                if value > max_value:
                    max_value, max_planet = value, planet["name"]
            except ValueError:
                continue

    return (min_planet, min_value) if min_planet else None, (
        (max_planet, max_value) if max_planet else None
    )


def planet_with_most_resources(planets, resource_type):
    """Return all planets with the highest count of a given resource type."""
    max_resources = 0
    planets_with_max = []

    for planet in planets:
        count = len(planet["resources"].get(resource_type, []))

        if count > max_resources:
            max_resources = count
            planets_with_max = [planet["name"]]
        elif count == max_resources and count > 0:
            planets_with_max.append(planet["name"])

    return planets_with_max, max_resources


def system_with_most(systems, parameter, values):
    """Return all systems with the most planets of specified types, e.g., 'gas giants'."""
    max_count = 0
    systems_with_max = []

    for system in systems:
        count = sum(
            1
            for planet in system["planets"]
            if parameter == "planet_type"
            and planet["attributes"][parameter][0] in values
        )

        # Track the systems with the highest count
        if count > max_count:
            max_count = count
            systems_with_max = [system["name"]]
        elif count == max_count and count > 0:
            systems_with_max.append(system["name"])

    return systems_with_max, max_count


def system_with_most_planets(systems):
    """Return the system with the most planets."""
    return max(systems, key=lambda system: len(system["planets"]))["name"]


def system_with_least_planets(systems):
    """Return the system with the most planets."""
    return min(systems, key=lambda system: len(system["planets"]))["name"]


### HIGHS_AND_LOWS ###


def planet_with_highest_lowest_score(planets, score_type):
    """Return the planets with the highest and lowest specified score."""
    max_planet, min_planet = None, None
    max_score, min_score = float("-inf"), float("inf")

    for planet in planets:
        score = float(planet["scores"].get(score_type, 0))

        if score > max_score:
            max_score = score
            max_planet = planet["name"]
        if score < min_score:
            min_score = score
            min_planet = planet["name"]

    return (max_planet, max_score), (min_planet, min_score)


def system_with_highest_lowest_score(systems, score_type):
    """Return the systems with the highest and lowest specified score."""
    max_system, min_system = None, None
    max_score, min_score = float("-inf"), float("inf")

    for system in systems:
        score = float(system["scores"].get(score_type, 0))

        if score > max_score:
            max_score = score
            max_system = system["name"]
        if score < min_score:
            min_score = score
            min_system = system["name"]

    return (max_system, max_score), (min_system, min_score)


### TOP_10S ###


def top_n_systems(systems, score_type, n=10):
    """Return the top N systems based on the specified score type."""
    sorted_systems = sorted(
        systems, key=lambda x: float(x["scores"].get(score_type, 0)), reverse=True
    )
    return [
        (system["name"], float(system["scores"].get(score_type, 0)))
        for system in sorted_systems[:n]
    ]


def top_n_planets(planets, score_type, n=10):
    """Return the top N planets based on the specified score type."""
    sorted_planets = sorted(
        planets, key=lambda x: float(x["scores"].get(score_type, 0)), reverse=True
    )
    return [
        (planet["name"], float(planet["scores"].get(score_type, 0)))
        for planet in sorted_planets[:n]
    ]


###  BIOME_GROUP_TENDENCY ###


def calculate_statistical_significance(frequency_data, expected_biome_distribution):
    significance_results = {}

    for resource, biomes in frequency_data.items():
        observed_counts = []
        expected_counts = []
        observed_vs_expected = {}

        for biome, count in biomes.items():
            observed_counts.append(count)
            expected = expected_biome_distribution.get(biome, 0) * sum(observed_counts)
            expected_counts.append(expected)
            observed_vs_expected[biome] = {
                "observed": count,
                "expected": expected,
                "ratio": count / expected if expected > 0 else 0,
            }

        # Perform chi-squared test
        chi2, p_value = chi2_contingency([observed_counts, expected_counts])[:2]

        # Store results, including observed vs expected data
        significance_results[resource] = {
            "p_value": p_value,
            "significant": float(p_value) < 0.05,  # type: ignore
            "observed_distribution": biomes,
            "observed_vs_expected": observed_vs_expected,
        }

    return significance_results


def print_significance_results(significance_results):
    print("\nSignificance Results:\n" + "=" * 30)
    for resource, data in significance_results.items():
        print(f"\nResource: {resource}")
        print(f"  - P-Value: {data['p_value']:.4f}")
        print(f"  - Significant: {'Yes' if data['significant'] else 'No'}")
        print("  - Observed vs. Expected Ratios:")
        for biome, values in data["observed_vs_expected"].items():
            observed = values["observed"]
            expected = values["expected"]
            ratio = values["ratio"]
            significance = " (significant)" if data["significant"] and ratio > 1 else ""
            print(
                f"      {biome}: observed {observed:.2f} vs expected {expected:.2f} -> ratio {ratio:.2f}{significance}"
            )
    print("=" * 30 + "\n")


import matplotlib.pyplot as plt

import matplotlib.pyplot as plt


def plot_biome_distribution(significance_results):
    for resource, data in significance_results.items():
        biomes = list(data["observed_vs_expected"].keys())
        observed_values = [
            values["observed"] for values in data["observed_vs_expected"].values()
        ]
        expected_values = [
            values["expected"] for values in data["observed_vs_expected"].values()
        ]

        plt.figure(figsize=(10, 6))
        bars = plt.bar(biomes, observed_values, label="Observed")
        plt.xticks(rotation=90)
        plt.xlabel("Biomes")
        plt.ylabel("Observed Value")
        plt.title(f"Observed vs Expected Biome Distribution for {resource}")

        # Add observed labels and individual expected lines for each bar
        for bar, expected, observed in zip(bars, expected_values, observed_values):
            # Label with the observed value above each bar
            yval = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                yval,
                f"{observed:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )
            # Draw a horizontal line at the expected value over the width of each bar
            plt.hlines(
                y=expected,
                xmin=bar.get_x(),
                xmax=bar.get_x() + bar.get_width(),
                color="red",
                linestyle="--",
                linewidth=1,
            )

            # Adjust expected text position if it overlaps with observed text
            text_offset = 5  # Offset in points to nudge the text up or down
            expected_va = "bottom" if abs(expected - observed) > 10 else "top"
            expected_y = expected + (
                text_offset if expected_va == "bottom" else -text_offset
            )

            # Label the expected line with its value
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                expected_y,
                f"Expected {expected:.2f}",
                ha="center",
                va=expected_va,
                color="red",
                fontsize=5,
            )

        plt.tight_layout()

        # Save the plot as an image file
        filename = f"{resource.replace(' ', '_')}_biome_distribution_vs_expected.png"
        plt.savefig(filename, dpi=150)
        plt.close()  # Close the figure to free memory and prevent display


def query_unique_values(planets):
    planet_fields = [
        "planet_type",
        "temperature",
        "atmosphere",
        "magnetosphere",
        "water",
        "biomes",
    ]
    print("----- Unique Values -----")
    for value in planet_fields:
        print(f"Unique {value}:", get_unique_values(planets, value))


def query_two_value_histogram(planets):
    # get_attribute_combos(planets, 'magnetosphere', 'planet_type')
    get_attribute_combos(planets, "atmosphere", "planetary_habitation")


def query_fun_facts(systems, planets):
    terrestrial_planets = [
        planet for planet in planets if planet["attributes"]["planet_type"][0] == "Terrestrial"
    ]
    gas_planets = [planet for planet in planets if planet["attributes"]["planet_type"][0] == "Gas"]

    print("\n----- Ranges -----")
    print("Gravity range:", get_min_max(terrestrial_planets, "gravity"))
    print(
        "Day length range (in hours):", get_min_max(terrestrial_planets, "day_length")
    )

    print("\n----- Resource Queries -----")
    print(
        "Planet with most inorganic resources:",
        planet_with_most_resources(terrestrial_planets, "inorganic"),
    )
    print(
        "Planet with most organic resources:",
        planet_with_most_resources(terrestrial_planets, "organic"),
    )

    print("\n----- System Queries -----")
    print("System with most planets:", system_with_most_planets(systems))
    print(
        "System with most gas giants:",
        system_with_most(systems, "planet_type", {"Gas"}),
    )
    print("System with least planets:", system_with_least_planets(systems))


def query_highs_and_lows(systems, planets):

    highest_lowest_hab_score = planet_with_highest_lowest_score(
        planets, "habitability_score"
    )
    highest_lowest_org_score = planet_with_highest_lowest_score(
        planets, "organic_score"
    )
    highest_lowest_inorg_score = planet_with_highest_lowest_score(
        planets, "inorganic_score"
    )

    highest_lowest_sys_hab_score = system_with_highest_lowest_score(
        systems, "habitability_score"
    )
    highest_lowest_sys_org_score = system_with_highest_lowest_score(
        systems, "organic_score"
    )
    highest_lowest_sys_inorg_score = system_with_highest_lowest_score(
        systems, "inorganic_score"
    )

    print("----- Planet Scores -----")
    print(
        f"Planet with highest habitability score: {highest_lowest_hab_score[0][0]} ({highest_lowest_hab_score[0][1]})"
    )
    print(
        f"Planet with lowest habitability score: {highest_lowest_hab_score[1][0]} ({highest_lowest_hab_score[1][1]})"
    )
    print(
        f"Planet with highest organic score: {highest_lowest_org_score[0][0]} ({highest_lowest_org_score[0][1]})"
    )
    print(
        f"Planet with lowest organic score: {highest_lowest_org_score[1][0]} ({highest_lowest_org_score[1][1]})"
    )
    print(
        f"Planet with highest inorganic score: {highest_lowest_inorg_score[0][0]} ({highest_lowest_inorg_score[0][1]})"
    )
    print(
        f"Planet with lowest inorganic score: {highest_lowest_inorg_score[1][0]} ({highest_lowest_inorg_score[1][1]})"
    )

    print("\n----- System Scores -----")
    print(
        f"System with highest habitability score: {highest_lowest_sys_hab_score[0][0]} ({highest_lowest_sys_hab_score[0][1]})"
    )
    print(
        f"System with lowest habitability score: {highest_lowest_sys_hab_score[1][0]} ({highest_lowest_sys_hab_score[1][1]})"
    )
    print(
        f"System with highest organic score: {highest_lowest_sys_org_score[0][0]} ({highest_lowest_sys_org_score[0][1]})"
    )
    print(
        f"System with lowest organic score: {highest_lowest_sys_org_score[1][0]} ({highest_lowest_sys_org_score[1][1]})"
    )
    print(
        f"System with highest inorganic score: {highest_lowest_sys_inorg_score[0][0]} ({highest_lowest_sys_inorg_score[0][1]})"
    )
    print(
        f"System with lowest inorganic score: {highest_lowest_sys_inorg_score[1][0]} ({highest_lowest_sys_inorg_score[1][1]})"
    )


def query_top_tens(systems, planets):

    top_hab_systems = top_n_systems(systems, "habitability_score", 10)
    top_hab_planets = top_n_planets(planets, "habitability_score", 10)
    top_inorg_systems = top_n_systems(systems, "inorganic_score", 10)
    top_inorg_planets = top_n_planets(planets, "inorganic_score", 10)
    top_org_systems = top_n_systems(systems, "organic_score", 10)
    top_org_planets = top_n_planets(planets, "organic_score", 10)

    print("\n----- Top Habitable Systems -----")
    for i, (name, score) in enumerate(top_hab_systems, start=1):
        print(f"{i}. {name}: {score}")

    print("\n----- Top Habitable Planets -----")
    for i, (planet_name, score) in enumerate(top_hab_planets, start=1):
        print(f"{i}. {planet_name}: {score}")

    print("\n----- Top Inorganic Systems -----")
    for i, (name, score) in enumerate(top_inorg_systems, start=1):
        print(f"{i}. {name}: {score}")

    print("\n----- Top Inorganic Planets -----")
    for i, (planet_name, score) in enumerate(top_inorg_planets, start=1):
        print(f"{i}. {planet_name}: {score}")

    print("\n----- Top Organic Systems -----")
    for i, (name, score) in enumerate(top_org_systems, start=1):
        print(f"{i}. {name}: {score}")

    print("\n----- Top Organic Systems -----")
    for i, (planet_name, score) in enumerate(top_org_planets, start=1):
        print(f"{i}. {planet_name}: {score}")


def query_flora_fauna(planets):
    domesticable_flora = set()
    domesticable_fauna = set()
    gatherable_flora = set()
    gatherable_fauna = set()
    for planet in planets:
        domesticable_flora.update(planet["flora"]["domesticable"].keys())
        domesticable_fauna.update(planet["fauna"]["domesticable"].keys())
        gatherable_flora.update(planet["flora"]["gatherable"].keys())
        gatherable_fauna.update(planet["fauna"]["gatherable"].keys())

    all_domesticable = domesticable_fauna | domesticable_flora
    all_gatherable = gatherable_fauna | gatherable_flora
    gatherable_only = [
        resource for resource in all_gatherable if resource not in all_domesticable
    ]

    gatherable_only_flora = [
        flora for flora in gatherable_flora if flora in gatherable_only
    ]
    gatherable_only_fauna = [
        fauna for fauna in gatherable_fauna if fauna in gatherable_only
    ]

    domesticable_flora = [resource for resource in domesticable_flora]
    domesticable_fauna_only = [
        resource
        for resource in domesticable_fauna
        if resource not in domesticable_flora
    ]

    print(json.dumps(gatherable_only, indent=4))
    organics = {"flora": domesticable_flora, "fauna": domesticable_fauna_only}
    print(json.dumps(organics, indent=4))


def query_biome_group_tendency(systems, planets):
    # TODO: Fix to use new biome_resources data.
    resource_biome_data = []
    inorganic_rarity = load_resources(INORGANIC_DATA_PATH)
    gatherable_only = load_resource_groups(GATHERABLE_ONLY_PATH)

    unique = {
        key
        for key, value in inorganic_rarity.items()
        if value == "Unique" and key not in gatherable_only["inorganic"]
    }

    inorganic_groups = load_resource_groups(INORGANIC_GROUPS_PATH, unique)
    print(json.dumps(inorganic_groups, indent=4))
    for system in systems:
        for planet in system.get("planets", []):
            grouped_resources = get_grouped_inorganics(
                planet["resources"]["inorganic"], inorganic_groups
            )
            for resource in grouped_resources:
                resource_biomes = {
                    "planet": planet["name"],
                    "resource": (
                        [resource] if isinstance(resource, str) else resource
                    ),  # Ensure resource is a list
                    "biomes": planet.get("biomes", []),
                }
                resource_biome_data.append(resource_biomes)

    frequency_data = {}
    total_counts = {}
    total_biome_distribution = {}
    # Populate frequency_data and total_counts
    for datum in resource_biome_data:
        for resource in datum["resource"]:  # Iterate over each resource in the list
            if resource not in frequency_data:
                frequency_data[resource] = {}
                total_counts[resource] = 0
            total_counts[
                resource
            ] += 1  # Increment total count for each resource occurrence
            for biome in datum["biomes"]:
                total_biome_distribution[biome] = (
                    total_biome_distribution.get(biome, 0) + 1
                )
                frequency_data[resource][biome] = (
                    frequency_data[resource].get(biome, 0) + 1
                )

    # Convert total biome distribution to relative frequencies
    total_biome_count = sum(total_biome_distribution.values())
    expected_biome_distribution = {
        biome: count / total_biome_count
        for biome, count in total_biome_distribution.items()
    }

    # Calculate significance results
    significance_results = calculate_statistical_significance(
        frequency_data, expected_biome_distribution
    )
    print_significance_results(significance_results)
    plot_biome_distribution(significance_results)


def query_planets_with_specific_organics(planets, inorganic_groups):

    planets_with_organics = {}
    organics = [
        "Adhesive",
        "Antimicrobial",
        "Aromatic",
        "Hypercatalyst",
        "Ornamental Material",
        "Pigment",
        "Polymer",
        "Structural Material",
    ]

    for planet in planets:
        organics_on_planet = planet["resources"]["organic"]
        inorganics_on_planet = planet["resources"]["inorganic"]

        # Check if any organic resource is present on the planet
        if any(organic in organics_on_planet for organic in organics):
            planet_groups = get_grouped_inorganics(
                inorganics_on_planet, inorganic_groups
            )

            # Ensure there is at least one value of 3 or more and not all values are 1
            if any(value == 3 for value in planet_groups.values()) and any(
                value != 1 for value in planet_groups.values()
            ):
                planets_with_organics[planet] = planet_groups

    print("Output")
    for planet, planet_groups in planets_with_organics.items():
        # Print planet name
        print(planet["name"])

        # Print resources, skipping those with a value of 1
        for resource, amount in planet_groups.items():
            if amount != 1:
                print(f"\t{resource}: {amount}")


def query_planets_with_gas_and_atmo(planets, resource_state, filter_by_resources=[]):
    candidate_resources = []

    # Validate filter_by_resources if provided
    if filter_by_resources:
        for filter_resource in filter_by_resources:
            if resource_state.get(filter_resource) != "Gas":
                raise ValueError("Non-Gas resource selected in filter")
            else:
                candidate_resources.append(filter_resource)
    else:
        # No filter provided, gather all resources with state 'Gas'
        for resource, state in resource_state.items():
            if state == "Gas":
                candidate_resources.append(resource)

    # Find planets that meet the criteria
    candidate_planets = {}
    for planet in planets:
        matching_resources = []
        for resource in candidate_resources:
            if (
                resource in planet["resources"]["inorganic"]
                and planet["attributes"]["atmosphere"]["density"] != "None"
            ):
                matching_resources.append(resource)

        # Only add planet if there are matching resources
        if matching_resources:
            candidate_planets[planet["name"]] = matching_resources

    print("Planets with Resources:\n")
    for planet, resources in sorted(candidate_planets.items()):
        print(f"{planet}:")
        for resource in resources:
            print(f"    - {resource}")
    print()  # For spacing after the list


def query_atmohe3_by_habitability(planets):

    atmohe3_planets = [
        "Algorab III-a",
        "Andromas III",
        "Arcturus I",
        "Beta Andraste I-a",
        "Beta Ternion III-a",
        "Cassiopeia II-a",
        "Denebola I-b",
        "Eridani III-b",
        "Fermi IX-d",
        "Feynman IV",
        "Frost",
        "Katydid I-a",
        "Kreet",
        "Lantana VII",
        "Lantana VIII-d",
        "Luyten's Rock",
        "Syrma III",
        "Zosma III-a",
    ]

    scores_atmohe3 = {}
    for planet in planets:
        if planet["name"] in atmohe3_planets:
            scores_atmohe3[planet["name"]] = float(planet["scores"]["habitability_score"])

    sorted_scores = sorted(scores_atmohe3.items(), key=lambda item: item[1], reverse=True)
    pprint(sorted_scores)

# query_resource_from_list(planets, capture_planets, ["Fiber", "Water"])
def query_resource_from_list(all_planets, query_planets, query_resources):
    
    for planet in all_planets:
        planet_resources = []
        if planet["name"] in query_planets:
            planet_resources.extend(planet["resources"]["organic"])
            planet_resources.extend(planet["resources"]["inorganic"])

            if all(resource in planet_resources for resource in query_resources):
                print(f"Candidate: {planet["name"]}")


def run_queries():
    systems = load_system_data(SCORED_SYSTEM_DATA_PATH)
    planets = [planet for system in systems for planet in system["planets"]]
    capture_planets = ["Katydid I-a", "Decaran VII-b", "Schrodinger II", "Carinae III-a", "Huygens VII-a", "Verne I", "Katydid III", "Fermi VII-a", "Linnaeus II", "Zelazny III", "Bardeen III", "Schrodinger III", "Zeta Ophiuchi I", "Eridani III", "Verne VII-d", "Charybdis II", "Zeta Ophiuchi VI-a", "Procyon III", "Jaffa I", "Sumati", "Codos", "Alpha Andraste III", "Beta Ternion I", "Hyla II", ]


    query_unique_values(planets)
    #query_two_value_histogram(planets)
    query_fun_facts(systems, planets)
    query_highs_and_lows(systems, planets)
    query_top_tens(systems, planets)
    # query_flora_fauna(planets)
    # query_biome_group_tendency(systems, planets)

    # inorganic_groups = load_resource_groups(INORGANIC_GROUPS_PATH)
    # query_planets_with_specific_organics(planets, inorganic_groups)

    # resource_state = load_resources(INORGANIC_DATA_PATH, state=True)
    # query_planets_with_gas_and_atmo(planets, resource_state, filter_by_resources=['Helium-3'])

    #query_atmohe3_by_habitability(planets)

    #query_resource_from_list(planets, capture_planets, ["Immunostimulant"])


if __name__ == "__main__":
    run_queries()
