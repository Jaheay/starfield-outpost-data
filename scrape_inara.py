from time import sleep
import requests
from bs4 import BeautifulSoup
import json
import re
import os
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
    # Mapping of subscript Unicode characters to their normal number counterparts
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

    # Remove all non-ASCII characters
    text = re.sub(r"[^\x00-\x7F]+", "", text)

    # Replace multiple whitespace characters with a single space
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

    planets = []
    tree_items = soup.find_all("li", class_="treeitem")
    for tree_item in tree_items:
        planet = {}

        # Extract and clean planet name
        find_planet_name = tree_item.find("h3", class_="bodyname")
        if not find_planet_name:
            raise ValueError("Planet name not found.")
        planet["name"] = clean_output(find_planet_name.text.strip())

        # Initialize planet attributes dictionary
        planet["attributes"] = {}
        find_attributes_tags = tree_item.find_all("div", class_="itempaircontainer")
        if not find_planet_name or len(find_attributes_tags) < 10:
            raise ValueError(
                f"Insufficient attributes for planet {planet['name']}. Expected 10, found {len(find_attributes_tags)}."
            )
        
        # Extract each attribute label and value
        for attr in find_attributes_tags:
            find_label_tag = attr.find("div", class_="itempairlabel")
            find_value_tag = attr.find("div", class_="itempairvalue")

            if not find_label_tag or not find_value_tag:
                print(f"Skipped attribute: {find_label_tag}{find_value_tag}")
                continue  # Skip if label or value is missing

            label = clean_output(find_label_tag.text.lower().replace(" ", "_").strip())
            value = clean_output(find_value_tag.text.strip())
            planet["attributes"][label] = value

        # Extract resources associated with the planet
        planet["resources"] = []
        find_resources_section = tree_item.find("span", string="Resources")
        if find_resources_section:
            resources_containers = []
            # Iterate over siblings after the Resources section to find resource containers
            for sibling in find_resources_section.next_siblings:
                if sibling.name == "div" and "tagcontainer" in sibling.get("class", []):
                    resources_containers.append(sibling)
                elif sibling.name == "br":
                    continue  # Skip <br> tags
                elif sibling.name == "span" and "uppercase" in sibling.get("class", []):
                    # Reached the next section
                    break
            # Collect resources from all containers
            resources = []
            for container in resources_containers:
                resources.extend(
                    [
                        clean_output(a_tag.text.strip())
                        for a_tag in container.find_all("a", class_="tag")
                    ]
                )
            planet["resources"] = resources

        # Extract traits of the planet
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

        # Extract biomes of the planet
        planet["biomes"] = []
        find_biomes_section = tree_item.find(string="Biomes")
        if find_biomes_section:
            biomes_container = find_biomes_section.find_next(
                "div", class_="tagcontainer"
            )
            if biomes_container:
                biomes_tags = biomes_container.find_all("span", class_="tag minor")
                biomes = [clean_output(biome.text.strip()) for biome in biomes_tags]
                # Remove numeric suffixes from biomes
                planet['biomes'] = [re.split(r'\s\d', str(biome), maxsplit=1)[0].strip() for biome in biomes]

        # Initialize flora and fauna with counts from attributes
        flora_count = planet["attributes"].pop("flora", "0")
        fauna_count = planet["attributes"].pop("fauna", "0")

        planet["flora"] = {"count": flora_count, "domesticable": {}, "gatherable": {}}
        planet["fauna"] = {"count": fauna_count, "domesticable": {}, "gatherable": {}}

        # Extract flora and fauna details
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

                        # Extract the resource and source from the text
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

                        # Assign to flora or fauna based on the class
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

        # Check for moons in the next sibling
        next_sibling = tree_item.find_next_sibling()
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

        # Remove moons key if the planet does not have moons
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

    # Retrieve domesticable and gatherable resources
    domesticable, gatherable = get_gatherable_domesticable(planet)

    # Process each resource listed for the planet
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

    # Exclude gatherable resources that are not domesticable from the organic list
    organic = [res for res in organic if res not in gatherable or res in domesticable]

    # Organize resources into categories
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
    """
    Classifies the planet type as Jovian or Terrestrial based on its description.
    """
    if "giant" in planet_type.lower():
        new_planet_type = ["Jovian", planet_type]
    else:
        new_planet_type = ["Terrestrial", planet_type]
    return new_planet_type


