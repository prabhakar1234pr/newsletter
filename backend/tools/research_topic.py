"""Step 1: Web research via topic/subtopic RSS feeds + newspaper4k.

Fetches articles from curated RSS feeds matching the requested topic and
optional sub-topic, filters by keyword, and extracts full article text
using newspaper4k. Returns the same JSON structure as the original Firecrawl
implementation so all downstream tools are unaffected.

Usage:
    uv run python tools/research_topic.py --topic "AI & Technology" --num-results 5
    uv run python tools/research_topic.py --topic "Sports" --sub-genre "Cricket" --num-results 5
    uv run python tools/research_topic.py --topic "Cinema" --sub-genre "Telugu Cinema" --num-results 5
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
from dotenv import load_dotenv
from newspaper import Article
from newspaper.exceptions import ArticleException

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / ".tmp" / "research_raw.json"

# ---------------------------------------------------------------------------
# Topic / Sub-topic taxonomy
#
# TOPICS_CONFIG is the single source of truth for topics + sub-topics.
# Exported as JSON for the frontend to consume.
#
# SUBTOPIC_RSS_FEEDS maps sub-topic label → list of RSS feed URLs.
# TOPIC_RSS_FEEDS maps top-level topic → list of RSS feed URLs (used when
#   no sub-topic is specified).
# ---------------------------------------------------------------------------

TOPICS_CONFIG: dict[str, list[str]] = {
    "AI & Technology": [
        "Large Language Models",
        "ChatGPT & OpenAI",
        "Claude & Anthropic",
        "Gemini & Google AI",
        "Open Source AI",
        "AI Agents & Automation",
        "Robotics & Automation",
        "Computer Vision",
        "Generative AI",
        "AI in Healthcare",
        "AI in Education",
        "AI in Finance",
        "AI Ethics & Policy",
        "AI Regulation",
        "Cybersecurity",
        "Data Privacy & GDPR",
        "Hacking & Data Breaches",
        "Cloud Computing",
        "AWS & Amazon",
        "Google Cloud",
        "Microsoft Azure",
        "Semiconductors & Chips",
        "Quantum Computing",
        "Self-Driving Cars",
        "Blockchain & Web3",
        "AR & VR",
        "5G & Connectivity",
        "Smart Devices & IoT",
        "Tech Startups",
        "Tech Layoffs & Jobs",
        "Developer Tools",
        "Open Source Software",
        "Tech Policy & Antitrust",
    ],
    "Geopolitics": [
        "Middle East",
        "Israel-Palestine Conflict",
        "Iran",
        "Russia-Ukraine War",
        "US Politics",
        "US-China Relations",
        "US-Russia Relations",
        "NATO & Defense",
        "Europe",
        "UK Politics",
        "France",
        "Germany",
        "Asia Pacific",
        "China",
        "India",
        "India-Pakistan Relations",
        "Japan",
        "South Korea",
        "North Korea",
        "Southeast Asia",
        "Africa",
        "Latin America",
        "Climate Diplomacy",
        "United Nations",
        "Trade & Tariffs",
        "Sanctions",
        "Nuclear Arms",
        "Terrorism & Extremism",
        "Refugee & Migration Crisis",
        "Human Rights",
        "Espionage & Intelligence",
    ],
    "Cinema": [
        "Hollywood",
        "Bollywood",
        "Telugu Cinema",
        "Tamil Cinema",
        "Malayalam Cinema",
        "Kannada Cinema",
        "Marathi Cinema",
        "Bengali Cinema",
        "Korean Cinema",
        "Chinese Cinema",
        "Japanese Cinema",
        "French Cinema",
        "Independent Films",
        "Documentaries",
        "Animation",
        "Horror Films",
        "Action & Blockbusters",
        "OTT & Streaming",
        "Netflix",
        "Amazon Prime Video",
        "Disney+ & Marvel",
        "Apple TV+ & HBO Max",
        "Oscars & Academy Awards",
        "Cannes Film Festival",
        "BAFTA & Golden Globes",
        "Box Office News",
        "Movie Reviews",
        "Upcoming Releases",
        "Celebrity News",
        "Director Spotlights",
        "Remakes & Sequels",
    ],
    "Sports": [
        "Cricket",
        "Test Cricket",
        "IPL",
        "ICC World Cup",
        "Football",
        "Premier League",
        "La Liga",
        "UEFA Champions League",
        "FIFA World Cup",
        "Formula 1",
        "NASCAR & Motorsports",
        "Basketball",
        "NBA",
        "WNBA",
        "Tennis",
        "Wimbledon",
        "US Open Tennis",
        "French Open",
        "Australian Open",
        "Golf & PGA Tour",
        "Rugby",
        "Olympics",
        "Swimming",
        "Athletics & Track",
        "Boxing",
        "MMA & UFC",
        "Ice Hockey",
        "Baseball & MLB",
        "NFL & American Football",
        "Kabaddi",
        "Badminton",
        "Table Tennis",
        "Esports",
    ],
    "Business & Finance": [
        "Stock Markets",
        "Wall Street & NYSE",
        "NASDAQ & Tech Stocks",
        "Indian Stock Market",
        "Global Markets",
        "Startups & VC",
        "Series A & Fundraising",
        "Unicorns & IPOs",
        "M&A & Acquisitions",
        "Cryptocurrency",
        "Bitcoin",
        "Ethereum",
        "Altcoins & DeFi",
        "NFTs",
        "Economy & Policy",
        "US Economy",
        "Indian Economy",
        "Global Economy",
        "Interest Rates & Fed",
        "Inflation",
        "Oil & Energy Markets",
        "Real Estate",
        "Retail & E-commerce",
        "Banking & Finance",
        "FinTech",
        "Insurance",
        "Supply Chain",
        "Layoffs & Corporate News",
        "ESG & Sustainability",
        "Automotive Industry",
        "Aerospace & Defense",
    ],
    "Science & Environment": [
        "Space Exploration",
        "NASA",
        "SpaceX & Private Space",
        "Mars & Moon Missions",
        "Astronomy & Telescopes",
        "Climate & Environment",
        "Climate Change",
        "Carbon & Emissions",
        "Renewable Energy",
        "Solar & Wind Energy",
        "Biodiversity & Wildlife",
        "Oceans & Marine Life",
        "Deforestation",
        "Extreme Weather",
        "Medicine & Biology",
        "Cancer Research",
        "Vaccines & Immunology",
        "Genetics & Genomics",
        "Neuroscience",
        "Drug Discovery",
        "Disease Outbreaks",
        "Physics & Astronomy",
        "Particle Physics",
        "Nuclear Energy",
        "Quantum Physics",
        "Archaeology",
        "Paleontology",
        "AI in Science",
        "Marine Science",
        "Earthquakes & Geology",
        "Meteorology",
    ],
    "Health & Wellness": [
        "Mental Health",
        "Anxiety & Depression",
        "ADHD & Autism",
        "Mindfulness & Meditation",
        "Therapy & Counseling",
        "Fitness & Nutrition",
        "Weight Loss & Diet",
        "Exercise & Gym",
        "Running & Marathons",
        "Yoga & Pilates",
        "Sleep & Recovery",
        "Sports Nutrition",
        "Vegan & Plant-Based Diet",
        "Medical Research",
        "Cancer Treatment",
        "Heart Health & Cardiology",
        "Diabetes",
        "Women's Health",
        "Men's Health",
        "Children's Health",
        "Senior Health & Aging",
        "Gut Health",
        "Skin Health",
        "Dental Health",
        "COVID & Respiratory Health",
        "Addiction & Recovery",
        "Alternative Medicine",
        "Healthcare Policy",
        "Global Health & WHO",
    ],
    "Gaming & Esports": [
        "Console Gaming",
        "PlayStation",
        "Xbox & Game Pass",
        "Nintendo Switch",
        "PC Gaming",
        "Mobile Gaming",
        "iOS Games",
        "Android Games",
        "Pokémon GO & AR Games",
        "Esports",
        "League of Legends",
        "Valorant",
        "CS2 & Counter-Strike",
        "Dota 2",
        "Fortnite & Battle Royale",
        "Call of Duty",
        "FIFA & Sports Games",
        "RPG & Open World",
        "Horror & Indie Games",
        "Game Reviews & Releases",
        "Game Development",
        "Gaming Hardware & GPUs",
        "VR Gaming",
        "Game Streaming & Twitch",
        "YouTube Gaming",
        "Nintendo & Pokémon News",
        "Game Industry Business",
        "Gaming Controversies",
    ],
    "Culture & Entertainment": [
        "Music",
        "Pop Music",
        "Hip-Hop & Rap",
        "Rock & Metal",
        "K-Pop",
        "Bollywood Music",
        "Music Awards & Grammys",
        "Music Festivals & Concerts",
        "Fashion",
        "High Fashion & Runway",
        "Street Style",
        "Sustainable Fashion",
        "Celebrity Style",
        "Food & Travel",
        "Fine Dining & Restaurants",
        "Street Food & Food Culture",
        "Travel Destinations",
        "Budget Travel",
        "Books & Literature",
        "Fiction & Novels",
        "Non-Fiction & Biography",
        "Fantasy & Sci-Fi",
        "Television & TV Shows",
        "Reality TV",
        "Anime & Manga",
        "Comedy & Stand-Up",
        "Art & Museums",
        "Photography",
        "Theatre & Stage",
        "Celebrity News",
    ],
    "Education & Careers": [
        "EdTech",
        "Online Learning & MOOCs",
        "Coding & Programming Education",
        "AI in Education",
        "K-12 Education",
        "Special Education",
        "Early Childhood Education",
        "Higher Education",
        "Universities & Colleges",
        "MBA & Business School",
        "Medical Education",
        "Engineering & STEM",
        "Liberal Arts",
        "Study Abroad",
        "Scholarships & Financial Aid",
        "Job Market & Careers",
        "Tech Jobs",
        "Remote Work",
        "Internships & Graduate Programs",
        "MBA Careers",
        "Government & Public Sector Jobs",
        "Healthcare Careers",
        "Creative Careers",
        "Entrepreneurship & Freelancing",
        "Career Development",
        "Skills & Certifications",
        "Resume & Interview Tips",
        "Workplace Culture",
        "Diversity & Inclusion",
        "Future of Work",
    ],
}


# ---------------------------------------------------------------------------
# Sub-topic → RSS feeds
# ---------------------------------------------------------------------------

SUBTOPIC_RSS_FEEDS: dict[str, list[str]] = {

    # ── AI & Technology ─────────────────────────────────────────────────────
    "ChatGPT & OpenAI": [
        "https://venturebeat.com/category/ai/feed/",
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
    ],
    "Claude & Anthropic": [
        "https://venturebeat.com/category/ai/feed/",
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
    ],
    "Gemini & Google AI": [
        "https://venturebeat.com/category/ai/feed/",
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
    ],
    "Open Source AI": [
        "https://venturebeat.com/category/ai/feed/",
        "https://techcrunch.com/feed/",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://www.therobotreport.com/feed/",
    ],
    "AI Ethics & Policy": [
        "https://venturebeat.com/category/ai/feed/",
        "https://techcrunch.com/feed/",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://www.theguardian.com/technology/artificialintelligenceai/rss",
    ],
    "AI Regulation": [
        "https://venturebeat.com/category/ai/feed/",
        "https://techcrunch.com/feed/",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://www.theguardian.com/technology/artificialintelligenceai/rss",
    ],
    "Hacking & Data Breaches": [
        "https://feeds.feedburner.com/TheHackersNews",
        "https://www.bleepingcomputer.com/feed/",
        "https://krebsonsecurity.com/feed/",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
    ],
    "Semiconductors & Chips": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://venturebeat.com/feed/",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
    ],
    "Self-Driving Cars": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://venturebeat.com/feed/",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
    ],
    "Large Language Models": [
        "https://venturebeat.com/category/ai/feed/",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/",
    ],
    "Robotics & Automation": [
        "https://www.therobotreport.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://techcrunch.com/feed/",
    ],
    "Cybersecurity": [
        "https://feeds.feedburner.com/TheHackersNews",
        "https://krebsonsecurity.com/feed/",
        "https://www.bleepingcomputer.com/feed/",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
    ],
    "Cloud Computing": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://venturebeat.com/category/cloud/feed/",
    ],
    "Tech Startups": [
        "https://techcrunch.com/feed/",
        "https://venturebeat.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
    ],

    # ── Geopolitics ─────────────────────────────────────────────────────────
    "Middle East": [
        "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
    "US Politics": [
        "https://feeds.bbci.co.uk/news/politics/rss.xml",
        "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
    "Europe": [
        "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
    "Asia Pacific": [
        "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
    ],
    "India": [
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://timesofindia.indiatimes.com/india/rssfeeds/296589292.cms",
        "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],

    # ── Geopolitics ─────────────────────────────────────────────────────────
    "Israel-Palestine Conflict": [
        "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    ],
    "Iran": [
        "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
    "Russia-Ukraine War": [
        "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    ],
    "US-China Relations": [
        "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
        "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
    "UK Politics": [
        "https://feeds.bbci.co.uk/news/politics/rss.xml",
        "https://www.theguardian.com/politics/rss",
        "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
    ],
    "China": [
        "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    ],
    "North Korea": [
        "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
    "Human Rights": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.theguardian.com/world/rss",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    ],

    # ── Cinema ──────────────────────────────────────────────────────────────
    "Hollywood": [
        "https://variety.com/feed/",
        "https://www.hollywoodreporter.com/feed/",
        "https://deadline.com/feed/",
        "https://timesofindia.indiatimes.com/entertainment/english/rssfeeds/3.cms",
    ],
    "Bollywood": [
        "https://timesofindia.indiatimes.com/entertainment/hindi/rssfeeds/8201992.cms",
        "https://variety.com/feed/",
        "https://www.hollywoodreporter.com/feed/",
    ],
    "Tamil Cinema": [
        "https://timesofindia.indiatimes.com/entertainment/regional/rssfeeds/2297104512.cms",
        "https://timesofindia.indiatimes.com/entertainment/tamil/rssfeeds/1081479906.cms",
        "https://www.123telugu.com/feed/",
    ],
    "Malayalam Cinema": [
        "https://timesofindia.indiatimes.com/entertainment/regional/rssfeeds/2297104512.cms",
        "https://timesofindia.indiatimes.com/entertainment/malayalam/rssfeeds/1081479906.cms",
    ],
    "Kannada Cinema": [
        "https://timesofindia.indiatimes.com/entertainment/regional/rssfeeds/2297104512.cms",
    ],
    "Korean Cinema": [
        "https://variety.com/feed/",
        "https://deadline.com/feed/",
        "https://www.hollywoodreporter.com/feed/",
    ],
    "Animation": [
        "https://variety.com/feed/",
        "https://deadline.com/feed/",
        "https://www.hollywoodreporter.com/feed/",
        "https://feeds.ign.com/ign/all",
    ],
    "Netflix": [
        "https://variety.com/feed/",
        "https://deadline.com/feed/",
        "https://www.hollywoodreporter.com/feed/",
        "https://timesofindia.indiatimes.com/entertainment/english/rssfeeds/3.cms",
    ],
    "Amazon Prime Video": [
        "https://variety.com/feed/",
        "https://deadline.com/feed/",
        "https://www.hollywoodreporter.com/feed/",
    ],
    "Disney+ & Marvel": [
        "https://variety.com/feed/",
        "https://deadline.com/feed/",
        "https://www.hollywoodreporter.com/feed/",
        "https://feeds.ign.com/ign/all",
    ],
    "Oscars & Academy Awards": [
        "https://variety.com/feed/",
        "https://deadline.com/feed/",
        "https://www.hollywoodreporter.com/feed/",
    ],
    "Telugu Cinema": [
        "https://www.123telugu.com/feed/",
        "https://timesofindia.indiatimes.com/entertainment/telugu/moviereviews/rssfeeds/2286976241.cms",
        "https://timesofindia.indiatimes.com/entertainment/telugu/rssfeeds/1081479906.cms",
        "https://timesofindia.indiatimes.com/entertainment/regional/rssfeeds/2297104512.cms",
    ],
    "Korean Cinema": [
        "https://variety.com/feed/",
        "https://www.hollywoodreporter.com/feed/",
        "https://deadline.com/feed/",
    ],
    "OTT & Streaming": [
        "https://variety.com/feed/",
        "https://deadline.com/feed/",
        "https://www.hollywoodreporter.com/feed/",
        "https://timesofindia.indiatimes.com/entertainment/english/rssfeeds/3.cms",
    ],

    # ── Sports ──────────────────────────────────────────────────────────────
    "IPL": [
        "https://timesofindia.indiatimes.com/sports/cricket/rssfeeds/4719148.cms",
        "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
        "https://feeds.bbci.co.uk/sport/cricket/rss.xml",
    ],
    "ICC World Cup": [
        "https://timesofindia.indiatimes.com/sports/cricket/rssfeeds/4719148.cms",
        "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
        "https://feeds.bbci.co.uk/sport/cricket/rss.xml",
    ],
    "Premier League": [
        "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "https://www.espn.com/espn/rss/soccer/news",
        "https://timesofindia.indiatimes.com/sports/rssfeeds/4719161.cms",
    ],
    "La Liga": [
        "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "https://www.espn.com/espn/rss/soccer/news",
    ],
    "UEFA Champions League": [
        "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "https://www.espn.com/espn/rss/soccer/news",
    ],
    "FIFA World Cup": [
        "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "https://www.espn.com/espn/rss/soccer/news",
        "https://timesofindia.indiatimes.com/sports/rssfeeds/4719161.cms",
    ],
    "NASCAR & Motorsports": [
        "https://www.espn.com/espn/rss/rpm/news",
        "https://www.autosport.com/rss/feed/all",
        "https://www.espn.com/espn/rss/news",
    ],
    "NBA": [
        "https://www.espn.com/espn/rss/nba/news",
        "https://feeds.bbci.co.uk/sport/basketball/rss.xml",
        "https://www.espn.com/espn/rss/news",
    ],
    "Wimbledon": [
        "https://feeds.bbci.co.uk/sport/tennis/rss.xml",
        "https://www.espn.com/espn/rss/tennis/news",
    ],
    "Golf & PGA Tour": [
        "https://www.espn.com/espn/rss/golf/news",
        "https://feeds.bbci.co.uk/sport/golf/rss.xml",
        "https://www.espn.com/espn/rss/news",
    ],
    "Olympics": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.espn.com/espn/rss/news",
        "https://timesofindia.indiatimes.com/sports/rssfeeds/4719161.cms",
    ],
    "Boxing": [
        "https://www.espn.com/espn/rss/boxing/news",
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.espn.com/espn/rss/news",
    ],
    "MMA & UFC": [
        "https://www.espn.com/espn/rss/mma/news",
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.espn.com/espn/rss/news",
    ],
    "Baseball & MLB": [
        "https://www.espn.com/espn/rss/mlb/news",
        "https://www.espn.com/espn/rss/news",
    ],
    "NFL & American Football": [
        "https://www.espn.com/espn/rss/nfl/news",
        "https://www.espn.com/espn/rss/news",
        "https://feeds.bbci.co.uk/sport/american-football/rss.xml",
    ],
    "Cricket": [
        "https://timesofindia.indiatimes.com/sports/cricket/rssfeeds/4719148.cms",
        "https://feeds.bbci.co.uk/sport/cricket/rss.xml",
        "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
        "https://www.espn.com/espn/rss/news",
    ],
    "Football": [
        "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "https://www.espn.com/espn/rss/soccer/news",
        "https://timesofindia.indiatimes.com/sports/rssfeeds/4719161.cms",
        "https://www.espn.com/espn/rss/news",
    ],
    "Formula 1": [
        "https://feeds.bbci.co.uk/sport/formula1/rss.xml",
        "https://www.espn.com/espn/rss/rpm/news",
        "https://www.autosport.com/rss/feed/all",
        "https://www.espn.com/espn/rss/news",
    ],
    "Basketball": [
        "https://www.espn.com/espn/rss/nba/news",
        "https://feeds.bbci.co.uk/sport/basketball/rss.xml",
        "https://www.espn.com/espn/rss/news",
    ],
    "Tennis": [
        "https://feeds.bbci.co.uk/sport/tennis/rss.xml",
        "https://www.espn.com/espn/rss/tennis/news",
        "https://timesofindia.indiatimes.com/sports/rssfeeds/4719161.cms",
        "https://www.espn.com/espn/rss/news",
    ],

    # ── Business & Finance ───────────────────────────────────────────────────
    "Bitcoin": [
        "https://feeds.feedburner.com/CoinDesk",
        "https://cointelegraph.com/rss",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
    ],
    "Ethereum": [
        "https://feeds.feedburner.com/CoinDesk",
        "https://cointelegraph.com/rss",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
    ],
    "IPOs": [
        "https://techcrunch.com/feed/",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.theguardian.com/business/rss",
    ],
    "M&A & Acquisitions": [
        "https://techcrunch.com/feed/",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.theguardian.com/business/rss",
    ],
    "Oil & Energy Markets": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://feeds.bbci.co.uk/news/business/economy/rss.xml",
        "https://www.theguardian.com/environment/energy/rss",
    ],
    "Real Estate": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://timesofindia.indiatimes.com/business/rssfeeds/1898055.cms",
        "https://www.theguardian.com/business/realestate/rss",
    ],
    "FinTech": [
        "https://techcrunch.com/feed/",
        "https://venturebeat.com/feed/",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
    ],
    "ESG & Sustainability": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.theguardian.com/environment/rss",
        "https://www.theguardian.com/business/rss",
    ],
    "Stock Markets": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://timesofindia.indiatimes.com/business/rssfeeds/1898055.cms",
        "https://www.theguardian.com/business/rss",
        "https://feeds.bbci.co.uk/news/business/economy/rss.xml",
    ],
    "Startups & VC": [
        "https://techcrunch.com/feed/",
        "https://venturebeat.com/feed/",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.theguardian.com/business/rss",
    ],
    "Cryptocurrency": [
        "https://feeds.feedburner.com/CoinDesk",
        "https://cointelegraph.com/rss",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://timesofindia.indiatimes.com/technology/rssfeeds/2286831.cms",
    ],
    "Economy & Policy": [
        "https://feeds.bbci.co.uk/news/business/economy/rss.xml",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://timesofindia.indiatimes.com/business/rssfeeds/1898055.cms",
        "https://www.theguardian.com/business/economics/rss",
    ],

    # ── Science & Environment ────────────────────────────────────────────────
    "NASA": [
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "https://spacenews.com/feed/",
        "https://www.space.com/feeds/all",
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    ],
    "SpaceX & Private Space": [
        "https://spacenews.com/feed/",
        "https://www.space.com/feeds/all",
        "https://techcrunch.com/feed/",
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    ],
    "Mars & Moon Missions": [
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "https://spacenews.com/feed/",
        "https://www.space.com/feeds/all",
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    ],
    "Climate Change": [
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://www.theguardian.com/environment/climate-crisis/rss",
        "https://www.theguardian.com/environment/rss",
    ],
    "Renewable Energy": [
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://www.theguardian.com/environment/renewableenergy/rss",
        "https://techcrunch.com/feed/",
    ],
    "Vaccines & Immunology": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://www.sciencedaily.com/rss/top/health_medicine.xml",
        "https://www.theguardian.com/society/health/rss",
    ],
    "Genetics & Genomics": [
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://www.sciencedaily.com/rss/top/science.xml",
        "https://www.theguardian.com/science/rss",
    ],
    "Disease Outbreaks": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://www.sciencedaily.com/rss/top/health_medicine.xml",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    ],
    "Nuclear Energy": [
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.theguardian.com/environment/energy/rss",
    ],
    "Space Exploration": [
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "https://spacenews.com/feed/",
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://www.space.com/feeds/all",
    ],
    "Climate & Environment": [
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://www.theguardian.com/environment/rss",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
    "Medicine & Biology": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://www.sciencedaily.com/rss/top/health_medicine.xml",
        "https://www.theguardian.com/science/rss",
    ],
    "Physics & Astronomy": [
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://www.sciencedaily.com/rss/top/science.xml",
        "https://www.space.com/feeds/all",
        "https://www.theguardian.com/science/rss",
    ],

    # ── Health & Wellness ────────────────────────────────────────────────────
    "Anxiety & Depression": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://www.theguardian.com/society/mentalhealth/rss",
        "https://www.sciencedaily.com/rss/top/health_medicine.xml",
    ],
    "Women's Health": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://www.theguardian.com/lifeandstyle/women/rss",
        "https://www.sciencedaily.com/rss/top/health_medicine.xml",
    ],
    "Heart Health & Cardiology": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://www.sciencedaily.com/rss/top/health_medicine.xml",
        "https://www.theguardian.com/society/health/rss",
    ],
    "Healthcare Policy": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://www.theguardian.com/society/health/rss",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    ],
    "Mental Health": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://www.theguardian.com/society/mentalhealth/rss",
        "https://www.sciencedaily.com/rss/top/health_medicine.xml",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    ],
    "Fitness & Nutrition": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://www.theguardian.com/lifeandstyle/health-and-wellbeing/rss",
        "https://www.sciencedaily.com/rss/top/health_medicine.xml",
    ],
    "Medical Research": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://www.sciencedaily.com/rss/top/health_medicine.xml",
        "https://www.theguardian.com/science/rss",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    ],

    # ── Gaming & Esports ─────────────────────────────────────────────────────
    "PlayStation": [
        "https://feeds.ign.com/ign/all",
        "https://www.eurogamer.net/feed",
        "https://www.gamespot.com/feeds/news/",
        "https://www.theverge.com/rss/index.xml",
    ],
    "Xbox & Game Pass": [
        "https://feeds.ign.com/ign/all",
        "https://www.eurogamer.net/feed",
        "https://www.gamespot.com/feeds/news/",
        "https://www.theverge.com/rss/index.xml",
    ],
    "Nintendo Switch": [
        "https://feeds.ign.com/ign/all",
        "https://www.eurogamer.net/feed",
        "https://www.gamespot.com/feeds/news/",
    ],
    "League of Legends": [
        "https://www.espn.com/espn/rss/esports/news",
        "https://dotesports.com/feed",
        "https://feeds.ign.com/ign/all",
    ],
    "Valorant": [
        "https://www.espn.com/espn/rss/esports/news",
        "https://dotesports.com/feed",
        "https://feeds.ign.com/ign/all",
    ],
    "Fortnite & Battle Royale": [
        "https://feeds.ign.com/ign/all",
        "https://www.eurogamer.net/feed",
        "https://dotesports.com/feed",
    ],
    "Game Reviews & Releases": [
        "https://feeds.ign.com/ign/all",
        "https://www.eurogamer.net/feed",
        "https://www.gamespot.com/feeds/news/",
        "https://www.theverge.com/rss/index.xml",
    ],
    "Gaming Hardware & GPUs": [
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.ign.com/ign/all",
        "https://techcrunch.com/feed/",
    ],
    "Game Streaming & Twitch": [
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/",
        "https://feeds.ign.com/ign/all",
    ],
    "Console Gaming": [
        "https://feeds.ign.com/ign/all",
        "https://www.eurogamer.net/feed",
        "https://www.theverge.com/rss/index.xml",
        "https://www.gamespot.com/feeds/news/",
    ],
    "Mobile Gaming": [
        "https://feeds.ign.com/ign/all",
        "https://toucharcade.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/",
    ],
    "Esports": [
        "https://www.espn.com/espn/rss/esports/news",
        "https://dotesports.com/feed",
        "https://feeds.ign.com/ign/all",
        "https://www.theverge.com/rss/index.xml",
    ],

    # ── Culture & Entertainment ──────────────────────────────────────────────
    "Pop Music": [
        "https://www.theguardian.com/music/rss",
        "https://www.rollingstone.com/music/feed/",
        "https://variety.com/feed/",
    ],
    "Hip-Hop & Rap": [
        "https://www.theguardian.com/music/rss",
        "https://www.rollingstone.com/music/feed/",
        "https://variety.com/feed/",
    ],
    "K-Pop": [
        "https://variety.com/feed/",
        "https://www.hollywoodreporter.com/feed/",
        "https://www.theguardian.com/music/rss",
    ],
    "Bollywood Music": [
        "https://timesofindia.indiatimes.com/entertainment/music/rssfeeds/3707701.cms",
        "https://timesofindia.indiatimes.com/entertainment/hindi/rssfeeds/8201992.cms",
    ],
    "Music Awards & Grammys": [
        "https://variety.com/feed/",
        "https://www.rollingstone.com/music/feed/",
        "https://www.theguardian.com/music/rss",
    ],
    "High Fashion & Runway": [
        "https://www.theguardian.com/fashion/rss",
        "https://variety.com/feed/",
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    ],
    "Travel Destinations": [
        "https://www.theguardian.com/travel/rss",
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    ],
    "Fiction & Novels": [
        "https://www.theguardian.com/books/fiction/rss",
        "https://www.theguardian.com/books/rss",
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    ],
    "Anime & Manga": [
        "https://feeds.ign.com/ign/all",
        "https://www.theguardian.com/culture/rss",
        "https://variety.com/feed/",
    ],
    "Television & TV Shows": [
        "https://variety.com/feed/",
        "https://deadline.com/feed/",
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
        "https://www.hollywoodreporter.com/feed/",
    ],
    "Music": [
        "https://www.theguardian.com/music/rss",
        "https://www.rollingstone.com/music/feed/",
        "https://timesofindia.indiatimes.com/entertainment/music/rssfeeds/3707701.cms",
        "https://variety.com/feed/",
    ],
    "Fashion": [
        "https://www.theguardian.com/fashion/rss",
        "https://variety.com/feed/",
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    ],
    "Food & Travel": [
        "https://www.theguardian.com/food/rss",
        "https://www.theguardian.com/travel/rss",
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    ],
    "Books & Literature": [
        "https://www.theguardian.com/books/rss",
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
        "https://www.theguardian.com/culture/rss",
    ],

    # ── Education & Careers ──────────────────────────────────────────────────
    "Online Learning & MOOCs": [
        "https://techcrunch.com/feed/",
        "https://www.theguardian.com/education/rss",
        "https://feeds.bbci.co.uk/news/education/rss.xml",
    ],
    "Tech Jobs": [
        "https://techcrunch.com/feed/",
        "https://venturebeat.com/feed/",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.theguardian.com/money/work-and-careers/rss",
    ],
    "Remote Work": [
        "https://techcrunch.com/feed/",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.theguardian.com/money/work-and-careers/rss",
    ],
    "Entrepreneurship & Freelancing": [
        "https://techcrunch.com/feed/",
        "https://venturebeat.com/feed/",
        "https://www.theguardian.com/money/work-and-careers/rss",
    ],
    "EdTech": [
        "https://techcrunch.com/feed/",
        "https://venturebeat.com/feed/",
        "https://www.theguardian.com/education/rss",
        "https://feeds.bbci.co.uk/news/education/rss.xml",
    ],
    "Higher Education": [
        "https://www.theguardian.com/education/rss",
        "https://feeds.bbci.co.uk/news/education/rss.xml",
        "https://timesofindia.indiatimes.com/education/rssfeeds/913168846.cms",
    ],
    "Job Market & Careers": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.theguardian.com/money/work-and-careers/rss",
        "https://techcrunch.com/feed/",
        "https://timesofindia.indiatimes.com/business/rssfeeds/1898055.cms",
    ],
}


# ---------------------------------------------------------------------------
# Top-level topic → RSS feeds (fallback when no sub-topic is given)
# ---------------------------------------------------------------------------

TOPIC_RSS_FEEDS: dict[str, list[str]] = {
    "AI & Technology": [
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://venturebeat.com/feed/",
        "https://timesofindia.indiatimes.com/technology/rssfeeds/2286831.cms",
    ],
    "Geopolitics": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://feeds.bbci.co.uk/news/politics/rss.xml",
    ],
    "Cinema": [
        "https://variety.com/feed/",
        "https://deadline.com/feed/",
        "https://www.123telugu.com/feed/",
        "https://timesofindia.indiatimes.com/entertainment/hindi/rssfeeds/8201992.cms",
        "https://timesofindia.indiatimes.com/entertainment/english/rssfeeds/3.cms",
    ],
    "Sports": [
        "https://www.espn.com/espn/rss/news",
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://timesofindia.indiatimes.com/sports/rssfeeds/4719161.cms",
    ],
    "Business & Finance": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://timesofindia.indiatimes.com/business/rssfeeds/1898055.cms",
        "https://www.theguardian.com/business/rss",
        "https://techcrunch.com/feed/",
    ],
    "Science & Environment": [
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://www.theguardian.com/science/rss",
        "https://www.sciencedaily.com/rss/top/science.xml",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    ],
    "Health & Wellness": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://www.theguardian.com/society/health/rss",
        "https://www.sciencedaily.com/rss/top/health_medicine.xml",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    ],
    "Gaming & Esports": [
        "https://feeds.ign.com/ign/all",
        "https://www.theverge.com/rss/index.xml",
        "https://www.eurogamer.net/feed",
        "https://www.gamespot.com/feeds/news/",
    ],
    "Culture & Entertainment": [
        "https://www.theguardian.com/culture/rss",
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
        "https://variety.com/feed/",
        "https://timesofindia.indiatimes.com/entertainment/rssfeeds/1081479906.cms",
    ],
    "Education & Careers": [
        "https://www.theguardian.com/education/rss",
        "https://feeds.bbci.co.uk/news/education/rss.xml",
        "https://techcrunch.com/feed/",
        "https://timesofindia.indiatimes.com/education/rssfeeds/913168846.cms",
    ],
    # Legacy aliases (backwards-compatible with old topic names)
    "AI": [
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://techcrunch.com/feed/",
        "https://venturebeat.com/feed/",
        "https://timesofindia.indiatimes.com/technology/rssfeeds/2286831.cms",
    ],
    "Telugu cinema": [
        "https://www.123telugu.com/feed/",
        "https://timesofindia.indiatimes.com/entertainment/telugu/moviereviews/rssfeeds/2286976241.cms",
        "https://timesofindia.indiatimes.com/entertainment/telugu/rssfeeds/1081479906.cms",
    ],
    "Cricket": [
        "https://timesofindia.indiatimes.com/sports/cricket/rssfeeds/4719148.cms",
        "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
        "https://feeds.bbci.co.uk/sport/cricket/rss.xml",
    ],
    "Crypto": [
        "https://feeds.feedburner.com/CoinDesk",
        "https://cointelegraph.com/rss",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
    ],
    # Fallback
    "_default": [
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://www.espn.com/espn/rss/news",
    ],
}


# ---------------------------------------------------------------------------
# Article fetching helpers
# ---------------------------------------------------------------------------

def _fetch_rss_articles(feed_urls: list[str], limit: int) -> list[dict]:
    """Fetch article metadata from a list of RSS feed URLs.

    Returns deduplicated list of {title, url, published, summary} dicts,
    sorted newest-first.
    """
    seen_urls: set[str] = set()
    articles: list[dict] = []

    for feed_url in feed_urls:
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                print(f"  RSS: 0 entries from {feed_url[:60]}", file=sys.stderr)
                continue
            print(f"  RSS: {len(feed.entries)} entries from {feed_url[:60]}", file=sys.stderr)
        except Exception as e:
            print(f"  RSS error ({feed_url[:60]}): {e}", file=sys.stderr)
            continue

        for entry in feed.entries:
            url = entry.get("link", "").strip()
            if not url or url in seen_urls:
                continue
            # Skip non-article URLs (galleries, videos, photos)
            if any(skip in url for skip in ["/gallery.", "/video.", "/photos.", "/slideshow."]):
                continue

            seen_urls.add(url)
            title = entry.get("title", "").strip()

            # Parse published date
            pub_dt = None
            if entry.get("published"):
                try:
                    pub_dt = parsedate_to_datetime(entry["published"])
                except Exception:
                    pass

            articles.append({
                "title": title,
                "url": url,
                "published": pub_dt,
                "summary": entry.get("summary", ""),
            })

        if len(articles) >= limit * 3:
            break  # Enough candidates

    # Sort by date — newest first
    articles.sort(
        key=lambda x: x["published"] if x["published"] else datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return articles


def _extract_article_text(url: str) -> str:
    """Extract full article text using newspaper4k.

    Falls back to empty string if newspaper4k fails.
    """
    try:
        a = Article(url, fetch_images=False, request_timeout=10)
        a.download()
        a.parse()
        text = a.text.strip()
        if len(text) > 100:
            return text
    except ArticleException as e:
        print(f"  newspaper skip ({url[:60]}): {e}", file=sys.stderr)
    except Exception as e:
        print(f"  newspaper error ({url[:60]}): {type(e).__name__}", file=sys.stderr)
    return ""


def _keyword_matches(article: dict, sub_genre: str | None) -> bool:
    """Return True if the article title/summary contains any sub-genre keyword."""
    if not sub_genre:
        return True
    keywords = [k.strip().lower() for k in sub_genre.replace(",", " ").split()]
    text = (article["title"] + " " + article["summary"]).lower()
    return any(kw in text for kw in keywords)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _google_news_search_url(query: str) -> str:
    """Build a Google News RSS search URL for any query."""
    from urllib.parse import quote
    return f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"


def _is_google_news_url(url: str) -> bool:
    """Return True if this is an encoded Google News redirect URL (not scrapable)."""
    return "news.google.com" in url


def research(topic: str, num_results: int = 5,
             sub_genre: str | None = None) -> dict:
    """Research a topic by fetching and scraping recent news articles.

    Feed resolution priority:
    1. SUBTOPIC_RSS_FEEDS[sub_genre]  — dedicated high-quality feeds (125 sub-topics)
    2. Google News search RSS         — dynamic fallback for any sub-topic not in (1)
    3. TOPIC_RSS_FEEDS[topic]         — parent feed used when no sub-topic given

    For (2), Google News article URLs are encoded and cannot be scraped.
    The RSS title + summary snippet is used directly (150-300 chars each).
    Five such snippets give Gemini enough context for a quality newsletter.

    Returns:
        Dict with topic, timestamp, and sources[] — same schema as the
        original Firecrawl implementation.
    """
    research_query = f"{topic} {sub_genre} news last 24 hours" if sub_genre else f"{topic} news last 24 hours"
    print(f"\nResearching: {research_query}", file=sys.stderr)

    if sub_genre and sub_genre in SUBTOPIC_RSS_FEEDS:
        # ── Priority 1: dedicated feeds (full article text via newspaper4k) ──
        feed_urls = SUBTOPIC_RSS_FEEDS[sub_genre]
        print(f"  Mode: dedicated feeds for '{sub_genre}'", file=sys.stderr)
        use_google_news_fallback = False

    elif sub_genre:
        # ── Priority 2: Google News search RSS (snippets, no scraping) ──────
        search_query = f"{topic} {sub_genre}"
        feed_urls = [_google_news_search_url(search_query)]
        print(f"  Mode: Google News search for '{search_query}'", file=sys.stderr)
        use_google_news_fallback = True

    else:
        # ── Priority 3: parent topic feeds ───────────────────────────────────
        normalised = topic.strip().title()
        feed_urls = (
            TOPIC_RSS_FEEDS.get(topic.strip())
            or TOPIC_RSS_FEEDS.get(normalised)
            or TOPIC_RSS_FEEDS["_default"]
        )
        use_google_news_fallback = False

    # Collect candidate articles from RSS
    candidates = _fetch_rss_articles(feed_urls, limit=num_results)

    # For dedicated feeds with a sub-genre: apply keyword filter for precision.
    # If no keyword matches, fall back to Google News search (more targeted than
    # serving unrelated articles from the parent feed).
    if sub_genre and not use_google_news_fallback:
        filtered = [a for a in candidates if _keyword_matches(a, sub_genre)]
        if filtered:
            candidates = filtered
            print(f"  Keyword filter '{sub_genre}': {len(candidates)} matches", file=sys.stderr)
        else:
            print(f"  No keyword matches in dedicated feeds, switching to Google News search", file=sys.stderr)
            gn_url = _google_news_search_url(f"{topic} {sub_genre}")
            candidates = _fetch_rss_articles([gn_url], limit=num_results)
            use_google_news_fallback = True  # switch to snippet mode

    # Scrape full text for top candidates
    sources = []
    tried = 0
    for article in candidates:
        if len(sources) >= num_results:
            break
        tried += 1
        if tried > num_results * 3:
            break  # Don't hammer too many sites

        print(f"  Processing [{tried}]: {article['title'][:60]}...", file=sys.stderr)

        if use_google_news_fallback or _is_google_news_url(article["url"]):
            # Google News URLs cannot be scraped (encoded redirects).
            # Use the RSS title + summary snippet directly.
            snippet = article.get("summary", "").strip()
            # Strip any HTML tags from the snippet
            import re as _re
            snippet = _re.sub(r"<[^>]+>", "", snippet).strip()
            text = f"{article['title']}\n\n{snippet}" if snippet else article["title"]
            if text:
                print(f"    → Google News snippet ({len(text)} chars)", file=sys.stderr)
            else:
                print(f"    → skipped (no content)", file=sys.stderr)
                continue
        else:
            text = _extract_article_text(article["url"])
            if not text and article.get("summary"):
                # Use RSS snippet as fallback
                text = f"{article['title']}\n\n{article['summary']}"
                print(f"    → RSS snippet fallback ({len(text)} chars)", file=sys.stderr)
            elif not text:
                print(f"    → skipped (no content)", file=sys.stderr)
                continue

        print(f"    → {len(text)} chars", file=sys.stderr)

        # Cap to avoid token overflow
        if len(text) > 4000:
            text = text[:4000] + "\n\n... [truncated]"

        sources.append({
            "url": article["url"],
            "title": article["title"],
            "markdown": text,
        })

    if not sources:
        print(f"ERROR: No sources collected for topic: {topic}", file=sys.stderr)
        sys.exit(1)

    print(f"\n✓ Collected {len(sources)} sources for: {research_query}", file=sys.stderr)

    return {
        "topic": research_query,
        "searched_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Research a topic via RSS + newspaper4k")
    parser.add_argument("--topic", required=True, help="Topic (e.g. 'AI & Technology', 'Sports')")
    parser.add_argument("--sub-genre", default=None, help="Sub-topic (e.g. 'Cricket', 'Telugu Cinema')")
    parser.add_argument("--num-results", type=int, default=5, help="Number of articles")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path")
    parser.add_argument("--list-topics", action="store_true", help="Print all topics and sub-topics")
    args = parser.parse_args()

    if args.list_topics:
        for topic, subtopics in TOPICS_CONFIG.items():
            print(f"\n{topic}:")
            for st in subtopics:
                marker = "✓" if st in SUBTOPIC_RSS_FEEDS else "○"
                print(f"  {marker} {st}")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)

    result = research(args.topic, args.num_results, args.sub_genre)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Output written to {args.output}", file=sys.stderr)
    print(str(args.output))


if __name__ == "__main__":
    main()
