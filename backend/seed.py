"""
Run inside the backend container:
  docker exec vibe-backend python seed.py
"""
import asyncio
import os
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

MONGODB_URI = os.environ["MONGODB_URI"]
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

GENRE_POOLS = [
    ["indie rock", "shoegaze", "dream pop", "lo-fi"],
    ["hip hop", "trap", "r&b", "soul"],
    ["pop", "synth-pop", "electropop", "dance pop"],
    ["jazz", "neo-soul", "funk", "soul"],
    ["folk", "americana", "singer-songwriter", "indie folk"],
    ["electronic", "ambient", "techno", "house"],
    ["punk", "post-punk", "hardcore", "emo"],
    ["classical", "chamber music", "orchestral", "baroque"],
    ["metal", "heavy metal", "doom metal", "post-metal"],
    ["reggae", "dancehall", "afrobeats", "latin"],
]

ARTIST_POOLS = [
    [{"id": "a1", "name": "Phoebe Bridgers"}, {"id": "a2", "name": "Big Thief"}, {"id": "a3", "name": "boygenius"}],
    [{"id": "b1", "name": "Kendrick Lamar"}, {"id": "b2", "name": "Frank Ocean"}, {"id": "b3", "name": "SZA"}],
    [{"id": "c1", "name": "Charli XCX"}, {"id": "c2", "name": "Dua Lipa"}, {"id": "c3", "name": "Carly Rae Jepsen"}],
    [{"id": "d1", "name": "Thundercat"}, {"id": "d2", "name": "Hiatus Kaiyote"}, {"id": "d3", "name": "Alfa Mist"}],
    [{"id": "e1", "name": "The Mountain Goats"}, {"id": "e2", "name": "Sufjan Stevens"}, {"id": "e3", "name": "Bon Iver"}],
    [{"id": "f1", "name": "Four Tet"}, {"id": "f2", "name": "Burial"}, {"id": "f3", "name": "Aphex Twin"}],
    [{"id": "g1", "name": "Idles"}, {"id": "g2", "name": "Shame"}, {"id": "g3", "name": "Fontaines D.C."}],
    [{"id": "h1", "name": "Beethoven"}, {"id": "h2", "name": "Bach"}, {"id": "h3", "name": "Chopin"}],
    [{"id": "i1", "name": "Sleep"}, {"id": "i2", "name": "Pallbearer"}, {"id": "i3", "name": "Bell Witch"}],
    [{"id": "j1", "name": "Burna Boy"}, {"id": "j2", "name": "Bad Bunny"}, {"id": "j3", "name": "Wizkid"}],
]

CITIES = ["New York", "Brooklyn", "Queens", "Manhattan", "Bronx"]
BIOS = [
    "Always at a show.", "Vinyl collector.", "Music is life.",
    "Know every lyric.", "Crate digger.", "Living for the bass drop.",
    "Concerts over everything.", "Headphones on, world off.",
    "Every genre, every mood.", "Let the music speak.",
]


async def main():
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client["vibe"]
    users = db["users"]

    password_hash = pwd_ctx.hash("12345678")
    now = datetime.now(timezone.utc)

    created = 0
    for i in range(1, 101):
        email = f"admin{i}@nyu.edu"
        existing = await users.find_one({"email": email})
        if existing:
            continue

        pool = (i - 1) % 10
        doc = {
            "email": email,
            "password_hash": password_hash,
            "display_name": f"Demo User {i}",
            "age": 20 + (i % 10),
            "city": CITIES[i % len(CITIES)],
            "bio": BIOS[i % len(BIOS)],
            "gender": "non-binary",
            "gender_preference": "any",
            "age_range_preference": {"min": 18, "max": 99},
            "photo_url": None,
            "contact_info": {"phone": None, "instagram": None},
            "is_spotify_connected": True,
            "spotify": {
                "top_genres": GENRE_POOLS[pool],
                "top_artists": ARTIST_POOLS[pool],
                "audio_features": {
                    "energy": 0.4 + (i % 5) * 0.1,
                    "valence": 0.3 + (i % 7) * 0.1,
                    "danceability": 0.5 + (i % 4) * 0.1,
                    "tempo": 100 + (i % 10) * 10,
                },
                "last_synced": now,
            },
            "likes_sent_today": 0,
            "likes_reset_at": now,
            "created_at": now,
            "updated_at": now,
        }
        await users.insert_one(doc)
        created += 1

    print(f"Seeded {created} users (skipped {100 - created} already existing).")
    client.close()


asyncio.run(main())