def standardize_atmosphere(atmosphere):
    """
    Standardizes the atmosphere description into a structured format.
    """
    # Replace abbreviations with full words
    atmosphere = atmosphere.replace("Extr", "Extreme").replace("Std", "Standard")

    # Regex pattern to capture density, type, and optional property
    pattern = r"^(Standard|Thin|High|Extreme) (\w+)(?: \((\w+)\))?$"
    match = re.match(pattern, atmosphere)
    if match:
        density, atm_type, property_ = match.groups()
        return {"density": density, "type": atm_type, "property": property_ or None}
    return {"density": "None", "type": "None", "property": None}


def standardize_day_length(day_length):
    """
    Converts day length descriptions into a standardized format in hours.
    """
    # Replace '-' with '0' to handle missing data
    day_length = re.sub(r"-", "0", day_length)

    # Convert day_length to hours based on its unit
    if "days" in day_length:
        day_length = float(day_length.split()[0]) * 24  # Convert days to hours
    elif "hours" in day_length:
        day_length = float(day_length.split()[0])

    return f"{day_length} hours"


def clean_attributes(attributes):
    """
    Cleans and standardizes the planet's attributes.
    """
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

    # Classify planet type as Jovian or Terrestrial
    if "planet_type" in attributes:
        attributes["planet_type"] = classify_planet_type(attributes["planet_type"])

    # Clean up gravity by removing spaces
    if "gravity" in attributes:
        attributes["gravity"] = attributes["gravity"].replace(" ", "")

    # Standardize atmosphere description
    if "atmosphere" in attributes:
        attributes["atmosphere"] = standardize_atmosphere(attributes["atmosphere"])

    # Standardize day length description
    if "day_length" in attributes:
        attributes["day_length"] = standardize_day_length(attributes["day_length"])

    return attributes


def scrape_inara():
    # Load dictionaries for inorganic, organic, and gatherable resources
    inorganic_dict = load_resources(INORGANIC_DATA_PATH, shortname=True)
    organic_dict = load_resources(ORGANIC_DATA_PATH, shortname=True)
    gatherable_dict = load_resource_groups(GATHERABLE_ONLY_PATH)

    # Load existing system data and extract their IDs
    all_systems = load_system_data(INARA_SYSTEM_DATA_PATH)
    system_ids = {system["id"] for system in all_systems}

    new_data = []
    # Iterate through system IDs from 1 to 122
    for system_id in range(1, 123):  # Inclusive of 1 to 122
        if system_id in system_ids:
            continue  # Skip systems that are already processed

        print(f"Scraping system #{system_id}...")
        inara_url = f"https://inara.cz/starfield/starsystem/{system_id}"
        try:
            # Scrape system data from the URL
            system_data = scrape_star_system(inara_url)
            system_data["id"] = system_id  # Add system ID

            # Process each planet within the system
            for planet in system_data["planets"]:
                process_resources(planet, organic_dict, inorganic_dict, gatherable_dict)
                clean_attributes(planet.get("attributes", {}))

            print(f'System Name Processed: {system_data["name"]}')
            new_data.append(system_data)

        except Exception as e:
            print(f"Failed to scrape system #{system_id}: {e}")
            continue  # Skip to the next system if an error occurs

        sleep(5)  # Pause to avoid overwhelming the server

    # Append newly scraped data to existing systems and save
    all_systems.extend(new_data)
    save_system_data(INARA_SYSTEM_DATA_PATH, all_systems)

if __name__ == "__main__":
    scrape_inara()