from time import sleep
import requests
from bs4 import BeautifulSoup
import json
import re
import os
import json
from common import (
    load_resource_groups,
    load_resources,
    load_system_data,
    get_gatherable_domesticable,
    save_system_data,
)
from config import *


def clean_output(text):
    """
    Cleans the given text by converting subscripts to normal numbers,
    removing unwanted Unicode characters, and excessive spaces.
    """

    # Convert subscripts (this is specific to numbers, extend as needed)
    subscripts = {
        "\u2080": "0",
        "\u2081": "1",
        "\u2082": "2",
        "\u2083": "3",
        "\u2084": "4",
        "\u2085": "5",
        "\u2086": "6",
        "\u2087": "7",
        "\u2088": "8",
        "\u2089": "9",
    }

    if text is None:
        print("Debug: Received None as input")  # Debug print for verification
        return None

    # Replace subscript numbers with normal ones
    for sub, norm in subscripts.items():
        text = text.replace(sub, norm)

    # Remove unwanted Unicode characters
    text = re.sub(r"[^\x00-\x7F]+", "", text)

    # Remove excessive spaces (e.g., around "100%")
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text


def scrape_star_system(url):
    """Scrapes the star system data from INARA for the given system URL."""

    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract and clean system name
    find_system_name = soup.find("h2", class_="itemname")
    if not find_system_name:
        raise ValueError("System name not found.")
    system_name = clean_output(find_system_name.text.strip())

    # Extract planet data
    planets = []
    tree_items = soup.find_all("li", class_="treeitem")
    for tree_item in tree_items:
        planet = {}

        # Clean planet name (header)
        find_planet_name = tree_item.find("h3", class_="bodyname")
        if not find_planet_name:
            raise ValueError("Planet name not found.")
        planet["name"] = clean_output(find_planet_name.text.strip())

        # Planet attributes
        planet["attributes"] = {}
        find_attributes_tags = tree_item.find_all("div", class_="itempaircontainer")
        if not find_planet_name or len(find_attributes_tags) < 10:
            raise ValueError(
                f"Insufficient attributes for planet {planet['name']}. Expected 10, found {len(find_attributes_tags)}."
            )
        for attr in find_attributes_tags:
            find_label_tag = attr.find("div", class_="itempairlabel")
            find_value_tag = attr.find("div", class_="itempairvalue")

            if not find_label_tag or not find_value_tag:
                print(f"Skipped attribute: {find_label_tag}{find_value_tag}")
                continue  # Skip if label or value is missing

            label = clean_output(find_label_tag.text.lower().replace(" ", "_").strip())
            value = clean_output(find_value_tag.text.strip())
            planet["attributes"][label] = value

        # Resources
        planet["resources"] = []
        find_resources_section = tree_item.find("span", string="Resources")
        if find_resources_section:
            resources_containers = []
            # Iterate over the siblings after the Resources section
            for sibling in find_resources_section.next_siblings:
                if sibling.name == "div" and "tagcontainer" in sibling.get("class", []):
                    resources_containers.append(sibling)
                elif sibling.name == "br":
                    continue  # Skip <br> tags
                elif sibling.name == "span" and "uppercase" in sibling.get("class", []):
                    # We've reached the next section
                    break
            # Now collect resources from all containers
            resources = []
            for container in resources_containers:
                resources.extend(
                    [
                        clean_output(a_tag.text.strip())
                        for a_tag in container.find_all("a", class_="tag")
                    ]
                )
            planet["resources"] = resources

        # Traits
        planet["traits"] = []
        find_traits_section = tree_item.find(string="Traits")
        if find_traits_section:
            find_traits_container = find_traits_section.find_next(
                "div", class_="tagcontainer"
            )
            if find_traits_container:
                find_traits_tags = find_traits_container.find_all("span", class_="tag")
                planet["traits"] = [
                    clean_output(trait.text.strip()) for trait in find_traits_tags
                ]

        # Biomes
        planet["biomes"] = []
        find_biomes_section = tree_item.find(string="Biomes")
        if find_biomes_section:
            biomes_container = find_biomes_section.find_next(
                "div", class_="tagcontainer"
            )
            if biomes_container:
                biomes_tags = biomes_container.find_all("span", class_="tag minor")
                biomes = [clean_output(biome.text.strip()) for biome in biomes_tags]
                planet['biomes'] = [re.split(r'\s\d', biome, 1)[0].strip() for biome in biomes]

        # Flora and Fauna Sections
        # Initialize flora and fauna dictionaries with counts
        flora_count = planet["attributes"].pop("flora", "0")
        fauna_count = planet["attributes"].pop("fauna", "0")

        planet["flora"] = {"count": flora_count, "domesticable": {}, "gatherable": {}}

        planet["fauna"] = {"count": fauna_count, "domesticable": {}, "gatherable": {}}

        for category in ["domesticable", "gatherable"]:
            find_ff_section = tree_item.find(string=category)
            if find_ff_section:
                find_ff_list = find_ff_section.find_next("ul")
                if find_ff_list:
                    find_ff_items = find_ff_list.find_all("li")
                    for item in find_ff_items:
                        span_tag = item.find("span")
                        if not span_tag or "class" not in span_tag.attrs:
                            continue  # Skip if span tag or class not found
                        color_class = span_tag["class"]

                        # Extract the resource and source
                        try:
                            organic_resource = clean_output(
                                item.text.split("(")[1].split(")")[0]
                            )
                        except IndexError:
                            continue  # Skip if the format is unexpected
                        resource_source_tag = item.find("a")
                        if not resource_source_tag:
                            continue  # Skip if resource source not found
                        resource_source = clean_output(resource_source_tag.text.strip())

                        # Assign to flora or fauna directly
                        if "npcfloracolor" in color_class:
                            planet["flora"][category][
                                organic_resource
                            ] = resource_source
                        elif "npcfaunacolor" in color_class:
                            planet["fauna"][category][
                                organic_resource
                            ] = resource_source

        # Initialize moon attributes
        planet["attributes"]["isMoon"] = False
        planet["moons"] = []

        # Check for moons
        next_sibling = tree_item.find_next_sibling()
        # Check if the very next sibling has the desired class
        if (
            next_sibling
            and next_sibling.name == "ul"
            and "treelevel" in next_sibling.get("class", [])
            and "treeitem" in next_sibling.get("class", [])
        ):
            find_moons = next_sibling  # Only assign if it matches
        else:
            find_moons = None

        if find_moons:
            planet["attributes"]["hasMoon"] = True
            find_moons_items = find_moons.find_all("li", class_="treeitem")
            for moon_item in find_moons_items:
                find_moon_name_name = moon_item.find("h3", class_="bodyname")
                if not find_moon_name_name:
                    continue
                moon_name = clean_output(find_moon_name_name.text.strip())
                planet["moons"].append(moon_name)
        else:
            planet["attributes"]["hasMoon"] = False

        planets.append(planet)

    # Update isMoon attribute for moons
    for planet in planets:
        if planet["name"] in [moon for p in planets for moon in p["moons"]]:
            planet["attributes"]["isMoon"] = True

        # Get rid of errant empty moons key
        if planet["attributes"]["hasMoon"] == False:
            if planet["moons"]:
                del planet["moons"]

    return {"name": system_name, "planets": planets}


