from __future__ import annotations

SAMPLE_TRACK = {
    "id": "878dadea-33c5-4c08-bdb9-e2b117475a99",
    "trackTitle": "All Too Well",
    "artists": [
        {
            "id": "c7b330b5-a62e-420c-bf02-943ca6bb8746",
            "name": "Taylor Swift",
            "href": "https://open.spotify.com/artist/06HL4z0CvFAxyc27GXpf02",
        }
    ],
    "durationMs": 329160,
    "isrc": "USCJY1231021",
    "href": "https://open.spotify.com/track/00vJzaoxM3Eja1doBUhX0P",
}

SAMPLE_FEATURES = {
    "acousticness": 0.12,
    "danceability": 0.55,
    "energy": 0.72,
    "instrumentalness": 0.0,
    "key": 0,
    "liveness": 0.11,
    "loudness": -5.2,
    "mode": 1,
    "speechiness": 0.04,
    "tempo": 93.5,
    "valence": 0.48,
    "timeSignature": 4,
    "durationMs": 329160,
}

SPOTIFY_TRACK_ID = "00vJzaoxM3Eja1doBUhX0P"
RECCOBEATS_TRACK_ID = SAMPLE_TRACK["id"]

SPOTIFY_TRACK_ID_2 = "11wKzaoxM3Eja1doBUhX0Q"


def _batch_item(track: dict, features: dict) -> dict:
    merged = {**track, **features}
    merged["id"] = track["id"]
    merged["trackTitle"] = track.get("trackTitle")
    merged["href"] = track.get("href")
    merged["isrc"] = track.get("isrc")
    return merged


SAMPLE_BATCH_FEATURES = {
    "content": [
        _batch_item(SAMPLE_TRACK, SAMPLE_FEATURES),
    ]
}


def batch_response_for_spotify_ids(spotify_ids: list[str]) -> dict:
    items = []
    for sid in spotify_ids:
        track = {**SAMPLE_TRACK, "href": f"https://open.spotify.com/track/{sid}"}
        items.append(_batch_item(track, SAMPLE_FEATURES))
    return {"content": items}
