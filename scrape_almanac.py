import json
import shutil
from time import sleep
from pprint import pprint
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager



# Local Imports
from config import *
from common import load_system_data, save_system_data


# Function to save links to a JSON file
def save_link_data(path, links):
    # TODO: Merge with save_system_data
    with open(path, "w", encoding="utf-8") as file:
        json.dump(links, file, ensure_ascii=False, indent=4)


# Function to load links from a JSON file
def load_link_data(path):
    # TODO: Merge with load_system_data
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return None


def initialize_driver():
    print("Initializing chromedriver")
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")
    options.add_argument("--incognito")
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    return driver


# Initialize driver setup
def scrape_all_systems_page(url, driver):
    driver.get(url)
    all_links = []
    page_count = 1

    while True:
        print(f"Scraping Page {page_count} - {driver.title}")
        try:
            # Wait for the main block to be visible
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "body > div > main > div > div.flex-grow.m-2")
                )
            )
        except TimeoutException:
            print("Timeout: Main block not found within 10 seconds.")

        # Get page content and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")
        main_div = soup.select_one("body > div > main > div > div.flex-grow.m-2")

        # Extract all <a> tags and store their hrefs
        if main_div:
            links = [a["href"] for a in main_div.find_all("a", href=True)]
        else: 
            raise ValueError("No Main Div found when scraping systems page")
        
        all_links.extend(links)

        # Find the "Next" button
        try:
            next_button = driver.find_element(
                By.XPATH, '//button[contains(text(), "Next")]'
            )
            if next_button.get_attribute("disabled"):
                break  # Exit loop if "Next" button is disabled
            next_button.click()
            print(f"Scraped {len(all_links)} systems so far...")
            page_count += 1
        except Exception as e:
            print("No more pages or error navigating:", e)
            break

    print(f"Scraped {len(all_links)} systems.")
    return all_links


def scrape_system_page(base_url, system_link, driver):
    url = base_url + system_link
    driver.get(url)
    try:
        # Wait for the main block to be visible
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "body > div > main > div > div:nth-child(1) > aside > div:nth-child(2) > div:first-child",
                )
            )
        )
    except TimeoutException:
        print("Timeout: Main block not found within 10 seconds.")

    print("Scraping:", driver.title)
    # Once the main block is visible, retrieve page source and parse it
    soup = BeautifulSoup(driver.page_source, "html.parser")
    print("Scraping:", driver.title)

    # Extract system name or other elements from soup
    system_name_tag = soup.select_one(
        "body > div > main > div > div:nth-child(1) > aside > div:nth-child(2) > div:first-child"
    )
    system_name = system_name_tag.text.strip() if system_name_tag else "Unknown System"

    # Extract star properties
    star_properties = {}
    star_div = soup.select_one(
        "body > div > main > div > div:nth-child(1) > aside > div.grid.grid-cols-2.justify-between.uppercase.mt-2.border.border-saBorder"
    )
    if star_div:
        properties = star_div.find_all("div")
        for i in range(0, len(properties), 2):
            key = properties[i].text.strip()
            value = properties[i + 1].text.strip()
            star_properties[key] = value

    # Extract planets and their links
    planets = []
    planet_cards = soup.select(
        "div.lg\\:grid.grid-cols-3.bg-saBG\\/90.p-2.border-2.border-saBorder > div.m-2.max-w-sm.border-2.border-saBorder"
    )
    for card in planet_cards:
        planet_name_tag = card.select_one(
            "div.flex.items-center.mb-2.max-w-sm div.text-2xl a"
        )
        if planet_name_tag:
            planet_name = planet_name_tag.text.strip()
            planet_url = planet_name_tag["href"]
            if planet_name and "Moon of" not in planet_name:
                planets.append({"name": planet_name, "link": planet_url})

    print(f"Extracted {system_name}, Found {len(planets)} Planets")

    # Create output structure as specified
    system_data = {"name": system_name, "star_properties": star_properties}
    scrape_data = {"name": system_name, "link": system_link, "planets": planets}

    return scrape_data, system_data