def process_resources(planet, organic_dict, inorganic_dict, gatherable_dict):
    """
    Processes the resources of a planet, categorizing them into organic,
    inorganic, and others.
    """

    organic = []
    inorganic = []
    possible = []
    unknown = []

    domesticable, gatherable = get_gatherable_domesticable(planet)

    # Process each resource
    for resource in planet.get("resources", []):

        cleaned_resource = clean_output(resource)
        if cleaned_resource == "Ct":
            possible.append(inorganic_dict[cleaned_resource]["Resource"])
        elif cleaned_resource in inorganic_dict:
            inorganic.append(inorganic_dict[cleaned_resource]["Resource"])
        elif cleaned_resource in organic_dict:
            organic.append(organic_dict[cleaned_resource]["Resource"])
        else:
            unknown.append(resource)

    # Remove gatherable resources that are not domesticable from the organic list
    organic = [res for res in organic if res not in gatherable or res in domesticable]

    resources = {
        "inorganic": inorganic,
        "organic": organic,
    }
    if possible:
        resources["possible"] = possible
    if unknown:
        resources["unknown"] = unknown

    planet["resources"] = resources


def classify_planet_type(planet_type):
    if "giant" in planet_type.lower():
        new_planet_type = ["Jovian", planet_type]
    else:
        new_planet_type = ["Terrestrial", planet_type]
    return new_planet_type


