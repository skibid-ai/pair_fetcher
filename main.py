import requests
from lxml import html
import json
import re

def get_all_espn_tennis_tabs_links(url):
    """
    Extract all links from tennis tabs/sections in the fittPageContainer 
    using a dynamic pattern-based approach and organizes players into match pairs.
    
    Args:
        url (str): The ESPN URL to scrape
    
    Returns:
        dict: Dictionary with tournament info, links, and match pairs
    """
    # Add headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        # Get the page content
        print(f"Fetching data from {url}...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Parse the HTML with lxml
        tree = html.fromstring(response.content)
        
        # Extract tournament name using the specific XPath
        tournament_xpath = '//*[@id="fittPageContainer"]/div[2]/div[2]/div/div/div[1]/div/section/div/div[1]/div/h1'
        tournament_elements = tree.xpath(tournament_xpath)
        tournament_name = tournament_elements[0].text_content().strip() if tournament_elements else "Unknown Tournament"
        
        # Fallback to a more general selector if the specific XPath doesn't work
        if not tournament_elements:
            print("Tournament name not found with specific XPath, trying alternative...")
            tournament_elements = tree.xpath('//div[contains(@class, "ScoreboardHeader__Name")]')
            tournament_name = tournament_elements[0].text_content().strip() if tournament_elements else "Unknown Tournament"
            
        # Extract date from the URL (format YYYYMMDD)
        date_match = re.search(r'date/(\d{8})', url)
        date_str = "Unknown Date"
        if date_match:
            # Convert from YYYYMMDD to YYYY-MM-DD format
            date_raw = date_match.group(1)
            try:
                date_str = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
            except Exception as e:
                print(f"Error formatting date: {e}")
                date_str = date_raw
        
        # Locate the main container first
        container_xpath = '//*[@id="fittPageContainer"]/div[2]/div[2]/div/div/div[1]/div/div/section/div/div[2]'
        container = tree.xpath(container_xpath)
        
        if not container:
            print("Main container not found. Website structure may have changed.")
            return {"error": "Main container not found"}
        
        # Find all div elements that have ul/li/a structure inside the container
        # This is more flexible than hard-coded XPaths
        all_links = []
        
        # First approach: look for the pattern div/div/ul/li/a
        tabs_divs = tree.xpath(f"{container_xpath}/div")
        
        print(f"Found {len(tabs_divs)} potential tab divs")
        
        for div_index, div in enumerate(tabs_divs, 1):
            # Check if this div contains the list of links we're looking for
            link_elements = div.xpath('./div/ul/li/a')
            
            if not link_elements:
                # Try alternative structure
                link_elements = div.xpath('./ul/li/a')
            
            for li_index, link in enumerate(link_elements, 1):
                text = link.text_content().strip()
                href = link.get('href')
                
                # Generate the XPath for this element relative to the page
                xpath = f"{container_xpath}/div[{div_index}]/div/ul/li[{li_index}]/a"
                alt_xpath = f"{container_xpath}/div[{div_index}]/ul/li[{li_index}]/a"
                
                # Determine which XPath is valid by checking if element exists
                correct_xpath = xpath if tree.xpath(xpath) else alt_xpath
                
                all_links.append({
                    "section": div_index,
                    "index": li_index,
                    "text": text,
                    "href": href,
                    "xpath": correct_xpath
                })
        
        # If we didn't find links with the above approach, try a more general search
        if not all_links:
            print("Using alternative search method...")
            # Find all links within the container that match our pattern
            all_as = tree.xpath(f"{container_xpath}//a")
            
            for i, link in enumerate(all_as):
                # Only include links that are likely to be tab links (typically short text, not empty)
                text = link.text_content().strip()
                if text and len(text) < 100:  # Arbitrary limit to filter out non-tab links
                    href = link.get('href')
                    # Get the full XPath for this link
                    xpath = tree.getpath(link)
                    all_links.append({
                        "index": i+1,
                        "text": text,
                        "href": href,
                        "xpath": xpath
                    })
        
        # Now create player pairs from the list of player names
        player_names = [link['text'] for link in all_links]
        formatted_matches = create_player_pairs(player_names, tournament_name, date_str)
        
        return {
            "tournament": tournament_name,
            "tournament_date": date_str,
            "links_count": len(all_links),
            "links": all_links,
            "matches": formatted_matches
        }
        
    except requests.exceptions.RequestException as e:
        print(f"Error accessing ESPN: {e}")
        return {"error": f"Request error: {str(e)}"}
    except Exception as e:
        print(f"Error processing data: {e}")
        return {"error": f"Processing error: {str(e)}"}

def create_player_pairs(player_names, tournament_name, tournament_date):
    """
    Takes a flat list of player names and returns them as pairs
    where each pair represents a match, along with tournament info.
    
    Args:
        player_names (list): List of player names
        tournament_name (str): Name of the tournament
        tournament_date (str): Date of the tournament (YYYY-MM-DD)
    
    Returns:
        dict: Dictionary with tournament info and match pairs
    """
    if len(player_names) % 2 != 0:
        print("Warning: Odd number of players. One player will be without a pair.")
    
    # Create the base structure with tournament info
    result = {
        "Tournament Name": tournament_name,
        "Tournament Day": tournament_date
    }
    
    # Group players into pairs (matches)
    for i in range(0, len(player_names), 2):
        match_id = i // 2 + 1
        
        # Handle the case where there might be an odd number of players
        if i + 1 < len(player_names):
            result[f"match_{match_id}"] = {
                "player1": player_names[i],
                "player2": player_names[i + 1]
            }
        else:
            result[f"match_{match_id}"] = {
                "player1": player_names[i],
                "player2": "N/A"  # No opponent
            }
    
    return result

if __name__ == "__main__":
    # Use the URL provided
    url = "https://www.espn.com/tennis/scoreboard/tournament/_/eventId/713-2025/competitionType/1/date/20250322"
    
    result = get_all_espn_tennis_tabs_links(url)
    
    # Print the results
    if "error" in result:
        print(f"Failed to get data: {result['error']}")
    else:
        print(f"\nTournament: {result['tournament']}")
        print(f"Found {result['links_count']} links")
        
        print("\nExtracted Links:")
        for link in result['links']:
            print(f"  Text: {link['text']}")
        
        print("\nTournament Information:")
        print(f"Tournament: {result['matches']['Tournament Name']}")
        print(f"Date: {result['matches']['Tournament Day']}")
        
        print("\nPlayer Matches:")
        print("-" * 40)
        # Skip the tournament info keys when printing matches
        for key, value in result['matches'].items():
            if key not in ["Tournament Name", "Tournament Day"]:
                print(f"{key}: {value['player1']} vs {value['player2']}")
        
        # Export the matches to a JSON file
        with open("tennis_matches.json", "w") as f:
            json.dump(result['matches'], f, indent=2)
        print("\nMatches exported to tennis_matches.json in the requested format")