def scrape_planet_page(base_url, planet_link, driver):
    url = base_url + planet_link
    driver.get(url)

    try:
        # Wait for the main block to be visible
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "div.bg-saBG\\/90.p-2.border-2.border-saBorder.w-full > div > div.block",
                )
            )
        )
    except TimeoutException:
        print("Timeout: Main block not found within 10 seconds.")

    print("Scraping:", driver.title)
    # Parse page source with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Dictionary to store all biomes with the biome name as the key
    biomes_data = {}

    # Locate the block wrapping around all biome containers
    main_block = soup.select_one(
        "div.bg-saBG\\/90.p-2.border-2.border-saBorder.w-full > div > div.block"
    )
    if not main_block:
        print("No biomes found for this planet.")
        return biomes_data

    # Loop through each biome container within the main block
    biome_containers = main_block.select("div.flex.flex-wrap.mb-4")
    for container in biome_containers:
        # Attempt to extract the biome name if it exists
        biome_name_tag = container.select_one(
            "div.flex-grow.align-top > div.custTitleBG > p"
        )
        biome_name = biome_name_tag.text.strip() if biome_name_tag else "Unknown Biome"

        # Initialize lists for flora, fauna, and inorganics
        flora, fauna, inorganics = [], [], []

        # Extract Flora, Fauna, and Extractables from the resource containers
        resource_sections = container.select(
            "div.flex-grow.align-top > div.border.border-saBorder > div > div"
        )
        for section in resource_sections:
            p_tag = section.select_one("p")
            if p_tag is not None:
                title = p_tag.text.strip()
            else: 
                continue
            
            items = [item.text.strip() for item in section.select("ul li")]

            # Categorize based on title
            if title == "Flora":
                flora.extend(items)
            elif title == "Fauna":
                fauna.extend(items)
            elif title == "Extractables":
                inorganics.extend(items)

            for resource in range(len(inorganics)):
                if inorganics[resource] == "Helium 3":
                    inorganics[resource] = "Helium-3"

                if inorganics[resource] == "Carboxylic Acid":
                    inorganics[resource] = "Carboxylic Acids"

        # Store the details under the biome name as the key
        biomes_data[biome_name] = {
            "flora": flora,
            "fauna": fauna,
            "resources": {"inorganic": inorganics},
        }

    # Adjust print for optimal use of terminal width
    print(f"Scraping found {len(biomes_data)} biomes.")
    terminal_width = shutil.get_terminal_size().columns - 16
    #print("Planet biomes data:")
    #pprint(biomes_data, compact=True, width=terminal_width)

    return biomes_data


def scrape_almanac():
    base_url = "https://starfieldalmanac.com"
    systems_url = f"{base_url}/system"

    UPDATE_DATA = False
    ALMANAC_SYSTEM_LINKS_PATH = "data_systems/almanac_system_links.json"
    ALMANAC_PLANET_LINKS_PATH = "data_systems/almanac_planet_links.json"

    # Load existing links or fetch if not available
    if not UPDATE_DATA:
        all_system_links = load_link_data(ALMANAC_SYSTEM_LINKS_PATH)
        all_planet_links = load_link_data(ALMANAC_PLANET_LINKS_PATH)
        all_system_data = load_system_data(ALMANAC_SYSTEM_DATA_PATH)

    driver = initialize_driver()

    if all_system_links is None:
        all_system_links = scrape_all_systems_page(systems_url, driver)
        save_link_data(ALMANAC_SYSTEM_LINKS_PATH, all_system_links)

    if all_planet_links is None or all_system_data is None:
        all_planet_links = [] if all_planet_links is None else all_planet_links
        all_system_data = [] if all_system_data is None else all_system_data
        existing_systems = {system["name"] for system in all_system_data}

        # Scrape each system's details if not already in all_system_data
        for system_link in all_system_links:
            planet_links, system_data = scrape_system_page(
                base_url, system_link, driver
            )

            # Only append if this system has not been processed
            if system_data["name"] not in existing_systems:
                all_planet_links.append(planet_links)
                all_system_data.append(system_data)

        save_link_data(
            ALMANAC_PLANET_LINKS_PATH,
            all_planet_links,
        )
        save_system_data(ALMANAC_SYSTEM_DATA_PATH, all_system_data)

    # Populate planet data in all_system_data if missing
    for system in all_planet_links:
        # Find or create the system entry in all_system_data
        system_name = system["name"]
        matching_system_data = next(
            (s for s in all_system_data if s["name"] == system_name), None
        )

        if matching_system_data:
            # Only update if 'planets' data is missing
            if (
                "planets" not in matching_system_data
                or not matching_system_data["planets"]
            ):
                planet_data = []
                for planet in system["planets"]:
                    planet_biomes = scrape_planet_page(base_url, planet["link"], driver)
                    planet_data.append(
                        {"name": planet["name"], "biomes": planet_biomes}
                    )

                # Update the existing system data with planet data
                matching_system_data["planets"] = planet_data
        else:
            # If system does not exist, create a new entry with star_properties and planet data
            planet_data = []
            for planet in system["planets"]:
                planet_biomes = scrape_planet_page(base_url, planet["link"], driver)
                planet_data.append({"name": planet["name"], "biomes": planet_biomes})

            all_system_data.append(
                {
                    "name": system_name,
                    "star_properties": {},  # Keep empty if star properties were not scraped
                    "planets": planet_data,
                }
            )

    # Save the updated all_system_data
    save_system_data(ALMANAC_SYSTEM_DATA_PATH, all_system_data)

    driver.quit()
    print("Completed scraping all systems.")

if __name__ == "__main__":
    scrape_almanac()