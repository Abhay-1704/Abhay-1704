import os
import requests
import json

USERNAME = "Abhay-1704"
TOKEN = os.getenv("GITHUB_TOKEN")  # Get token from environment variable

if not TOKEN:
    raise Exception("❌ GITHUB_TOKEN environment variable not set!")

API_URL = "https://api.github.com/graphql"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

QUERY = """
{
  user(login: "%s") {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            color
            contributionCount
          }
        }
      }
    }
  }
}
""" % USERNAME

def get_github_color(contribution_count):
    if contribution_count == 0:
        return "#151B23"
    elif 1 <= contribution_count <= 4:
        return "#033A16"
    elif 5 <= contribution_count <= 9:
        return "#196C2E"
    elif 10 <= contribution_count <= 14:
        return "#2EA043"
    else:
        return "#56D364"

def fetch_contributions():
    res = requests.post(API_URL, json={'query': QUERY}, headers=HEADERS)
    if res.status_code != 200:
        raise Exception(f"GitHub API Error: {res.status_code} - {res.text}")
    data = res.json()

    weeks = data['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
    grid = []

    # Ensure full 7x52 grid (some weeks may not have 7 days)
    for col in range(53):  # 52 weeks
        week = weeks[col] if col < len(weeks) else {'contributionDays': []}
        days = week['contributionDays']

        for row in range(7):  # 7 days per week
            if row < len(days):
                count = days[row]['contributionCount']
                color = get_github_color(count)
            else:
                color = "#151B23"  # default light gray for missing days

            grid.append({
                'x': col * 14,
                'y': row * 14 + 20,
                'color': color
            })

    return grid

def build_svg(bricks):
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="740" height="200" viewBox="0 0 740 200" xmlns="http://www.w3.org/2000/svg">
  <style>
    rect {{ rx: 2; ry: 2; }}
  </style>
'''

    # Draw each brick
    for brick in bricks:
        svg += f'<rect x="{brick["x"]}" y="{brick["y"]}" width="12" height="12" fill="{brick["color"]}" />\n'

    svg += '</svg>'
    return svg

def main():
    print("📄 Fetching contributions...")
    bricks = fetch_contributions()

    print("🧱 Building SVG...")
    svg_code = build_svg(bricks)

    path = "brickbreaker.svg"
    with open(path, "w") as f:
        f.write(svg_code)

    print(f"✅ SVG generated: {path}")

if __name__ == "__main__":
    main()