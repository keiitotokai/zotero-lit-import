import json
import urllib.request
import urllib.parse

ZOTERO_API_BASE = "https://api.zotero.org"
ZOTERO_API_VERSION = "3"


def zget(api_key, path):
    """GET a Zotero API path, return parsed JSON."""
    req = urllib.request.Request(
        ZOTERO_API_BASE + path,
        headers={"Zotero-API-Key": api_key, "Zotero-API-Version": ZOTERO_API_VERSION})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def zpost(api_key, path, payload):
    """POST JSON to a Zotero API path, return (parsed_json, status)."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        ZOTERO_API_BASE + path, data=data, method="POST",
        headers={"Zotero-API-Key": api_key, "Zotero-API-Version": ZOTERO_API_VERSION,
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read()), r.status


def get_zotero_auth(credential_name=None):
    """Resolve Zotero API key + numeric userID from a Claude Science credential.

    Reads the API key from the named credential (default "ZOTERO"), then
    calls the Zotero API to resolve userID and access scopes.
    Returns {"api_key", "user_id", "access"}.
    Requires api.zotero.org on the network allowlist.
    """
    if credential_name is None:
        credential_name = "ZOTERO"
    d = host.credentials.get(credential_name)
    key = d.get("value") or d.get("token")
    if not key:
        raise RuntimeError("no API key found in credential %r" % credential_name)
    info = zget(key, "/keys/%s" % key)
    return {"api_key": key, "user_id": info.get("userID"),
            "access": info.get("access", {})}


def list_zotero_collections(auth):
    """Return the user's collections as dicts with key / name / parent.
    `auth` is the dict from get_zotero_auth()."""
    cols = zget(auth["api_key"], "/users/%s/collections?limit=100" % auth["user_id"])
    out = []
    for c in cols:
        dd = c["data"]
        out.append({"key": dd["key"], "name": dd["name"],
                    "parent": dd.get("parentCollection") or None})
    return out


def create_zotero_collection(auth, name, parent_key=None):
    """Create a collection (top-level if parent_key is None). Returns its key."""
    payload = [{"name": name, "parentCollection": parent_key if parent_key else False}]
    resp, st = zpost(auth["api_key"], "/users/%s/collections" % auth["user_id"], payload)
    if resp.get("failed"):
        raise RuntimeError("collection create failed: %s" % json.dumps(resp["failed"]))
    return resp["successful"]["0"]["data"]["key"]


def crossref_record(doi, email=None):
    """Fetch a normalized bibliography dict from CrossRef for one DOI.
    Returns authors/title/journal/volume/issue/pages/year/doi/type/retracted.
    Requires api.crossref.org on the allowlist."""
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    if email:
        url += "?mailto=" + urllib.parse.quote(email)
    req = urllib.request.Request(url, headers={"User-Agent": "python-urllib"})
    with urllib.request.urlopen(req, timeout=30) as r:
        m = json.loads(r.read())["message"]
    issued = m.get("issued", {}).get("date-parts", [[None]])[0]
    return {
        "authors": ["%s, %s" % (a.get("family", ""), a.get("given", ""))
                    for a in m.get("author", [])],
        "title": (m.get("title") or [""])[0],
        "journal": (m.get("container-title") or [""])[0],
        "volume": m.get("volume", ""), "issue": m.get("issue", ""),
        "pages": m.get("page", ""), "year": issued[0] if issued else None,
        "doi": doi, "type": m.get("type"),
        "retracted": any(u.get("type") == "retraction"
                         for u in (m.get("update-to") or [])),
    }


def bib_to_zotero_items(records, collection_key=None, extra_tags=None):
    """Convert normalized bibliography dicts into Zotero journalArticle payloads.

    Each record may contain: authors (list of "Last, First"), title, journal,
    volume, issue, pages, year, doi, pmid. Returns item dicts for post_zotero_items.
    """
    if extra_tags is None:
        extra_tags = []
    items = []
    for r in records:
        creators = []
        for a in r.get("authors", []):
            parts = [x.strip() for x in a.split(",", 1)]
            last = parts[0]; first = parts[1] if len(parts) > 1 else ""
            if last:
                creators.append({"creatorType": "author",
                                 "firstName": first, "lastName": last})
        item = {
            "itemType": "journalArticle",
            "title": r.get("title", ""),
            "creators": creators,
            "publicationTitle": r.get("journal", ""),
            "volume": str(r.get("volume") or ""),
            "issue": str(r.get("issue") or ""),
            "pages": r.get("pages") or "",
            "date": str(r.get("year") or ""),
            "DOI": r.get("doi", ""),
            "url": ("https://doi.org/%s" % r["doi"]) if r.get("doi") else "",
            "extra": ("PMID: %s" % r["pmid"]) if r.get("pmid") else "",
            "tags": [{"tag": t} for t in extra_tags],
        }
        if collection_key:
            item["collections"] = [collection_key]
        items.append(item)
    return items


def post_zotero_items(auth, items):
    """POST item payloads to the library (chunks at 50/request).
    Returns {"successful", "failed", "failures"}."""
    key = auth["api_key"]; uid = auth["user_id"]
    ok = 0; failed = 0; failures = []
    for i in range(0, len(items), 50):
        resp, st = zpost(key, "/users/%s/items" % uid, items[i:i + 50])
        ok += len(resp.get("successful", {}))
        failed += len(resp.get("failed", {}))
        if resp.get("failed"):
            failures.append(resp["failed"])
    return {"successful": ok, "failed": failed, "failures": failures}
