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

Here is some fun data from the query script: 

----- Ranges -----
Gravity range: (('Phobos', 0.01), ('Groombridge II', 2.18))
Day length range (in hours): (('Porrima II-a', 0.0), ('Venus', 5832.0))


----- System Queries -----
System with most planets: Cheyenne
System with most gas giants: ([], 0)
System with least planets: Sagan

----- Planet Scores -----
Planet with highest habitability score: Nemeria IV-a (24.0)
Planet with lowest habitability score: Venus (-13.0)
Planet with highest organic score: Zelazny III (21.522)
Planet with lowest organic score: Porrima I (0.0)
Planet with highest inorganic score: Carinae V-c (45.0)
Planet with lowest inorganic score: Porrima II-a (0.0)

----- System Scores -----
System with highest habitability score: Cheyenne (66.5)
System with lowest habitability score: Aranae (0.0)
System with highest organic score: Bardeen (40.0)
System with lowest organic score: Sol (0.0)
System with highest inorganic score: Kumasi (109.0)
System with lowest inorganic score: Van Maanen's Star (2.0)

----- Top Habitable Systems -----
1. Cheyenne: 66.5
2. Lantana: 61.0
3. Syrma: 60.0
4. Ixyll: 58.0
5. Porrima: 57.0
6. Schrodinger: 55.5
7. Serpentis: 53.5
8. Alpha Tirna: 53.5
9. Bardeen: 50.0
10. Nemeria: 50.0

----- Top Habitable Planets -----
1. Nemeria IV-a: 24.0
2. Syrma VII-a: 23.5
3. Codos: 19.5
4. Katydid I-a: 19.0
5. Archimedes V-a: 17.5
6. Montara Luna: 17.0
7. Zeta Ophiuchi I: 16.5
8. Huygens VII-b: 16.0
9. Ixyll II: 16.0
10. Schrodinger VIII-a: 16.0

----- Top Inorganic Systems -----
1. Kumasi: 109.0
2. Hyla: 103.0
3. Feynman: 101.0
4. Schrodinger: 101.0
5. Cheyenne: 99.0
6. Muphrid: 97.0
7. Huygens: 95.0
8. Verne: 93.0
9. Jaffa: 93.0
10. Alpha Tirna: 93.0

----- Top Inorganic Planets -----
1. Carinae V-c: 45.0
2. Fermi VII-b: 42.0
3. Nemeria V-c: 40.333
4. Tirna VIII-a: 39.0
5. Eridani VII-c: 39.0
6. Maheo II: 39.0
7. Rutherford VI-a: 39.0
8. Mars: 38.0
9. Al-Battani II: 38.0
10. Verne I: 38.0

----- Top Organic Systems -----
1. Bardeen: 40.0
2. Shoza: 36.0
3. Cheyenne: 32.0
4. Zelazny: 30.0
5. Schrodinger: 29.0
6. Alpha Tirna: 26.0
7. Beta Ternion: 24.0
8. Fermi: 22.0
9. Ursae Majoris: 22.0
10. Beta Marae: 21.0

----- Top Organic Systems -----
1. Zelazny III: 21.522
2. Bardeen III: 18.0
3. Fermi VII-a: 16.0
4. Linnaeus II: 15.222
5. Masada III: 14.818
6. Beta Ternion II: 13.667
7. Ternion III: 12.87
8. Alpha Andraste III: 12.308
9. Codos: 12.0
10. Zeta Ophiuchi I: 11.619

----- Unique Values -----
Unique values for planet_type: {'Ice giant', 'Rock', 'Asteroid', 'Gas giant', 'Ice', 'Barren', 'Hot gas giant'}
Unique planet_type: {'Ice giant', 'Rock', 'Asteroid', 'Gas giant', 'Ice', 'Barren', 'Hot gas giant'}
Unique values for temperature: {'Deep freeze', 'Scorched', 'Hot', 'Cold', 'Frozen', 'Temperate', 'Inferno'}
Unique temperature: {'Deep freeze', 'Scorched', 'Hot', 'Cold', 'Frozen', 'Temperate', 'Inferno'}
Unique values for atmosphere: {'Extreme CO2', 'Extreme M', 'High M', 'High CO2', 'Thin M', 'Thin O2', 'Thin N2', 'Thin CO2', 'Standard CO2', 'Extreme N2', 'Extreme O2', 'Standard M', 'High O2', 'Standard N2', 'High N2', 'None None', 'Standard O2'}   
Unique atmosphere: {'Extreme CO2', 'Extreme M', 'High M', 'High CO2', 'Thin M', 'Thin O2', 'Thin N2', 'Thin CO2', 'Standard CO2', 'Extreme N2', 'Extreme O2', 'Standard M', 'High O2', 'Standard N2', 'High N2', 'None None', 'Standard O2'}
Unique values for magnetosphere: {'Very weak', 'Massive', 'Powerful', 'Very strong', 'None', 'Weak', 'Strong', 'Extreme', 'Average'}
Unique magnetosphere: {'Very weak', 'Massive', 'Powerful', 'Very strong', 'None', 'Weak', 'Strong', 'Extreme', 'Average'}
Unique values for water: {'None', 'Safe', 'Biological', 'Chemical', 'Radioactive', 'Heavy metal'}
Unique water: {'None', 'Safe', 'Biological', 'Chemical', 'Radioactive', 'Heavy metal'}
Unique values for biomes: {'Frozen Volcanic', 'Wetlands Frozen', 'Ocean', 'Volcanic', 'Frozen Dunes', 'Rocky Desert', 'Frozen Plains', 'Frozen Crevasses', 'Frozen Mountains', 'Frozen Hills', 'Savanna', 'Swamp', 'Craters', 'Tropical Forest', 'Wetlands', 'Hills', 'Mountains', 'Deciduous Forest', 'Sandy Desert', 'Coniferous Forest', 'Plateau', 'Frozen Craters'}
Unique biomes: {'Frozen Volcanic', 'Wetlands Frozen', 'Ocean', 'Volcanic', 'Frozen Dunes', 'Rocky Desert', 'Frozen Plains', 'Frozen Crevasses', 'Frozen Mountains', 'Frozen Hills', 'Savanna', 'Swamp', 'Craters', 'Tropical Forest', 'Wetlands', 'Hills', 'Mountains', 'Deciduous Forest', 'Sandy Desert', 'Coniferous Forest', 'Plateau', 'Frozen Craters'}

## Contributing

Contributions are welcome! Please submit pull requests or open issues to help improve the project.

## License

This project is licensed under the MIT License.