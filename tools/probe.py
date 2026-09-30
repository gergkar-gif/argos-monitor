"""Probe URLs: print status, and for feeds the item count + newest date. Uses curl (handles gzip and Windows certs)."""
import sys, subprocess, xml.etree.ElementTree as ET, concurrent.futures as cf, email.utils, re
import os, tempfile
UA = "Mozilla/5.0 (compatible; ArgosMonitor/0.1)"  # VOV returns 403 to a Chrome-like UA
JAR = os.path.join(tempfile.gettempdir(), "argos_probe_cookies.txt")  # QDND needs cookies kept
DATE_TAGS = ("pubDate", "{http://www.w3.org/2005/Atom}updated", "{http://purl.org/dc/elements/1.1/}date")
def probe(url):
    p = subprocess.run(["curl", "-sL", "-m", "30", "--compressed", "-A", UA, "-c", JAR, "-b", JAR,
                        "-w", "\n%{http_code}|%{content_type}|%{url_effective}", url], capture_output=True)
    if p.returncode != 0:
        return url, f"ERR curl exit {p.returncode}"
    body, _, tail = p.stdout.rpartition(b"\n")
    code, ct, final = tail.decode("utf8", "ignore").split("|", 2)
    if code != "200":
        return url, f"HTTP {code}"
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        links = sorted(set(re.findall(rb'href="([^"]*(?:rss|feed)[^"]*)"', body, re.I)))[:8]
        return url, f"200 {ct[:25]} NOT-XML len={len(body)} rsslinks={[l.decode('utf8','ignore') for l in links]}"
    items = (root.findall(".//item") or root.findall(".//{http://purl.org/rss/1.0/}item")
             or root.findall(".//{http://www.w3.org/2005/Atom}entry"))
    dates = []
    for it in items:
        for tag in DATE_TAGS:
            e = it.find(tag)
            if e is not None and e.text:
                try: dates.append(email.utils.parsedate_to_datetime(e.text).isoformat()[:10])
                except Exception: dates.append(e.text.strip()[:10])
                break
    return url, f"200 feed items={len(items)} newest={max(dates) if dates else '?'}" + (f" ->{final}" if final != url else "")
if __name__ == "__main__":
    urls = [l.strip() for l in open(sys.argv[1], encoding="utf8") if l.strip() and not l.startswith("#")]
    with cf.ThreadPoolExecutor(8) as ex:
        for u, res in ex.map(probe, urls): print(u, "|", res)
