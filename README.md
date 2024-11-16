# Starfield Outpost Finder

Unlock the secrets of the universe in **Starfield** by discovering the most optimal outpost locations! This project is a comprehensive pipeline of Python scripts designed to scrape, process, and analyze data from various sources to help you identify the best planets for your outposts.

## Overview

The **Starfield Outpost Finder** leverages data scraped from [inara.cz](https://inara.cz/starfield/) and [starfieldalmanac.com](https://starfieldalmanac.com/) to compile an extensive database of planetary systems, resources, and biomes. By processing this data, the scripts identify planets that offer the most valuable resources and optimal conditions for building outposts.

### Features

- **Data Scraping**: Collects detailed planetary and resource data from multiple sources.
- **Data Processing**: Combines and scores data to prioritize the best systems.
- **Outpost Optimization**: Finds the minimal set of planets needed to gather all farmable resources.
- **Query Tools**: Provides utilities to answer specific questions and generate graphs about the game world.

## Usage

### Prerequisites

- Python 3.x
- Required Python libraries (listed in `requirements.txt`)

### Steps

1. **Data Scraping**

   Run the scraping scripts to collect data:

   ```bash
   python scrape_inara.py
   python scrape_almanac.py
   ```

2. **Data Processing**

   Combine and score the scraped data:

   ```bash
   python combine_scrape_data.py
   python score_data.py
   ```

3. **Find Optimal Outposts**

   Use the processed data to find the best outpost locations:

   ```bash
   python find_outposts_fullchain.py
   ```

4. **Explore Data**

   Use the query script to explore the data and answer specific questions:

   ```bash
   python query_data.py
   ```

## Project Structure

### Data Game (`data_game/`)

Contains game data such as lists of all inorganic and organic resources:

- **`inorganic.csv`**: CSV file listing inorganic resources.
- **`organic.csv`**: CSV file listing organic resources.
- **`gatherable_only.json`**: JSON file of resources that are gatherable only.
- **`inorganic_groups.json` & `organic_groups.json`**: JSON files containing resource groups, which can be loaded using `common.py`'s `load_resource_groups` function.

### Data Systems (`data_systems/`)

Stores intermediary and final data files from scraping and processing:

- **`inara_systems_data.json`**: Data scraped from inara.cz.
- **`almanac_systems_data.json`**: Data scraped from starfieldalmanac.com.
- **`raw_systems_data.json`**: Combined data from both sources using `combine_scrape_data.py`.
- **`scored_systems_data.json`**: Scored data based on resource availability and other factors using `score_data.py`.
- **`final_systems_data.json`**: The final output used by `find_outposts_fullchain.py`.
- **`my_system_data.yaml`**: Personal data collected during gameplay (work in progress).

### Testing (`testing/`)

Contains working notes and experiments:

- **Helium-3 Atmospheric Worlds**: Research and notes on planets with atmospheric Helium-3.
  - Reddit Post: [All Worlds with Atmospheric Helium-3](https://www.reddit.com/r/Starfield/comments/1gq7rro/all_worlds_with_atmospheric_helium3_and_why_you/)
- **Optimal Planets Capture Notes**: Documentation on capturing the 23 optimal planets reported by `find_outposts_fullchain.py`.
  - Reddit Post: [Every Farmable Resource in 23 Outposts](https://www.reddit.com/r/Starfield/comments/1gkao0r/every_farmable_resource_in_23_outposts_and_an/)

### Main Directory

Contains the core Python scripts forming the data pipeline:

- **Input Scripts**
  - `scrape_inara.py`: Scrapes data from inara.cz.
  - `scrape_almanac.py`: Scrapes data from starfieldalmanac.com.

- **Processing Scripts**
  - `combine_scrape_data.py`: Combines scraped data into a unified format.
  - `score_data.py`: Scores the combined data based on various criteria.

- **Output Scripts**
  - `find_outposts_fullchain.py`: Finds the optimal combination of outposts.
  - `find_outposts_fullchain_exhaustive.py`: Exhaustively searches all possible combinations (no longer updated).
  - `find_outposts_biome_map.py`: Work in progress to find a 22-biome solution using biome-resource mapping.

- **Utilities**
  - `common.py`: Shared functions for data loading and saving.
  - `config.py`: Global configurations and constants.
  - `query_data.py`: Functions to query data, generate graphs, and explore the dataset.

### Best Combinations (`best_combinations/`)

Intended to store the output of `find_outposts_fullchain_exhaustive.py` (work in progress).

## TODO

- Incorporate `my_system_data.yaml` into the raw data processing pipeline.
- Update `find_outposts_fullchain_exhaustive.py` and populate `best_combinations/`.
- Complete `find_outposts_biome_map.py` to find optimal biome combinations.
- Enhance `query_data.py` with more querying capabilities.

## Credits

This project was developed out of a passion for exploring the vast universe of **Starfield** and optimizing the gameplay experience. Special thanks to:

- [inara.cz](https://inara.cz/starfield/) for providing comprehensive game data.
- [starfieldalmanac.com](https://starfieldalmanac.com/) for their detailed planetary information.
- The Starfield community on Reddit for their invaluable insights and discussions.

## Fun Data

*Placeholder for fun data to be added.*

## Contributing

Contributions are welcome! Please submit pull requests or open issues to help improve the project.

## License

This project is licensed under the MIT License.