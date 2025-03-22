import requests
from lxml import html
import json
import re
from datetime import datetime

def get_current_tournaments():
    """
    Fetches the current tennis tournaments from the ESPN schedule page.
    
    Returns:
        list: List of dictionaries with tournament name, url, and dates
    """
    url = "https://www.espn.com/tennis/schedule"
    
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
        print(f"Fetching tournaments from {url}...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Parse the HTML with lxml
        tree = html.fromstring(response.content)
        
        # Find the section with current tournaments
        # Look for a title element that indicates "Current Tournaments"
        current_tournaments_section = None
        tournament_links = []  # Initialize this variable outside the conditional blocks
        
        section_headers = tree.xpath('//div[contains(@class, "Table__Title")]')
        
        for header in section_headers:
            if "Current" in header.text_content():
                # Found the Current Tournaments section
                current_tournaments_section = header.getparent().getparent()
                break
        
        if not current_tournaments_section:
            # Try alternative approach using the provided XPath pattern
            print("Trying alternative approach to find current tournaments...")
            tournament_links = tree.xpath('//*[@id="fittPageContainer"]/div[2]/div[2]/div/div/div[1]/section/div/div[4]/div/div/div[2]/div/div[2]/table/tbody/tr/td[2]/div/a')
            
            if not tournament_links:
                # One more attempt with a more general selector
                tournament_links = tree.xpath('//div[contains(@class, "Table__TBODY")]//a[contains(@href, "/tennis/")]')
        else:
            # Found the section, now get all tournament links within it
            tournament_links = current_tournaments_section.xpath('.//tbody//a[contains(@href, "/tennis/")]')
        
        if not tournament_links:
            print("No tournament links found.")
            return {}
        
        tournaments = {}
        for i, link in enumerate(tournament_links, 1):
            tournament_name = link.text_content().strip()
            href = link.get('href')
            
            # Skip player links - they contain "/player/" in the URL
            if href and "/player/" in href:
                continue
                
            # Skip links that don't contain "tournament" or "eventId" - they're likely not tournament links
            if href and not ("/tournament/" in href or "/eventId/" in href):
                continue
            
            # Try to find date information
            # This might be in a nearby cell
            tr_element = link.getparent()
            while tr_element is not None and tr_element.tag != 'tr':
                tr_element = tr_element.getparent()
            
            date_info = "Unknown Date"
            if tr_element is not None:
                date_cells = tr_element.xpath('./td[contains(@class, "date")]')
                if date_cells:
                    date_info = date_cells[0].text_content().strip()
            
            # Process the tournament URL to extract useful information
            tournament_id = None
            if href:
                # Extract tournament ID from URL if available
                id_match = re.search(r'eventId/([^/]+)', href)
                if id_match:
                    tournament_id = id_match.group(1)
            
            # Get today's date in the format YYYYMMDD for creating a scoreboard URL
            today = datetime.now().strftime("%Y%m%d")
            
            # Construct a scoreboard URL
            scoreboard_url = None
            if tournament_id:
                scoreboard_url = f"https://www.espn.com/tennis/scoreboard/tournament/_/eventId/{tournament_id}/competitionType/1/date/{today}"
            else:
                # If we couldn't extract a tournament ID but the URL contains "tournament", it's likely a valid tournament URL
                if href and "/tournament/" in href:
                    # Check if URL already has a date parameter
                    if "/date/" not in href:
                        # Add today's date to the URL
                        if href.endswith("/"):
                            scoreboard_url = f"{href}date/{today}"
                        else:
                            scoreboard_url = f"{href}/date/{today}"
                    else:
                        # URL already has a date, use it as is
                        scoreboard_url = href
            
            tournaments[f"tournament_{i}"] = {
                "name": tournament_name,
                "dates": date_info,
                "tournament_id": tournament_id,
                "original_url": href,
                "scoreboard_url": scoreboard_url
            }
        
        return tournaments
        
    except requests.exceptions.RequestException as e:
        print(f"Error accessing ESPN schedule: {e}")
        return {}
    except Exception as e:
        print(f"Error processing tournament data: {e}")
        return {}

def create_tournament_dict():
    """
    Creates a formatted dictionary of current tournaments.
    
    Returns:
        dict: Dictionary with tournament information
    """
    tournaments = get_current_tournaments()
    
    # If no tournaments were found, return an empty dict
    if not tournaments:
        return {"error": "No tournaments found"}
    
    # Format the output dictionary
    result = {}
    
    # Add general information
    result["tournament_count"] = len(tournaments)
    result["fetch_date"] = datetime.now().strftime("%Y-%m-%d")
    result["tournaments"] = tournaments
    
    return result

# Example usage
if __name__ == "__main__":
    tournament_dict = create_tournament_dict()
    print(json.dumps(tournament_dict, indent=2))
    
    # Optionally save to file
    with open("tennis_tournaments.json", "w") as f:
        json.dump(tournament_dict, f, indent=2)
    print("\nTournament data saved to tennis_tournaments.json")


print(get_current_tournaments())