def standardize_atmosphere(atmosphere):
    atmosphere = atmosphere.replace("Extr", "Extreme").replace("Std", "Standard")

    pattern = r"^(Standard|Thin|High|Extreme) (\w+)(?: \((\w+)\))?$"
    match = re.match(pattern, atmosphere)
    if match:
        density, atm_type, property_ = match.groups()
        return {"density": density, "type": atm_type, "property": property_ or None}
    return {"density": "None", "type": "None", "property": None}


def standardize_day_length(day_length):
    # Replace '-' with '0'
    day_length = re.sub(r"-", "0", day_length)

    # Convert day_length to hours
    if "days" in day_length:
        day_length = float(day_length.split()[0]) * 24  # Convert days to hours
    elif "hours" in day_length:
        day_length = float(day_length.split()[0])

    return f"{day_length} hours"


def clean_attributes(attributes):

    # Convert "Rank X required" in planetary_habitation to just "X"
    if "planetary_habitation" in attributes:
        match = re.search(r"Rank (\d)", attributes["planetary_habitation"])
        if match:
            attributes["planetary_habitation"] = match.group(1)
        elif attributes["planetary_habitation"] == "-":
            attributes["planetary_habitation"] = "0"
        else:
            attributes["planetary_habitation"] = str(
                attributes["planetary_habitation"]
            ).strip()

    # Classify planet type
    if "planet_type" in attributes:
        attributes["planet_type"] = classify_planet_type(attributes["planet_type"])

    # Clean up gravity
    if "gravity" in attributes:
        attributes["gravity"] = attributes["gravity"].replace(" ", "")

    # Standardize atmosphere
    if "atmosphere" in attributes:
        attributes["atmosphere"] = standardize_atmosphere(attributes["atmosphere"])

    # Standardize day length
    if "day_length" in attributes:
        attributes["day_length"] = standardize_day_length(attributes["day_length"])

    # Update planet with modified attributes

    return attributes


if __name__ == "__main__":

    inorganic_dict = load_resources(INORGANIC_DATA_PATH, shortname=True)
    organic_dict = load_resources(ORGANIC_DATA_PATH, shortname=True)
    gatherable_dict = load_resource_groups(GATHERABLE_ONLY_PATH)

    all_systems = load_system_data(INARA_SYSTEM_DATA_PATH)
    system_ids = {system["id"] for system in all_systems}

    new_data = []
    for system_id in range(1, 123):  # Inclusive of 1 to 122
        if system_id in system_ids:
            continue

        print(f"Scraping system #{system_id}...")
        inara_url = f"https://inara.cz/starfield/starsystem/{system_id}"
        try:
            system_data = scrape_star_system(inara_url)
            system_data["id"] = system_id  # Add ID
            for planet in system_data["planets"]:
                process_resources(planet, organic_dict, inorganic_dict, gatherable_dict)
                clean_attributes(planet.get("attributes", {}))

            print(f'System Name Processed: {system_data["name"]}')
            new_data.append(system_data)

        except Exception as e:
            print(f"Failed to scrape system #{system_id}: {e}")
            continue

        sleep(5)

    all_systems.extend(new_data)
    save_system_data(INARA_SYSTEM_DATA_PATH, all_systems)
